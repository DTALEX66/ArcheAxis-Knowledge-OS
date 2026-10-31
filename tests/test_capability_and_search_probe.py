"""What the product says it can do, and what searching it actually answered.

Two things are recorded here rather than asserted as good news. The capability list the handshake
returns is empty and the test pins that, so wiring the catalogue through cannot pass unnoticed. The
search attempts are recorded with whatever they answered, and the tests assert only that an outcome
was recorded - search is not reported as working, because it did not answer.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "scripts" / "probes" / "capability_and_search_probe.py"


def test_failed_migration_preserves_the_legacy_shared_workspace(tmp_path, monkeypatch):
    """A new attempt must never delete another attempt's existing evidence."""
    spec = importlib.util.spec_from_file_location("capability_probe_routing", PROBE)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    legacy = tmp_path / ".project-local/runs/capability-search-probe-run"
    legacy.mkdir(parents=True)
    sentinel = legacy / "original-failure.json"
    sentinel.write_bytes(b'{"original_failure":true}\n')
    owned = tmp_path / "owned-attempt"
    owned.mkdir()
    monkeypatch.setattr(probe, "REPO", tmp_path)
    monkeypatch.setattr(probe, "_work_directory", lambda: owned, raising=False)
    monkeypatch.setattr(probe.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 1))
    result = probe.run()
    assert result["failed_step"] == "migrate"
    assert sentinel.read_bytes() == b'{"original_failure":true}\n'
    assert not (legacy / "archeaxis.sqlite").exists()


def test_attempts_have_distinct_roots_in_the_current_owned_run():
    spec = importlib.util.spec_from_file_location("capability_probe_roots", PROBE)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    first = probe._work_directory()
    second = probe._work_directory()
    try:
        assert first != second
        assert first.parent == second.parent
        assert first.parent.name == "capability-search-probe"
        assert first.is_relative_to(Path(os.environ["ARCHEAXIS_RUN_ROOT"]) / "artifacts")
    finally:
        first.rmdir()
        second.rmdir()


def test_foreign_run_is_rejected_without_writing_there(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("capability_probe_foreign", PROBE)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    marker = foreign / "keep.txt"
    marker.write_text("preserve", encoding="utf-8")
    monkeypatch.setenv("ARCHEAXIS_RUN_ROOT", str(foreign))
    with pytest.raises(ValueError, match="different worktree"):
        probe._work_directory()
    assert list(foreign.iterdir()) == [marker]
    assert marker.read_text(encoding="utf-8") == "preserve"


@pytest.fixture(scope="module")
def receipt():
    result = subprocess.run([sys.executable, str(PROBE)], cwd=str(REPO), capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=900)
    payload = (result.stdout or "").strip()
    start = payload.find("{")
    if start < 0:
        pytest.fail(f"probe produced no receipt (exit {result.returncode}): {payload[-400:]}")
    return json.loads(payload[start:])


def test_the_sanctioned_migration_ran_first(receipt):
    steps = {step["step"]: step for step in receipt["steps"]}
    assert steps["migrate"]["exit"] == 0


def test_completed_probe_cleans_only_its_owned_workspace(receipt):
    work = Path(receipt["work_root"])
    assert work.is_relative_to(Path(os.environ["ARCHEAXIS_RUN_ROOT"]) / "artifacts")
    assert Path(receipt["vault_root"]).parent == work
    assert not work.exists()


def test_the_handshake_answers(receipt):
    steps = {step["step"]: step for step in receipt["steps"]}
    assert steps["handshake"]["status"] == 200


def test_the_capability_catalogue_is_still_empty(receipt):
    """Pinned on purpose: this is the Q09 gap, and fixing it must fail this test deliberately.

    app/workspace/system.py builds the handshake with a literal empty list for capabilities, while
    the Rust core has a capability registry. When someone wires the two together, this assertion
    fails and the change has to be acknowledged rather than passing silently.
    """
    assert receipt["handshake_capabilities"] == []
    assert receipt["handshake_capabilities_is_empty_list"] is True


def test_every_search_attempt_recorded_an_outcome(receipt):
    attempts = receipt["searches"]
    assert attempts
    for attempt in attempts:
        assert attempt.get("status") is not None or attempt.get("error"), attempt["root_kind"]


def test_the_search_body_shape_used_is_the_documented_one(receipt):
    """The route takes {root, query}; both keys were sent on every attempt."""
    assert len(receipt["searches"]) == 2
    kinds = {attempt["root_kind"] for attempt in receipt["searches"]}
    assert kinds == {"purpose-built-vault", "fixture-vault"}


def test_the_learning_surface_answers_read_only(receipt):
    """Read-only, and the receipt records its shape."""
    assert receipt["learning_status"] is not None
    if receipt["learning_status"] == 200:
        assert receipt["learning_keys"] is not None


def test_no_review_was_posted_and_no_human_is_claimed(receipt):
    """The human review decision lives on a Core route the authority index marks human-only.

    This asserts that nothing in the receipt records a claim to have made one, so a review cannot
    appear to have happened by a probe running.
    """
    payload = (receipt.get("learning_payload") or "") + (receipt.get("candidates_payload") or "")
    for forbidden in ("reviewer", "approved_by", "human_review"):
        assert forbidden not in payload


def test_the_candidate_listing_answers_without_any_identity(receipt):
    """Read-only, and the receipt records what it returned."""
    assert receipt["candidates_status"] is not None
    if receipt["candidates_status"] == 200:
        assert receipt["candidates_keys"] is not None


def test_the_candidate_listing_attributes_no_decision_to_a_person(receipt):
    """The disposition path has no reviewer field, so a listing cannot name one either.

    This asserts the absence of reviewer-attribution keys rather than their presence, which is the
    property the task depends on: nothing here can be read as a human having approved something.
    """
    payload = receipt.get("candidates_payload") or ""
    for forbidden in ("reviewer", "approved_by", "approvedBy"):
        assert forbidden not in payload


def test_search_answers_for_a_vault_root(receipt):
    """Search works, and this is asserted only after it reproduced in two environments.

    An earlier version of this file pinned that search did not answer, from one local run; CI
    returned 200 and rejected it. The cause of that first local failure was then found to be the
    root I passed - the working directory, full of the database and its sidecars - rather than the
    capability. With a purpose-built vault the route answers here as well as in CI, so a positive
    claim is now reproducible rather than a single machine's behaviour.
    """
    by_kind = {attempt["root_kind"]: attempt for attempt in receipt["searches"]}
    assert by_kind["purpose-built-vault"]["status"] == 200
    assert by_kind["purpose-built-vault"]["match_count"] >= 1
    assert by_kind["fixture-vault"]["status"] == 200
