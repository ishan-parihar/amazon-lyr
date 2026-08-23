"""Min-interval throttle. Amazon sends no rate headers, so we self-throttle."""

from __future__ import annotations

import asyncio
import time


class RateLimiter:
    def __init__(self, min_interval: float = 1.5):
        self.min_interval = min_interval
        self._last_request = 0.0

    async def acquire(self) -> None:
        elapsed = time.monotonic() - self._last_request
        remaining = self.min_interval - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        self._last_request = time.monotonic()
