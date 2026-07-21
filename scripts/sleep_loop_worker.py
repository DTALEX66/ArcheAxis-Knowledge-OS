"""Standalone worker for HERMES bedtime unattended loop.

Run directly:
    python scripts/sleep_loop_worker.py

PM2:
    pm2 start ecosystem.config.cjs --only hermes-sleep-loop-worker
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _engine():
    from app.sleep_runtime import tick_once
    from shared.sleep_loop_engine import status

    return status, tick_once


def _sleep_seconds() -> int:
    status, _ = _engine()
    current = status()
    cfg = current.get("config", {})
    if not current.get("active"):
        return int(os.getenv("SLEEP_LOOP_IDLE_SECONDS", cfg.get("idle_poll_interval_seconds", 30)))
    if current.get("status") in {"sleeping", "paused", "idle"}:
        return int(cfg.get("idle_poll_interval_seconds", 30))
    return int(cfg.get("active_poll_interval_seconds", 1))


def _validate_runtime_schema() -> None:
    from shared.storage import validate_schema_online

    validate_schema_online()


def main() -> None:
    _validate_runtime_schema()
    print("[sleep-loop-worker] started", flush=True)
    while True:
        try:
            _, tick_once = _engine()
            result = tick_once()
            print(result, flush=True)
            time.sleep(max(1, _sleep_seconds()))
        except KeyboardInterrupt:
            print("[sleep-loop-worker] stopped by KeyboardInterrupt", flush=True)
            raise
        except Exception as exc:  # noqa: BLE001 - daemon must not crash on one tick
            print({"status": "worker_error", "error": str(exc)[:300]}, flush=True)
            time.sleep(30)


if __name__ == "__main__":
    main()
