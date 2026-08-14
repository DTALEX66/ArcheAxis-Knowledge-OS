"""BackendSupervisor — thread-safe backend lifecycle state machine (AXW-RUN-204).

Python-side state machine plus status/logs/restart API. This task does
NOT kill or spawn real processes — ``restart()`` simulates the lifecycle
(``ready -> reconnecting -> ready``) with a configurable (default zero)
delay. Process control is wired by the desktop shell (Rust) later.

State machine (fail-closed): illegal transitions raise ``ValueError``.
"""

from __future__ import annotations

import collections
import os
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from shared.runtime_profile import RuntimeProfile


class BackendSupervisorState(Enum):
    STARTING = "starting"
    MIGRATING = "migrating"
    READY = "ready"
    RECONNECTING = "reconnecting"
    INCOMPATIBLE = "incompatible"
    FAILED = "failed"
    STOPPED = "stopped"


_ALLOWED_TRANSITIONS: dict[BackendSupervisorState, set[BackendSupervisorState]] = {
    BackendSupervisorState.STOPPED: {BackendSupervisorState.STARTING},
    BackendSupervisorState.STARTING: {
        BackendSupervisorState.MIGRATING,
        BackendSupervisorState.FAILED,
        BackendSupervisorState.STOPPED,
    },
    BackendSupervisorState.MIGRATING: {
        BackendSupervisorState.READY,
        BackendSupervisorState.FAILED,
        BackendSupervisorState.STOPPED,
    },
    BackendSupervisorState.READY: {
        BackendSupervisorState.RECONNECTING,
        BackendSupervisorState.FAILED,
        BackendSupervisorState.STOPPED,
    },
    BackendSupervisorState.RECONNECTING: {
        BackendSupervisorState.READY,
        BackendSupervisorState.FAILED,
        BackendSupervisorState.STOPPED,
    },
    BackendSupervisorState.INCOMPATIBLE: {
        BackendSupervisorState.STOPPED,
        BackendSupervisorState.STARTING,
    },
    BackendSupervisorState.FAILED: {
        BackendSupervisorState.STARTING,
        BackendSupervisorState.RECONNECTING,
        BackendSupervisorState.STOPPED,
    },
}


