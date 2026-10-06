"""The donor-disposition check reports what it found, including the document's own inconsistency.

Failures this pins, each of which made an earlier version of the check misleading:

* matching on substrings reported donors as present because `vad` appears inside unrelated package
  names, so a row with no declaration at all looked installed;
* searching only dependency manifests reported pip-audit and gitleaks as unabsorbed while both are
  actually invoked by the CI workflow;
* matching whole words could not see the four REST clients the check exists to find — the term is
  `crossref`, the identifier is `CrossrefClient` and no word boundary separates them, so their rows
  were credited to `.pyc` caches and docstrings instead;
* a name mentioned in prose or in a string literal was reported as an implementation, which is how
  a donor the repository never adopted (`mozilla`, matching a `developer.mozilla.org` domain entry)
  read as absorbed;
* a first-party module whose *filename* contained a donor name (`shared/audio_vad.py`) was reported
  as a vendored upstream copy.

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


def test_the_check_marks_whether_the_name_is_implemented_named_or_merely_mentioned(tmp_path):
    """Naming a capability in code, naming it only where it is unavailable, and naming it in prose
    are three different findings, and the report must not collapse them."""
    report, document = run_check(tmp_path)
    rows = {row["id"]: row for row in document["rows"]}

    # The four clients are found by their identifiers, in the module that defines them.
    for row_id, term in (("A018", "crossref"), ("A019", "datacite"),
                         ("A020", "openalex"), ("A021", "wikidata")):
        hits = rows[row_id]["source"][term]
        assert hits, rows[row_id]
        assert "shared/evidence_connectors.py" in hits[0], rows[row_id]

    # Readability's identifier is `readabilipy`, and it is both declared and used. The row used to
    # be searched as `mozilla`, which only ever matched documentation URLs, and this assertion then
    # pinned that under-claim as if it were a finding: a wrong term and a passing test together are
    # worse than a failing one, because they look verified.
    readability = rows["A011"]
    assert readability["evidence_state"] == "DECLARED", readability
    assert "shared/adapter_fixtures.py:153" in readability["source"]["readabilipy"], readability

    # A vendored model copy is credited as one, and a donor that exists nowhere is not credited
    # from a licence word: `apache` used to make the Tika sidecar look declared.
    magika = rows["A001"]
    assert magika["evidence_state"] == "DECLARED_AND_VENDORED", magika
    assert magika["vendored"]["magika"] == ["shared/models/magika"], magika
    assert rows["A010"]["evidence_state"] == "NONE", rows["A010"]

    # A stub registry names the capability where it declares itself unavailable, which is not the
    # same fact as implementing it.
    for row_id in ("A002", "A003"):
        stub = rows[row_id]
        assert stub["evidence_state"] == "STUB_IN_SOURCE", stub
        assert "shared/bakeoff_engines.py" in list(stub["stub_source"].values())[0][0], stub

    # A first-party module is not a vendored upstream copy, whatever its filename says.
    assert rows["A016"]["evidence_state"] != "DECLARED_AND_VENDORED", rows["A016"]
    assert not rows["A008"]["vendored"] and not rows["A016"]["vendored"], (rows["A008"], rows["A016"])

    # Compiled caches and build output are never evidence.
    every_locator = [hit for row in document["rows"]
                     for group in ("evidence", "source", "stub_source", "mentions", "vendored")
                     for hits in row[group].values() for hit in hits]
    assert not any("__pycache__" in hit or hit.endswith(".pyc") for hit in every_locator), every_locator[:5]


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
