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
async def test_github_source_list_files_filters_root_and_glob_recursive_py():
    fake = FakeGitHubClient(files=[
        "README.md",
        "src/app.py",
        "src/utils/helpers.py",
        "docs/guide.md",
    ])

    src = GitHubSource(client=fake, repo_url="https://github.com/octocat/Hello-World", ref="main")

    # Glob is relative to root ("src"), so "**/*.py" matches both direct + nested .py files.
    out = await src.list_files(root="src", glob="**/*.py", recursive=True)
    assert out == ["src/app.py", "src/utils/helpers.py"]


@pytest.mark.asyncio
async def test_github_source_list_files_glob_is_relative_to_root_non_recursive_pattern():
    fake = FakeGitHubClient(files=[
        "src/app.py",
        "src/utils/helpers.py",
        "src/utils/more/deep.py",
    ])

    src = GitHubSource(client=fake, repo_url="https://github.com/octocat/Hello-World", ref="main")

    # With the "new" behavior, glob="*.py" is checked relative to root,
    # so it should match ONLY files directly under "src/".
    out = await src.list_files(root="src", glob="*.py", recursive=True)
    assert out == ["src/app.py"]


@pytest.mark.asyncio
async def test_github_source_list_files_glob_relative_subdir_under_root():
    fake = FakeGitHubClient(files=[
        "src/app.py",
        "src/utils/helpers.py",
        "src/utils/other.txt",
        "src/docs/guide.md",
    ])

    src = GitHubSource(client=fake, repo_url="https://github.com/octocat/Hello-World", ref="main")

    # glob is relative to root, so "utils/*.py" should match "src/utils/helpers.py"
    out = await src.list_files(root="src", glob="utils/*.py", recursive=True)
    assert out == ["src/utils/helpers.py"]


@pytest.mark.asyncio
async def test_github_source_list_files_root_normalization():
    fake = FakeGitHubClient(files=[
        "src/app.py",
        "src/utils/helpers.py",
        "docs/guide.md",
    ])

    src = GitHubSource(client=fake, repo_url="https://github.com/octocat/Hello-World", ref="main")

    # root="./src/" should behave the same as "src"
    out = await src.list_files(root="./src/", glob="**/*.py", recursive=True)
    assert out == ["src/app.py", "src/utils/helpers.py"]


@pytest.mark.asyncio
async def test_github_source_read_file_passthrough():
    fake = FakeGitHubClient(content="hello")
    src = GitHubSource(client=fake, repo_url="https://github.com/octocat/Hello-World", ref="dev")

    out = await src.read_file(path="README.md", max_chars=10)
    assert out == "hello"
    assert fake.calls[-1][:4] == ("read", "https://github.com/octocat/Hello-World", "README.md", "dev")
