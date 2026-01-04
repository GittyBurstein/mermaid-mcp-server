"""Configuration and environment helpers for the project.

Provides small helpers to read typed environment variables and exposes
project-level configuration constants used across the codebase (e.g.
PROJECT_ROOT, HTTP_VERIFY, KROKI_BASE_URL, timeouts and limits).
"""

from __future__ import annotations

import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


# Project root for LocalSource security boundary
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", ".")).resolve()

# Network / HTTP
HTTP_VERIFY = _env_bool("HTTP_VERIFY", False)

# Kroki
KROKI_BASE_URL = os.environ.get("KROKI_BASE_URL", "https://kroki.io").strip()
KROKI_TIMEOUT = _env_float("KROKI_TIMEOUT", 20.0)

# Limits / output
MAX_FILE_CHARS = _env_int("MAX_FILE_CHARS", 200_000)
DIAGRAM_OUT_DIR = os.environ.get("DIAGRAM_OUT_DIR", "diagrams").strip()
