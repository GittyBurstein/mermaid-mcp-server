"""Utility to interpret server-side throttling signals and sleep when needed.

This encapsulates simple GitHub-relevant logic:
- Honor Retry-After on 429 responses.
- On 403 with X-RateLimit-Remaining==0, use X-RateLimit-Reset to delay retries.
- Bounds sleep to a configurable maximum to avoid long blocking.
"""

from __future__ import annotations

import asyncio
import time
from typing import Mapping, Optional

import httpx


class RateLimiter:
    # GitHub rate-limit / throttle handling
    def __init__(self, *, max_sleep_seconds: int = 60) -> None:
        self._max_sleep_seconds = int(max_sleep_seconds)

    async def maybe_sleep_and_retry(self, response: httpx.Response) -> bool:
        # Returns True if caller should retry after sleeping.
        if response.status_code == 429:
            retry_after = self._parse_int_header(response.headers, "Retry-After")
            if retry_after is not None:
                await self._sleep_bounded(retry_after)
                return True
            return False

        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            reset = self._parse_int_header(response.headers, "X-RateLimit-Reset")
            if reset is not None:
                sleep_for = max(0, reset - int(time.time())) + 1
                await self._sleep_bounded(sleep_for)
                return True

        return False

    async def _sleep_bounded(self, seconds: int) -> None:
        # Sleep for at most _max_sleep_seconds to avoid blocking too long
        await asyncio.sleep(min(int(seconds), self._max_sleep_seconds))

    def _parse_int_header(self, headers: Mapping[str, str], name: str) -> Optional[int]:
        value = headers.get(name)
        if not value:
            return None
        value = value.strip()
        if not value.isdigit():
            return None
        try:
            return int(value)
        except ValueError:
            return None
