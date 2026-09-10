"""R15: the format status matrix must be refusable.

The matrix claims what each of the sixteen format groups can do today, so the
checker is only meaningful if it fails when the matrix drifts. Each negative here
starts from the real matrix (a copy of it, in a temp directory) and mutates one
thing: a dropped group, a redefined requirement, an invented route, a route paired
with the wrong worker, a custody-only row that claims extraction, a status without
evidence. The positives run the same checker over the matrix as committed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "check_format_matrix.py"
MATRIX = REPO / "docs/authority/taskpack-0910-r3/R15-FORMAT-STATUS.json"


def _load():
    spec = importlib.util.spec_from_file_location("format_matrix_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_module = _load()


def _matrix_copy(tmp_path: Path) -> tuple[Path, dict]:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    target = tmp_path / "matrix.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target, payload


def _write(target: Path, payload: dict) -> Path:
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _row(payload: dict, row_id: str) -> dict:
    return next(row for row in payload["formats"] if row["format_id"] == row_id)


def _failures(target: Path) -> list[str]:
    failures, _ = check_module.check(target)
    return failures


# ------------------------------------------------------------------- positives


def test_the_committed_matrix_passes_against_the_real_tables():
    failures, detail = check_module.check(MATRIX)
    assert failures == []
    assert detail["rows"] == 16
    assert detail["counts"] == {"complete": 0, "partial": 12, "custody_only": 4}
    # the checker really parsed the code, not an empty set
    assert detail["core_routes_parsed"] == 7
    assert detail["worker_routes_parsed"] == 6


def test_every_group_carries_a_gap_or_a_clean_status(tmp_path):
    """No group may be silent: partial and custody-only rows must state the gap."""
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    for row in payload["formats"]:
        if row["status"] in ("partial", "custody_only"):
            assert row["gap"].strip(), f"{row['format_id']} states no gap"
        assert row["implemented_now"].strip(), f"{row['format_id']} states nothing implemented"
    # and the requirement text is carried, not rewritten
    carried = json.loads((REPO / "docs/authority/taskpack-0907/FORMAT-COVERAGE.json").read_text(encoding="utf-8"))
    assert {row["format_id"] for row in carried["formats"]} == {row["format_id"] for row in payload["formats"]}


# ------------------------------------------------------------------- negatives


def test_a_dropped_group_is_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    payload["formats"] = [row for row in payload["formats"] if row["format_id"] != "F16"]
    payload["coverage_summary"]["total"] = 15
    failures = _failures(_write(target, payload))
    assert any("sixteen carried groups must all be present" in line for line in failures)


def test_a_redefined_requirement_is_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    _row(payload, "F01")["required_output"] = "文本"
    failures = _failures(_write(target, payload))
    assert any("F01: required_output was changed from the carried record" in line for line in failures)


def test_an_invented_route_is_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    row = _row(payload, "F07")
    row["status"] = "partial"
    row["evidence"]["core_routes"] = [
        {"kind": "docx", "capability": "docx.extract", "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    ]
    row["evidence"]["tests"] = ["tests/test_unified_job_contract.py"]
    failures = _failures(_write(target, payload))
    assert any("F07: claims Core route" in line and "not in the ROUTES table" in line for line in failures)


def test_a_route_paired_with_the_wrong_worker_is_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    _row(payload, "F05")["evidence"]["worker_routes"] = [
        {"capability": "pdf.extract", "worker": "services/python-workers/vision/worker_ocr.py"}
    ]
    failures = _failures(_write(target, payload))
    assert any("F05: claims capability 'pdf.extract'" in line for line in failures)


def test_a_custody_only_row_that_claims_extraction_is_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    # F02 (static web/HTML) is still custody-only, so a route claim there is a lie
    assert _row(payload, "F02")["status"] == "custody_only"
    _row(payload, "F02")["evidence"]["core_routes"] = [
        {"kind": "text", "capability": "text.extract", "media_type": "text/plain"}
    ]
    failures = _failures(_write(target, payload))
    assert any("F02: status is custody_only but it claims an extraction route" in line for line in failures)


def test_a_status_without_evidence_is_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    row = _row(payload, "F03")
    row["status"] = "partial"
    row["evidence"]["core_routes"] = []
    failures = _failures(_write(target, payload))
    assert any("F03: status is partial but no Core route is claimed" in line for line in failures)


def test_a_hidden_gap_and_a_stale_summary_are_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    row = _row(payload, "F14")
    row["status"] = "complete"
    row["gap"] = ""
    payload["coverage_summary"]["complete"] = 1
    failures = _failures(_write(target, payload))
    # custody_only evidence is not enough for a complete claim
    assert any("F14: status is complete but no Core route is claimed" in line for line in failures)


def test_a_missing_evidence_path_is_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    _row(payload, "F02")["evidence"]["tests"] = ["crates/archeaxis-archive/tests/does_not_exist.rs"]
    failures = _failures(_write(target, payload))
    assert any("F02: evidence path" in line and "does not exist" in line for line in failures)


def test_a_mismatched_summary_is_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    payload["coverage_summary"]["partial"] = 9
    failures = _failures(_write(target, payload))
    assert any("coverage_summary.partial is 9 but the rows count 12" in line for line in failures)


def test_a_bad_status_word_is_refused(tmp_path):
    target, payload = _matrix_copy(tmp_path)
    _row(payload, "F03")["status"] = "mostly_ok"
    failures = _failures(_write(target, payload))
    assert any("F03: status 'mostly_ok' is not one of" in line for line in failures)
