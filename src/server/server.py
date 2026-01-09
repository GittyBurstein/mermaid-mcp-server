"""Server bootstrap for the Mermaid MCP service.

Creates the FastMCP instance, wires clients and tools, registers
resources and prompts, and starts the MCP server (stdio transport).
"""

from mcp.server.fastmcp import FastMCP

from clients.github import GitHubClient
from clients.kroki_client import KrokiClient
from config import HTTP_VERIFY, KROKI_BASE_URL, KROKI_TIMEOUT

from tools.list_files import register as register_list_files
from tools.read_file import register as register_read_file
from tools.render_mermaid import register as register_render_mermaid

from resources.mermaid_styles import register_resources
from prompts.mermaid_prompt import register_prompts

mcp = FastMCP("mermaid-mcp")


def register_tools() -> None:
    github_client = GitHubClient(verify=HTTP_VERIFY)  
    kroki_client = KrokiClient(base_url=KROKI_BASE_URL, timeout=KROKI_TIMEOUT, verify=HTTP_VERIFY)  # CHANGED (DI)

    register_list_files(mcp, github_client=github_client)
    register_read_file(mcp, github_client=github_client)
    register_render_mermaid(mcp, kroki_client=kroki_client)


def register_all() -> None:
    register_tools()
    register_resources(mcp)
    register_prompts(mcp)


register_all()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
