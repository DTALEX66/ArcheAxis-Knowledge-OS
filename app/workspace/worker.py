"""Bounded background worker for the local Workspace outbox.

The worker deliberately reuses :func:`dispatch_once`: lease ownership,
confirmation proof, checkpoint writes, and failure transitions stay in one
implementation. A bounded run is suitable for a supervisor, scheduled tick,
or deterministic smoke test and never silently claims that work completed.
"""
from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from pathlib import Path

from app.workspace.outbox_dispatcher import dispatch_once

Handler = Callable[[dict[str, object]], object]


def run_worker(
    *,
    db_path: str | Path,
    worker_name: str,
    handler: Handler,
    max_events: int = 100,
    idle_sleep_seconds: float = 0.0,
) -> dict[str, object]:
    """Process pending events until idle or ``max_events`` is reached.

    The returned summary is durable in the database through the dispatcher's
    per-event checkpoints; the summary itself is only an execution projection.
    Failed events are counted and left failed for an explicit retry operation.
    """

    if max_events < 1:
        raise ValueError("workspace worker max_events must be positive")
    if idle_sleep_seconds < 0:
        raise ValueError("workspace worker idle_sleep_seconds cannot be negative")

    processed = 0
    failed = 0
    while processed < max_events:
        result = dispatch_once(db_path=db_path, worker_name=worker_name, handler=handler)
        status = str(result["status"])
        if status == "idle":
            return {"status": "idle", "processed": processed, "failed": failed}
        if status not in {"delivered", "failed"}:
            raise RuntimeError(f"workspace worker returned unknown status: {status}")
        processed += 1
        if status == "failed":
            failed += 1
        if idle_sleep_seconds:
            time.sleep(idle_sleep_seconds)
    return {"status": "max_events", "processed": processed, "failed": failed}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Drain the local Workspace outbox safely")
    parser.add_argument("--db-path", required=True, type=Path)
    parser.add_argument("--worker-name", required=True)
    parser.add_argument("--max-events", type=int, default=100)
    parser.add_argument("--idle-sleep-seconds", type=float, default=0.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    from app.workspace.research_consumer import make_intake_research_handler

    result = run_worker(
        db_path=args.db_path,
        worker_name=args.worker_name,
        handler=make_intake_research_handler(
            db_path=args.db_path,
            consumer_name=f"{args.worker_name}-research-consumer",
        ),
        max_events=args.max_events,
        idle_sleep_seconds=args.idle_sleep_seconds,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if int(result["failed"]) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
