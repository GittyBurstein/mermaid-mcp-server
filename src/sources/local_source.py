from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List

from core.errors import AccessDeniedError, NotFoundError, ValidationError


class LocalSource:
    # Local filesystem implementation of FileSource.

    def __init__(self, *, project_root: Path) -> None:
        self._project_root = project_root.resolve()

    def _resolve_under_root(self, rel_path: str) -> Path:
        raw = (rel_path or "").strip()
        if not raw:
            raise ValidationError("Path is empty")

        p = (self._project_root / raw).resolve()

        # Strong containment check
        try:
            p.relative_to(self._project_root)
        except ValueError as e:
            raise AccessDeniedError("Access outside project root is not allowed") from e

        return p

    async def list_files(self, *, root: str = ".", glob: str = "**/*", recursive: bool = True) -> List[str]:
        # Path.glob("**/*") is recursive by design; we keep 'recursive' for a uniform API.
        base = self._resolve_under_root(root)

        def _do() -> List[str]:
            if not base.exists() or not base.is_dir():
                raise NotFoundError(f"Not a directory: {root}")

            out: List[str] = []
            for p in base.glob(glob):
                if p.is_file():
                   out.append(p.relative_to(base).as_posix())
            return sorted(out)

        return await asyncio.to_thread(_do)

    async def read_file(self, *, path: str, max_chars: int) -> str:
        p = self._resolve_under_root(path)

        def _do() -> str:
            if not p.exists():
                raise NotFoundError(f"File not found: {path}")
            if not p.is_file():
                raise ValidationError(f"Not a file: {path}")

            data = p.read_text(encoding="utf-8", errors="replace")
            if len(data) > max_chars:
                return data[:max_chars] + "\n\n...[TRUNCATED]..."
            return data

        return await asyncio.to_thread(_do)
