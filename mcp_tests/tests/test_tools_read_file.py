import pytest

from core.errors import ValidationError
from tools import read_file as read_file_tool


class FakeSource:
    def __init__(self, out):
        self._out = out
        self.calls = []

    async def read_file(self, *, path: str, max_chars: int):
        self.calls.append((path, max_chars))
        return self._out


@pytest.mark.asyncio
async def test_read_file_tool_validates_missing_path(dummy_mcp):
    read_file_tool.register(dummy_mcp, github_client=None)
    fn = dummy_mcp.tools["read_file"]

    with pytest.raises(ValidationError):
        await fn(source="local", path="")


@pytest.mark.asyncio
async def test_read_file_tool_validates_missing_repo_url(dummy_mcp):
    read_file_tool.register(dummy_mcp, github_client=None)
    fn = dummy_mcp.tools["read_file"]

    with pytest.raises(ValidationError):
        await fn(source="github", path="a.txt", repo_url="   ")


@pytest.mark.asyncio
async def test_read_file_tool_calls_factory_and_source(monkeypatch, dummy_mcp):
    fake_src = FakeSource(out="content")
    captured = {}

    def fake_get_file_source(source, **kwargs):
        captured["source"] = source
        captured["kwargs"] = kwargs
        return fake_src

    monkeypatch.setattr(read_file_tool, "get_file_source", fake_get_file_source)

    read_file_tool.register(dummy_mcp, github_client="INJECTED_CLIENT")
    fn = dummy_mcp.tools["read_file"]

    out = await fn(source="local", path="a.txt", max_chars=123)

    assert out == "content"
    assert captured["source"] == "local"
    assert fake_src.calls == [("a.txt", 123)]
