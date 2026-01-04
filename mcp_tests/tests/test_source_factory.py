import pytest

from sources.source_factory import get_file_source
from sources.local_source import LocalSource
from sources.github_source import GitHubSource
from core.errors import ValidationError


class FakeGitHubClient:
    pass


def test_get_file_source_local(tmp_path):
    src = get_file_source("local", project_root=tmp_path)
    assert isinstance(src, LocalSource)


def test_get_file_source_github_requires_repo_url(tmp_path):
    with pytest.raises(ValidationError):
        get_file_source("github", project_root=tmp_path, repo_url="  ")


def test_get_file_source_unknown(tmp_path):
    with pytest.raises(ValidationError):
        get_file_source("nope", project_root=tmp_path)


def test_get_file_source_uses_injected_client(tmp_path):
    injected = FakeGitHubClient()
    src = get_file_source(
        "github",
        project_root=tmp_path,
        repo_url="https://github.com/octocat/Hello-World",
        ref="main",
        github_client=injected,
        http_verify=False,
    )
    assert isinstance(src, GitHubSource)
    # Access private field to verify DI in tests.
    assert getattr(src, "_client") is injected
