"""AXW-096C: batch import control tests.

Verifies:
- a batch runs to completion with bounded retries (no infinite retry);
- pause stops task pickup and resume continues without losing work;
- shutdown joins workers, persists state and leaves no dangling threads;
- rate limiting spaces task starts;
- the JSONL ledger is append-only and from_checkpoint rehydrates
  completed/failed tasks with digests (silent corruption detectable).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from app.ingestion.batch_controller import BatchError, BatchImportController


def _ok_worker(task_id: str) -> dict[str, str]:
    return {"result_digest": f"sha256:{task_id}"}


def test_batch_runs_to_completion(tmp_path: Path) -> None:
    controller = BatchImportController(checkpoint_path=tmp_path / "ledger.jsonl")
    controller.add_tasks(["a", "b", "c"])
    state = controller.run(_ok_worker, max_concurrent=2)
    assert state.state == "finished"
    assert state.completed == 3
    assert state.failed == 0
    assert len(list((tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines())) >= 6


def test_failures_bounded_no_infinite_retry(tmp_path: Path) -> None:
    controller = BatchImportController(checkpoint_path=tmp_path / "ledger.jsonl", max_retries=1)

    def flaky(task_id: str) -> dict[str, str]:
        raise ValueError("boom")

    controller.add_tasks(["x", "y"])
    state = controller.run(flaky)
    assert state.state == "finished"
    assert state.failed == 2
    assert state.completed == 0
    status = controller.status()
    assert status["results"]["x"]["status"] == "failed"


def test_pause_resume_continues(tmp_path: Path) -> None:
    controller = BatchImportController(checkpoint_path=tmp_path / "ledger.jsonl")
    controller.add_tasks([f"t{i}" for i in range(10)])
    started: list[str] = []

    def slow_worker(task_id: str) -> dict[str, str]:
        started.append(task_id)
        time.sleep(0.01)
        return {"result_digest": f"sha256:{task_id}"}

    thread = threading_for_run(controller, slow_worker, max_concurrent=1)
    thread.start()
    time.sleep(0.05)
    controller.pause()
    paused_snapshot = controller.status()
    assert paused_snapshot["state"] == "paused"
    paused_count = paused_snapshot["completed"]
    time.sleep(0.1)
    # at most the in-flight task may finish; no new tasks may start
    assert controller.status()["completed"] <= paused_count + 1
    controller.resume()
    thread.join(timeout=10)
    assert controller.status()["state"] == "finished"
    assert controller.status()["completed"] == 10


def test_shutdown_safe_exit_no_orphans(tmp_path: Path) -> None:
    controller = BatchImportController(checkpoint_path=tmp_path / "ledger.jsonl")
    controller.add_tasks([f"t{i}" for i in range(20)])

    def slow_worker(task_id: str) -> dict[str, str]:
        time.sleep(0.005)
        return {"result_digest": f"sha256:{task_id}"}

    thread = threading_for_run(controller, slow_worker, max_concurrent=3)
    thread.start()
    time.sleep(0.03)
    controller.shutdown()
    thread.join(timeout=10)
    status = controller.status()
    assert status["state"] == "shutdown"
    assert status["completed"] + status["failed"] + status["skipped"] <= 20
    # no live worker threads remain
    assert all(not t.is_alive() for t in controller._workers)


def test_rate_limiting_spaces_starts(tmp_path: Path) -> None:
    controller = BatchImportController(checkpoint_path=tmp_path / "ledger.jsonl")
    controller.add_tasks(["a", "b", "c"])
    timestamps: list[float] = []

    def timed_worker(task_id: str) -> dict[str, str]:
        timestamps.append(time.monotonic())
        return {"result_digest": task_id}

    controller.run(timed_worker, max_concurrent=1, rate_per_second=20.0)
    assert len(timestamps) == 3
    gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    assert all(gap >= 0.04 for gap in gaps)  # 1/20s = 50ms, allow scheduling slack


def test_ledger_append_only_and_resume(tmp_path: Path) -> None:
    checkpoint = tmp_path / "ledger.jsonl"
    controller = BatchImportController(checkpoint_path=checkpoint)
    controller.add_tasks(["a", "b"])
    controller.run(_ok_worker, max_concurrent=2)
    before_lines = checkpoint.read_text(encoding="utf-8").splitlines()

    # rehydrate: completed tasks carry digests, pending re-queued
    resumed = BatchImportController.from_checkpoint(checkpoint)
    status = resumed.status()
    assert status["results"]["a"]["result_digest"] == "sha256:a"
    assert status["results"]["b"]["status"] == "completed"

    # ledger was appended, never rewritten
    after = checkpoint.read_text(encoding="utf-8").splitlines()
    assert after[: len(before_lines)] == before_lines
    # every line parses
    for line in after:
        json.loads(line)


def test_invalid_args_rejected(tmp_path: Path) -> None:
    with pytest.raises(BatchError):
        BatchImportController(checkpoint_path=tmp_path / "x.jsonl", max_retries=-1)
    controller = BatchImportController(checkpoint_path=tmp_path / "y.jsonl")
    with pytest.raises(BatchError):
        controller.run(_ok_worker, max_concurrent=0)
    with pytest.raises(BatchError):
        controller.run(_ok_worker, rate_per_second=0)


def threading_for_run(controller: BatchImportController, worker, **kwargs):
    import threading

    return threading.Thread(target=lambda: controller.run(worker, **kwargs), daemon=True)
