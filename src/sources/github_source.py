from __future__ import annotations

import fnmatch
from typing import List, Tuple

from clients.github import GitHubClient
from core.errors import ValidationError


"""GitHub-backed FileSource implementation.

- `root` filters by directory prefix inside the repo.
- `glob` is matched relative to `root` (consistent with LocalSource behavior).
"""


def _clean_root(root: str) -> str:
    # Normalize root to POSIX and treat '.', './', '/' as repository root
    r = (root or "").strip().replace("\\", "/")
    if r in ("", ".", "./", "/"):
        return ""
    while r.startswith("./"):
        r = r[2:]
    return r.strip("/")


def _split_posix(p: str) -> Tuple[str, ...]:
    # Split a POSIX path into non-empty segments
    p = (p or "").strip().replace("\\", "/").strip("/")
    if not p:
        return tuple()
    return tuple(seg for seg in p.split("/") if seg)


def _glob_match(rel_path: str, pattern: str) -> bool:
    # Component-wise glob matcher with '**' support
    parts = _split_posix(rel_path)
    pat = (pattern or "").strip().replace("\\", "/").strip("/")
    if not pat:
        pat = "**/*"
    pats = _split_posix(pat)

    def rec(i: int, j: int) -> bool:
        if j == len(pats):
            return i == len(parts)

        token = pats[j]
        if token == "**":
            return rec(i, j + 1) or (i < len(parts) and rec(i + 1, j))

        return i < len(parts) and fnmatch.fnmatchcase(parts[i], token) and rec(i + 1, j + 1)

    return rec(0, 0)


class GitHubSource:
    def __init__(self, *, client: GitHubClient, repo_url: str, ref: str = "main") -> None:
        self._client = client
        self._repo_url = (repo_url or "").strip()
        self._ref = (ref or "main").strip()

        if not self._repo_url:
            raise ValidationError("Missing repo_url")

    async def list_files(self, *, root: str = ".", glob: str = "**/*", recursive: bool = True) -> List[str]:
        all_files = await self._client.list_files_from_url(
            repo_url=self._repo_url,
            ref=self._ref,
            recursive=recursive,
        )

        clean_root = _clean_root(root)
        clean_glob = (glob or "").strip()

        out: List[str] = []

        for raw in all_files:
            # Normalize returned path to POSIX and remove leading markers
            path = (raw or "").strip().replace("\\", "/").lstrip("/")
            while path.startswith("./"):
                path = path[2:]
            if not path:
                continue

            # If a root was requested ensure the path is inside it
            if clean_root:
                if not (path == clean_root or path.startswith(clean_root + "/")):
                    continue
                if path == clean_root:
                    continue
                rel_path = path[len(clean_root) + 1 :]
            else:
                rel_path = path

            # Match glob relative to root
            if _glob_match(rel_path, clean_glob):
                out.append(path)

        return sorted(out)

    async def read_file(self, *, path: str, max_chars: int) -> str:
        # Normalize and validate read path
        p = (path or "").strip().replace("\\", "/").lstrip("/")
        while p.startswith("./"):
            p = p[2:]
        if not p:
            raise ValidationError("Missing path")

        return await self._client.read_text_file_from_url(
            repo_url=self._repo_url,
            path=p,
            ref=self._ref,
            max_chars=max_chars,
        )
