"""Shared preflight guard for the Core ASGI runtime."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager


@contextmanager
def core_runtime_guard(*, validate: Callable[[], object]) -> Iterator[None]:
    """Acquire, prepare, validate, and release a Core runtime lease on failure."""
    from shared import backup

    acquired_here = backup._RUNTIME_LOCK_FD is None
    backup.acquire_runtime_lock()
    try:
        backup.prepare_runtime_database()
        validate()
        yield
    finally:
        if acquired_here:
            backup.release_runtime_lock()
