"""R14: the evidence index must be refusable, or it indexes nothing.

The index exists so an independent auditor can re-check claims, which means its own
rules have to hold: statuses agree with the live state, no claim rests only on an
ignored local receipt, every cited path exists, every slice states its limits, and
neither independent gate is ever recorded as passed by this repository.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "check_evidence_index.py"
INDEX = REPO / "docs/authority/taskpack-0910-r3/R14-EVIDENCE-INDEX.json"
STATE = REPO / "docs/authority/taskpack-0910-r3/STATE.json"


def _load():
    spec = importlib.util.spec_from_file_location("evidence_index_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load()


def _copy(tmp_path: Path, mutate) -> Path:
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    mutate(payload)
    target = tmp_path / "index.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _row(payload: dict, name: str) -> dict:
    return next(row for row in payload["slices"] if row["slice"] == name)


def _failures(target: Path) -> list[str]:
    failures, _ = checker.check(target)
    return failures


# ------------------------------------------------------------------ positives


def test_the_committed_index_passes():
    failures, detail = checker.check(INDEX)
    assert failures == []
    assert detail["slices"] == 17
    assert detail["tracked_evidence"] > 0


def test_every_slice_agrees_with_the_live_state():
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert {row["slice"] for row in index["slices"]} == set(state)
    for row in index["slices"]:
        assert row["status"] == state[row["slice"]]["status"], row["slice"]


def test_no_independent_gate_is_recorded_as_passed():
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    for row in index["slices"]:
        if row["slice"] in ("R14", "R16"):
            assert row["status"] in ("TODO", "BLOCKED_EXTERNAL"), row
            assert row["independent_auditor"], row
            assert not row.get("independent_audit_passed")
            assert "NOT been run" in " ".join(row["limitations"])


# ------------------------------------------------------------------ negatives


def test_a_missing_slice_is_refused(tmp_path):
    target = _copy(tmp_path, lambda payload: payload["slices"].pop(0))
    assert any("missing slices" in line for line in _failures(target))


def test_a_status_that_disagrees_with_the_state_is_refused(tmp_path):
    def mutate(payload):
        _row(payload, "R13")["status"] = "IMPLEMENTED_PENDING_AUDIT"

    failures = _failures(_copy(tmp_path, mutate))
    assert any("R13: the index says" in line and "STATE.json says" in line for line in failures)


def test_a_self_signed_gate_is_refused(tmp_path):
    def mutate(payload):
        _row(payload, "R14")["status"] = "PASS"

    failures = _failures(_copy(tmp_path, mutate))
    assert any("R14: an independent gate may not be recorded as passed" in line for line in failures)
    assert any("R14: the index says 'PASS'" in line for line in failures)


def test_a_gate_without_a_named_auditor_is_refused(tmp_path):
    def mutate(payload):
        del _row(payload, "R16")["independent_auditor"]

    failures = _failures(_copy(tmp_path, mutate))
    assert any("R16: the gate must name who is to decide it" in line for line in failures)


def test_evidence_that_is_only_a_local_receipt_is_refused(tmp_path):
    def mutate(payload):
        row = _row(payload, "R01")
        row["evidence"] = [{"path": ".project-local/runs/r12-census.json", "kind": "receipt"}]

    failures = _failures(_copy(tmp_path, mutate))
    assert any("R01: every cited artifact is an ignored local receipt" in line for line in failures)


def test_a_receipt_marked_outside_the_ignored_tree_is_refused(tmp_path):
    def mutate(payload):
        _row(payload, "R13")["evidence"].append({"path": "docs/authority/r13.json", "kind": "receipt"})

    failures = _failures(_copy(tmp_path, mutate))
    assert any("marked a receipt but is not under .project-local/" in line for line in failures)


def test_a_missing_tracked_path_is_refused(tmp_path):
    def mutate(payload):
        _row(payload, "R15")["evidence"].append({"path": "crates/does-not-exist.rs", "kind": "tracked"})

    failures = _failures(_copy(tmp_path, mutate))
    assert any("cited tracked path crates/does-not-exist.rs does not exist" in line for line in failures)


def test_a_slice_without_a_command_or_without_limits_is_refused(tmp_path):
    def mutate(payload):
        _row(payload, "R03")["command"] = ""
        _row(payload, "R04")["limitations"] = []

    failures = _failures(_copy(tmp_path, mutate))
    assert any("R03: no command is recorded" in line for line in failures)
    assert any("R04: no limitation is recorded" in line for line in failures)


def test_a_command_naming_a_script_that_does_not_exist_is_refused(tmp_path):
    def mutate(payload):
        _row(payload, "R02")["command"] = "scripts/ci/not-a-script.bat -p archeaxis-domain"

    failures = _failures(_copy(tmp_path, mutate))
    assert any("names scripts/ci/not-a-script.bat" in line for line in failures)


def test_a_command_with_no_runnable_script_is_refused(tmp_path):
    def mutate(payload):
        _row(payload, "R05")["command"] = "cargo test -p archeaxis-application"

    failures = _failures(_copy(tmp_path, mutate))
    assert any("R05: the command names no script a reader could run" in line for line in failures)


def test_missing_not_claimed_list_is_refused(tmp_path):
    def mutate(payload):
        payload["not_claimed"] = []

    failures = _failures(_copy(tmp_path, mutate))
    assert any("must carry a not_claimed list" in line for line in failures)
