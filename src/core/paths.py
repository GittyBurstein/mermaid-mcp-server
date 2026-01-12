from __future__ import annotations

import fnmatch
from typing import Tuple

"""
Path utilities used across the project.

Provides consistent POSIX-style normalization and a component-wise
'**' supporting glob matcher used by sources and tools.
"""


def normalize_posix_relpath(p: str) -> str:
    """Normalize a user path to a clean POSIX relative path.

    Converts backslashes to '/', trims whitespace, removes leading '/'
    and repeated './' markers.
    """
    s = (p or "").strip()
    s = s.replace("\\", "/")        # Unify path separators across OSes.
    s = s.lstrip("/")               # Prevent accidental absolute paths.
    while s.startswith("./"):       # Drop repeated "./" prefixes.
        s = s[2:]
    return s


def clean_root(root: str) -> str:
    """Normalize a root directory hint.

    Treats '.', './', '/', and empty as repository root (returns '').
    """
    r = (root or "").strip().replace("\\", "/")
    if r in ("", ".", "./", "/"):
        return ""
    while r.startswith("./"):
        r = r[2:]
    return r.strip("/")


def split_posix(p: str) -> Tuple[str, ...]:
    """Split a POSIX path into non-empty segments."""
    s = (p or "").strip().replace("\\", "/").strip("/")
    if not s:
        return tuple()
    return tuple(seg for seg in s.split("/") if seg)


def glob_match(rel_path: str, pattern: str) -> bool:
    """Match a relative path against a glob pattern with '**' support."""
    parts = split_posix(rel_path)

    pat = (pattern or "").strip().replace("\\", "/").strip("/")
    if not pat:
        pat = "**/*"  # Default: match everything.
    pats = split_posix(pat)

    def rec(i: int, j: int) -> bool:
        if j == len(pats):
            return i == len(parts)

        token = pats[j]
        if token == "**":
            return rec(i, j + 1) or (i < len(parts) and rec(i + 1, j))

        return (
            i < len(parts)
            and fnmatch.fnmatchcase(parts[i], token)
            and rec(i + 1, j + 1)
        )

    return rec(0, 0)
