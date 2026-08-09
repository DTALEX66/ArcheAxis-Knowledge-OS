"""AXW-021A: durable import job reusing the existing Job/Outbox/Receipt store.

Importing a raw asset must produce a durable job, outbox event and command
receipt in the SAME transaction as the conversion business state, so that a
failed conversion leaves no orphaned outbox event behind.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.ingestion.import_job import (
    ImportJobError,
    ImportJobStore,
    run_import_with_receipt,
)


def _migrate(db: Path) -> None:
    from shared.migration_runner import MigrationOperator

    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS sentinel(id TEXT PRIMARY KEY)")
    MigrationOperator(db_path=db, backup_dir=db.parent / "backups").apply("workspace.sqlite")


def test_import_produces_job_outbox_and_receipt(tmp_path) -> None:
    db = tmp_path / "import.sqlite"
    _migrate(db)
    store = ImportJobStore(db_path=db, raw_root=tmp_path / "raw")
    blob = b"# imported markdown\nbody"
    result = run_import_with_receipt(
        store,
        command_id="cmd-import-1",
        source_name="a.md",
        blob=blob,
        convert=lambda raw: "# converted",
    )
    assert result.job_id.startswith("job_")
    assert result.command_id == "cmd-import-1"
    assert result.converted == "# converted"
    assert result.raw_sha256

    with sqlite3.connect(db) as conn:
        job = conn.execute("SELECT state FROM workspace_jobs_v1 WHERE job_id=?", (result.job_id,)).fetchone()
        outbox = conn.execute(
            "SELECT state FROM workspace_outbox_v1 WHERE job_id=?", (result.job_id,)
        ).fetchone()
        receipt = conn.execute(
            "SELECT command_id FROM workspace_command_receipts_v1 WHERE job_id=?",
            (result.job_id,),
        ).fetchone()
    assert job is not None and job[0] == "succeeded"
    assert outbox is not None and outbox[0] == "pending"
    assert receipt is not None and receipt[0] == "cmd-import-1"


def test_failed_conversion_leaves_no_orphan_outbox(tmp_path) -> None:
    """AXW-021A: business state + job/outbox/receipt must be in one transaction.
    A converter failure must roll back the outbox event (no orphaned 'pending'
    event pointing at a job that never completed)."""
    db = tmp_path / "import-fail.sqlite"
    _migrate(db)
    store = ImportJobStore(db_path=db, raw_root=tmp_path / "raw")

    def broken(raw):
        raise ValueError("converter exploded")

    with pytest.raises(ImportJobError):
        run_import_with_receipt(
            store,
            command_id="cmd-import-fail",
            source_name="bad.md",
            blob=b"data",
            convert=broken,
        )

    with sqlite3.connect(db) as conn:
        n_jobs = conn.execute("SELECT COUNT(*) FROM workspace_jobs_v1").fetchone()[0]
        n_outbox = conn.execute("SELECT COUNT(*) FROM workspace_outbox_v1").fetchone()[0]
        n_receipts = conn.execute("SELECT COUNT(*) FROM workspace_command_receipts_v1").fetchone()[0]
    # Rollback means no job/outbox/receipt rows were committed for the failure.
    assert (n_jobs, n_outbox, n_receipts) == (0, 0, 0)
    # The byte file written by store_original must also be removed (no orphan).
    raw_files = [p for p in (tmp_path / "raw").glob("*") if p.is_file()]
    assert raw_files == [], f"orphan raw files after failed import: {raw_files}"


def test_import_idempotent_same_command(tmp_path) -> None:
    """AXW-021A: the same command id with the same semantic input must be
    idempotent — re-importing returns the same result without extra rows."""
    db = tmp_path / "import-idem.sqlite"
    _migrate(db)
    store = ImportJobStore(db_path=db, raw_root=tmp_path / "raw")
    kwargs = dict(
        command_id="cmd-idem",
        source_name="c.md",
        blob=b"# same content",
        convert=lambda raw: "# converted",
    )
    first = run_import_with_receipt(store, **kwargs)
    second = run_import_with_receipt(store, **kwargs)
    assert first.job_id == second.job_id
    assert first.raw_sha256 == second.raw_sha256

    with sqlite3.connect(db) as conn:
        n_jobs = conn.execute("SELECT COUNT(*) FROM workspace_jobs_v1").fetchone()[0]
        n_outbox = conn.execute("SELECT COUNT(*) FROM workspace_outbox_v1").fetchone()[0]
    assert (n_jobs, n_outbox) == (1, 1)


def test_import_conflict_same_command_different_input_leaves_no_orphan(tmp_path) -> None:
    """AXW-021A review: a same-command-id conflict (different blob) must raise
    ImportJobError AND leave no orphaned raw file, exactly like a conversion
    failure."""
    db = tmp_path / "import-conflict.sqlite"
    _migrate(db)
    store = ImportJobStore(db_path=db, raw_root=tmp_path / "raw")

    run_import_with_receipt(
        store,
        command_id="cmd-conflict",
        source_name="d.md",
        blob=b"# first content",
        convert=lambda raw: "# converted",
    )

    with pytest.raises(ImportJobError):
        run_import_with_receipt(
            store,
            command_id="cmd-conflict",
            source_name="d.md",
            blob=b"# different content",
            convert=lambda raw: "# converted-2",
        )

    # The conflicting second write must not leave an orphaned raw file behind.
    raw_files = [p.name for p in (tmp_path / "raw").iterdir() if p.is_file()]
    assert len(raw_files) == 1, f"expected 1 retained raw file, got {raw_files}"
    # And the original job/outbox rows are preserved.
    with sqlite3.connect(db) as conn:
        n_jobs = conn.execute("SELECT COUNT(*) FROM workspace_jobs_v1").fetchone()[0]
    assert n_jobs == 1
