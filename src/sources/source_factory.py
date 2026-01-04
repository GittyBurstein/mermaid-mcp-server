"""Factory for selecting the appropriate FileSource implementation.

Exposes get_file_source which returns either a LocalSource or
GitHubSource based on the requested source type.
"""

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
    source: Optional[SourceType] = None,
    *,
    project_root: Path,
    repo_url: Optional[str] = None,
    ref: str = "main",
    github_timeout: float = 20.0,
    http_verify: bool = False,
    github_client: Optional[GitHubClient] = None,  
) -> FileSource:
    """
    Factory that returns the correct FileSource implementation.
    
    Priority Logic:
    1. If a repo_url is provided -> Use GitHubSource.
    2. If source == "github" (explicitly requested) -> Use GitHubSource.
    3. Default -> Use LocalSource.
    """

    if (repo_url and repo_url.strip()) or source == "github":
        if not repo_url or not repo_url.strip():
            raise ValidationError("Missing repo_url for github source")
        
        client = github_client or GitHubClient(timeout=github_timeout, verify=http_verify)
        return GitHubSource(client=client, repo_url=repo_url, ref=ref)

    return LocalSource(project_root=project_root)