from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent

from clients.kroki_client import KrokiClient
from config import DIAGRAM_OUT_DIR, HTTP_VERIFY, KROKI_BASE_URL, KROKI_TIMEOUT, PROJECT_ROOT
from core.errors import AccessDeniedError, ValidationError


def _sanitize_filename_stem(title: str) -> str:
    # Keep ASCII-ish stems to avoid weird filenames.
    s = (title or "").strip()
    if not s:
        return "diagram"
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = s.strip().replace(" ", "_")
    return s[:80] if s else "diagram"


def _safe_out_dir() -> Path:
    # Resolve output directory safely under PROJECT_ROOT unless absolute.
    raw = (DIAGRAM_OUT_DIR or "").strip() or "diagrams"
    p = Path(raw)
    out_dir = p if p.is_absolute() else (PROJECT_ROOT / p)
    out_dir = out_dir.resolve()

    # Strong containment unless user gave an absolute path inside project root.
    try:
        out_dir.relative_to(PROJECT_ROOT)
    except ValueError as e:
        raise AccessDeniedError("DIAGRAM_OUT_DIR must be within PROJECT_ROOT") from e

    return out_dir


def register(mcp: FastMCP, *, kroki_client: Optional[KrokiClient] = None) -> None:  # CHANGED (DI)
    client = kroki_client or KrokiClient(  # CHANGED (DI)
        base_url=KROKI_BASE_URL,
        timeout=KROKI_TIMEOUT,
        verify=HTTP_VERIFY,
    )

    @mcp.tool(name="render_mermaid")
    async def render_mermaid(mermaid: str, title: Optional[str] = None) -> ImageContent:
        code = (mermaid or "").strip()
        if not code:
            raise ValidationError("Mermaid code is empty")

        stem = _sanitize_filename_stem(title or "diagram")

        png = await client.render_mermaid_png(code)

        out_dir = _safe_out_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{stem}.png").write_bytes(png)

        return ImageContent(
            type="image",
            mimeType="image/png",
            data=base64.b64encode(png).decode("ascii"),
        )
