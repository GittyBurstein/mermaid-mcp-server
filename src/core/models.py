from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


SourceType = Literal["local", "github"]


@dataclass(frozen=True)
class SourceRequest:
    # Common
    source: SourceType

    # Local
    root: str = "."
    glob: str = "**/*"

    # GitHub
    repo_url: Optional[str] = None
    ref: str = "main"

    # Shared
    recursive: bool = True


@dataclass(frozen=True)
class ReadRequest:
    source: SourceType
    path: str

    # GitHub
    repo_url: Optional[str] = None
    ref: str = "main"

    # Shared
    max_chars: int = 200_000
