"""Simple in-memory rate limiter — sliding window per IP/token.

Usage:
    from shared.rate_limit import RateLimiter
    limiter = RateLimiter(max_requests=100, window_seconds=60)
    if not limiter.allow(client_id):
        raise HTTPException(429)
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any


class RateLimiter:
    """Sliding window rate limiter (in-memory, per-key)."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        """Check if a request is allowed. Returns True if under limit."""
        now = time.time()
        window = self._windows[key]

        # Remove expired entries
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.pop(0)

        if len(window) < self.max_requests:
            window.append(now)
            return True
        return False

    def remaining(self, key: str) -> int:
        """Return remaining requests in current window."""
        self.allow(key)  # trigger cleanup
        return max(0, self.max_requests - len(self._windows[key]))

    def reset(self, key: str) -> None:
        """Reset counter for a key."""
        self._windows.pop(key, None)

    def stats(self) -> dict[str, Any]:
        """Return current rate limiter stats."""
        return {
            "active_keys": len(self._windows),
            "total_requests": sum(len(v) for v in self._windows.values()),
            "max_per_window": self.max_requests,
            "window_seconds": self.window_seconds,
        }


# Singleton for use as middleware
default_limiter = RateLimiter(max_requests=200, window_seconds=60)
