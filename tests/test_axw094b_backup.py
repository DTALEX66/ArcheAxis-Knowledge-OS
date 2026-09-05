"""AXW-094B: backup / verify / restore tests.

Verifies:
- backup snapshots files with a manifest of hashes;
- verification passes intact and detects corruption, missing files,
  partial backups and incompatible versions;
- dry-run restore plans without touching the target;
- real restore is atomic, refuses clobbering without overwrite, and
  writes a receipt.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.exchange.backup import BackupError, create_backup, restore_backup, verify_backup


def _make_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "docs").mkdir(parents=True)
    (source / "raw").mkdir(parents=True)
    (source / "docs" / "note.md").write_text("# note", encoding="utf-8")
    (source / "raw" / "asset.bin").write_bytes(b"\x00\x01\x02")
    (source / "manifest.json").write_text('{"k": "v"}', encoding="utf-8")
    return source


def test_backup_verify_roundtrip(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    backup_dir = tmp_path / "backup"
    manifest = create_backup(source=source, backup_dir=backup_dir)

    assert manifest["schema_version"] == "v1"
    assert manifest["file_count"] == 3
    result = verify_backup(backup_dir)
    assert result["verified_files"] == 3
    # files copied verbatim
    assert (backup_dir / "docs" / "note.md").read_text(encoding="utf-8") == "# note"


def test_verify_detects_corruption(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    backup_dir = tmp_path / "backup"
    create_backup(source=source, backup_dir=backup_dir)

    (backup_dir / "docs" / "note.md").write_text("tampered", encoding="utf-8")
    with pytest.raises(BackupError, match="corrupted backup file"):
        verify_backup(backup_dir)


def test_verify_detects_missing_file(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    backup_dir = tmp_path / "backup"
    create_backup(source=source, backup_dir=backup_dir)

    (backup_dir / "raw" / "asset.bin").unlink()
    with pytest.raises(BackupError, match="missing backup file"):
        verify_backup(backup_dir)


def test_verify_detects_partial_backup(tmp_path: Path) -> None:
    partial = tmp_path / "partial"
    (partial / "docs").mkdir(parents=True)
    (partial / "docs" / "note.md").write_text("# note", encoding="utf-8")
    with pytest.raises(BackupError, match="missing \\(partial"):
        verify_backup(partial)


def test_verify_rejects_incompatible_version(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    backup_dir = tmp_path / "backup"
    create_backup(source=source, backup_dir=backup_dir)

    manifest_path = backup_dir / "backup-manifest.json"
    manifest = manifest_path.read_text(encoding="utf-8").replace('"schema_version": "v1"', '"schema_version": "v9"')
    manifest_path.write_text(manifest, encoding="utf-8")
    with pytest.raises(BackupError, match="incompatible backup version"):
        verify_backup(backup_dir)


def test_dry_run_plans_without_writing(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    backup_dir = tmp_path / "backup"
    create_backup(source=source, backup_dir=backup_dir)

    target = tmp_path / "restored"
    result = restore_backup(backup_dir=backup_dir, target=target, dry_run=True)
    assert result["dry_run"] is True
    assert len(result["plan"]) == 3
    assert not target.exists()  # nothing written


def test_real_restore_writes_and_receipt(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    backup_dir = tmp_path / "backup"
    create_backup(source=source, backup_dir=backup_dir)

    target = tmp_path / "restored"
    result = restore_backup(backup_dir=backup_dir, target=target, dry_run=False)
    assert result["dry_run"] is False
    assert result["restored_files"] == 3
    assert (target / "docs" / "note.md").read_text(encoding="utf-8") == "# note"
    assert (target / "raw" / "asset.bin").read_bytes() == b"\x00\x01\x02"
    assert (target / "restore-receipt.json").is_file()
    # restored content matches the receipt's recorded hashes
    import json

    receipt = json.loads((target / "restore-receipt.json").read_text(encoding="utf-8"))
    assert receipt["restored_files"] == 3
    for entry in receipt["files"]:
        restored_file = target / entry["path"]
        import hashlib

        digest = hashlib.sha256(restored_file.read_bytes()).hexdigest()
        assert digest == entry["sha256"], entry["path"]


def test_restore_refuses_clobber_without_overwrite(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    backup_dir = tmp_path / "backup"
    create_backup(source=source, backup_dir=backup_dir)

    target = tmp_path / "restored"
    (target / "docs").mkdir(parents=True)
    (target / "docs" / "note.md").write_text("existing", encoding="utf-8")
    with pytest.raises(BackupError, match="already exists"):
        restore_backup(backup_dir=backup_dir, target=target, dry_run=False)

    # overwrite=True replaces it
    result = restore_backup(backup_dir=backup_dir, target=target, dry_run=False, overwrite=True)
    assert result["restored_files"] == 3
    assert (target / "docs" / "note.md").read_text(encoding="utf-8") == "# note"


def test_backup_refuses_nonempty_destination(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "stale.txt").write_text("x", encoding="utf-8")
    with pytest.raises(BackupError, match="not empty"):
        create_backup(source=source, backup_dir=occupied)


def test_backup_skips_transient_runtime_artifacts(tmp_path: Path) -> None:
    """Runtime lock files and migration lock ledgers never enter a snapshot.

    Regression for the online-backup crash: the live core holds a Windows
    byte-range lock on ``.archeaxis.sqlite.runtime.lock``, so a naive full
    walk raised PermissionError while hashing it (backup create -> 500).
    """
    source = tmp_path / "source"
    (source / "docs").mkdir(parents=True)
    (source / "docs" / "note.md").write_text("# note", encoding="utf-8")
    # artifacts that must be excluded:
    (source / ".archeaxis.sqlite.runtime.lock").write_text("1", encoding="ascii")
    (source / ".archeaxis.sqlite.abc.migration_operator_locks.lockdb").write_bytes(b"\x00\x01")
    # ordinary content next to them must still be snapshotted:
    (source / "archeaxis.sqlite").write_bytes(b"sqlite-bytes")

    backup_dir = tmp_path / "backup"
    manifest = create_backup(source=source, backup_dir=backup_dir)

    backup_paths = [entry["path"] for entry in manifest["files"]]
    assert "docs/note.md" in backup_paths
    assert "archeaxis.sqlite" in backup_paths
    assert not any(".runtime.lock" in p or ".lockdb" in p for p in backup_paths)
    assert manifest["file_count"] == 2
    assert verify_backup(backup_dir)["verified_files"] == 2


@pytest.mark.skipif(os.name != "nt", reason="Windows byte-range lock semantics")
def test_backup_succeeds_while_lease_file_is_byte_locked(tmp_path: Path) -> None:
    """create_backup must tolerate a byte-range-locked .runtime.lock file.

    The core holds the runtime lease through msvcrt.locking; another handle
    reading the locked byte raises PermissionError, which used to abort the
    whole backup. The lease file is now excluded before hashing.
    """
    import msvcrt

    source = tmp_path / "source"
    (source / "docs").mkdir(parents=True)
    (source / "docs" / "note.md").write_text("# note", encoding="utf-8")
    lock_path = source / ".archeaxis.sqlite.runtime.lock"
    lock_path.write_text("1", encoding="ascii")

    fd = os.open(lock_path, os.O_RDWR)
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        # sanity: a raw read of the locked file is denied (the old crash)
        try:
            lock_path.read_bytes()
        except OSError:
            pass
        else:
            raise AssertionError("expected PermissionError reading byte-locked lease file")

        backup_dir = tmp_path / "backup"
        manifest = create_backup(source=source, backup_dir=backup_dir)
        assert manifest["file_count"] == 1
        assert manifest["files"][0]["path"] == "docs/note.md"
        assert verify_backup(backup_dir)["verified_files"] == 1
    finally:
        try:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        os.close(fd)
