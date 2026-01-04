import pytest

from sources.local_source import LocalSource
from core.errors import AccessDeniedError, NotFoundError, ValidationError


@pytest.mark.asyncio
async def test_local_list_files_basic(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.md").write_text("x", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("x", encoding="utf-8")

    src = LocalSource(project_root=tmp_path)

    out = await src.list_files(root=".", glob="**/*", recursive=True)
    assert out == ["a.txt", "b.md", "sub/c.py"]


@pytest.mark.asyncio
async def test_local_list_files_glob_filters(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.md").write_text("x", encoding="utf-8")

    src = LocalSource(project_root=tmp_path)
    out = await src.list_files(root=".", glob="*.md", recursive=True)
    assert out == ["b.md"]


@pytest.mark.asyncio
async def test_local_list_files_not_a_directory(tmp_path):
    (tmp_path / "file.txt").write_text("x", encoding="utf-8")

    src = LocalSource(project_root=tmp_path)
    with pytest.raises(NotFoundError):
        await src.list_files(root="file.txt", glob="**/*", recursive=True)


@pytest.mark.asyncio
async def test_local_read_file_success(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")

    src = LocalSource(project_root=tmp_path)
    out = await src.read_file(path="a.txt", max_chars=200_000)
    assert out == "hello"


@pytest.mark.asyncio
async def test_local_read_file_truncates(tmp_path):
    (tmp_path / "a.txt").write_text("a" * 30, encoding="utf-8")

    src = LocalSource(project_root=tmp_path)
    out = await src.read_file(path="a.txt", max_chars=10)
    assert out.startswith("a" * 10)
    assert "TRUNCATED" in out


@pytest.mark.asyncio
async def test_local_read_file_not_found(tmp_path):
    src = LocalSource(project_root=tmp_path)
    with pytest.raises(NotFoundError):
        await src.read_file(path="nope.txt", max_chars=200_000)


@pytest.mark.asyncio
async def test_local_access_denied_outside_root(tmp_path):
    src = LocalSource(project_root=tmp_path)
    with pytest.raises(AccessDeniedError):
        await src.read_file(path="../secret.txt", max_chars=200_000)


def test_local_resolve_empty_path_raises(tmp_path):
    src = LocalSource(project_root=tmp_path)
    with pytest.raises(ValidationError):
        src._resolve_under_root("")
