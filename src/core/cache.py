"""Small in-memory TTL cache with simple LRU eviction.

Store values with a monotonic expiration timestamp and evict oldest
entries when maxsize is exceeded.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class CacheEntry(Generic[T]):
    # Stores value + monotonic expiration time
    value: T
    expires_at: float  # time.monotonic()


class TTLCache(Generic[T]):
    # Small TTL cache with simple LRU-ish eviction using OrderedDict
    def __init__(self, *, ttl_seconds: float, maxsize: int) -> None:
        self._ttl = float(ttl_seconds)
        self._maxsize = max(1, int(maxsize))
        self._store: "OrderedDict[object, CacheEntry[T]]" = OrderedDict()

    def get(self, key: object) -> Optional[T]:
        entry = self._store.get(key)
        if entry is None:
            return None

        # Expire entries using time.monotonic to avoid time-shift issues
        if time.monotonic() >= entry.expires_at:
            self._store.pop(key, None)
            return None

        # Move to end to mark as recently used
        self._store.move_to_end(key, last=True)
        return entry.value

    def set(self, key: object, value: T) -> None:
        self._store[key] = CacheEntry(value=value, expires_at=time.monotonic() + self._ttl)
        self._store.move_to_end(key, last=True)

        # Evict oldest entries while over maxsize (simple LRU policy)
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)
