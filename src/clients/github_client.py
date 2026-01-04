"""GitHub API client utilities.

This module provides a lightweight async client wrapper around the
GitHub API for listing repository files and reading file contents. It
also includes a small helper to parse GitHub repository URLs.
"""

from __future__ import annotations

import os
import re
import httpx
from typing import List, Optional, Tuple
from core.errors import NotFoundError, ValidationError

# --- Constants & Helpers ---
_REPO_URL_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")

def parse_repo_url(repo_url: str) -> Tuple[str, str]:
    raw = (repo_url or "").strip()
    match = _REPO_URL_RE.match(raw)
    if not match:
        raise ValidationError("Invalid GitHub repository URL")
    return match.group(1), match.group(2)

# --- Main Client ---
class GitHubClient:
    BASE_URL = "https://api.github.com"
    JSON_ACCEPT = "application/vnd.github+json"
    RAW_ACCEPT = "application/vnd.github.raw"

    def __init__(self, *, timeout: float = 20.0, verify: bool = False) -> None:
        self._timeout = timeout
        self._verify = verify
        
        token = os.environ.get("GITHUB_TOKEN")
        self._headers = {"Accept": self.JSON_ACCEPT}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    def _create_client(self, custom_headers: Optional[dict] = None) -> httpx.AsyncClient:
        headers = {**self._headers, **(custom_headers or {})}
        return httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=self._timeout,
            verify=self._verify
        )

    async def list_files_from_url(self, *, repo_url: str, ref: str = "main", recursive: bool = True) -> List[str]:
        owner, repo = parse_repo_url(repo_url)
        
        async with self._create_client() as client:
            tree_sha = await self._resolve_tree_sha(client, owner, repo, ref)
            params = {"recursive": "1"} if recursive else {}
            
            response = await client.get(f"/repos/{owner}/{repo}/git/trees/{tree_sha}", params=params)
            if response.status_code == 404:
                raise NotFoundError(f"Tree not found for ref: {ref}")
            response.raise_for_status()

            tree = response.json().get("tree", [])
            paths = [item["path"] for item in tree if item.get("type") == "blob" and "path" in item]
            return sorted(paths)

    async def read_text_file_from_url(
        self, 
        *, 
        repo_url: str, 
        path: str, 
        ref: str = "main", 
        max_chars: int = 200_000
    ) -> str:
        owner, repo = parse_repo_url(repo_url)
        clean_path = (path or "").lstrip("/").strip()
        if not clean_path:
            raise ValidationError("File path is required")

        async with self._create_client(custom_headers={"Accept": self.RAW_ACCEPT}) as client:
            response = await client.get(
                f"/repos/{owner}/{repo}/contents/{clean_path}",
                params={"ref": ref}
            )
            
            if response.status_code == 404:
                raise NotFoundError(f"File '{clean_path}' not found")
            response.raise_for_status()

            content = response.content.decode("utf-8", errors="replace")
            if len(content) > max_chars:
                return content[:max_chars] + "\n\n...[TRUNCATED]..."
            return content

    # --- Internal Resolution Logic ---
    async def _resolve_tree_sha(self, client: httpx.AsyncClient, owner: str, repo: str, ref: str) -> str:
        sha = await self._fetch_tree_sha(client, owner, repo, ref)
        if sha:
            return sha

        # Fallback to default branch if the provided ref fails
        repo_resp = await client.get(f"/repos/{owner}/{repo}")
        if repo_resp.status_code == 404:
            raise NotFoundError("Repository not found")
        repo_resp.raise_for_status()
        
        default_branch = repo_resp.json().get("default_branch")
        if default_branch and default_branch != ref:
            sha = await self._fetch_tree_sha(client, owner, repo, default_branch)
            if sha:
                return sha

        raise NotFoundError(f"Unable to resolve reference: {ref}")

    async def _fetch_tree_sha(self, client: httpx.AsyncClient, owner: str, repo: str, ref: str) -> Optional[str]:
        try:
            resp = await client.get(f"/repos/{owner}/{repo}/commits/{ref}")
            if resp.status_code in (404, 422):
                return None
            resp.raise_for_status()
            return resp.json()["commit"]["tree"]["sha"]
        except (httpx.HTTPError, KeyError):
            return None