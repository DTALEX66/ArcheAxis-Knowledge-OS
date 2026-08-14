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
from typing import Any


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
    """Thread-safe supervisor state machine with a bounded log ring buffer."""

    def __init__(self, restart_delay: float = 0.0, log_capacity: int = 200) -> None:
        self._lock = threading.Lock()
        self._state = BackendSupervisorState.STOPPED
        self._logs: collections.deque[str] = collections.deque(maxlen=log_capacity)
        self._events: list[dict[str, Any]] = []
        self._started_at: float | None = None
        self._pid: int | None = None
        self._restart_delay = restart_delay

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

    # ── queries ─────────────────────────────────────────────────

    def status(self, tail_n: int = 10) -> dict[str, Any]:
        with self._lock:
            uptime = (
                round(time.monotonic() - self._started_at, 3)
                if self._started_at is not None
                else 0.0
            )
            return {
                "state": self._state.value,
                "uptime": uptime,
                "pid": self._pid,
                "logs_tail": list(self._logs)[-tail_n:],
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
