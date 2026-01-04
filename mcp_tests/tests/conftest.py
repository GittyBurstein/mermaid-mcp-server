import pytest


class DummyMCP:
    """Minimal FastMCP stand-in to capture tool registration."""

    def __init__(self) -> None:
        self.tools = {}

    def tool(self, *, name: str):
        def _decorator(fn):
            self.tools[name] = fn
            return fn
        return _decorator


@pytest.fixture
def dummy_mcp():
    return DummyMCP()
