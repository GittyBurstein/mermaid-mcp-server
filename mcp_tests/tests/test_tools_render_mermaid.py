import base64
import pytest

from core.errors import AccessDeniedError, ValidationError
from tools import render_mermaid as render_tool


class FakeKrokiClient:
    def __init__(self, png=b"PNG"):
        self.png = png
        self.calls = []

    async def render_mermaid_png(self, mermaid: str) -> bytes:
        self.calls.append(mermaid)
        return self.png


def test_sanitize_filename_stem():
    assert render_tool._sanitize_filename_stem("Hello world!") == "Hello_world"
    assert render_tool._sanitize_filename_stem("   ") == "diagram"


def test_safe_out_dir_denies_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(render_tool, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(render_tool, "DIAGRAM_OUT_DIR", "../outside")

    with pytest.raises(AccessDeniedError):
        render_tool._safe_out_dir()


def test_safe_out_dir_allows_inside(tmp_path, monkeypatch):
    monkeypatch.setattr(render_tool, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(render_tool, "DIAGRAM_OUT_DIR", "diagrams")

    out = render_tool._safe_out_dir()
    assert str(out).startswith(str(tmp_path))


@pytest.mark.asyncio
async def test_render_mermaid_tool_writes_png_and_returns_image_content(tmp_path, monkeypatch, dummy_mcp):
    # Force output dir inside tmp_path
    monkeypatch.setattr(render_tool, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(render_tool, "DIAGRAM_OUT_DIR", "diagrams")

    fake = FakeKrokiClient(png=b"PNG_BYTES")

    render_tool.register(dummy_mcp, kroki_client=fake)
    fn = dummy_mcp.tools["render_mermaid"]

    img = await fn("flowchart TD; A-->B", title="My Diagram")
    assert img.mimeType == "image/png"
    assert base64.b64decode(img.data.encode("ascii")) == b"PNG_BYTES"

    written = tmp_path / "diagrams" / "My_Diagram.png"
    assert written.exists()
    assert written.read_bytes() == b"PNG_BYTES"


@pytest.mark.asyncio
async def test_render_mermaid_tool_empty_code_raises(tmp_path, monkeypatch, dummy_mcp):
    monkeypatch.setattr(render_tool, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(render_tool, "DIAGRAM_OUT_DIR", "diagrams")

    fake = FakeKrokiClient()

    render_tool.register(dummy_mcp, kroki_client=fake)
    fn = dummy_mcp.tools["render_mermaid"]

    with pytest.raises(ValidationError):
        await fn("   ", title="X")
