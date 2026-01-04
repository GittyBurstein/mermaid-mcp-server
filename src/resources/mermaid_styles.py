# src/server/resources/mermaid_styles.py

from pathlib import Path
from mcp.server.fastmcp import FastMCP


BASE_DIR = Path(__file__).parent


def register_resources(mcp: FastMCP) -> None:
    """
    Register Mermaid style resources for the MCP server.
    """

    @mcp.resource(
        "mermaid://styles/blue-flowchart",
        mime_type="text/plain",
        description="Canonical blue Mermaid flowchart style"
    )
    def blue_flowchart_style() -> str:
        path = BASE_DIR / "mermaid_style_blue_flowchart.mmd"
        return path.read_text(encoding="utf-8")
