import pytest

from sources.github_source import GitHubSource
from core.errors import ValidationError


class FakeGitHubClient:
    def __init__(self, files=None, content=""):
        self._files = files or []
        self._content = content
        self.calls = []

    async def list_files_from_url(self, *, repo_url: str, ref: str, recursive: bool):
        self.calls.append(("list", repo_url, ref, recursive))
        return list(self._files)

    async def read_text_file_from_url(self, *, repo_url: str, path: str, ref: str, max_chars: int):
        self.calls.append(("read", repo_url, path, ref, max_chars))
        return self._content


def test_github_source_requires_repo_url():
    with pytest.raises(ValidationError):
        GitHubSource(client=FakeGitHubClient(), repo_url="   ")


@pytest.mark.asyncio
async def test_github_source_list_files_filters_root_and_glob():
    fake = FakeGitHubClient(files=[
        "README.md",
        "src/app.py",
        "src/utils/helpers.py",
        "docs/guide.md",
    ])

    src = GitHubSource(client=fake, repo_url="https://github.com/octocat/Hello-World", ref="main")

    out = await src.list_files(root="src", glob="**/*.py", recursive=True)
    assert out == ["src/app.py", "src/utils/helpers.py"]


@pytest.mark.asyncio
async def test_github_source_read_file_passthrough():
    fake = FakeGitHubClient(content="hello")
    src = GitHubSource(client=fake, repo_url="https://github.com/octocat/Hello-World", ref="dev")

    out = await src.read_file(path="README.md", max_chars=10)
    assert out == "hello"
    assert fake.calls[-1][:4] == ("read", "https://github.com/octocat/Hello-World", "README.md", "dev")
