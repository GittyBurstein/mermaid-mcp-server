from __future__ import annotations

from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from clients.github_client import GitHubClient 
from config import HTTP_VERIFY, PROJECT_ROOT
from core.errors import ValidationError
from core.models import SourceType
from sources.source_factory import get_file_source


def register(mcp: FastMCP, *, github_client: Optional[GitHubClient] = None) -> None:
    @mcp.tool(name="list_files")
    async def list_files(
        source: SourceType = "local",
        root: str = ".",
        glob: str = "**/*",
        repo_url: Optional[str] = None,
        ref: str = "main",
        recursive: bool = True,
    ) -> List[str]:
        if source == "github" and (not repo_url or not repo_url.strip()):
            raise ValidationError("Missing repo_url for github source")

        src = get_file_source(
            source,
            project_root=PROJECT_ROOT,
            repo_url=repo_url,
            ref=ref,
            http_verify=HTTP_VERIFY,
            github_client=github_client,
        )

        return await src.list_files(root=root, glob=glob, recursive=recursive)
