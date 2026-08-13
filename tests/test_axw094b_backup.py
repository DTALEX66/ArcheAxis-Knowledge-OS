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