class BackendSupervisor:
    """Thread-safe supervisor state machine with a bounded log ring buffer.

    Hot reload (AXW-DEV-301): when configured with the ``external-dev``
    runtime profile (``reload: true``), ``request_reload()`` (fired by
    the file watcher) and ``reload()`` (manual entry) run the
    ``ready -> reconnecting -> ready`` cycle and record
    ``reload_count`` / ``last_reload_at``. Any other profile (or no
    profile at all) is fail-closed: both entry points raise and the
    state machine never moves.
    """

    def __init__(
        self,
        restart_delay: float = 0.0,
        log_capacity: int = 200,
        profile: RuntimeProfile | None = None,
        reload_interval_ms: int = 1000,
    ) -> None:
        self._lock = threading.Lock()
        self._state = BackendSupervisorState.STOPPED
        self._logs: collections.deque[str] = collections.deque(maxlen=log_capacity)
        self._events: list[dict[str, Any]] = []
        self._started_at: float | None = None
        self._pid: int | None = None
        self._restart_delay = restart_delay
        self._profile = profile
        self._reload_interval_ms = reload_interval_ms
        self._reload_count = 0
        self._last_reload_at: str | None = None

    def set_profile(
        self, profile: RuntimeProfile | None, reload_interval_ms: int | None = None
    ) -> None:
        """Bind a runtime profile (enables/disables hot reload, fail-closed).

        The module-level singleton starts unbound; the app wires the
        active profile here. A non-external-dev profile (or ``None``)
        disables hot reload.
        """
        with self._lock:
            self._profile = profile
            if reload_interval_ms is not None:
                self._reload_interval_ms = reload_interval_ms

    # ── lifecycle ────────────────────────────────────────────────

    def start(self) -> BackendSupervisorState:
        """Bring the backend up: stopped -> starting -> migrating -> ready."""
        with self._lock:
            if self._state not in (
                BackendSupervisorState.STOPPED,
                BackendSupervisorState.FAILED,
                BackendSupervisorState.INCOMPATIBLE,
            ):
                raise ValueError(f"cannot start from state {self._state.value}")
            self._transition_locked(BackendSupervisorState.STARTING, "start requested")
            self._transition_locked(BackendSupervisorState.MIGRATING, "schema migration phase")
            self._pid = os.getpid()
            self._started_at = time.monotonic()
            self._transition_locked(BackendSupervisorState.READY, "backend ready")
            return self._state

    def stop(self) -> BackendSupervisorState:
        """Stop the backend (idempotent when already stopped)."""
        with self._lock:
            if self._state is BackendSupervisorState.STOPPED:
                return self._state
            self._transition_locked(BackendSupervisorState.STOPPED, "stop requested")
            self._pid = None
            self._started_at = None
            return self._state

    def restart(self) -> BackendSupervisorState:
        """Simulated restart: ready -> reconnecting -> ready (delay 0 or short).

        Raises ``ValueError`` when the backend is not running.
        """
        with self._lock:
            if self._state is BackendSupervisorState.STOPPED:
                raise ValueError("backend is not running")
            self._transition_locked(BackendSupervisorState.RECONNECTING, "restart requested")
        if self._restart_delay > 0:
            time.sleep(self._restart_delay)
        with self._lock:
            if self._state is not BackendSupervisorState.RECONNECTING:
                # a concurrent fail()/stop() already moved on — do not clobber it
                return self._state
            self._transition_locked(BackendSupervisorState.READY, "restart completed")
            return self._state

    def fail(self, reason: str) -> BackendSupervisorState:
        """Report a failure (e.g. schema migration error) -> failed state."""
        with self._lock:
            if self._state is BackendSupervisorState.STOPPED:
                raise ValueError("cannot fail a stopped supervisor")
            if self._state is BackendSupervisorState.FAILED:
                return self._state
            self._transition_locked(BackendSupervisorState.FAILED, reason or "failure reported")
            return self._state

    # ── hot reload (AXW-DEV-301) ────────────────────────────────

    def request_reload(self, changed: list[Path] | None = None) -> BackendSupervisorState:
        """Hot-reload entry point fired by the file watcher.

        Gated (fail-closed): only allowed for the ``external-dev``
        profile with ``reload: true``, while READY. Runs the
        ``ready -> reconnecting -> ready`` cycle and records
        ``reload_count`` / ``last_reload_at``.
        """
        with self._lock:
            self._assert_reload_allowed_locked()
            detail = f"{len(changed)} file(s) changed" if changed else "change detected"
            return self._do_reload_locked(f"hot reload requested ({detail})")

    def reload(self) -> BackendSupervisorState:
        """Manual hot-reload entry (same gate and cycle as request_reload).

        Only ``external-dev`` with ``reload: true`` may call this;
        anything else raises ``ValueError`` (fail-closed).
        """
        with self._lock:
            self._assert_reload_allowed_locked()
            return self._do_reload_locked("manual reload requested")

    def _assert_reload_allowed_locked(self) -> None:
        profile = self._profile
        if profile is None or profile.name != "external-dev" or not profile.reload:
            current = "none" if profile is None else f"{profile.name}/reload={profile.reload}"
            raise ValueError(
                "hot reload requires external-dev profile with reload:true "
                f"(current profile: {current})"
            )
        if self._state is BackendSupervisorState.STOPPED:
            raise ValueError("backend is not running")
        if self._state is not BackendSupervisorState.READY:
            raise ValueError(
                f"cannot hot-reload from state {self._state.value} (only ready)"
            )

    def _do_reload_locked(self, reason: str) -> BackendSupervisorState:
        self._transition_locked(BackendSupervisorState.RECONNECTING, reason)
        self._transition_locked(BackendSupervisorState.READY, "hot reload completed")
        self._reload_count += 1
        self._last_reload_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return self._state

    # ── queries ─────────────────────────────────────────────────

    def status(self, tail_n: int = 10) -> dict[str, Any]:
        with self._lock:
            uptime = (
                round(time.monotonic() - self._started_at, 3)
                if self._started_at is not None
                else 0.0
            )
            profile = self._profile
            reload_enabled = (
                profile is not None and profile.name == "external-dev" and profile.reload
            )
            return {
                "state": self._state.value,
                "uptime": uptime,
                "pid": self._pid,
                "logs_tail": list(self._logs)[-tail_n:],
                "reload": {
                    "enabled": reload_enabled,
                    "interval_ms": self._reload_interval_ms,
                    "reload_count": self._reload_count,
                    "last_reload_at": self._last_reload_at,
                },
            }

    def logs(self, tail_n: int = 200) -> list[str]:
        with self._lock:
            return list(self._logs)[-tail_n:]

    def events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    @property
    def state(self) -> BackendSupervisorState:
        with self._lock:
            return self._state

    # ── internals ───────────────────────────────────────────────

    def _transition_locked(self, target: BackendSupervisorState, reason: str) -> None:
        current = self._state
        if target not in _ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"illegal state transition: {current.value} -> {target.value}"
            )
        self._state = target
        self._log(f"state: {current.value} -> {target.value} ({reason})")
        self._events.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "from": current.value,
                "to": target.value,
                "reason": reason,
            }
        )

    def _log(self, message: str) -> None:
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._logs.append(f"[{stamp}] {message}")


# Module-level singleton consumed by the system API (app/workspace/system.py).
supervisor = BackendSupervisor()
