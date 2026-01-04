"""Immutable dataclasses for request models used by the MCP tools.

Includes models describing file-source selection and read/list
requests (SourceRequest, ReadRequest) to keep the tool APIs explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


SourceType = Literal["local", "github"]


@dataclass(frozen=True)
class SourceRequest:
    """Request model for listing files from a source.

    Field groups:
    - Common: source
    - Local: root, glob
    - GitHub: repo_url, ref
    - Shared: recursive
    """

    source: SourceType

    root: str = "."
    glob: str = "**/*"

    repo_url: Optional[str] = None
    ref: str = "main"

    recursive: bool = True


@dataclass(frozen=True)
class ReadRequest:
    """Request model for reading a file from a source.

    Field groups:
    - Common: source, path
    - GitHub: repo_url, ref
    - Shared: max_chars
    """

    source: SourceType
    path: str

    repo_url: Optional[str] = None
    ref: str = "main"

    max_chars: int = 200_000
