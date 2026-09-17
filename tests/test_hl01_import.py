import json
from pathlib import Path

import pytest

from app.evidence.hl01_import import (
    _resolve_source_path,
    import_registry_candidates,
    verify_registry_receipt,
)
from app.evidence.source_store_v2 import SourceConflictError, SourceStoreV2
from shared.migration_runner import MigrationOperator


def test_hl01_registry_import_is_idempotent_and_candidate_only(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "knowledge.sqlite"
    database.touch()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("workspace.sqlite")
    operator.apply("knowledge-governance.sqlite")
    registry = Path(__file__).parents[1] / "docs/current/R5-HL01-SOURCE-REGISTRY.json"
    store = SourceStoreV2(database)
    monkeypatch.chdir(tmp_path)

    first = import_registry_candidates(
        store,
        registry,
        created_at="2026-09-13T00:00:00Z",
        rights_status="owned",
        command_id="hl01-import-1",
    )
    second = import_registry_candidates(
        store,
        registry,
        created_at="2026-09-13T00:00:00Z",
        rights_status="owned",
        command_id="hl01-import-1",
    )

    assert first.imported == 215
    assert first.duplicates == 0
    assert second.imported == 0
    assert second.duplicates == 215
    assert len(first.source_ids) == 215
    assert first.command_id == second.command_id == "hl01-import-1"
    assert first.job_id == second.job_id
    assert first.event_id == second.event_id
    verified = verify_registry_receipt(database, "hl01-import-1")
    assert verified["source_count"] == 215
    assert verified["state"] == "succeeded"
    sources = store.list_sources()
    assert len(sources) == 215
    assert {source.source_id for source in sources} == set(first.source_ids)
    assert all(source.version == 1 and source.original_retained for source in sources)


def test_hl01_source_path_cannot_escape_repository_root() -> None:
    registry = Path(__file__).parents[1] / "docs/current/R5-HL01-SOURCE-REGISTRY.json"
    try:
        _resolve_source_path(registry, "C:/outside/secret.json")
    except ValueError as exc:
        assert "escapes repository root" in str(exc)
    else:
        raise AssertionError("external source path was accepted")


def test_hl01_replay_with_changed_rights_status_is_rejected(tmp_path: Path) -> None:
    database = tmp_path / "rights.sqlite"
    database.touch()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("workspace.sqlite")
    operator.apply("knowledge-governance.sqlite")
    registry = Path(__file__).parents[1] / "docs/current/R5-HL01-SOURCE-REGISTRY.json"
    store = SourceStoreV2(database)
    import_registry_candidates(
        store,
        registry,
        created_at="2026-09-13T00:00:00Z",
        rights_status="owned",
        command_id="hl01-rights-1",
    )
    with pytest.raises(SourceConflictError, match="immutable"):
        import_registry_candidates(
            store,
            registry,
            created_at="2026-09-13T00:00:00Z",
            rights_status="licensed",
            command_id="hl01-rights-1",
        )


def test_hl01_truncated_registry_fails_before_writing(tmp_path: Path) -> None:
    database = tmp_path / "truncated.sqlite"
    database.touch()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("workspace.sqlite")
    operator.apply("knowledge-governance.sqlite")
    original = Path(__file__).parents[1] / "docs/current/R5-HL01-SOURCE-REGISTRY.json"
    payload = json.loads(original.read_text(encoding="utf-8"))
    payload["records"] = payload["records"][:-1]
    tampered = tmp_path / "registry.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    store = SourceStoreV2(database)
    with pytest.raises(ValueError, match="record count mismatch"):
        import_registry_candidates(
            store,
            tampered,
            created_at="2026-09-13T00:00:00Z",
            rights_status="owned",
            command_id="hl01-truncated-1",
        )
    assert store.list_sources() == []


def test_hl01_source_hash_failure_fails_before_any_write(tmp_path: Path) -> None:
    database = tmp_path / "hash.sqlite"
    database.touch()
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "backups")
    operator.apply("workspace.sqlite")
    operator.apply("knowledge-governance.sqlite")
    original = Path(__file__).parents[1] / "docs/current/R5-HL01-SOURCE-REGISTRY.json"
    payload = json.loads(original.read_text(encoding="utf-8"))
    for category in payload["categories"]:
        category["source_path"] = str((Path(__file__).parents[1] / category["source_path"]).resolve())
    for record in payload["records"]:
        record["source_path"] = str((Path(__file__).parents[1] / record["source_path"]).resolve())
    payload["records"][100]["source_sha256"] = "0" * 64
    tampered = tmp_path / "registry-hash.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    store = SourceStoreV2(database)
    with pytest.raises(ValueError, match="hash mismatch"):
        import_registry_candidates(
            store,
            tampered,
            created_at="2026-09-13T00:00:00Z",
            rights_status="owned",
            command_id="hl01-hash-1",
            repository_root=Path(__file__).parents[1],
        )
    assert store.list_sources() == []
