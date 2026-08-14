"""AXW-DATA-403 — Legacy single-database migration tests.

Builds a small 3-table SQLite source database (one BLOB row, one text
row) and proves the full pipeline: backup (VACUUM INTO, hash-readable,
idempotent, missing-source skip) → dry-run plan → migrate into the
four-asset-domain workspace layout → rollback readback with hash match →
legacy database kept → second migrate is a no-op.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.workspace.migrate import (
    MIGRATION_MANIFEST_NAME,
    backup,
    content_hash,
    dry_run,
    list_backups,
    migrate,
    rollback_readback,
)
from shared.workspace_manifest import create_workspace, load


@pytest.fixture()
def legacy_db(tmp_path: Path) -> Path:
    """A small legacy single database: blob row + text row + ledger row."""
    database = tmp_path / "cognitive_os.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE attachments (id TEXT PRIMARY KEY, name TEXT, blob BLOB)"
        )
        connection.execute(
            "CREATE TABLE kb_documents (id TEXT PRIMARY KEY, title TEXT, content TEXT)"
        )
        connection.execute("CREATE TABLE evidence_claims (id TEXT PRIMARY KEY, claim TEXT)")
        connection.execute(
            "INSERT INTO attachments VALUES ('a1', 'sample.bin', ?)",
            (b"\x00\x01binary\xffpayload",),
        )
        connection.execute(
            "INSERT INTO kb_documents VALUES ('d1', 'First note', 'hello legacy world')"
        )
        connection.execute(
            "INSERT INTO evidence_claims VALUES ('c1', 'migration preserves claims')"
        )
    return database


@pytest.fixture()
def workspace(tmp_path: Path):
    return create_workspace(tmp_path / "root", "ws")


def _backup_files(backup_dir: Path) -> list[Path]:
    return sorted(backup_dir.glob("cognitive_os.pre-*.sqlite"))


def test_backup_creates_hash_readable_snapshot(
    legacy_db: Path, workspace, tmp_path: Path
) -> None:
    backup_dir = tmp_path / "backups"
    result = backup(legacy_db, backup_dir)
    assert result["status"] == "ok"
    assert result["skipped"] is False
    assert result["source_hash"] == content_hash(legacy_db)

    snapshot = Path(str(result["backup_path"]))
    assert snapshot.is_file()
    assert snapshot.suffix == ".sqlite"
    assert "cognitive_os.pre-" in snapshot.name
    # The snapshot's logical content hash matches the source: VACUUM INTO
    # changes raw bytes, so verification is content-based.
    assert content_hash(snapshot) == result["source_hash"]

    # The snapshot is a readable SQLite database containing the data.
    with sqlite3.connect(snapshot) as connection:
        row = connection.execute("SELECT COUNT(*) FROM evidence_claims").fetchone()
        assert int(row[0]) == 1

    # Idempotent: backing up the same source again adds no second file.
    again = backup(legacy_db, backup_dir)
    assert again["skipped"] is True
    assert again["backup_path"] == result["backup_path"]
    assert len(_backup_files(backup_dir)) == 1


def test_backup_missing_source_skips_ok(tmp_path: Path) -> None:
    result = backup(tmp_path / "absent.sqlite", tmp_path / "backups")
    assert result["status"] == "ok"
    assert result["skipped"] is True
    assert result["backup_path"] is None
    assert len(_backup_files(tmp_path / "backups")) == 0


def test_dry_run_plans_without_executing(legacy_db: Path, workspace) -> None:
    result = dry_run(legacy_db, workspace_root_dir(workspace))
    assert result["status"] == "ok"
    plan = result["plan"]
    assert plan is not None
    assert plan["source_hash"] == content_hash(legacy_db)

    by_name = {entry["name"]: entry for entry in plan["tables"]}
    assert set(by_name) == {"attachments", "kb_documents", "evidence_claims"}
    assert by_name["attachments"]["rows"] == 1
    assert by_name["kb_documents"]["rows"] == 1
    assert by_name["evidence_claims"]["rows"] == 1
    # Target paths point into the four-asset-domain layout.
    assert by_name["attachments"]["domain"] == "source_archive"
    assert by_name["kb_documents"]["domain"] == "human_learning_vault"
    assert by_name["evidence_claims"]["domain"] == "evidence_ledger"
    assert "evidence_ledger" in plan["targets"]

    # Dry-run wrote nothing.
    assert not list(workspace_root_dir(workspace).rglob("ledger.sqlite"))
    assert content_hash(legacy_db) == plan["source_hash"]


def test_migrate_moves_data_into_domain_layout(
    legacy_db: Path, workspace, tmp_path: Path
) -> None:
    root = workspace_root_dir(workspace)
    manifest = load(root / "manifest.json")
    result = migrate(legacy_db, root)

    assert result["status"] == "ok"
    assert result["already_migrated"] is False
    assert result["legacy_db_kept"] is True
    assert result["backup_path"]

    # 1) ledger table landed in the evidence-ledger domain.
    ledger_path = Path(manifest.domains["evidence_ledger"].path) / "ledger.sqlite"
    assert ledger_path.is_file()
    with sqlite3.connect(ledger_path) as connection:
        claim = connection.execute(
            "SELECT claim FROM evidence_claims WHERE id = 'c1'"
        ).fetchone()
        assert claim == ("migration preserves claims",)

    # 2) BLOB row became a hash-named file in the source archive.
    archive = Path(manifest.domains["source_archive"].path)
    blob_files = list(archive.rglob("*.bin"))
    assert len(blob_files) == 1
    assert blob_files[0].read_bytes() == b"\x00\x01binary\xffpayload"

    # 3) text row became a Markdown file in the learning vault.
    vault = Path(manifest.domains["human_learning_vault"].path)
    note_files = list(vault.rglob("*.md"))
    assert len(note_files) == 1
    assert "hello legacy world" in note_files[0].read_text(encoding="utf-8")

    # 4) migration manifest records source hash + backup path.
    marker = json.loads((root / MIGRATION_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert marker["source_hash"] == content_hash(legacy_db)
    assert Path(str(marker["backup_path"])).is_file()
    assert marker["legacy_db_kept"] is True

    # 5) the legacy database itself is untouched and still present.
    assert legacy_db.is_file()
    with sqlite3.connect(legacy_db) as connection:
        assert int(connection.execute("SELECT COUNT(*) FROM kb_documents").fetchone()[0]) == 1


def test_rollback_readback_verifies_backup_and_offers_restore_candidate(
    legacy_db: Path, workspace, tmp_path: Path
) -> None:
    backup_result = backup(legacy_db, tmp_path / "backups")
    snapshot = str(backup_result["backup_path"])
    expected_hash = str(backup_result["source_hash"])

    readback = rollback_readback(snapshot, expected_source_hash=expected_hash)
    assert readback["status"] == "ok"
    assert readback["integrity"] == "ok"
    assert readback["hash_matches"] is True
    assert readback["source_hash"] == expected_hash
    # Restore candidate is the backup file itself; current state untouched.
    assert readback["restore_candidate"] == snapshot
    assert "never overwritten" in readback["restore_note"]

    # The backup is directly usable as a database (restore target).
    with sqlite3.connect(snapshot) as connection:
        row = connection.execute("SELECT claim FROM evidence_claims WHERE id = 'c1'").fetchone()
        assert row == ("migration preserves claims",)

    # A hash mismatch must be reported (fail-closed, not silent).
    tampered = rollback_readback(snapshot, expected_source_hash="0" * 64)
    assert tampered["hash_matches"] is False


def test_migrate_is_idempotent_and_keeps_legacy_db(
    legacy_db: Path, workspace, tmp_path: Path
) -> None:
    root = workspace_root_dir(workspace)
    backup_dir = tmp_path / "backups"

    first = migrate(legacy_db, root, backup_dir=backup_dir)
    assert first["already_migrated"] is False
    backups_after_first = len(_backup_files(backup_dir))
    assert backups_after_first == 1

    second = migrate(legacy_db, root, backup_dir=backup_dir)
    assert second["status"] == "ok"
    assert second["already_migrated"] is True
    assert second["backup_path"] == first["backup_path"]
    # No second backup was created.
    assert len(_backup_files(backup_dir)) == backups_after_first
    # The legacy database is still in place after both runs.
    assert legacy_db.is_file()
    assert list_backups(backup_dir) == [str(first["backup_path"])]


def test_migrate_missing_source_skips_ok(workspace, tmp_path: Path) -> None:
    result = migrate(tmp_path / "absent.sqlite", workspace_root_dir(workspace))
    assert result["status"] == "ok"
    assert result["skipped"] is True


def workspace_root_dir(workspace) -> Path:
    """The workspace directory owning the manifest."""
    return Path(workspace.domains["source_archive"].path).parent
