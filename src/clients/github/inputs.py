from __future__ import annotations

import re
from typing import Tuple

from core.errors import ValidationError


_REPO_URL_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


def parse_repo_url(repo_url: str) -> Tuple[str, str]:
    raw = (repo_url or "").strip()
    m = _REPO_URL_RE.match(raw)
    if not m:
        raise ValidationError("Invalid GitHub repository URL")
    return m.group(1), m.group(2)


def normalize_ref(ref: str) -> str:
    ref_clean = (ref or "main").strip()
    if not ref_clean:
        raise ValidationError("ref must be non-empty")
    return ref_clean


def normalize_path(path: str) -> str:
    path_clean = (path or "").strip().lstrip("/")
    if not path_clean:
        raise ValidationError("path must be non-empty")
    return path_clean


def normalize_max_chars(max_chars: int) -> int:
    n = int(max_chars)
    if n <= 0:
        raise ValidationError("max_chars must be positive")
    return n
