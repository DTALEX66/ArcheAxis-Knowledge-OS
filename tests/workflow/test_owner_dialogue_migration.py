"""Regress the lost retired-reference check without changing frozen source bytes."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "owner_dialogue_migration", ROOT / "scripts/maintenance/verify_owner_dialogue.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def migration(root):
    old = "docs/current/retired.json"
    new = "docs/history/repository-consolidation-20261019/current/retired.json"
    path = root / new
    path.parent.mkdir(parents=True)
    path.write_bytes(b"original bytes\n")
    entry = dict(original_path=old, archive_path=new, bytes=15,
                 sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return old, path, entry


def test_registered_retired_reference_requires_original_identity(tmp_path):
    old, path, entry = migration(tmp_path)
    assert VERIFIER.resolve_reference(tmp_path, old, [entry]) == path
    path.write_bytes(b"replaced bytes\n")
    with pytest.raises(ValueError, match="bytes mismatch"):
        VERIFIER.resolve_reference(tmp_path, old, [entry])


def test_unregistered_and_duplicate_migrations_fail(tmp_path):
    old, _, entry = migration(tmp_path)
    with pytest.raises(ValueError, match="unregistered missing"):
        VERIFIER.resolve_reference(tmp_path, old, [])
    with pytest.raises(ValueError, match="ambiguous"):
        VERIFIER.resolve_reference(tmp_path, old, [entry, entry])


def test_revived_original_cannot_mask_retired_identity(tmp_path):
    old, _, entry = migration(tmp_path)
    original = tmp_path / old
    original.parent.mkdir(parents=True)
    original.write_bytes(b"revived")
    with pytest.raises(ValueError, match="revived"):
        VERIFIER.resolve_reference(tmp_path, old, [entry])


@pytest.mark.parametrize("name", ["../outside", "D:/outside", ".project-local/private", ".env", "docs/../private", "docs\\private", ".npmrc", ".pypirc", "id_rsa", "id_ed25519", "docs/.npmrc"])
def test_public_resolver_rejects_private_and_escaping_paths(tmp_path, name):
    with pytest.raises(ValueError):
        VERIFIER.resolve_reference(tmp_path, name, [])


def test_migration_cannot_route_to_private_or_nonarchive_file(tmp_path):
    old, _, entry = migration(tmp_path)
    for target in [".project-local/private", "docs/history/unregistered.json",
                   "docs/history/repository-consolidation-20261019/../private",
                   "docs/history/repository-consolidation-20261019/.npmrc"]:
        with pytest.raises(ValueError):
            VERIFIER.resolve_reference(tmp_path, old, [dict(entry, archive_path=target)])


def test_selected_missing_archive_fails_document_gate(tmp_path):
    spec = importlib.util.spec_from_file_location("dialogue_gate", ROOT / "scripts/ci/check_document_authority.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    gate.REPO = tmp_path
    gate.load_active_execution = lambda: ({"continuation_context": {"resource_navigation": {
        "owner_dialogue_archive": "docs/history/owner-dialogue-20261019/README.md"}}}, [])
    assert any("owner dialogue archive" in error for error in gate.check_owner_dialogue_archive())


def test_real_archive_has_four_hash_checked_migrations():
    result = VERIFIER.verify()
    assert result["status"] == "PASS"
    assert result["source_records"] == 39
    assert len(result["migration_identities_checked"]) == 4
