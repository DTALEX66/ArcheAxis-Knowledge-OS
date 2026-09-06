"""BULK-0907 P19: logical business fixture self-constraints (no real database).

Every fixture under tests/fixtures/vnext/business is validated against its pinned v1
JSON Schema with an offline resolver (no network, no runtime domain execution), its
content hash is checked against the pinned manifest, and negative clones prove each
schema actually rejects a single-field violation. This prepares domain design input
for GPT; it is not a migration or a real-database acceptance.
"""

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts" / "v1"
FIXTURES = ROOT / "tests" / "fixtures" / "vnext" / "business"


def _registry() -> dict[str, dict]:
    return {
        json.loads(p.read_text(encoding="utf-8")).get("$id", p.name):
        json.loads(p.read_text(encoding="utf-8"))
        for p in CONTRACTS.glob("*.schema.json")
    }


def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((CONTRACTS / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, resolver=RefResolver.from_schema(schema, store=_registry()))


def _errors(schema_name: str, payload: dict) -> list:
    return list(_validator(schema_name).iter_errors(payload))


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_every_fixture_matches_its_pinned_hash_and_schema():
    manifest = _load("business-manifest.json")
    for name, meta in manifest["entries"].items():
        raw = (FIXTURES / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == meta["sha256"], name
        payload = json.loads(raw)
        assert not _errors(meta["schema"], payload), (name, meta["schema"])


def test_learning_feedback_negative_event_is_rejected():
    base = _load("learning-feedback.json")
    assert _errors("learning-feedback.schema.json", {**base, "event": "slept"})


def test_machine_feedback_negative_event_and_missing_budget_are_rejected():
    base = _load("machine-feedback.json")
    assert _errors("machine-feedback.schema.json", {**base, "event": "hallucinated"})
    missing = {k: v for k, v in base.items() if k != "context_budget_chars"}
    assert _errors("machine-feedback.schema.json", missing)


def test_job_status_and_assessment_vocabulary_are_closed_enums():
    status = _load("job-status.json")
    assert not _errors("job-status.schema.json", status)
    assert _errors("job-status.schema.json", {**status, "worker_status": "killed"})
    vocab = _load("assessment-vocabulary.json")
    assert not _errors("assessment-vocabulary.schema.json", vocab)
    assert _errors("assessment-vocabulary.schema.json", {**vocab, "review_status": "APPROVED"})


def test_anchor_coordinate_geometry_and_loss_receipt_coverage_are_schema_checked():
    anchor = _load("anchor-coordinate.json")
    assert not _errors("anchor-coordinate.schema.json", anchor)
    bad_geometry = {**anchor, "coordinate": {"kind": "media_time", "offset_ms": 0,
                                             "duration_ms": 0, "track": "audio"}}
    assert _errors("anchor-coordinate.schema.json", bad_geometry)
    receipt = _load("loss-receipt.json")
    assert not _errors("loss-receipt.schema.json", receipt)
    assert _errors("loss-receipt.schema.json", {**receipt, "coverage": 2.0})


def test_manifest_covers_only_present_non_private_files():
    manifest = _load("business-manifest.json")
    files = {p.name for p in FIXTURES.glob("*.json") if p.name != "business-manifest.json"}
    assert files == set(manifest["entries"])
