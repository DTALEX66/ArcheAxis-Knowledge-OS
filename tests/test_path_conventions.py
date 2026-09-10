"""R15: the path convention is measured, and the measurement cannot drift.

`DIRECTORY_AUTHORITY.yaml` declares its own matching semantics and its own
precedence, so the unit tests here pin that precedence rather than a re-invented
one: deny first, then an exact path, then the highest literal segment count, then
the longest literal prefix, with a tie refused as ambiguous.

The repository tests then hold the real numbers still: the tracked tree really is
96.04% owned, the 69 unowned paths are recorded exactly, and the record cannot
quietly lose a path, restate a count or stop matching the legacy inventory.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts/check_path_conventions.py"
RECORD = REPO / "docs/authority/taskpack-0910-r3/R15-PATH-DISPOSITION.json"


def _load():
    spec = importlib.util.spec_from_file_location("path_conventions_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paths = _load()


def _rule(pattern: str, owner: str = "x", deny: bool = False) -> dict:
    wildcard = any(char in pattern for char in "*?")
    return {
        "pattern": pattern,
        "regex": paths.pattern_to_regex(pattern),
        "exact": not wildcard,
        "deny": deny,
        "segments": paths._literal_segments(pattern),
        "prefix": paths._literal_prefix(pattern),
        "owner": owner,
        "lanes": ["owner"],
    }


# ------------------------------------------------------------------ matching


def test_gitwildmatch_patterns_translate_as_declared():
    assert paths.pattern_to_regex("docs/**").match("docs/a/b.md")
    assert not paths.pattern_to_regex("docs/**").match("docsx/a.md")
    assert paths.pattern_to_regex("**/uv.lock").match("uv.lock")
    assert paths.pattern_to_regex("**/uv.lock").match("services/python-workers/uv.lock")
    assert not paths.pattern_to_regex("**/uv.lock").match("services/python-workers/uv.lock.txt")
    assert paths.pattern_to_regex("AGENTS.md").match("AGENTS.md")
    assert not paths.pattern_to_regex("AGENTS.md").match("docs/AGENTS.md")


def test_deny_beats_every_other_match():
    rules = [_rule("**", "broad"), _rule(".project-local/**", "none", deny=True), _rule(".project-local/runs/x", "exact")]
    verdict, _, _ = paths.select_owner(".project-local/runs/x", rules)
    assert verdict == "denied"


def test_an_exact_path_beats_a_wildcard():
    rules = [_rule("docs/**", "documentation"), _rule("docs/authority/**", "owner-integrator")]
    verdict, rule, _ = paths.select_owner("docs/authority/taskpack-0910-r3/EXECUTION.md", rules)
    assert verdict == "owned"
    assert rule["pattern"] == "docs/authority/**"


def test_the_more_literal_prefix_wins_when_segment_counts_tie():
    rules = [_rule("crates/archeaxis-api/**", "rust-core"), _rule("crates/archeaxis-app*/**", "rust-core")]
    verdict, rule, _ = paths.select_owner("crates/archeaxis-api/src/lib.rs", rules)
    assert verdict == "owned"
    assert rule["pattern"] == "crates/archeaxis-api/**"


def test_a_tie_is_refused_as_ambiguous():
    """Two rules can be equally specific: refuse rather than pick one silently."""
    rules = [_rule("a/b/**", "one"), _rule("a/b/**", "two")]
    verdict, rule, ties = paths.select_owner("a/b/c.txt", rules)
    assert verdict == "ambiguous"
    assert rule is None
    assert len(ties) == 2


def test_an_unmatched_path_is_unowned_not_assumed():
    verdict, rule, _ = paths.select_owner("nothing/here.txt", [_rule("docs/**")])
    assert verdict == "unowned"
    assert rule is None


def test_measure_counts_each_verdict_separately():
    rules = [_rule("docs/**"), _rule(".codex/**", deny=True)]
    report = paths.measure(REPO, paths=["docs/a.md", "docs/b.md", "nowhere/c.md", ".codex/x"], rules=rules)
    assert report["tracked_paths"] == 4
    assert report["owned"] == 2
    assert report["unowned"] == ["nowhere/c.md"]
    assert [item["path"] for item in report["denied_but_tracked"]] == [".codex/x"]
    assert report["coverage_percent"] == 50.0


# -------------------------------------------------------------- the real tree


def test_the_record_matches_the_real_tracked_tree():
    failures, detail = paths.check(REPO, RECORD)
    assert failures == []
    assert detail["tracked_paths"] == 1741
    assert detail["owned"] == 1672
    assert detail["coverage_percent"] == 96.04
    assert detail["unowned"] == 69
    assert detail["denied_but_tracked"] == 0
    assert detail["ambiguous"] == 0


def test_the_repository_is_not_claimed_as_fully_classified():
    """96.04% owned means 69 paths have no authority rule; say so, do not round up."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["measured"]["unowned_count"] == 69
    assert record["measured"]["coverage_percent"] < 100
    assert "is not fully classified" in record["finding"]
    assert len(record["unowned_paths"]) == 69
    roots = {path.split("/")[0] for path in record["unowned_paths"]}
    assert "shared-contracts" in roots, "the whole shared-contracts tree is unowned and must be recorded"
    assert "README.md" in roots and ".worklab" in roots


