"""The S01 decision table must not call an entry referenced because a short
token happens to appear in ordinary prose."""

from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/maintenance/layout_decision_report.py"
SPEC = importlib.util.spec_from_file_location("layout_decision_report", SCRIPT)
assert SPEC and SPEC.loader
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


@pytest.mark.parametrize("name", ["c", "p", "n", "g", "dist", "state", "inspect", "probe2"])
def test_short_or_generic_names_are_not_distinctive(name):
    assert REPORT.distinctive(name) is False


@pytest.mark.parametrize(
    "name",
    [
        "deeptutor-val",
        "zcode-newcore-20261030",
        "stitch-research-stage-20261022",
        "closure-delivery-blocker-20261026.json",
        "a_long_underscored_name",
    ],
)
def test_long_or_separated_names_are_distinctive(name):
    assert REPORT.distinctive(name) is True


def test_path_token_is_qualified_for_each_kind():
    assert REPORT.path_token(".project-local", "acceptance/") == ".project-local/acceptance"
    assert REPORT.path_token("runs", "ssl-regression") == ".project-local/runs/ssl-regression"
    assert REPORT.path_token("root", "notes.txt") == "notes.txt"


def test_bare_name_alone_is_not_a_strong_reference():
    # Ordinary text mentions "c" and "dist" constantly; that is not evidence.
    assert REPORT.strong_reference(path_hit=False, bare_hit=True, name="c") is False
    assert REPORT.strong_reference(path_hit=False, bare_hit=True, name="dist") is False
    # A distinctive historical name in prose is still a citation.
    assert (
        REPORT.strong_reference(path_hit=False, bare_hit=True, name="deeptutor-val") is True
    )
    # A path-qualified citation always counts.
    assert REPORT.strong_reference(path_hit=True, bare_hit=False, name="c") is True


def test_classify_keeps_the_existing_vocabulary():
    base = {"exists": True, "files": 2}
    assert (
        REPORT.classify(kind=".project-local", name="mystery", referenced=False, run_layout=False, **base)
        == "UNREFERENCED_CANDIDATE"
    )
    assert (
        REPORT.classify(kind=".project-local", name="acceptance", referenced=False, run_layout=False, **base)
        == "PROTECTED_OR_GENERIC"
    )
    assert (
        REPORT.classify(kind="runs", name="ssl-regression", referenced=False, run_layout=True, **base)
        == "RUNS_LAYOUT"
    )
    assert (
        REPORT.classify(kind=".project-local", name="mystery", referenced=True, run_layout=False, **base)
        == "REFERENCED"
    )


def test_path_pattern_has_a_segment_boundary():
    pattern = REPORT.path_pattern(".project-local", "p")
    assert re.search(pattern, "cited as .project-local/p/inside.txt")
    assert re.search(pattern, "cited as .project-local/p\n")
    assert not re.search(pattern, "cited as .project-local/proposals/plan.md")
    assert not re.search(pattern, "cited as .project-local/probe2/x")
    runs = REPORT.path_pattern("runs", "ssl")
    assert not re.search(runs, ".project-local/runs/ssl-regression/x")
    assert re.search(runs, ".project-local/runs/ssl/x")


def test_reference_evidence_separates_path_citation_from_bare_noise(tmp_path):
    repo = tmp_path
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "doc.md").write_text(
        "the decision table names .project-local/foo-bar-20260101/artifact.json\n",
        encoding="utf-8",
    )
    (repo / "prose.md").write_text("the letter c and the word dist appear here\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)

    cited = REPORT.reference_evidence(".project-local", "foo-bar-20260101", repo)
    assert cited == {
        "referenced": True,
        "reference_path": True,
        "reference_bare_name": True,
        "reference_note": "cited by path",
    }

    noisy = REPORT.reference_evidence(".project-local", "c", repo)
    assert noisy["referenced"] is False
    assert noisy["reference_bare_name"] is True
    assert noisy["reference_note"].startswith("bare token matches only")

    absent = REPORT.reference_evidence(".project-local", "nobody-mentions-this-20260101", repo)
    assert absent["referenced"] is False
    assert absent["reference_note"] == "no tracked citation"
