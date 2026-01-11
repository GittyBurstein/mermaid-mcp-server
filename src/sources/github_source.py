from __future__ import annotations

import fnmatch
from typing import List

from clients.github import GitHubClient
from core.errors import ValidationError


"""GitHub-backed FileSource implementation.

Wraps the GitHubClient to provide a FileSource-compatible API for
listing and reading repository files while applying root/glob filtering.
"""


class GitHubSource:
    # GitHub implementation of FileSource (wraps GitHubClient).

    def __init__(self, *, client: GitHubClient, repo_url: str, ref: str = "main") -> None:
        self._client = client
        self._repo_url = (repo_url or "").strip()
        self._ref = (ref or "main").strip()

        if not self._repo_url:
            raise ValidationError("Missing repo_url")

    async def list_files(self, *, root: str = ".", glob: str = "**/*", recursive: bool = True) -> List[str]:
        # Fetch all files from the repository via the client
        all_files = await self._client.list_files_from_url(
            repo_url=self._repo_url, 
            ref=self._ref, 
            recursive=recursive
        )

        # Normalize root path for comparison (strip leading/trailing separators)
        clean_root = root.strip("./").strip("/")
        
        filtered_files: List[str] = []
        
        for path in all_files:
            # 1. Check if the file is within the requested root directory
            if clean_root and not (path == clean_root or path.startswith(clean_root + "/")):
                continue
            
            # 2. Check if the file matches the glob pattern
            # Note: fnmatch handles standard glob patterns like *.py or **/*.md
            if fnmatch.fnmatch(path, glob):
                filtered_files.append(path)

        return sorted(filtered_files)

    async def read_file(self, *, path: str, max_chars: int) -> str:
        # Implementation remains consistent with the client call
        return await self._client.read_text_file_from_url(
            repo_url=self._repo_url,
            path=path,
            ref=self._ref,
            max_chars=max_chars,
        )