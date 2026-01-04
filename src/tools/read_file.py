from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from clients.github_client import GitHubClient  # CHANGED (DI): new import
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
        # English comments only:
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
            github_client=github_client,  # CHANGED (DI): pass injected client down
        )

        return await src.read_file(path=path, max_chars=max_chars)
