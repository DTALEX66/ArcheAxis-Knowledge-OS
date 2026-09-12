"""External-dev hot reload watcher (AXW-DEV-301).

Poll-based file watcher (mtime + size, no third-party dependency) that
monitors ``*.py`` files under an ``external-dev`` profile's
``source_root`` and fires a callback (the backend supervisor's
``request_reload()``) whenever a change is detected.

Fail-closed rules:

* ``start()`` refuses any profile that is not ``external-dev`` with
  ``reload: true`` — hot reload only ever runs for the external-dev
  profile (task pack §8.2: external modifiable backends only via
  external-dev).
* ``start()`` refuses a missing or non-directory ``source_root``.
* Standard VCS/tooling directories are never scanned: ``.git``,
  ``.venv``, ``.hermes``, ``__pycache__``, ``node_modules``.
* Detected changes are recorded in a bounded ring buffer
  (``last_events``, default capacity 50) and delivered to the callback
  as a list of changed ``Path`` objects.
"""

from __future__ import annotations

import collections
import os
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.runtime_profile import RuntimeProfile

# Directories that are never scanned for Python source changes.
IGNORED_DIRS: frozenset[str] = frozenset(
    {".git", ".venv", ".hermes", ".project-local", "__pycache__", "node_modules"}
)

DEFAULT_POLL_INTERVAL = 1.0
DEFAULT_EVENT_CAPACITY = 50

ChangeCallback = Callable[[list[Path]], None]

_Snapshot = dict[Path, tuple[int, int]]  # path -> (mtime_ns, size)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class HotReloadWatcher:
    """mtime-polling watcher over an external-dev profile's source root.

    ``start()`` snapshots the tree and spawns a daemon thread; each poll
    tick (``interval`` seconds) rescans and compares mtime_ns/size for
    every ``*.py`` file, then delivers changed paths to the callback.
    ``stop()`` is idempotent and joins the thread.
    """

    def __init__(
        self,
        profile: RuntimeProfile,
        callback: ChangeCallback,
        interval: float = DEFAULT_POLL_INTERVAL,
        capacity: int = DEFAULT_EVENT_CAPACITY,
    ) -> None:
        if profile.name != "external-dev" or not profile.reload:
            raise ValueError(
                "hot reload watcher requires profile external-dev with reload:true "
                f"(got name={profile.name!r}, reload={profile.reload!r})"
            )
        if not profile.source_root:
            raise ValueError("hot reload watcher requires profile.source_root")
        source_root = Path(profile.source_root)
        if not source_root.is_dir():
            raise ValueError(f"hot reload source_root is not a directory: {source_root}")
        if interval <= 0:
            raise ValueError(f"hot reload poll interval must be positive, got {interval!r}")
        self._profile = profile
        self._callback = callback
        self._interval = float(interval)
        self._source_root = source_root
        # Bounded ring buffer of change events (public, task contract).
        self.last_events: collections.deque[dict[str, Any]] = collections.deque(
            maxlen=capacity
        )
        self._snapshot: _Snapshot = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ── lifecycle ────────────────────────────────────────────────

    def start(self) -> threading.Thread:
        """Snapshot the source tree and start the polling thread.

        Returns the thread handle. Refuses to run twice (fail-closed).
        """
        if self._thread is not None and self._thread.is_alive():
            raise ValueError("hot reload watcher is already running")
        self._snapshot = self._scan()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="archeaxis-hotreload",
            daemon=True,
        )
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        """Stop the polling thread (idempotent) and join it."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(self._interval * 2.0, 2.0))
        self._thread = None

    # ── polling ──────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            try:
                self._tick()
            except Exception as exc:  # pragma: no cover - defensive
                # A failing scan must never kill the watcher silently;
                # record the error and keep polling.
                self.last_events.append(
                    {"ts": _now_iso(), "path": str(self._source_root), "event": "error",
                     "detail": str(exc)}
                )

    def _tick(self) -> None:
        current = self._scan()
        previous = self._snapshot
        changed: list[Path] = []
        for path, signature in current.items():
            if path not in previous:
                changed.append(path)
                self._record(path, "created")
            elif previous[path] != signature:
                changed.append(path)
                self._record(path, "modified")
        for path in previous:
            if path not in current:
                changed.append(path)
                self._record(path, "deleted")
        self._snapshot = current
        if changed:
            try:
                self._callback(changed)
            except Exception as exc:  # pragma: no cover - defensive
                self.last_events.append(
                    {"ts": _now_iso(), "path": str(self._source_root),
                     "event": "callback_error", "detail": str(exc)}
                )

    def _record(self, path: Path, event: str) -> None:
        self.last_events.append(
            {"ts": _now_iso(), "path": str(path), "event": event}
        )

    def _scan(self) -> _Snapshot:
        """Collect (mtime_ns, size) for every *.py file under source_root."""
        snapshot: _Snapshot = {}
        for root, dirs, files in os.walk(self._source_root):
            dirs[:] = [name for name in dirs if name not in IGNORED_DIRS]
            root_path = Path(root)
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = root_path / name
                try:
                    stat = path.stat()
                except OSError:
                    continue
                snapshot[path] = (stat.st_mtime_ns, stat.st_size)
        return snapshot


# ── module-level convenience API (single default watcher) ──────────

_watcher: HotReloadWatcher | None = None
last_events: collections.deque[dict[str, Any]] = collections.deque(
    maxlen=DEFAULT_EVENT_CAPACITY
)


def start(
    profile: RuntimeProfile,
    callback: ChangeCallback,
    interval: float = DEFAULT_POLL_INTERVAL,
) -> threading.Thread:
    """Start the module-level watcher and return its thread handle.

    Any previously running watcher is stopped first (fail-closed: at
    most one active watcher per process).
    """
    global _watcher
    stop()
    _watcher = HotReloadWatcher(profile=profile, callback=callback, interval=interval)
    _watcher.last_events = last_events  # share the module ring buffer
    return _watcher.start()


def stop() -> None:
    """Stop the module-level watcher (idempotent)."""
    global _watcher
    if _watcher is not None:
        _watcher.stop()
        _watcher = None
    last_events.clear()
