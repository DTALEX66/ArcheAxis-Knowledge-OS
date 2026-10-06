"""The donor-disposition check reports what it found, including the document's own inconsistency.

Two failures this pins, both of which made an earlier version of the check misleading:

* matching on substrings reported donors as present because `vad` appears inside unrelated package
  names, so a row with no declaration at all looked installed;
* searching only dependency manifests reported pip-audit and gitleaks as unabsorbed while both are
  actually invoked by the CI workflow.

It also pins the vocabulary finding, because it is the reason a per-row verdict cannot be scored:
the rows use five verdicts the document never defines.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "audit" / "oss_disposition_evidence.py"
DISPOSITION = REPO / "docs" / "current" / "AAOS-OSS-DONOR-DISPOSITION-V2-20261002.json"


def run_check(tmp_path: Path) -> tuple[str, dict]:
    out = tmp_path / "evidence.json"
    finished = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--json", str(out)],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="surrogateescape",
    )
    assert finished.returncode == 0, finished.stderr[-800:]
    return finished.stdout, json.loads(out.read_text(encoding="utf-8"))


def test_the_check_separates_evidence_from_the_rows_verdict(tmp_path):
    report, document = run_check(tmp_path)
    rows = {row["id"]: row for row in document["rows"]}
    assert len(rows) == 47

    # A dependency declared in a manifest is evidence, with the place it was found.
    assert rows["C010"]["evidence_state"] == "DECLARED"
    assert any("pyproject.toml" in hit for hit in rows["C010"]["evidence"]["loguru"])

    # A tool the pipeline invokes is absorbed without a manifest entry; missing this reported
    # pip-audit and gitleaks as unabsorbed when they were already running as CI gates.
    for row_id, term in (("A023", "pip-audit"), ("A024", "gitleaks")):
        assert rows[row_id]["evidence_state"] == "DECLARED", rows[row_id]
        assert any(".github/workflows/" in hit for hit in rows[row_id]["evidence"][term]), rows[row_id]

    # A REST capability is absorbed by writing a client, so source is its own evidence class.
    for row_id in ("A018", "A019", "A020", "A021"):
        assert rows[row_id]["evidence_state"] == "IMPLEMENTED_IN_SOURCE", rows[row_id]

    # Nothing in the repository backs these two, and the report says so instead of assuming.
    assert rows["A012"]["evidence_state"] == "NONE", rows["A012"]
    assert rows["A022"]["evidence_state"] == "NONE", rows["A022"]

    # Every row carries both facts, and the verdict's own definition status is one of them.
    assert all("verdict_defined" in row and "evidence_state" in row for row in document["rows"])


def test_the_document_defines_fewer_verdicts_than_its_rows_use(tmp_path):
    report, document = run_check(tmp_path)
    defined = {"REFERENCE", "ADAPTER", "ABSORB", "PROVIDER", "SIDECAR", "BENCHMARK", "REJECT"}
    asserted = json.loads(DISPOSITION.read_text(encoding="utf-8"))["verdict_definitions"]
    assert set(asserted) == defined

    used = {row["disposition"] for row in document["rows"]}
    undefined = used - defined
    assert undefined == {"ADOPT", "CURRENT", "EVALUATE", "REJECT-CORE", "REVIEW-BLOCK"}, undefined
    # The mismatch is stated, not silently resolved by guessing what the author meant.
    assert "used but undefined by the document (5)" in report
    assert all(row["verdict_defined"] == (row["disposition"] in defined) for row in document["rows"])
