"""MCP tool that reads text files from a configured source.

Registers the 'read_file' tool which returns file contents with a
max size and validates inputs before delegating to a FileSource.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from clients.github import GitHubClient
from config import HTTP_VERIFY, MAX_FILE_CHARS, PROJECT_ROOT
from core.errors import ValidationError
from core.models import SourceType
from sources.source_factory import get_file_source


def register(mcp: FastMCP, *, github_client: Optional[GitHubClient] = None) -> None:  # CHANGED (DI)
    @mcp.tool(name="read_file")
    async def read_file(
        source: SourceType = "local",
        path: str = "",
        repo_url: Optional[str] = None,
        ref: str = "main",
        max_chars: int = MAX_FILE_CHARS,
    ) -> str:
        """Read a text file from a source and return its UTF-8 contents.

        Fetches a file from either a local filesystem or a GitHub repository.
        Parameters:
          - source: "local" or "github" (default: "local").
          - path: file path relative to the source root (required).
          - repo_url: required when source is "github" (e.g. https://github.com/owner/repo).
          - ref: git reference to resolve (branch, tag, or SHA). Default: "main".
          - max_chars: maximum characters to return (default from config).

        Returns:
          The file contents as a UTF-8 string. If the content exceeds max_chars
          it will be truncated and the suffix "\n\n...[TRUNCATED]..." appended.

        Raises:
          ValidationError for missing/invalid inputs, and NotFoundError or
          source-specific errors when the file or repository cannot be resolved.
        """
        if not path or not path.strip():
            raise ValidationError("Missing file path")

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

        return await src.read_file(path=path, max_chars=max_chars)
