from __future__ import annotations

from typing import List

from clients.github import GitHubClient
from core.errors import ValidationError
from core.paths import clean_root, glob_match, normalize_posix_relpath


"""GitHub-backed FileSource implementation.

- `root` filters by directory prefix inside the repo.
- `glob` is matched relative to `root` (consistent with LocalSource behavior).
"""


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

        clean_root_val = clean_root(root)
        clean_glob = (glob or "").strip()

        out: List[str] = []

        for raw in all_files:
            # Normalize returned path to a clean POSIX-style relative path.
            path = normalize_posix_relpath(raw)
            if not path:
                continue

            # If a root was requested, ensure the path is inside it.
            # Then compute rel_path relative to that root for glob matching.
            if clean_root_val:
                if not (path == clean_root_val or path.startswith(clean_root_val + "/")):
                    continue
                if path == clean_root_val:
                    # Root itself is a directory marker, not a file.
                    continue
                rel_path = path[len(clean_root_val) + 1 :]
            else:
                rel_path = path

            # Match glob relative to root (same semantics as LocalSource).
            if glob_match(rel_path, clean_glob):
                out.append(path)

        return sorted(out)

    async def read_file(self, *, path: str, max_chars: int) -> str:
        # Normalize and validate read path.
        p = normalize_posix_relpath(path)
        if not p:
            raise ValidationError("Missing path")

        return await self._client.read_text_file_from_url(
            repo_url=self._repo_url,
            path=p,
            ref=self._ref,
            max_chars=max_chars,
        )