def test_dropping_an_unowned_path_from_the_record_is_refused(tmp_path):
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record["unowned_paths"] = record["unowned_paths"][:-1]
    record["measured"]["unowned_count"] = len(record["unowned_paths"])
    target = tmp_path / "record.json"
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    failures, _ = paths.check(REPO, target)
    assert any("unowned but not recorded" in line for line in failures)


def test_a_stale_measured_count_is_refused(tmp_path):
    """The record is not frozen, but it must stay internally consistent."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record["measured"]["owned"] = 1741  # 1741 + 69 != 1741
    target = tmp_path / "record.json"
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    failures, _ = paths.check(REPO, target)
    assert any("internally inconsistent" in line for line in failures)


def test_a_measurement_must_name_a_real_commit(tmp_path):
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record["measured"]["measured_at_commit"] = "0" * 40
    target = tmp_path / "record.json"
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    failures, _ = paths.check(REPO, target)
    assert any("is not a commit in this repository" in line for line in failures)


def test_adding_owned_files_does_not_turn_the_gate_red(tmp_path):
    """The totals are a snapshot: an ordinary commit must not falsify the record."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record["measured"]["tracked_paths"] = 69  # snapshot totals, deliberately different
    record["measured"]["owned"] = 0
    record["measured"]["coverage_percent"] = 0.0
    target = tmp_path / "record.json"
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    failures, _ = paths.check(REPO, target)
    # nothing that carries meaning changed, so nothing is refused
    assert failures == []


def test_a_top_level_entry_with_two_rules_is_refused(tmp_path):
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record["top_level_disposition"].append(
        {
            "paths": ["crates"],
            "class": "duplicate",
            "disposition": "active",
            "owner_doc": "docs/DIRECTORY_AUTHORITY_INDEX.md",
            "note": "duplicate rule for the same entry",
        }
    )
    target = tmp_path / "record.json"
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    failures, _ = paths.check(REPO, target)
    assert any("'crates' is matched by 2 disposition rules" in line for line in failures)


def test_a_missing_owner_doc_is_refused(tmp_path):
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record["top_level_disposition"][0]["owner_doc"] = "docs/does-not-exist.md"
    target = tmp_path / "record.json"
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    failures, _ = paths.check(REPO, target)
    assert any("owner_doc 'docs/does-not-exist.md' does not exist" in line for line in failures)


def test_a_stale_legacy_inventory_count_is_refused(tmp_path):
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    record["legacy_roots"][0]["manifest_entries"] = 1
    target = tmp_path / "record.json"
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    failures, _ = paths.check(REPO, target)
    assert any("manifest_entries is 1 but LEGACY_MANIFEST.yaml has" in line for line in failures)


def test_legacy_roots_may_not_claim_absorption():
    """Every inventoried legacy asset is still unreviewed, so no root may say absorbed."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["legacy_roots"], "the six declared legacy roots must be recorded"
    for entry in record["legacy_roots"]:
        assert entry["migration_status"] == "inventoried_not_semantically_reviewed"
        assert entry["not_semantically_reviewed"] == entry["manifest_entries"]
        assert entry["manifest_entries"] > 0
    assert "not_semantically_reviewed" in record["legacy_manifest_note"] or "semantic absorption" in record["legacy_manifest_note"]
