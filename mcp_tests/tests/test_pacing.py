import pytest

import core.pacing as pacing_mod
from core.pacing import Pacer


@pytest.mark.asyncio
async def test_pacer_disabled_no_sleep(monkeypatch):
    calls = []

    async def fake_sleep(seconds: float):
        calls.append(seconds)

    monkeypatch.setattr(pacing_mod.asyncio, "sleep", fake_sleep)

    p = Pacer(rate_per_sec=0)
    await p.wait()
    await p.wait()

    assert calls == []


@pytest.mark.asyncio
async def test_pacer_enforces_min_interval(monkeypatch):
    calls = []
    # Provide a sequence of monotonic times; when exhausted return the last value
    times_iter = iter([0.0, 0.1, 0.5])

    def fake_monotonic():
        try:
            return next(times_iter)
        except StopIteration:
            # Return the final known time if monkeypatch calls monotonic again
            return 0.5

    async def fake_sleep(seconds: float):
        calls.append(seconds)

    monkeypatch.setattr(pacing_mod.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(pacing_mod.asyncio, "sleep", fake_sleep)

    p = Pacer(rate_per_sec=2.0)  # min interval = 0.5 sec

    await p.wait()  # sets next_allowed = 0.5
    await p.wait()  # sleeps 0.4

    assert pytest.approx(calls[0], rel=1e-6) == 0.4
