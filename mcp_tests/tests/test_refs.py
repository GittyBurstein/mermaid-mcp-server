import pytest
import httpx

from core.errors import NotFoundError
from clients.github.refs import fetch_tree_sha, resolve_tree_sha


def _json_response(status: int, url: str, data: dict):
    req = httpx.Request("GET", f"https://example.test{url}")
    return httpx.Response(status, json=data, request=req)


def _status_response(status: int, url: str, headers: dict[str, str] | None = None):
    req = httpx.Request("GET", f"https://example.test{url}")
    return httpx.Response(status, headers=headers or {}, request=req)


@pytest.mark.asyncio
async def test_fetch_tree_sha_ok():
    async def request(_client: httpx.AsyncClient, url: str, *, params=None):
        assert url == "/repos/o/r/commits/main"
        return _json_response(200, url, {"commit": {"tree": {"sha": "TREE123"}}})

    async with httpx.AsyncClient() as c:
        sha = await fetch_tree_sha(request, c, owner="o", repo="r", ref="main")
        assert sha == "TREE123"


@pytest.mark.asyncio
async def test_fetch_tree_sha_none_on_404_and_422():
    async def request(_client: httpx.AsyncClient, url: str, *, params=None):
        return _status_response(404, url)

    async with httpx.AsyncClient() as c:
        assert await fetch_tree_sha(request, c, owner="o", repo="r", ref="nope") is None

    async def request2(_client: httpx.AsyncClient, url: str, *, params=None):
        return _status_response(422, url)

    async with httpx.AsyncClient() as c:
        assert await fetch_tree_sha(request2, c, owner="o", repo="r", ref="bad") is None


@pytest.mark.asyncio
async def test_resolve_tree_sha_fallback_to_default_branch():
    calls = []

    async def request(_client: httpx.AsyncClient, url: str, *, params=None):
        calls.append(url)
        if url == "/repos/o/r/commits/main":
            return _status_response(422, url)
        if url == "/repos/o/r":
            return _json_response(200, url, {"default_branch": "dev"})
        if url == "/repos/o/r/commits/dev":
            return _json_response(200, url, {"commit": {"tree": {"sha": "TREEDEV"}}})
        raise AssertionError(f"Unexpected URL: {url}")

    async with httpx.AsyncClient() as c:
        sha = await resolve_tree_sha(request, c, owner="o", repo="r", ref="main")
        assert sha == "TREEDEV"
        assert calls == ["/repos/o/r/commits/main", "/repos/o/r", "/repos/o/r/commits/dev"]


@pytest.mark.asyncio
async def test_resolve_tree_sha_repo_not_found():
    async def request(_client: httpx.AsyncClient, url: str, *, params=None):
        if url.endswith("/commits/main"):
            return _status_response(404, url)
        if url == "/repos/o/r":
            return _status_response(404, url)
        raise AssertionError(f"Unexpected URL: {url}")

    async with httpx.AsyncClient() as c:
        with pytest.raises(NotFoundError):
            await resolve_tree_sha(request, c, owner="o", repo="r", ref="main")


@pytest.mark.asyncio
async def test_resolve_tree_sha_unable_to_resolve():
    async def request(_client: httpx.AsyncClient, url: str, *, params=None):
        if url.endswith("/commits/main"):
            return _status_response(404, url)
        if url == "/repos/o/r":
            return _json_response(200, url, {"default_branch": "dev"})
        if url.endswith("/commits/dev"):
            return _status_response(404, url)
        raise AssertionError(f"Unexpected URL: {url}")

    async with httpx.AsyncClient() as c:
        with pytest.raises(NotFoundError):
            await resolve_tree_sha(request, c, owner="o", repo="r", ref="main")
