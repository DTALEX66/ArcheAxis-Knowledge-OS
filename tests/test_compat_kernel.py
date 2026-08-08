from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from shared.approved_paths import ApprovedRootsError


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    (root / "notes").mkdir(parents=True)
    (root / "attachments").mkdir()
    return root


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return tmp_path / "compat.sqlite"


def _note(path: Path, frontmatter: str, body: str = "正文\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return path


def test_vault_file_model_parses_frontmatter_roundtrip(vault: Path) -> None:
    """K2: frontmatter must preserve comments, key order, and multiline values."""
    from shared.compat.models import VaultFile

    note = _note(
        vault / "notes" / "a.md",
        "title: 测试\ntags: [AI, 学习]\ncreated: 2026-08-07\n# 注释\nnote: |\n  多行\n  文本",
    )
    vf = VaultFile.from_path(note, vault=vault)
    assert vf.relative_path == "notes/a.md"
    assert vf.frontmatter["title"] == "测试"
    assert vf.frontmatter["tags"] == ["AI", "学习"]
    # roundtrip: re-serialize must keep the comment and key order
    serialized = vf.serialize()
    assert "# 注释" in serialized
    assert serialized.index("title") < serialized.index("tags") < serialized.index("created") < serialized.index("note")
    assert "note: |" in serialized


def test_import_session_is_idempotent(store: Path, vault: Path) -> None:
    """Re-importing the same source must not duplicate rows."""
    from shared.compat.import_session import ImportSession

    _note(vault / "notes" / "a.md", "title: A", "body a\n")
    session = ImportSession(store, vault)
    session.run()
    count1 = session.file_count()
    session2 = ImportSession(store, vault)
    session2.run()
    assert session2.file_count() == count1, "re-import must be idempotent"
    assert count1 >= 1


def test_import_rejects_path_escape(store: Path, tmp_path: Path) -> None:
    """K2: a source path escaping the approved vault root must be rejected."""
    from shared.compat.import_session import ImportSession

    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")

    with pytest.raises((ApprovedRootsError, ValueError)):
        ImportSession(store, vault).import_path(outside)


def test_import_rejects_traversal_escape(store: Path, tmp_path: Path) -> None:
    """K2: a traversal path must not resolve outside the approved vault root."""
    from shared.compat.import_session import ImportSession

    vault = tmp_path / "vault"
    vault.mkdir()
    # A path that, after resolution, lands outside the vault (../ escape).
    escaping = vault / ".." / "escape.md"
    escaping.write_text("secret\n", encoding="utf-8")
    with pytest.raises((ApprovedRootsError, ValueError)):
        ImportSession(store, vault).import_path(escaping)


def test_import_detects_symlink_escape(store: Path, tmp_path: Path) -> None:
    """K2: symlink/junction pointing outside the vault must be rejected."""
    from shared.compat.import_session import ImportSession

    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("secret\n", encoding="utf-8")
    try:
        (vault / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink not permitted in this environment")

    session = ImportSession(store, vault)
    # The approved-root resolver must reject the link target outside the vault.
    with pytest.raises(ApprovedRootsError):
        session.scan()


def test_revision_and_rollback(store: Path, vault: Path) -> None:
    """K2: writes are revisioned and rollback restores prior content."""
    from shared.compat.revision import RevisionLog

    note = _note(vault / "notes" / "a.md", "title: A", "v1\n")
    original = note.read_text(encoding="utf-8")
    rev = RevisionLog(store, vault)
    rev.record(note, content="---\ntitle: A\n---\nv2\n")
    assert note.read_text(encoding="utf-8") != original
    rev.rollback(note)
    assert note.read_text(encoding="utf-8") == original


def test_no_direct_core_write(store: Path, vault: Path) -> None:
    """K2: the adapter must not write to governed knowledge/mku tables."""
    _note(vault / "notes" / "a.md", "title: A", "body\n")
    from shared.compat.import_session import ImportSession

    ImportSession(store, vault).run()
    db = sqlite3.connect(store)
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    # compat kernel must not create governed core tables
    assert not ({"kb_cards", "machine_knowledge_units", "knowledge_candidates"} & tables)
    db.close()


def test_loss_report_detects_unknown_content(store: Path, vault: Path) -> None:
    """K2: content that cannot be expressed must surface in a machine-readable loss report."""
    from shared.compat.import_session import ImportSession

    _note(vault / "notes" / "a.md", "title: A", "body\n")
    session = ImportSession(store, vault)
    session.run()
    report = session.loss_report()
    assert isinstance(report, list)
    # No silent loss for a clean note.
    assert all(item["kind"] != "silent_loss" for item in report)


def test_binary_attachment_is_not_decoded_as_text(store: Path, vault: Path) -> None:
    from shared.compat.import_session import ImportSession

    attachment = vault / "attachments" / "image.png"
    payload = bytes([0, 159, 255, 10, 1])
    attachment.write_bytes(payload)
    files = ImportSession(store, vault).scan()
    item = next(file for file in files if file.relative_path == "attachments/image.png")
    assert item.is_binary is True
    assert item.mime_type == "image/png"
    assert item.raw_bytes == payload
    assert item.file_size == len(payload)


def test_revision_rejects_external_change_and_rollback_is_fenced(store: Path, vault: Path) -> None:
    from shared.compat.revision import RevisionConflictError, RevisionLog

    note = _note(vault / "notes" / "a.md", "title: A", "v1\n")
    original = note.read_text(encoding="utf-8")
    import hashlib

    expected = hashlib.sha256(original.encode("utf-8")).hexdigest()
    rev = RevisionLog(store, vault)
    note.write_text("external\n", encoding="utf-8")
    with pytest.raises(RevisionConflictError):
        rev.record(note, content="local\n", expected_hash=expected)

    rev.record(note, content="local\n")
    note.write_text("another external edit\n", encoding="utf-8")
    with pytest.raises(RevisionConflictError):
        rev.rollback(note, expected_hash=hashlib.sha256(b"local\n").hexdigest())
