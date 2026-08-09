"""AXW-021A: durable import job reusing the existing Job/Outbox/Receipt store.

Importing a raw asset writes the conversion business state, a durable job, an
outbox event and a command receipt in the SAME SQLite transaction. A failed
conversion rolls back the entire set so no orphaned outbox event survives.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.raw_asset import RawAssetStore
from app.workspace.job_outbox import record_command_in_transaction


class ImportJobError(RuntimeError):
    """Raised when a raw-asset import fails; the enclosing transaction is rolled back."""


@dataclass(frozen=True)
class ImportJobResult:
    command_id: str
    job_id: str
    event_id: str
    raw_sha256: str
    converted: str


class ImportJobStore:
    """Bind raw-asset import + conversion to the durable Job/Outbox/Receipt store."""

    def __init__(self, db_path: str | Path, raw_root: str | Path) -> None:
        self.db_path = Path(db_path)
        self.assets = RawAssetStore(root=raw_root)


def run_import_with_receipt(
    store: ImportJobStore,
    *,
    command_id: str,
    source_name: str,
    blob: bytes,
    convert: Callable[[bytes], str],
) -> ImportJobResult:
    """Import a raw asset and record its job/outbox/receipt in one transaction.

    The original bytes are stored immutably, converted, and a durable job +
    outbox + receipt are written. On any failure everything is rolled back so
    no orphaned outbox event points at a job that never completed.
    """
    wrote_original = False
    with sqlite3.connect(store.db_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        try:
            # 1. Persist the original bytes immutably (content-addressed).
            original = store.assets.store_original(blob, source_name)
            wrote_original = True  # content-addressed file exists for this import
            # 2. Convert; a failure raises and rolls back the whole set.
            converted = convert(blob)
            # 3. Write receipt + job + outbox in the same transaction. A
            #    conflict (same command_id, different input) raises RuntimeError.
            record = record_command_in_transaction(
                connection,
                command_id=command_id,
                command_type="raw_asset.import",
                aggregate_id=source_name,
                payload={"raw_sha256": original.sha256, "source_name": source_name},
                job_state="succeeded",
                event_type="raw_asset.import.completed",
            )
            connection.commit()
            return ImportJobResult(
                command_id=command_id,
                job_id=record["job_id"],
                event_id=record["event_id"],
                raw_sha256=original.sha256,
                converted=converted,
            )
        except Exception as exc:
            # SQLite rolls back. Clean up the byte file written by this attempt
            # so a failed import leaves no orphaned original file behind.
            if wrote_original:
                store.assets.remove_original(original.sha256)
            if isinstance(exc, ImportJobError):
                raise
            raise ImportJobError(str(exc)) from exc
