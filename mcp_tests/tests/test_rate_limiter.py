import pytest
import httpx

import core.rate_limiter as rl_mod
from core.rate_limiter import RateLimiter


def _resp(status: int, headers: dict[str, str]):
    req = httpx.Request("GET", "https://example.test/x")
    return httpx.Response(status, headers=headers, request=req)


@pytest.mark.asyncio
async def test_rate_limiter_429_honors_retry_after(monkeypatch):
    calls = []

    async def fake_sleep(seconds: float):
        calls.append(seconds)

    monkeypatch.setattr(rl_mod.asyncio, "sleep", fake_sleep)

    rl = RateLimiter(max_sleep_seconds=60)
    r = _resp(429, {"Retry-After": "10"})

    assert await rl.maybe_sleep_and_retry(r) is True
    assert calls == [10]


@pytest.mark.asyncio
async def test_rate_limiter_429_missing_retry_after_no_retry(monkeypatch):
    calls = []

    async def fake_sleep(seconds: float):
        calls.append(seconds)

    monkeypatch.setattr(rl_mod.asyncio, "sleep", fake_sleep)

    rl = RateLimiter(max_sleep_seconds=60)
    r = _resp(429, {})

    assert await rl.maybe_sleep_and_retry(r) is False
    assert calls == []


@pytest.mark.asyncio
async def test_rate_limiter_429_bounded_sleep(monkeypatch):
    calls = []

    async def fake_sleep(seconds: float):
        calls.append(seconds)

    monkeypatch.setattr(rl_mod.asyncio, "sleep", fake_sleep)

    rl = RateLimiter(max_sleep_seconds=5)
    r = _resp(429, {"Retry-After": "10"})

    assert await rl.maybe_sleep_and_retry(r) is True
    assert calls == [5]


@pytest.mark.asyncio
async def test_rate_limiter_403_rate_limit_reset(monkeypatch):
    calls = []

    async def fake_sleep(seconds: float):
        calls.append(seconds)

    monkeypatch.setattr(rl_mod.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(rl_mod.time, "time", lambda: 100)

    rl = RateLimiter(max_sleep_seconds=60)
    r = _resp(
        403,
        {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "120"},
    )

    assert await rl.maybe_sleep_and_retry(r) is True
    assert calls == [21]
