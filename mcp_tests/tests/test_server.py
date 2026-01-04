import sys
import types
import uuid
import importlib.util
from pathlib import Path


def _find_server_py() -> Path:
    # Try common layouts:
    # 1) <root>/server.py
    # 2) <root>/server/server.py
    # 3) <root>/src/server/server.py
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "server.py",
        root / "server" / "server.py",
        root / "src" / "server" / "server.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Could not find server.py. Tried: {candidates}")


def _install_fake_modules(monkeypatch, captures: dict):
    # ---- Fake mcp.server.fastmcp.FastMCP ----
    mcp_mod = types.ModuleType("mcp")
    mcp_server_mod = types.ModuleType("mcp.server")
    fastmcp_mod = types.ModuleType("mcp.server.fastmcp")

    class DummyFastMCP:
        def __init__(self, name: str):
            captures["fastmcp_name"] = name
            captures["mcp_instance"] = self
            self.run_calls = []

        def run(self, *, transport: str):
            self.run_calls.append({"transport": transport})
            captures["run_calls"] = list(self.run_calls)

    fastmcp_mod.FastMCP = DummyFastMCP

    # Mark package structure
    mcp_mod.__path__ = []
    mcp_server_mod.__path__ = []

    monkeypatch.setitem(sys.modules, "mcp", mcp_mod)
    monkeypatch.setitem(sys.modules, "mcp.server", mcp_server_mod)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_mod)

    # ---- Fake config ----
    config_mod = types.ModuleType("config")
    config_mod.HTTP_VERIFY = True
    config_mod.KROKI_BASE_URL = "https://kroki.example"
    config_mod.KROKI_TIMEOUT = 12.3
    monkeypatch.setitem(sys.modules, "config", config_mod)

    # ---- Fake clients ----
    clients_pkg = types.ModuleType("clients")
    clients_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "clients", clients_pkg)

    gh_client_mod = types.ModuleType("clients.github_client")
    kroki_client_mod = types.ModuleType("clients.kroki_client")

    class FakeGitHubClient:
        def __init__(self, *, verify: bool = False, timeout: float = 20.0):
            captures["github_client_ctor_calls"] = captures.get("github_client_ctor_calls", []) + [
                {"verify": verify, "timeout": timeout}
            ]
            captures["github_client_instance"] = self

    class FakeKrokiClient:
        def __init__(self, *, base_url: str, timeout: float, verify: bool = False):
            captures["kroki_client_ctor_calls"] = captures.get("kroki_client_ctor_calls", []) + [
                {"base_url": base_url, "timeout": timeout, "verify": verify}
            ]
            captures["kroki_client_instance"] = self

    gh_client_mod.GitHubClient = FakeGitHubClient
    kroki_client_mod.KrokiClient = FakeKrokiClient

    monkeypatch.setitem(sys.modules, "clients.github_client", gh_client_mod)
    monkeypatch.setitem(sys.modules, "clients.kroki_client", kroki_client_mod)

    # ---- Fake tools + resources + prompts ----
    def _ensure_pkg(name: str):
        pkg = types.ModuleType(name)
        pkg.__path__ = []
        monkeypatch.setitem(sys.modules, name, pkg)

    _ensure_pkg("tools")
    _ensure_pkg("resources")
    _ensure_pkg("prompts")

    tools_list_mod = types.ModuleType("tools.list_files")
    tools_read_mod = types.ModuleType("tools.read_file")
    tools_render_mod = types.ModuleType("tools.render_mermaid")
    res_mod = types.ModuleType("resources.mermaid_styles")
    prompts_mod = types.ModuleType("prompts.mermaid_prompt")

    def register_list_files(mcp, *, github_client=None):
        captures["register_list_files_calls"] = captures.get("register_list_files_calls", []) + [
            {"mcp": mcp, "github_client": github_client}
        ]

    def register_read_file(mcp, *, github_client=None):
        captures["register_read_file_calls"] = captures.get("register_read_file_calls", []) + [
            {"mcp": mcp, "github_client": github_client}
        ]

    def register_render_mermaid(mcp, *, kroki_client=None):
        captures["register_render_mermaid_calls"] = captures.get("register_render_mermaid_calls", []) + [
            {"mcp": mcp, "kroki_client": kroki_client}
        ]

    def register_resources(mcp):
        captures["register_resources_calls"] = captures.get("register_resources_calls", []) + [{"mcp": mcp}]

    def register_prompts(mcp):
        captures["register_prompts_calls"] = captures.get("register_prompts_calls", []) + [{"mcp": mcp}]

    tools_list_mod.register = register_list_files
    tools_read_mod.register = register_read_file
    tools_render_mod.register = register_render_mermaid
    res_mod.register_resources = register_resources
    prompts_mod.register_prompts = register_prompts

    monkeypatch.setitem(sys.modules, "tools.list_files", tools_list_mod)
    monkeypatch.setitem(sys.modules, "tools.read_file", tools_read_mod)
    monkeypatch.setitem(sys.modules, "tools.render_mermaid", tools_render_mod)
    monkeypatch.setitem(sys.modules, "resources.mermaid_styles", res_mod)
    monkeypatch.setitem(sys.modules, "prompts.mermaid_prompt", prompts_mod)


def _load_server_module(monkeypatch, captures: dict):
    _install_fake_modules(monkeypatch, captures)

    server_path = _find_server_py()
    mod_name = f"server_under_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(mod_name, server_path)
    assert spec and spec.loader

    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def test_server_register_all_and_di(monkeypatch):
    captures = {}
    module = _load_server_module(monkeypatch, captures)

    # FastMCP created with correct name
    assert captures["fastmcp_name"] == "mermaid-mcp"
    mcp = captures["mcp_instance"]

    # Clients are created once in register_tools()
    assert len(captures.get("github_client_ctor_calls", [])) == 1
    assert captures["github_client_ctor_calls"][0]["verify"] is True

    assert len(captures.get("kroki_client_ctor_calls", [])) == 1
    assert captures["kroki_client_ctor_calls"][0]["base_url"] == "https://kroki.example"
    assert captures["kroki_client_ctor_calls"][0]["timeout"] == 12.3
    assert captures["kroki_client_ctor_calls"][0]["verify"] is True

    # Tool registrations called
    assert len(captures.get("register_list_files_calls", [])) == 1
    assert len(captures.get("register_read_file_calls", [])) == 1
    assert len(captures.get("register_render_mermaid_calls", [])) == 1

    # Both list_files and read_file must receive the SAME injected github_client instance
    gh1 = captures["register_list_files_calls"][0]["github_client"]
    gh2 = captures["register_read_file_calls"][0]["github_client"]
    assert gh1 is gh2
    assert gh1 is captures["github_client_instance"]

    # render_mermaid gets the injected kroki client instance
    kc = captures["register_render_mermaid_calls"][0]["kroki_client"]
    assert kc is captures["kroki_client_instance"]

    # resources + prompts are registered
    assert len(captures.get("register_resources_calls", [])) == 1
    assert len(captures.get("register_prompts_calls", [])) == 1
    assert captures["register_resources_calls"][0]["mcp"] is mcp
    assert captures["register_prompts_calls"][0]["mcp"] is mcp

    # main() runs stdio transport
    module.main()
    assert captures["run_calls"] == [{"transport": "stdio"}]
