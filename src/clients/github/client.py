"""GitHub client module: list files and read file contents with simple caching and throttling.

This module provides a small, dependency-light async client focused on two
operations used by the server: listing repository files (Git Trees API)
and reading file contents (Contents API). It relies on `core.cache.TTLCache`
for short-term caching and `core.rate_limiter.RateLimiter` to honor
explicit server-side throttling signals.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Tuple

import httpx

from core.cache import TTLCache
from core.errors import ExternalServiceError, NotFoundError
from core.rate_limiter import RateLimiter
from core.pacing import Pacer

from .inputs import parse_repo_url, normalize_max_chars, normalize_path, normalize_ref
from .refs import resolve_tree_sha


@dataclass(frozen=True, slots=True)
class _ListCacheKey:
    # Cache key grouping for tree listings: repo URL + ref + recursion flag
    repo_url: str
    ref: str
    recursive: bool


@dataclass(frozen=True, slots=True)
class _ReadCacheKey:
    # Cache key for file reads: includes max_chars to support truncated variants
    repo_url: str
    ref: str
    path: str
    max_chars: int


class GitHubClient:
    """Async GitHub client for listing and reading repository files.

    Purpose:
      - list_files_from_url(repo_url, ref='main', recursive=True) -> List[str]
      - read_text_file_from_url(repo_url, path, ref='main', max_chars=200_000) -> str

    Key behavior:
      - Uses TTL caches for tree and file results.
      - Limits concurrency (Semaphore) and uses a pacer for simple client-side pacing.
      - Honors server-side throttling (Retry-After, rate-limit reset) via RateLimiter.
    """

    BASE_URL = "https://api.github.com"
    JSON_ACCEPT = "application/vnd.github+json"
    RAW_ACCEPT = "application/vnd.github.raw"

    _MAX_RATE_LIMIT_RETRIES = 2  # total attempts = 1 + retries

    def __init__(
        self,
        *,
        timeout: float = 20.0,
        verify: bool = False,
        max_concurrency: int = 5,
        rate_per_sec: float = 2.0,
        cache_ttl_seconds: float = 60.0,
        cache_maxsize: int = 256,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self._timeout = float(timeout)
        self._verify = bool(verify)

        self._headers = self._build_headers()

        self._sem = asyncio.Semaphore(max(1, int(max_concurrency)))
        self._pacer = Pacer(rate_per_sec=rate_per_sec)
        self._rate_limiter = rate_limiter or RateLimiter()

        ttl = float(cache_ttl_seconds)
        maxsize = max(1, int(cache_maxsize))
        self._list_cache: TTLCache[List[str]] = TTLCache(ttl_seconds=ttl, maxsize=maxsize)
        self._read_cache: TTLCache[str] = TTLCache(ttl_seconds=ttl, maxsize=maxsize)

    async def list_files_from_url(
        self,
        *,
        repo_url: str,
        ref: str = "main",
        recursive: bool = True,
    ) -> List[str]:
        """List repository file paths at `ref` (sorted, stable)."""
        owner, repo = parse_repo_url(repo_url)
        ref_clean = normalize_ref(ref)

        # Build and check a cache key before making network calls
        cache_key = _ListCacheKey(repo_url=repo_url.strip(), ref=ref_clean, recursive=bool(recursive))
        cached = self._list_cache.get(cache_key)
        if cached is not None:
            return list(cached)

        async with self._create_client() as client:
            # Resolve the ref to a tree SHA; this may fall back to default branch
            tree_sha = await resolve_tree_sha(
                self._request,
                client,
                owner=owner,
                repo=repo,
                ref=ref_clean,
            )
            # Git Trees API expects recursive=1 to list nested files
            params = {"recursive": "1"} if recursive else None

            resp = await self._request(
                client,
                f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
                params=params,
            )
            if resp.status_code == 404:
                raise NotFoundError(f"Tree not found for ref: {ref_clean}")

            self._raise_for_status(resp, context="list_files_from_url(tree)")
            tree = resp.json().get("tree", [])
            paths = [
                item["path"]
                for item in tree
                if item.get("type") == "blob" and isinstance(item.get("path"), str)
            ]

            out = sorted(paths)
            # Cache the sorted result for short-term reuse
            self._list_cache.set(cache_key, out)
            return out

    async def read_text_file_from_url(
        self,
        *,
        repo_url: str,
        path: str,
        ref: str = "main",
        max_chars: int = 200_000,
    ) -> str:
        """Read a file from GitHub at `ref`, decode as text, and optionally truncate."""
        owner, repo = parse_repo_url(repo_url)
        ref_clean = normalize_ref(ref)
        path_clean = normalize_path(path)
        max_chars_clean = normalize_max_chars(max_chars)

        cache_key = _ReadCacheKey(
            repo_url=repo_url.strip(),
            ref=ref_clean,
            path=path_clean,
            max_chars=max_chars_clean,
        )
        # Return cached text if present to avoid repeated network IO
        cached = self._read_cache.get(cache_key)
        if cached is not None:
            return cached

        # Request raw file bytes so httpx decodes to text reliably
        async with self._create_client(custom_headers={"Accept": self.RAW_ACCEPT}) as client:
            resp = await self._request(
                client,
                f"/repos/{owner}/{repo}/contents/{path_clean}",
                params={"ref": ref_clean},
            )

            if resp.status_code == 404:
                raise NotFoundError(f"File not found: {path_clean}")

            self._raise_for_status(resp, context="read_text_file_from_url(contents)")
            # Use response.text (httpx) which handles decoding; truncate if needed
            text = resp.text or ""
            if len(text) > max_chars_clean:
                text = text[:max_chars_clean]
            self._read_cache.set(cache_key, text)
            return text

    # --- HTTP helpers ---

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": self.JSON_ACCEPT,
            "User-Agent": "mermaid-mcp-server",
        }
        # If GITHUB_TOKEN present, add Authorization for higher rate limits
        token = (os.environ.get("GITHUB_TOKEN") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _create_client(self, custom_headers: Optional[Mapping[str, str]] = None) -> httpx.AsyncClient:
        headers = {**self._headers, **dict(custom_headers or {})}
        return httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=self._timeout,
            verify=self._verify,
        )

    def _external(self, context: str, err: BaseException) -> ExternalServiceError:
        return ExternalServiceError(f"GitHub request failed ({context}): {err}")

    def _raise_for_status(self, resp: httpx.Response, *, context: str) -> None:
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise self._external(context, e) from e

    async def _request(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
    ) -> httpx.Response:
        """GET with pacing + concurrency + bounded retries for explicit throttling signals."""
        attempts = self._MAX_RATE_LIMIT_RETRIES + 1

        for attempt in range(attempts):
            # Client-side pacing to avoid sending bursts of requests
            await self._pacer.wait()

            try:
                # Limit concurrent requests across tasks
                async with self._sem:
                    resp = await client.get(url, params=dict(params or {}))
            except httpx.HTTPError as e:
                raise self._external(f"GET {url}", e) from e

            if attempt < attempts - 1:
                # If server indicates throttling, sleep via RateLimiter then retry
                should_retry = await self._rate_limiter.maybe_sleep_and_retry(resp)
                if should_retry:
                    continue

            return resp

        raise RuntimeError("Unreachable: _request did not return a response")

