import pytest

from core.errors import ValidationError
from tools import list_files as list_files_tool


class FakeSource:
    def __init__(self, out):
        self._out = out
        self.calls = []

    async def list_files(self, *, root: str, glob: str, recursive: bool):
        self.calls.append((root, glob, recursive))
        return list(self._out)


@pytest.mark.asyncio
async def test_list_files_tool_validates_missing_repo_url(dummy_mcp):
    list_files_tool.register(dummy_mcp, github_client=None)
    fn = dummy_mcp.tools["list_files"]

    with pytest.raises(ValidationError):
        await fn(source="github", repo_url=None)


@pytest.mark.asyncio
async def test_list_files_tool_calls_factory_and_source(monkeypatch, dummy_mcp):
    fake_src = FakeSource(out=["a", "b"])

    captured = {}

    def fake_get_file_source(source, **kwargs):
        captured["source"] = source
        captured["kwargs"] = kwargs
        return fake_src

    monkeypatch.setattr(list_files_tool, "get_file_source", fake_get_file_source)

    list_files_tool.register(dummy_mcp, github_client="INJECTED_CLIENT")
    fn = dummy_mcp.tools["list_files"]

    out = await fn(source="local", root=".", glob="**/*", recursive=True)

    assert out == ["a", "b"]
    assert captured["source"] == "local"
    assert fake_src.calls == [(".", "**/*", True)]
