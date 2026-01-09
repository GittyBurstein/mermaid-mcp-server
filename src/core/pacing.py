"""
Pacing utilities.

Best-effort client-side smoothing: enforces a minimum interval between requests
to reduce burstiness in async workloads. Not a replacement for server-side rate limits.
"""

from __future__ import annotations

import asyncio
import time


class Pacer:
    def __init__(self, *, rate_per_sec: float) -> None:
        rate = float(rate_per_sec)
        self._min_interval = 0.0 if rate <= 0 else 1.0 / rate

        # Use monotonic time so pacing isn't affected by system clock changes.
        self._next_allowed = 0.0

        # Lock is critical: without it, multiple tasks could read the same
        # _next_allowed and "reserve" the same slot (burst escapes).
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        # No pacing when interval is non-positive.
        if self._min_interval <= 0:
            return

        async with self._lock:
            now = time.monotonic()

            # Choose our slot: either now (if allowed) or the reserved timestamp.
            slot = self._next_allowed if now < self._next_allowed else now

            # Reserve next slot for the caller after us.
            self._next_allowed = slot + self._min_interval

            # Compute how long we need to wait until our slot.
            delay = slot - now

        # Sleep outside the lock to avoid blocking other tasks.
        if delay > 0:
            await asyncio.sleep(delay)
