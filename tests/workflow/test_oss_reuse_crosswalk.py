import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("reuse_inventory", ROOT / "scripts/audit/build_oss_reuse_inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def decisions():
    return json.loads((ROOT / "docs/current/OSS-REUSE-DECISIONS-20261008.json").read_text(encoding="utf-8"))


def test_every_original_row_in_every_source_is_retained_and_duplicates_are_not_collapsed():
    result = inventory.build(ROOT, decisions())
    rows = result["records"]
    assert len([r for r in rows if r["scope"] == "pool"]) == 369
    assert len({r["record_key"] for r in rows}) == len(rows)
    for path, source in result["sources"].items():
        assert sum(r["source_path"] == path for r in rows) == source["row_count"]
        assert len(source["sha256"]) == 64
    assert sum(r["original_name"] == "opendatalab/MinerU" and r["scope"] == "registry" for r in rows) == 2
    assert any(r["original_name"] == "Crossref REST" for r in rows)
    assert all(r["category"] != "A" for r in rows)  # no execution receipt supplied
    assert all(r["reason"] and r["reevaluate_when"] and r["original_record"] for r in rows)


def test_an_alias_collision_and_an_unsupported_absorption_claim_are_refused():
    plan = decisions()
    collision = copy.deepcopy(plan["decisions"][0])
    collision["canonical_name"] = "different-owner/different-product"
    plan["decisions"].append(collision)
    with pytest.raises(ValueError, match="ambiguous"):
        inventory.build(ROOT, plan)
    plan = decisions()
    plan["decisions"][0]["category"] = "A"
    with pytest.raises(ValueError, match="bound verification"):
        inventory.build(ROOT, plan)


def test_only_result_evidence_at_a_named_entry_can_promote_a_candidate():
    plan = decisions()
    result = inventory.build(ROOT, plan, {"capabilities":{"html.structure":{"status":"PASS","level":"SIMULATED","entry":"mock","assertions":["mock"]}}})
    assert not any(r["category"] == "A" for r in result["records"])
    proof = {"capabilities":{"html.structure":{"status":"PASS","level":"INTEGRATED","entry":"POST /jobs/{id}/executions","assertions":["real saved bytes produced text and donor receipt"]}}}
    result = inventory.build(ROOT, plan, proof)
    assert any(r["category"] == "A" and r["capability_id"] == "html.structure" for r in result["records"])
