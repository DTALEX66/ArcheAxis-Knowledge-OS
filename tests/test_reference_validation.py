"""Planted-fault tests for the strict reference validator.

A control that cannot fail guards nothing, so every fault below is *planted* in a
temporary tree and asserted to turn red in a specific verdict class -- and one control
case proves the validator can still say PASS when the citation is genuinely exact.

The last test re-implements the retired tool's own rule (rglob by basename) on the same
fixtures, to prove these faults are that tool's blind spot rather than a straw man.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "audit" / "reference_validation.py"


def _load():
    spec = importlib.util.spec_from_file_location("reference_validation_under_test", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rv = _load()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def tree(tmp_path: Path):
    """A record tree with a cited evidence directory and a decoy sibling."""
    evidence = tmp_path / "evidence"
    cited = evidence / "run-a-20261008"
    decoy = evidence / "run-b-20261008"
    cited.mkdir(parents=True)
    decoy.mkdir(parents=True)
    (cited / "receipt.raw.log").write_bytes(b"line one\nline two\n")
    (cited / "summary.json").write_bytes(json.dumps({"ok": True}).encode("utf-8"))
    (decoy / "summary.json").write_bytes(json.dumps({"ok": False}).encode("utf-8"))
    roots = {"project_local": tmp_path}
    return tmp_path, roots, cited, decoy


def _ref(tree_, citation: str, **kwargs):
    _, roots, _, _ = tree_
    return rv.parse_reference(
        citation, [rv.Root("project_local", roots["project_local"], ".project-local")],
        default_root="project_local", **kwargs)


def _verdict(tree_, citation: str, **kwargs):
    _, roots, _, _ = tree_
    return rv.validate_reference(_ref(tree_, citation, **kwargs), roots, repo=None)


# ------------------------------------------------------------------ the control (must pass)


def test_exact_citation_with_matching_hash_resolves(tree) -> None:
    _, _, cited, _ = tree
    verdict = _verdict(
        tree, ".project-local/evidence/run-a-20261008/summary.json",
        expected_sha256=sha(cited / "summary.json"))
    assert verdict.verdict == rv.PASS
    assert verdict.resolved_path and Path(verdict.resolved_path) == cited / "summary.json"
    assert rv.exit_code([verdict]) == 0


# --------------------------------------------------------------------- planted fault 1: path


def test_file_that_exists_only_under_a_different_directory_is_refused(tree) -> None:
    """Cite run-a's summary.json, but plant it only in run-b: not a match, and not missing."""
    _, roots, cited, decoy = tree
    (cited / "summary.json").unlink()
    verdict = _verdict(tree, ".project-local/evidence/run-a-20261008/summary.json")
    assert verdict.verdict == rv.AMBIGUOUS
    assert verdict.reason.startswith("cited path does not exist; same-named file(s)")
    assert any("run-b-20261008" in candidate for candidate in verdict.candidates)
    assert not verdict.satisfied
    assert rv.exit_code([verdict]) == 1


# ------------------------------------------------------------ planted fault 2: two candidates


def test_two_same_named_candidates_are_ambiguous_and_both_are_listed(tmp_path: Path) -> None:
    for name in ("alpha", "beta", "gamma"):
        directory = tmp_path / "evidence" / name
        directory.mkdir(parents=True)
        (directory / "summary.json").write_bytes(b"{}")
    roots = {"project_local": tmp_path}
    ref = rv.parse_reference(
        ".project-local/evidence/missing/summary.json",
        [rv.Root("project_local", tmp_path, "")], default_root="project_local")
    verdict = rv.validate_reference(ref, roots, repo=None)
    assert verdict.verdict == rv.AMBIGUOUS
    assert len(verdict.candidates) == 3
    assert not verdict.satisfied


# ------------------------------------------------------------ planted fault 3: missing file


def test_missing_cited_file_with_no_namesake_is_unresolved(tree) -> None:
    verdict = _verdict(tree, ".project-local/evidence/run-a-20261008/no-such-receipt.json")
    assert verdict.verdict == rv.UNRESOLVED
    assert "no same-named file" in verdict.reason
    assert verdict.candidates == ()
    assert rv.exit_code([verdict]) == 1


# ---------------------------------------------------------- planted fault 3b: bare basename


def test_bare_basename_citation_is_never_a_pass(tree) -> None:
    """The retired tool accepted these. The invariant is that the citation is refused, not
    which sentence says so: a slashless name resolves only as an exact root-relative file,
    so when that file is absent it must not be satisfied by a same-named file found elsewhere
    -- and a slashless token with no extension names no location at all."""
    verdict = _verdict(tree, "summary.json")
    assert verdict.verdict != rv.PASS
    assert verdict.verdict == rv.AMBIGUOUS
    assert "does not exist" in verdict.reason
    assert len(verdict.candidates) == 2
    extensionless = _verdict(tree, "evidence-dir")
    assert extensionless.verdict != rv.PASS
    assert "basename" in extensionless.reason


