import httpx
import pytest

from clients.kroki_client import KrokiClient
from core.errors import ExternalServiceError, ValidationError


def _transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_render_mermaid_png_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("/mermaid/png")
        return httpx.Response(200, content=b"PNG_BYTES")

    c = KrokiClient(base_url="https://kroki.example", timeout=5.0, verify=False)

    # Patch AsyncClient to use MockTransport.
    orig = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = _transport(handler)
        return orig(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_async_client)

    out = await c.render_mermaid_png("flowchart TD; A-->B")
    assert out == b"PNG_BYTES"


@pytest.mark.asyncio
async def test_render_mermaid_png_empty_raises():
    c = KrokiClient(base_url="https://kroki.example", timeout=5.0, verify=False)
    with pytest.raises(ValidationError):
        await c.render_mermaid_png("  ")


@pytest.mark.asyncio
async def test_render_mermaid_png_http_error_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    c = KrokiClient(base_url="https://kroki.example", timeout=5.0, verify=False)

    orig = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = _transport(handler)
        return orig(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_async_client)

    with pytest.raises(ExternalServiceError):
        await c.render_mermaid_png("flowchart TD; A-->B")
