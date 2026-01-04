from __future__ import annotations

from pathlib import Path
from typing import Optional

from clients.github_client import GitHubClient
from core.errors import ValidationError
from core.interfaces import FileSource
from core.models import SourceType
from sources.github_source import GitHubSource
from sources.local_source import LocalSource


def get_file_source(
    source: SourceType,
    *,
    project_root: Path,
    repo_url: Optional[str] = None,
    ref: str = "main",
    github_timeout: float = 20.0,
    http_verify: bool = False,
    github_client: Optional[GitHubClient] = None,  
) -> FileSource:
    # Factory that returns the correct FileSource implementation.

    if source == "local":
        return LocalSource(project_root=project_root)

    if source == "github":
        if not repo_url or not repo_url.strip():
            raise ValidationError("Missing repo_url for github source")
        client = github_client or GitHubClient(timeout=github_timeout, verify=http_verify)  
        return GitHubSource(client=client, repo_url=repo_url, ref=ref)

    raise ValidationError(f"Unknown source: {source}")