def test_a_directory_citation_resolves_without_claiming_file_identity(tree) -> None:
    """Operating documents cite folders. A trailing slash means that directory and nothing
    else, and it must not be reported as a missing file nor be given a byte identity it has
    no bytes to back."""
    present = _verdict(tree, "evidence/run-a-20261008/")
    assert present.verdict == rv.PASS
    assert "directory" in present.reason and "no file identity" in present.reason
    assert present.measured_sha256 is None
    missing = _verdict(tree, "evidence/no-such-run/")
    assert missing.verdict != rv.PASS


def test_a_pattern_citation_stands_for_the_set_it_matches(tree) -> None:
    """`evidence/*/summary.json` is a legitimate citation of a family; it passes only because
    the pattern actually matches, and it names the match count rather than vouching for one
    verified file."""
    matched = _verdict(tree, "evidence/*/summary.json")
    assert matched.verdict == rv.PASS
    assert "2 path(s)" in matched.reason
    unmatched = _verdict(tree, "evidence/run-c-*/summary.json")
    assert unmatched.verdict != rv.PASS, "a pattern that matches nothing cannot pass"


def test_record_relative_citations_resolve_only_exactly(tmp_path, capsys) -> None:
    """An index page cites its neighbours relative to itself. That is still an exact path:
    a same-named file elsewhere in the tree must not rescue a wrong citation."""
    repo = tmp_path / "repo"
    (repo / "docs" / "current").mkdir(parents=True)
    (repo / "docs" / "current" / "thing.md").write_text("real\n", encoding="utf-8")
    (repo / "docs" / "history").mkdir(parents=True)
    (repo / "docs" / "history" / "thing.md").write_text("elsewhere\n", encoding="utf-8")
    index = repo / "docs" / "INDEX.md"
    index.write_text("see `current/thing.md` and also `missing-thing.md`\n", encoding="utf-8")

    assert rv.main(["--record", str(index), "--root", f"repo={repo}", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    by_citation = {item["citation"]: item for item in payload["verdicts"]}
    assert by_citation["current/thing.md"]["verdict"] == rv.PASS
    assert "record's own directory" in by_citation["current/thing.md"]["reason"]
    assert by_citation["missing-thing.md"]["verdict"] != rv.PASS, (
        "docs/history/thing.md must not satisfy a citation for a root-level file")


def test_a_line_anchor_is_stripped_for_resolution_but_kept_in_the_report(tree) -> None:
    """`path.py:12` is how this repository cites lines. Resolving the whole token makes
    every such reference look dangling, which is how a strict gate gets switched off."""
    repo, _, _, _ = tree
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "truth.md").write_text("line one\nline two\n", encoding="utf-8")
    anchored = _verdict(tree, "docs/truth.md:2")
    assert anchored.verdict == rv.PASS, anchored.reason
    assert anchored.citation == "docs/truth.md:2", "the printed citation keeps its anchor"
    missing = _verdict(tree, "docs/truth.md:999")
    assert missing.verdict == rv.PASS, "a line number beyond the file is not this tool's claim"
    absent = _verdict(tree, "docs/nope.md:2")
    assert absent.verdict != rv.PASS


def test_a_root_relative_filename_still_resolves_exactly(tree) -> None:
    """The refinement that the above depends on: `README.md` means <repo>/README.md and is a
    PASS only when that exact file is there, never because a copy was located by searching."""
    repo, _, _, _ = tree
    (repo / "README.md").write_text("root level\n", encoding="utf-8")
    assert _verdict(tree, "README.md").verdict == rv.PASS
    (repo / "README.md").unlink()
    hidden = repo / "docs" / "history"
    hidden.mkdir(parents=True, exist_ok=True)
    (hidden / "README.md").write_text("elsewhere\n", encoding="utf-8")
    buried = _verdict(tree, "README.md")
    assert buried.verdict != rv.PASS, "a deeper same-named file must not satisfy a root citation"


# ---------------------------------------------------------- planted fault 4: hash mismatch


def test_hash_mismatch_is_a_class_of_its_own(tree) -> None:
    _, _, cited, _ = tree
    verdict = _verdict(tree, ".project-local/evidence/run-a-20261008/summary.json",
                       expected_sha256="0" * 64)
    assert verdict.verdict == rv.HASH_MISMATCH
    assert verdict.measured_sha256 == sha(cited / "summary.json")
    assert verdict.recorded_sha256 == "0" * 64
    assert rv.exit_code([verdict]) == 1


# ------------------------------------------------------------------ historical references


def test_historical_citation_stays_resolvable_but_marked(tree) -> None:
    _, _, cited, _ = tree
    verdict = _verdict(tree, ".project-local/evidence/run-a-20261008/summary.json",
                       expected_sha256=sha(cited / "summary.json"), historical=True)
    assert verdict.verdict == rv.HISTORICAL
    assert verdict.satisfied                 # admissible, but never counted as current
    assert "not counted as current" in verdict.reason


def test_historical_citation_is_not_auto_satisfied_by_a_namesake(tree) -> None:
    _, _, cited, _ = tree
    (cited / "summary.json").unlink()
    verdict = _verdict(tree, ".project-local/evidence/run-a-20261008/summary.json",
                       historical=True)
    assert verdict.verdict == rv.AMBIGUOUS
    assert not verdict.satisfied


# ------------------------------------------------------------------- the five classes distinct


def test_verdict_classes_are_not_collapsed_across_a_mixed_corpus(tree) -> None:
    _, _, cited, _ = tree
    verdicts = [
        _verdict(tree, ".project-local/evidence/run-a-20261008/summary.json",
                 expected_sha256=sha(cited / "summary.json")),
        _verdict(tree, ".project-local/evidence/run-a-20261008/nothing.json"),
        _verdict(tree, ".project-local/evidence/run-b-20261008/summary.json",
                 expected_sha256="1" * 64),
        _verdict(tree, "summary.json"),
        _verdict(tree, ".project-local/evidence/run-a-20261008/receipt.raw.log",
                 historical=True),
    ]
    classes = {v.verdict for v in verdicts}
    assert classes == {rv.PASS, rv.UNRESOLVED, rv.HASH_MISMATCH, rv.AMBIGUOUS, rv.HISTORICAL}
    summary = rv.summarise(verdicts)
    assert set(summary) == {*rv.VERDICT_CLASSES, "TOTAL"}
    assert summary["TOTAL"] == 5 and summary["PASS"] == 1


# ------------------------------------------------- raw bytes vs newline-normalised hashing


def test_raw_and_lf_normalised_hashes_are_named_separately(tmp_path: Path) -> None:
    """Windows ``write_text`` can turn LF bytes into CRLF; the two hashes must not be
    conflated, or a corrected record looks like a corrupted one."""
    target = tmp_path / "crlf.txt"
    target.write_bytes(b"alpha\r\nbeta\r\n")
    assert rv.sha256_raw(target) != rv.sha256_lf_normalized(target)
    assert rv.sha256_lf_normalized(target) == hashlib.sha256(b"alpha\nbeta\n").hexdigest()
    assert rv.sha256_raw(target) == hashlib.sha256(b"alpha\r\nbeta\r\n").hexdigest()
    lf = tmp_path / "lf.txt"
    lf.write_bytes(b"alpha\nbeta\n")
    assert rv.sha256_raw(lf) == rv.sha256_lf_normalized(lf)


# ------------------------------------------------------------------ commit identity checks


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    tracked = repo / "docs"
    tracked.mkdir()
    (tracked / "note.md").write_bytes(b"committed bytes\n")

    def run(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    run("-c", "init.defaultBranch=main", "init")
    run("-c", "user.email=audit@example.invalid", "-c", "user.name=audit", "add", "docs/note.md")
    run("-c", "user.email=audit@example.invalid", "-c", "user.name=audit", "commit", "-m", "note")
    return repo


def _commit_of(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def test_commit_identity_mismatch_is_hash_mismatch(git_repo: Path) -> None:
    roots = {"repo": git_repo}
    (git_repo / "docs" / "note.md").write_bytes(b"silently rewritten bytes\n")
    ref = rv.parse_reference("docs/note.md", [rv.Root("repo", git_repo, "")],
                             default_root="repo", commit=_commit_of(git_repo))
    verdict = rv.validate_reference(ref, roots, repo=git_repo)
    assert verdict.verdict == rv.HASH_MISMATCH
    assert "on-disk bytes hash to" in verdict.reason


def test_unresolvable_commit_is_unresolved_not_a_pass(git_repo: Path) -> None:
    roots = {"repo": git_repo}
    ref = rv.parse_reference("docs/note.md", [rv.Root("repo", git_repo, "")],
                             default_root="repo", commit="deadbeef" + "0" * 32)
    verdict = rv.validate_reference(ref, roots, repo=git_repo)
    assert verdict.verdict == rv.UNRESOLVED
    assert "does not resolve" in verdict.reason


def test_untracked_artifact_says_identity_is_not_verifiable(git_repo: Path) -> None:
    """An artifact that no commit tracks (e.g. under the ignored project-local root) is
    neither a mismatch nor a pass: commit identity simply cannot be checked for it."""
    untracked = git_repo / ".project-local" / "evidence"
    untracked.mkdir(parents=True)
    (untracked / "receipt.json").write_bytes(b"{}")
    roots = {"repo": git_repo, "project_local": git_repo / ".project-local"}
    ref = rv.parse_reference(
        ".project-local/evidence/receipt.json",
        [rv.Root("repo", git_repo, ""),
         rv.Root("project_local", git_repo / ".project-local", ".project-local")],
        default_root="repo", commit=_commit_of(git_repo))
    verdict = rv.validate_reference(ref, roots, repo=git_repo)
    assert verdict.verdict == rv.UNRESOLVED
    assert "identity not verifiable" in verdict.reason


# ------------------------------------------------------- hash fields that name no file


def test_record_hash_field_that_names_no_file_is_not_resolved(tmp_path: Path) -> None:
    """The FINDING 4 shape: a receipt records ``receipt_sha256`` without naming which
    file it hashes. That must not be satisfied by a same-named guess."""
    directory = tmp_path / "run"
    directory.mkdir()
    (directory / "receipt.raw.log").write_bytes(b"{}\n")
    (directory / "summary.json").write_bytes(json.dumps(
        {"evidence_class": "REAL_MODEL", "receipt_sha256": "a" * 64}).encode("utf-8"))
    findings = rv.audit_hash_fields(directory)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.verdict == rv.UNRESOLVED
    assert "names no file" in finding.reason
    assert set(finding.directory_files) == {"receipt.raw.log", "summary.json"}


def test_record_hash_field_naming_its_file_is_checked_against_bytes(tmp_path: Path) -> None:
    directory = tmp_path / "run"
    directory.mkdir()
    (directory / "receipt.raw.log").write_bytes(b"payload\n")
    (directory / "summary.json").write_bytes(json.dumps(
        {"receipt_file": "receipt.raw.log", "receipt_sha256": "b" * 64}).encode("utf-8"))
    finding = rv.audit_hash_fields(directory)[0]
    assert finding.verdict == rv.HASH_MISMATCH
    assert finding.measured_sha256 == sha(directory / "receipt.raw.log")
    (directory / "summary.json").write_bytes(json.dumps(
        {"receipt_file": "receipt.raw.log",
         "receipt_sha256": sha(directory / "receipt.raw.log")}).encode("utf-8"))
    assert rv.audit_hash_fields(directory)[0].verdict == rv.PASS


# --------------------------------------------- absolute paths and traversal cannot resolve


def test_absolute_citation_is_refused_even_when_the_bytes_exist(tmp_path: Path) -> None:
    """A path outside every declared root names no verifiable location, even if the file
    is really there -- this is how the retired rule let a drive-letter path read 'resolved'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "Record"
    outside.mkdir()
    target = outside / "AAOS_UI_FRONTEND_TASKPACK_20260930.zip"
    target.write_bytes(b"zip")
    ref = rv.parse_reference(str(target), [rv.Root("repo", repo, "")], default_root="repo")
    verdict = rv.validate_reference(ref, {"repo": repo}, repo=None)
    assert verdict.verdict == rv.UNRESOLVED
    assert "absolute" in verdict.reason and "outside every declared root" in verdict.reason


def test_parent_traversal_cannot_walk_out_of_the_stated_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    project_local = tmp_path / "repo" / ".project-local"
    project_local.mkdir(parents=True)
    secret = tmp_path / "outside-of-root.txt"
    secret.write_bytes(b"do not reach me through a citation")
    roots = {"repo": repo, "project_local": project_local}
    ref = rv.parse_reference(
        ".project-local/../outside-of-root.txt",
        [rv.Root("repo", repo, ""),
         rv.Root("project_local", project_local, ".project-local")],
        default_root="project_local")
    verdict = rv.validate_reference(ref, roots, repo=repo)
    assert verdict.verdict in {rv.UNRESOLVED, rv.AMBIGUOUS}
    assert not verdict.satisfied
    assert verdict.resolved_path is None


# ------------------------------------------- the retired rule would have called these fine


def _retired_basename_rule(root: Path, token: str) -> bool:
    """The old lines 58-63 verbatim in spirit: basename match anywhere counts as resolved."""
    tail = token.split("…/")[-1].split("/")[-1].strip("，。、（）()")
    return bool(sorted(root.rglob(tail)))


def test_planted_faults_were_invisible_to_the_retired_rule(tree) -> None:
    """Each planted fault is the retired rule's blind spot, not a straw man."""
    _, _, cited, _ = tree
    (cited / "summary.json").unlink()
    for citation in (".project-local/evidence/run-a-20261008/summary.json", "summary.json"):
        assert _verdict(tree, citation).verdict == rv.AMBIGUOUS, citation
        assert _retired_basename_rule(cited.parent, citation) is True, citation
    missing = ".project-local/evidence/run-a-20261008/no-such-receipt.json"
    assert _verdict(tree, missing).verdict == rv.UNRESOLVED
    assert _retired_basename_rule(cited.parent, missing) is False
