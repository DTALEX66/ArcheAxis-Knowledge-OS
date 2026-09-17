import json
from pathlib import Path


def test_hl01_registry_preserves_r5_source_counts_and_boundaries():
    root = Path(__file__).parents[1]
    registry = json.loads(
        (root / "docs/current/R5-HL01-SOURCE-REGISTRY.json").read_text(encoding="utf-8")
    )

    assert registry["schema"] == "archeaxis.hl01-source-registry/v1"
    assert registry["total_records"] == 215
    assert {item["category"]: item["record_count"] for item in registry["categories"]} == {
        "methods": 40,
        "research": 35,
        "disciplines": 36,
        "resources": 104,
    }
    assert all(item["qualification_state"] == "candidate" for item in registry["categories"])
    assert all(item["activation"] == "not_activated" for item in registry["categories"])
    assert registry["eligibility_boundaries"]["private_history"].startswith("not_accessed")

    records = registry["records"]
    assert len(records) == 215
    assert len({(item["namespace"], item["record_id"]) for item in records}) == 215
    assert all(item["core_id"].startswith("hl01:") for item in records)
    assert all(item["version"] == 1 for item in records)
