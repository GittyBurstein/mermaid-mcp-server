import httpx
import pytest

from clients.github_client import GitHubClient, parse_repo_url
from core.errors import NotFoundError, ValidationError


# ---------------------------
# Helpers
# ---------------------------

def patch_github_transport(monkeypatch, client: GitHubClient, routes: dict):
    """
    Patch GitHubClient._create_client() to use httpx.MockTransport.

    routes keys:
        (METHOD, PATH) -> httpx.Response  OR  (status_code, json, content)
    """
    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method.upper(), request.url.path)

        if key not in routes:
            return httpx.Response(404, json={"message": "not found"})

        val = routes[key]

        if isinstance(val, httpx.Response):
            return val

        status_code, js, content = val
        if content is not None:
            return httpx.Response(status_code, content=content)
        return httpx.Response(status_code, json=js)

    transport = httpx.MockTransport(handler)

    def _create_client(custom_headers=None):
        headers = {**client._headers, **(custom_headers or {})}
        return httpx.AsyncClient(
            base_url=client.BASE_URL,
            headers=headers,
            timeout=client._timeout,
            verify=client._verify,
            transport=transport,
        )

    monkeypatch.setattr(client, "_create_client", _create_client)


# ---------------------------
# parse_repo_url
# ---------------------------

def test_parse_repo_url_valid():
    owner, repo = parse_repo_url("https://github.com/octocat/Hello-World")
    assert owner == "octocat"
    assert repo == "Hello-World"


@pytest.mark.parametrize("bad", ["", "octocat/Hello-World", "https://example.com/a/b", "https://github.com/a"])
def test_parse_repo_url_invalid(bad):
    with pytest.raises(ValidationError):
        parse_repo_url(bad)


# ---------------------------
# list_files_from_url
# ---------------------------

@pytest.mark.asyncio
async def test_list_files_from_url_success(monkeypatch):
    client = GitHubClient(timeout=5.0, verify=False)

    routes = {
        ("GET", "/repos/octocat/Hello-World/commits/main"): (
            200,
            {"commit": {"tree": {"sha": "tree_sha_123"}}},
            None,
        ),
        ("GET", "/repos/octocat/Hello-World/git/trees/tree_sha_123"): (
            200,
            {
                "tree": [
                    {"path": "README.md", "type": "blob"},
                    {"path": "src/app.py", "type": "blob"},
                    {"path": "src", "type": "tree"},
                ]
            },
            None,
        ),
    }

    patch_github_transport(monkeypatch, client, routes)

    out = await client.list_files_from_url(
        repo_url="https://github.com/octocat/Hello-World",
        ref="main",
        recursive=True,
    )
    assert out == ["README.md", "src/app.py"]


@pytest.mark.asyncio
async def test_list_files_from_url_fallback_to_default_branch(monkeypatch):
    client = GitHubClient(timeout=5.0, verify=False)

    routes = {
        # ref fails -> fallback
        ("GET", "/repos/octocat/Hello-World/commits/main"): (422, {"message": "invalid ref"}, None),
        ("GET", "/repos/octocat/Hello-World"): (200, {"default_branch": "master"}, None),
        ("GET", "/repos/octocat/Hello-World/commits/master"): (
            200,
            {"commit": {"tree": {"sha": "tree_sha_master"}}},
            None,
        ),
        ("GET", "/repos/octocat/Hello-World/git/trees/tree_sha_master"): (
            200,
            {"tree": [{"path": "a.txt", "type": "blob"}]},
            None,
        ),
    }

    patch_github_transport(monkeypatch, client, routes)

    out = await client.list_files_from_url(
        repo_url="https://github.com/octocat/Hello-World",
        ref="main",
        recursive=True,
    )
    assert out == ["a.txt"]


@pytest.mark.asyncio
async def test_list_files_from_url_tree_not_found(monkeypatch):
    client = GitHubClient(timeout=5.0, verify=False)

    routes = {
        ("GET", "/repos/octocat/Hello-World/commits/main"): (
            200,
            {"commit": {"tree": {"sha": "tree_sha_404"}}},
            None,
        ),
        ("GET", "/repos/octocat/Hello-World/git/trees/tree_sha_404"): (404, {"message": "not found"}, None),
    }

    patch_github_transport(monkeypatch, client, routes)

    with pytest.raises(NotFoundError):
        await client.list_files_from_url(
            repo_url="https://github.com/octocat/Hello-World",
            ref="main",
            recursive=True,
        )


# ---------------------------
# read_text_file_from_url
# ---------------------------

@pytest.mark.asyncio
async def test_read_text_file_from_url_success(monkeypatch):
    client = GitHubClient(timeout=5.0, verify=False)

    routes = {
        ("GET", "/repos/octocat/Hello-World/contents/README.md"): (200, None, b"hello"),
    }

    patch_github_transport(monkeypatch, client, routes)

    out = await client.read_text_file_from_url(
        repo_url="https://github.com/octocat/Hello-World",
        path="README.md",
        ref="main",
        max_chars=200_000,
    )
    assert out == "hello"


@pytest.mark.asyncio
async def test_read_text_file_from_url_truncates(monkeypatch):
    client = GitHubClient(timeout=5.0, verify=False)

    routes = {
        ("GET", "/repos/octocat/Hello-World/contents/README.md"): (200, None, b"a" * 30),
    }

    patch_github_transport(monkeypatch, client, routes)

    out = await client.read_text_file_from_url(
        repo_url="https://github.com/octocat/Hello-World",
        path="README.md",
        ref="main",
        max_chars=10,
    )
    assert out.startswith("a" * 10)
    assert "TRUNCATED" in out


@pytest.mark.asyncio
async def test_read_text_file_from_url_not_found(monkeypatch):
    client = GitHubClient(timeout=5.0, verify=False)

    routes = {
        ("GET", "/repos/octocat/Hello-World/contents/nope.txt"): (404, {"message": "not found"}, None),
    }

    patch_github_transport(monkeypatch, client, routes)

    with pytest.raises(NotFoundError):
        await client.read_text_file_from_url(
            repo_url="https://github.com/octocat/Hello-World",
            path="nope.txt",
            ref="main",
            max_chars=200_000,
        )


@pytest.mark.asyncio
async def test_read_text_file_from_url_empty_path_raises():
    client = GitHubClient(timeout=5.0, verify=False)

    with pytest.raises(ValidationError):
        await client.read_text_file_from_url(
            repo_url="https://github.com/octocat/Hello-World",
            path="  ",
            ref="main",
            max_chars=200_000,
        )
