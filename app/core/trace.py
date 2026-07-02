"""Execution trace — SQLite-backed, replaces JSONL."""
from app.schemas import ExecutionTrace
from app.memory.database import save_trace, list_traces_db


def log_trace(trace: ExecutionTrace) -> None:
    save_trace(trace.model_dump())


def list_traces() -> list[dict]:
    return list_traces_db()
