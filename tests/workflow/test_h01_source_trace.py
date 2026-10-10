"""H01 local source regressions against the real registered input CSVs/ledger.

No copied fixture baseline is generated. Missing local registered source bytes fail
collection/setup honestly; this gate is not an automatically enabled cloud-CI gate.
"""
from __future__ import annotations

import copy
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/check_h01_source_trace.py"
spec = importlib.util.spec_from_file_location("h01_source_gate", SCRIPT)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


@pytest.fixture(scope="module")
def current_sources():
    if os.environ.get("CI") and not os.environ.get("AAOS_H01_REPO"):
        pytest.skip("H01 original containers are owner-local; cloud tests do not qualify local preservation. Supply AAOS_H01_REPO explicitly to require this gate.")
    repo = Path(os.environ.get("AAOS_H01_REPO", str(ROOT)))
    scope = gate.owning_root(repo)
    trace = Path(os.environ.get("AAOS_H01_TRACE", str(repo / gate.TRACE)))
    document = gate.load(trace, scope)
    # This loads original96 CSV, independent186 JSON, original270 ledger,
    # original97 CSV and source6 bytes, rather than trusting projection counts.
    assert gate.validate(document, repo, scope) == []
    return repo, scope, document


def problems(current_sources, mutation):
    repo, scope, baseline = current_sources
    document = copy.deepcopy(baseline)
    mutation(document)
    return gate.validate(document, repo, scope)


def test_real_input_source_preservation_and_96_22_270_coverage(current_sources):
    repo, scope, document = current_sources
    assert gate.validate(document, repo, scope) == []


def test_missing_historical_locator_cannot_hide_270_coverage(current_sources):
    result = problems(current_sources, lambda d: d["source_locators"].pop(0))
    assert any("426 unique" in item for item in result)
    assert any("old source row hash" in item for item in result)


def test_duplicate_namespace_locator_fails(current_sources):
    def mutate(d):
        d["source_locators"].append(copy.deepcopy(d["source_locators"][0]))
    assert any("426 unique" in item for item in problems(current_sources, mutate))


def test_original96_row_hash_tamper_fails(current_sources):
    def mutate(d):
        next(row for row in d["source_locators"] if row["source_locator_key"] == "FINAL-20261009:R003")["source_row_sha256"] = "0" * 64
    assert any("original96 row hash: R003" in item for item in problems(current_sources, mutate))


def test_invented_target_or_erased_disposition_fails(current_sources):
    def mutate(d):
        d["source_locators"][0]["target_slices"] = ["NOT_A_TASK"]
        d["source_locators"][0]["reason"] = ""
    result = problems(current_sources, mutate)
    assert any("old destination/reason preservation" in item for item in result)
    assert any("unknown target slice" in item for item in result)


def test_missing_original_page_row_fails(current_sources):
    assert any("22 original" in item for item in problems(current_sources, lambda d: d["page_coverage"].pop()))


def test_missing_or_false_pass_child_fails(current_sources):
    def mutate(d):
        d["design_source_signals"].pop()
        d["design_source_signals"][0]["implementation_qualification"] = "PASS"
    result = problems(current_sources, mutate)
    assert any("186 source-signal" in item for item in result)
    assert any("design false qualification" in item for item in result)


def test_invented_independent_lexical_match_fails(current_sources):
    def mutate(d):
        d["design_source_signals"][0]["independent_exact_text_sources"] = ["invented-source.md"]
    assert any("independent lexical signal" in item for item in problems(current_sources, mutate))


def test_source_container_hash_tamper_fails(current_sources):
    def mutate(d):
        d["independent_source_readback"][0]["sha256"] = "0" * 64
        d["input_bindings"]["source_register"]["sha256"] = "0" * 64
    result = problems(current_sources, mutate)
    assert any("six source byte preservation" in item for item in result)
    assert any("source binding: source_register" in item for item in result)


def test_97_table_never_claims_all_original_bodies_or_public_artifacts(current_sources):
    def mutate(d):
        d["asset_read_scope"]["all97_original_bodies_verified"] = True
        d["evidence_references"][-1]["publication"] = "PUBLIC"
    result = problems(current_sources, mutate)
    assert "97 false body verification" in result
    assert "local artifact claimed public" in result


def test_wrong_current_authority_or_progress_db_fails(current_sources):
    def mutate(d):
        d["current_authority"]["active_taskpack"] = "docs/authority/taskpack-0919-r6"
        d["source_locators"][0]["completed"] = True
    result = problems(current_sources, mutate)
    assert "current authority routing" in result
    assert "second progress database field" in result


def test_outside_and_private_sources_rejected_before_stat(monkeypatch, tmp_path):
    def forbidden_stat(self):
        raise AssertionError(f"forbidden target was probed: {self}")
    monkeypatch.setattr(Path, "lstat", forbidden_stat)
    for path in (tmp_path.parent / "outside.txt", tmp_path / ".codex/sessions/item.json", tmp_path / "../outside.txt", tmp_path / ".env"):
        with pytest.raises(ValueError):
            gate.safe_path(path, tmp_path)


def test_source_root_cannot_widen_project_boundary(current_sources):
    repo, scope, document = current_sources
    with pytest.raises(ValueError, match="project owning root"):
        gate.validate(document, repo, scope.parent)
