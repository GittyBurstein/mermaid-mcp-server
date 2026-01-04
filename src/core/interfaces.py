"""Core protocol and interface definitions.

Defines the FileSource protocol used by the tools and source
implementations (local/GitHub) to provide a uniform API.
"""

from __future__ import annotations

from typing import List, Protocol


class FileSource(Protocol):
    """Contract for any file source (local, GitHub, etc.)."""
    async def list_files(
        self,
        *,
        root: str = ".",
        glob: str = "**/*",
        recursive: bool = True,
    ) -> List[str]:
        ...

    async def read_file(
        self,
        *,
        path: str,
        max_chars: int,
    ) -> str:
        ...
