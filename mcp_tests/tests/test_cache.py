import pytest

import core.cache as cache_mod
from core.cache import TTLCache


def test_ttlcache_set_get_and_expire(monkeypatch):
    t = {"now": 0.0}

    def fake_monotonic():
        return t["now"]

    monkeypatch.setattr(cache_mod.time, "monotonic", fake_monotonic)

    c = TTLCache(ttl_seconds=10.0, maxsize=10)

    c.set("k", "v")
    assert c.get("k") == "v"

    t["now"] = 10.0
    assert c.get("k") is None


def test_ttlcache_eviction_by_maxsize(monkeypatch):
    t = {"now": 0.0}

    def fake_monotonic():
        return t["now"]

    monkeypatch.setattr(cache_mod.time, "monotonic", fake_monotonic)

    c = TTLCache(ttl_seconds=100.0, maxsize=2)

    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)

    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_ttlcache_lru_touch_moves_to_end(monkeypatch):
    t = {"now": 0.0}

    def fake_monotonic():
        return t["now"]

    monkeypatch.setattr(cache_mod.time, "monotonic", fake_monotonic)

    c = TTLCache(ttl_seconds=100.0, maxsize=2)

    c.set("a", 1)
    c.set("b", 2)

    assert c.get("a") == 1

    c.set("c", 3)

    assert c.get("a") == 1
    assert c.get("b") is None
    assert c.get("c") == 3
