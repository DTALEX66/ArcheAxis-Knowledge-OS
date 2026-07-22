"""Execution trace — SQLite-backed, replaces JSONL."""

from pathlib import Path

from app.memory.database import list_traces_db, save_trace
from app.schemas import ExecutionTrace


def log_trace(trace: ExecutionTrace, *, db_path: str | Path | None = None) -> None:
    save_trace(trace.model_dump(), db_path=db_path)


def list_traces() -> list[dict]:
    return list_traces_db()
