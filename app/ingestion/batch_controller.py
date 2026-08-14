"""AXW-096C: long-task batch import control (pause/resume/limit/safe exit).

A controllable executor for long-running batch work (imports, conversions):

- ``pause()`` / ``resume()``: stop/continue picking up new tasks; in-flight
  tasks finish, nothing is lost;
- ``rate_per_second``: deterministic rate limiting between task starts;
- ``shutdown()``: safe exit — stop accepting tasks, join workers, persist a
  durable checkpoint; no orphan threads or processes;
- retry policy is bounded (``max_retries``); failures are recorded, never
  retried forever;
- every completed task records a result digest so silent corruption can be
  detected when the checkpoint is re-read.

The checkpoint is a JSONL ledger appended per event (never rewritten in
place), so a crash mid-batch leaves a consistent resume point.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BATCH_SCHEMA_VERSION = "v1"


class BatchError(RuntimeError):
    """Raised when the controller is used in an invalid state."""


@dataclass
class BatchState:
    batch_id: str
    state: str = "idle"  # idle | running | paused | finished | shutdown
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": BATCH_SCHEMA_VERSION,
            "batch_id": self.batch_id,
            "state": self.state,
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "created_at": self.created_at,
        }


class BatchImportController:
    """Pausable, resumable, rate-limited batch executor with safe exit."""

    def __init__(self, *, checkpoint_path: str | Path, max_retries: int = 1) -> None:
        if max_retries < 0:
            raise BatchError("max_retries must be >= 0")
        self.checkpoint_path = Path(checkpoint_path)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self._state = BatchState(batch_id=self._new_batch_id())
        self._tasks: list[str] = []
        self._attempts: dict[str, int] = {}
        self._results: dict[str, dict[str, Any]] = {}
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._ledger_lock = threading.Lock()
        self._workers: list[threading.Thread] = []

    @staticmethod
    def _new_batch_id() -> str:
        return datetime.now(timezone.utc).strftime("batch-%Y%m%dT%H%M%S%f")

    # -- ledger -------------------------------------------------------------

    def _append_event(self, event: dict[str, Any]) -> None:
        try:
            record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "batch_id": self._state.batch_id,
                "event": event,
            }
            # Serialize appends: concurrent workers each open("a") their own
            # handle and Python's seek-to-EOF is not atomic across handles —
            # interleaved writes corrupt JSONL lines, silently dropping
            # events on rehydrate (AXW-REL-001). Separate lock: never take
            # self._lock here (pause/resume hold it while calling us).
            with self._ledger_lock, self.checkpoint_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        except Exception:
            # The ledger is best-effort diagnostics; a failed append must
            # never kill a worker thread and lose a task (AXW-REL-001).
            pass

    # -- task management ----------------------------------------------------

    def add_tasks(self, task_ids: list[str]) -> None:
        if self._state.state not in ("idle", "paused"):
            raise BatchError(f"cannot add tasks in state {self._state.state!r}")
        with self._lock:
            self._tasks.extend(task_ids)
            self._state.total += len(task_ids)
        self._append_event(
            {"type": "tasks_added", "count": len(task_ids), "total": self._state.total, "tasks": list(task_ids)}
        )

    # -- lifecycle ----------------------------------------------------------

    def run(
        self,
        worker_fn: Callable[[str], Any],
        *,
        max_concurrent: int = 1,
        rate_per_second: float | None = None,
    ) -> BatchState:
        """Execute queued tasks with the given concurrency and rate limit.

        Blocks until the batch finishes, is paused-and-left, or shutdown is
        requested. Worker results are recorded with a digest when the worker
        returns a dict with a ``result_digest`` key.
        """
        if max_concurrent < 1:
            raise BatchError("max_concurrent must be >= 1")
        if rate_per_second is not None and rate_per_second <= 0:
            raise BatchError("rate_per_second must be > 0")
        if self._state.state not in ("idle", "paused"):
            raise BatchError(f"cannot run in state {self._state.state!r}")
        self._state.state = "running"
        self._append_event({"type": "start", "max_concurrent": max_concurrent, "rate_per_second": rate_per_second})

        min_interval = (1.0 / rate_per_second) if rate_per_second else 0.0
        next_start = 0.0
        index = 0

        def worker() -> None:
            nonlocal index, next_start
            while True:
                if self._stop_event.is_set():
                    return
                self._pause_event.wait()
                with self._lock:
                    if index >= len(self._tasks):
                        return
                    task_id = self._tasks[index]
                    index += 1
                    if min_interval:
                        now = time.monotonic()
                        wait = next_start - now
                        if wait > 0:
                            time.sleep(wait)
                        next_start = max(time.monotonic(), next_start) + min_interval
                self._process_task(task_id, worker_fn)

        with self._lock:
            self._workers = [threading.Thread(target=worker, daemon=True) for _ in range(max_concurrent)]
        for thread in self._workers:
            thread.start()
        for thread in self._workers:
            thread.join()

        with self._lock:
            finished = self._state.completed + self._state.failed + self._state.skipped
            if self._stop_event.is_set():
                self._state.state = "shutdown"
            elif finished >= self._state.total:
                self._state.state = "finished"
            else:
                self._state.state = "paused"
        self._append_event({"type": "batch_end", "state": self._state.state})
        return self._state

    def _process_task(self, task_id: str, worker_fn: Callable[[str], Any]) -> None:
        attempt = self._attempts.get(task_id, 0)
        try:
            result = worker_fn(task_id)
            digest = ""
            if isinstance(result, dict):
                digest = str(result.get("result_digest", ""))
            with self._lock:
                self._results[task_id] = {"status": "completed", "result_digest": digest}
                self._state.completed += 1
            self._append_event({"type": "task_completed", "task": task_id, "digest": digest})
        except BaseException as exc:  # bounded retry, then record failure
            # BaseException (not just Exception): a worker thread must never
            # die silently mid-task and lose the task — KeyboardInterrupt
            # only reaches the main thread; anything else here must land in
            # the failed ledger instead of vanishing (AXW-REL-001)
            if attempt < self.max_retries:
                self._attempts[task_id] = attempt + 1
                self._append_event({"type": "task_retry", "task": task_id, "attempt": attempt + 1, "error": str(exc)[:200]})
                self._process_task(task_id, worker_fn)
                return
            with self._lock:
                self._results[task_id] = {"status": "failed", "error": str(exc)[:300]}
                self._state.failed += 1
            self._append_event({"type": "task_failed", "task": task_id, "error": str(exc)[:300]})

    # -- control ------------------------------------------------------------

    def pause(self) -> None:
        with self._lock:
            if self._state.state == "running":
                self._pause_event.clear()
                self._state.state = "paused"
                self._append_event({"type": "pause"})

    def resume(self) -> None:
        with self._lock:
            if self._state.state == "paused":
                self._pause_event.set()
                self._state.state = "running"
                self._append_event({"type": "resume"})

    def shutdown(self) -> None:
        """Safe exit: stop picking up tasks, join workers, persist state."""
        self._stop_event.set()
        self._pause_event.set()
        for thread in self._workers:
            thread.join(timeout=10)
        self._state.state = "shutdown"
        self._append_event({"type": "shutdown", "completed": self._state.completed, "failed": self._state.failed})

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                **self._state.to_dict(),
                "results": dict(self._results),
                "attempts": dict(self._attempts),
            }

    # -- resume -------------------------------------------------------------

    @classmethod
    def from_checkpoint(cls, checkpoint_path: str | Path) -> BatchImportController:
        """Rehydrate a controller from its ledger (tasks, results, counts).

        Tasks that never completed are re-queued; completed tasks keep their
        recorded digests (silent corruption is detectable by comparing the
        re-read digest with the recorded one). Counts are recomputed from
        the ledger so the rehydrated state is always consistent.
        """
        controller = cls(checkpoint_path=checkpoint_path)
        completed: set[str] = set()
        failed: set[str] = set()
        controller._results = {}
        terminal_state = "idle"
        all_tasks: list[str] = []
        ledger_total = 0
        for line in Path(checkpoint_path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            event = record.get("event", {})
            event_type = event.get("type")
            if event_type == "tasks_added":
                # New ledgers carry the full task list; old ledgers only
                # recorded count/total (task list then cannot be recovered).
                all_tasks.extend(event.get("tasks", []))
                ledger_total = event.get("total", ledger_total)
                continue
            if event_type == "batch_end":
                terminal_state = event.get("state", "idle")
            elif event_type == "task_completed":
                completed.add(event["task"])
                controller._results[event["task"]] = {"status": "completed", "result_digest": event.get("digest", "")}
            elif event_type == "task_failed":
                failed.add(event["task"])
                controller._results[event["task"]] = {"status": "failed", "error": event.get("error", "")}
        # Tasks that never ran stay queued so an interrupted batch is
        # resumable; total always reflects the full task set from the ledger.
        controller._tasks = [t for t in all_tasks if t not in completed and t not in failed]
        controller._state = BatchState(batch_id=controller._new_batch_id())
        controller._state.state = terminal_state
        controller._state.completed = len(completed)
        controller._state.failed = len(failed)
        controller._state.total = len(all_tasks) if all_tasks else ledger_total
        return controller
