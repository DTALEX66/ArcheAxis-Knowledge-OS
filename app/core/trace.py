"""Execution trace — SQLite-backed, replaces JSONL."""

from app.memory.database import list_traces_db, save_trace
from app.schemas import ExecutionTrace


def log_trace(trace: ExecutionTrace) -> None:
    save_trace(trace.model_dump())


def list_traces() -> list[dict]:
    return list_traces_db()
