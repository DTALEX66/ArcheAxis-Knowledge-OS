"""Thread-safe in-memory sliding-window rate limiting.

The limiter is process-local. It does not coordinate counters across workers or hosts.
"""

from __future__ import annotations

import math
import time
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class RateLimitResult:
    """Result of one atomic rate-limit decision."""

    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RateLimiter:
    """Thread-safe sliding-window rate limiter (in-memory, per-key)."""

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        *,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_requests < 1 or window_seconds < 1 or max_keys < 1:
            raise ValueError("max_requests, window_seconds, and max_keys must be positive")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._clock = clock
        self._windows: dict[str, deque[float]] = {}
        self._last_seen: OrderedDict[str, float] = OrderedDict()
        self._lock = Lock()

    def _discard_expired(self, window: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while window and window[0] <= cutoff:
            window.popleft()

    def _discard_stale_keys(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._last_seen:
            key, last_seen = next(iter(self._last_seen.items()))
            if last_seen > cutoff:
                break
            self._last_seen.popitem(last=False)
            self._windows.pop(key, None)

    def _mark_seen(self, key: str, now: float) -> None:
        self._last_seen[key] = now
        self._last_seen.move_to_end(key)

    def check(self, key: str) -> RateLimitResult:
        """Atomically consume one request or fail closed at the bucket cap."""
        now = self._clock()
        with self._lock:
            self._discard_stale_keys(now)
            window = self._windows.get(key)
            if window is None:
                if len(self._windows) >= self.max_keys:
                    _, oldest_seen = next(iter(self._last_seen.items()))
                    retry_after = max(1, math.ceil(oldest_seen + self.window_seconds - now))
                    return RateLimitResult(
                        allowed=False,
                        limit=self.max_requests,
                        remaining=0,
                        retry_after_seconds=retry_after,
                    )
                window = deque()
                self._windows[key] = window
            self._discard_expired(window, now)
            self._mark_seen(key, now)
            if len(window) < self.max_requests:
                window.append(now)
                return RateLimitResult(
                    allowed=True,
                    limit=self.max_requests,
                    remaining=self.max_requests - len(window),
                    retry_after_seconds=0,
                )
            retry_after = max(1, math.ceil(window[0] + self.window_seconds - now))
            return RateLimitResult(
                allowed=False,
                limit=self.max_requests,
                remaining=0,
                retry_after_seconds=retry_after,
            )

    def allow(self, key: str) -> bool:
        """Backward-compatible boolean rate-limit decision."""
        return self.check(key).allowed

    def release(self, key: str) -> None:
        """Release one successful pre-auth reservation without exposing its key."""
        with self._lock:
            window = self._windows.get(key)
            if not window:
                return
            window.pop()
            if not window:
                self._windows.pop(key, None)
                self._last_seen.pop(key, None)

    def remaining(self, key: str) -> int:
        """Return remaining requests without consuming one."""
        now = self._clock()
        with self._lock:
            self._discard_stale_keys(now)
            window = self._windows.get(key)
            if window is None:
                return self.max_requests
            self._discard_expired(window, now)
            if not window:
                self._windows.pop(key, None)
                self._last_seen.pop(key, None)
                return self.max_requests
            return max(0, self.max_requests - len(window))

    def reset(self, key: str) -> None:
        """Reset the counter for one opaque bucket key."""
        with self._lock:
            self._windows.pop(key, None)
            self._last_seen.pop(key, None)

    def stats(self) -> dict[str, Any]:
        """Return aggregate process-local statistics without exposing bucket keys."""
        now = self._clock()
        with self._lock:
            self._discard_stale_keys(now)
            return {
                "active_keys": len(self._windows),
                "total_requests": sum(len(window) for window in self._windows.values()),
                "max_per_window": self.max_requests,
                "window_seconds": self.window_seconds,
                "max_keys": self.max_keys,
            }


# Backward-compatible singleton. Gateway policies use dedicated limiters per policy.
default_limiter = RateLimiter(max_requests=200, window_seconds=60)
