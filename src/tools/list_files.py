"""MCP tool that lists files from a configured source.

Registers the 'list_files' tool which adapts FileSource implementations
(local/github) to the MCP tool interface used by prompts and agents.
"""

from __future__ import annotations

from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from clients.github import GitHubClient
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
        """List files from a source and return a sorted list of paths.

        Fetches file paths from a local directory or a GitHub repository.

        Params:
          - source: "local" or "github" (default: "local").
          - root: path within the source to list from (default: ".").
          - glob: glob pattern to filter files (default: "**/*").
          - repo_url: required when source is "github" (HTTPS repo URL).
          - ref: git reference to resolve (default: "main").
          - recursive: include subdirectories (default: True).

        Returns:
          Sorted list of file path strings.

        Raises:
          ValidationError for invalid inputs; NotFoundError or source-specific
          errors if the repository/ref/tree cannot be resolved.
        """
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
