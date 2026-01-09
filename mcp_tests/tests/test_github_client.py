import pytest
import httpx

from clients.github.client import GitHubClient, _ListCacheKey, _ReadCacheKey


class _FakeHTTPClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def get(self, url, params=None):
        self.calls.append((url, dict(params or {})))
        return self._responses.pop(0)


def _resp(status: int, url: str, *, json_data=None, text=None, headers=None):
    req = httpx.Request("GET", f"https://example.test{url}")
    if json_data is not None:
        return httpx.Response(status, json=json_data, headers=headers or {}, request=req)
    if text is not None:
        return httpx.Response(status, text=text, headers=headers or {}, request=req)
    return httpx.Response(status, headers=headers or {}, request=req)


@pytest.mark.asyncio
async def test_list_files_cache_hit_skips_network(monkeypatch):
    gh = GitHubClient()
    key = _ListCacheKey(repo_url="https://github.com/o/r", ref="main", recursive=True)
    gh._list_cache.set(key, ["a.py", "b.py"])

    def boom(*args, **kwargs):
        raise AssertionError("Should not create http client on cache hit")

    monkeypatch.setattr(gh, "_create_client", boom)

    out = await gh.list_files_from_url(repo_url="https://github.com/o/r", ref="main", recursive=True)
    assert out == ["a.py", "b.py"]


@pytest.mark.asyncio
async def test_read_text_cache_hit_skips_network(monkeypatch):
    gh = GitHubClient()
    key = _ReadCacheKey(repo_url="https://github.com/o/r", ref="main", path="README.md", max_chars=10)
    gh._read_cache.set(key, "cached")

    def boom(*args, **kwargs):
        raise AssertionError("Should not create http client on cache hit")

    monkeypatch.setattr(gh, "_create_client", boom)

    out = await gh.read_text_file_from_url(repo_url="https://github.com/o/r", path="README.md", ref="main", max_chars=10)
    assert out == "cached"


@pytest.mark.asyncio
async def test_request_retries_once_on_rate_limiter_signal(monkeypatch):
    gh = GitHubClient()

    async def no_pace():
        return None

    monkeypatch.setattr(gh._pacer, "wait", no_pace)

    seen = {"n": 0}

    async def fake_maybe_sleep_and_retry(resp):
        seen["n"] += 1
        return resp.status_code == 429

    monkeypatch.setattr(gh._rate_limiter, "maybe_sleep_and_retry", fake_maybe_sleep_and_retry)

    fake = _FakeHTTPClient(
        responses=[
            _resp(429, "/x", headers={"Retry-After": "1"}),
            _resp(200, "/x"),
        ]
    )

    r = await gh._request(fake, "/x", params={"a": "b"})
    assert r.status_code == 200
    assert len(fake.calls) == 2
