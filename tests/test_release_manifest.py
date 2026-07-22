from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def test_release_manifest_is_packaged_truth_and_matches_dependency_lock() -> None:
    from app.release import load_release_manifest, safe_release_summary
    from shared import core_schema, migration
    from shared.config import config
    from shared.knowledge_governance_migration import KNOWLEDGE_GOVERNANCE_MIGRATIONS
    from shared.migration_runner import default_registry

    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "app" / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert load_release_manifest() == manifest
    assert manifest["release"] == {
        "status": "unreleased",
        "channel": "development",
        "public": False,
    }
    assert manifest["product"]["version"] == "0.4.0"
    assert manifest["source"]["commit"] == "unavailable"
    assert manifest["verification"]["embedded_test_counts"] is False
    lock_digest = hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
    assert manifest["dependency_lock"]["digest"] == lock_digest
    manifest_owners = [
        {key: value for key, value in owner.items() if key != "steps"}
        for owner in manifest["migrations"]["owners"]
    ]
    assert manifest_owners == [asdict(owner) for owner in default_registry().owners]
    manifest_steps = {
        owner["owner"]: owner["steps"] for owner in manifest["migrations"]["owners"]
    }
    assert manifest_steps == {
        "core.sqlite": [core_schema.BASELINE_MIGRATION_NAME],
        "fts.cards": [],
        "fts.documents": [],
        "knowledge-governance.sqlite": list(KNOWLEDGE_GOVERNANCE_MIGRATIONS.values()),
        "research.sqlite": [migration.RESEARCH_SCHEMA_MIGRATION_NAME],
        "sleep-loop.sqlite": list(migration.SLEEP_LOOP_MIGRATIONS.values()),
        "taskpack.sqlite": list(migration.TASKPACK_MIGRATIONS.values()),
        "vector.cards": [],
        "vector.documents": [],
        "workspace.sqlite": [
            migration.WORKSPACE_SCHEMA_MIGRATION_NAME,
            migration.WORKSPACE_DELIVERY_RECEIPT_MIGRATION_NAME,
        ],
    }
    project_metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest["product"]["version"] == project_metadata["project"]["version"]
    assert manifest["product"]["version"] == config.get("app.version")
    assert safe_release_summary() == {
        "status": "unreleased",
        "version": "0.4.0",
        "channel": "development",
        "source_commit": "unavailable",
    }


def test_version_and_architecture_endpoints_do_not_copy_stale_claims() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    version = client.get("/version")
    architecture = client.get("/architecture")

    assert version.status_code == 200
    assert version.json()["release"]["status"] == "unreleased"
    assert version.json()["capabilities"]["asr_transcription"] == "not_implemented"
    assert "Human-grounded OCR/ASR accuracy benchmarks" not in version.text
    assert architecture.status_code == 200
    assert "modules" not in architecture.json()
    assert "tests" not in architecture.json()


def test_release_manifest_rejects_extra_fields_and_unverified_public_claims(
    monkeypatch, tmp_path
) -> None:
    from app import release

    source = json.loads(
        (Path(__file__).resolve().parents[1] / "app" / "release-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    target = tmp_path / "release-manifest.json"
    monkeypatch.setattr(release, "_MANIFEST_PATH", target)
    cases = []

    extra = json.loads(json.dumps(source))
    extra["release"]["unverified_claim"] = True
    cases.append(extra)

    public = json.loads(json.dumps(source))
    public["release"].update({"status": "released", "public": True})
    cases.append(public)

    bad_lock = json.loads(json.dumps(source))
    bad_lock["dependency_lock"]["digest"] = "not-a-sha256"
    cases.append(bad_lock)

    for candidate in cases:
        target.write_text(json.dumps(candidate), encoding="utf-8")
        release.load_release_manifest.cache_clear()
        with pytest.raises(RuntimeError):
            release.load_release_manifest()
    release.load_release_manifest.cache_clear()


def test_release_manifest_marks_unimplemented_product_surfaces_truthfully() -> None:
    from app.release import load_release_manifest

    capabilities = load_release_manifest()["capabilities"]
    assert capabilities["workspace_job_outbox_receipts"] == "available"
    assert capabilities["asynchronous_worker"] == "not_implemented"
    assert capabilities["outbox_dispatcher"] == "not_implemented"
    assert capabilities["server_sent_events"] == "not_implemented"
    assert capabilities["interactive_job_center"] == "not_implemented"
    assert capabilities["postgresql_runtime"] == "not_implemented"
    assert capabilities["qdrant_runtime"] == "not_implemented"


def test_truth_docs_do_not_overstate_startup_migration_or_delivery() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    migration = (root / "docs/MIGRATION_OPERATOR.md").read_text(encoding="utf-8")
    handoff = (root / "docs/HANDOFF_2026-07-21.md").read_text(encoding="utf-8")

    assert readme.index("python -m app.runtime_entrypoint migrate") < readme.index(
        "python -m app.runtime_entrypoint core"
    )
    assert "applies all nine registered owners" not in migration
    assert "applies the five registered SQLite owners" in migration
    assert "## 当前候选基线" in handoff
    assert "Hermes cron `" not in handoff
