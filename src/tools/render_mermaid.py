"""MCP tool to render Mermaid text into a PNG image using Kroki.

Registers 'render_mermaid' which calls Kroki, saves the PNG to disk
and returns an ImageContent payload usable by the MCP protocol.
"""

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
    # Safe filename: trim, remove unsafe chars, replace spaces, limit length
    s = (title or "").strip()
    if not s:
        return "diagram"
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = s.strip().replace(" ", "_")
    return s[:80] if s else "diagram"


def _safe_out_dir() -> Path:
    # Resolve and enforce output dir is inside PROJECT_ROOT
    raw = (DIAGRAM_OUT_DIR or "").strip() or "diagrams"
    p = Path(raw)
    out_dir = p if p.is_absolute() else (PROJECT_ROOT / p)
    out_dir = out_dir.resolve()

    try:
        out_dir.relative_to(PROJECT_ROOT)
    except ValueError as e:
        raise AccessDeniedError("DIAGRAM_OUT_DIR must be within PROJECT_ROOT") from e

    return out_dir


def register(mcp: FastMCP, *, kroki_client: Optional[KrokiClient] = None) -> None:  # CHANGED (DI)
    client = kroki_client or KrokiClient(  
        base_url=KROKI_BASE_URL,
        timeout=KROKI_TIMEOUT,
        verify=HTTP_VERIFY,
    )

    @mcp.tool(name="render_mermaid")
    async def render_mermaid(mermaid: str, title: Optional[str] = None) -> ImageContent:
        """Render Mermaid text to PNG via Kroki and return an ImageContent.

        Params:
          - mermaid: Mermaid source text (required).
          - title: optional title used for the output filename (sanitized).

        Returns:
          ImageContent with base64-encoded PNG data.

        Raises:
          ValidationError if mermaid is empty; AccessDeniedError if output
          directory is outside the project root; Kroki/network errors on render.
        """
        code = (mermaid or "").strip()
        if not code:
            raise ValidationError("Mermaid code is empty")

        # make a safe filename stem
        stem = _sanitize_filename_stem(title or "diagram")

        # render PNG via Kroki
        png = await client.render_mermaid_png(code)

        # ensure and create output directory
        out_dir = _safe_out_dir()
        out_dir.mkdir(parents=True, exist_ok=True)

        # save PNG as a simple cache
        (out_dir / f"{stem}.png").write_bytes(png)

        # return base64-encoded image payload
        return ImageContent(
            type="image",
            mimeType="image/png",
            data=base64.b64encode(png).decode("ascii"),
        )
