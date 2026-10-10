"""Falsify the document-authority gate: each guarded fault is injected and must be named.

A gate that only ever passes proves nothing about whether it can fail, and this one guards a defect
that already occurred twice in this repository — two live documents each claiming to be the current
record. Each case below builds a small fixture repository, points the gate at it, and asserts the
exact fault is reported.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "ci" / "check_document_authority.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("document_authority_gate", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LEDGER = "docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md"
PACK = "docs/taskpacks/aaos-ui-first-20261009"
PROGRESS = "docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md"


def build_repo(root: Path, *, ledger=PROGRESS, pack=PACK, authority_extra="") -> None:
    (root / "docs" / "current").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "truth").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "taskpacks").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "DOCUMENTATION_AUTHORITY_INDEX.md").write_text("index\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("agents\n", encoding="utf-8")
    (root / "README.md").write_text(f"current ledger {ledger}\ncurrent pack {pack}\n", encoding="utf-8")
    (root / "AUTHORITY.md").write_text(
        f"# root\ncurrent: {ledger} and {pack}\n{authority_extra}", encoding="utf-8")
    (root / "docs" / "truth" / "README.md").write_text("truth\n", encoding="utf-8")
    (root / "docs" / "taskpacks" / "README.md").write_text("packs\n", encoding="utf-8")
    (root / "docs" / "current" / Path(ledger).name).write_text("ledger\n", encoding="utf-8")
    (root / PACK).mkdir(parents=True, exist_ok=True)
    (root / PROGRESS).write_text("UI progress\n", encoding="utf-8")
    (root / LEDGER).write_text("inherited Q progress\n", encoding="utf-8")
    (root / "docs/current/AAOS-ACTIVE-EXECUTION.json").write_text(json.dumps({
        "schema": "archeaxis.active-execution/v1", "active_taskpack": PACK,
        "active_progress": PROGRESS, "inherited_progress": [LEDGER],
        "authority_routes": "docs/current/AAOS-AUTHORITY-ROUTES.json",
        "execution_control": {"state": "PAUSED_BY_OWNER", "automatic_continuation": False}}), encoding="utf-8")
    # The expanded main gate also requires a public identity routing registry.
    (root / "docs/current/AAOS-AUTHORITY-ROUTES.json").write_text(json.dumps({
        "schema": "archeaxis.authority-routes/v1",
        "active_pointer": "docs/current/AAOS-ACTIVE-EXECUTION.json",
        "entries": [{"path": name, "role": "LIVE_NAVIGATION"}
                    for name in ("README.md", "AUTHORITY.md", "AGENTS.md")]
                   + [{"path": "docs/current/AAOS-ACTIVE-EXECUTION.json", "role": "ACTIVE_ROUTER"}],
        "aliases": [],
        "rules": [{"pattern": "docs/current/**", "role": "DATED_SCOPED_RECORD_NOT_AUTOMATIC_AUTHORITY"},
                  {"pattern": "*.md", "role": "REFERENCE_REQUIRES_CONCERN_AUTHORITY"}]}), encoding="utf-8")
    for name in ("README.md", "AUTHORITY.md", "AGENTS.md"):
        with (root / name).open("a", encoding="utf-8") as stream:
            stream.write("\nAAOS-AUTHORITY-ROUTES.json\n")
    inputs = {
        "inputs_read_this_round": [
            {"path_or_locator": "docs/current/input.md", "byte_sha256": "0" * 64}],
        "appendix_sources": [],
    }
    (root / "docs" / "current" / "input.md").write_text("x", encoding="utf-8")
    (root / "docs" / "current" / "AAOS-INPUT-SOURCES-20261006.json").write_text(
        json.dumps(inputs), encoding="utf-8")
    identifiers = (
        [f"CAP-{n:04d}" for n in range(10, 170, 10)]
        + [f"Q{n:02d}" for n in range(16)]
        + [f"F{n:02d}" for n in range(15)]
        + [f"I{n}" for n in range(1, 7)]
    )
    (root / "docs" / "current" / "AAOS-COVERAGE-MATRIX-20261006.md").write_text(
        "\n".join(identifiers), encoding="utf-8")


def wire(monkeypatch, root: Path, **kw):
    gate = load_gate()
    build_repo(root, **kw)
    monkeypatch.setattr(gate, "REPO", root)
    monkeypatch.setattr(gate, "AUTHORITY", root / "AUTHORITY.md")
    monkeypatch.setattr(gate, "INPUTS", root / "docs" / "current" / "AAOS-INPUT-SOURCES-20261006.json")
    monkeypatch.setattr(gate, "MATRIX", root / "docs" / "current" / "AAOS-COVERAGE-MATRIX-20261006.md")
    monkeypatch.setattr(gate, "LIVE_ENTRY_DOCS",
                        ("README.md", "AUTHORITY.md", "AGENTS.md",
                         "docs/DOCUMENTATION_AUTHORITY_INDEX.md", "docs/truth/README.md",
                         "docs/taskpacks/README.md"))
    monkeypatch.setattr(gate, "MUST_NOT_CLAIM", ("docs/taskpacks/README.md",))
    return gate


def digest_of(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_clean_fixture_passes(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    # Make the recorded hash true so only the intended fault can fail.
    inputs = tmp_path / "docs" / "current" / "AAOS-INPUT-SOURCES-20261006.json"
    document = json.loads(inputs.read_text(encoding="utf-8"))
    document["inputs_read_this_round"][0]["byte_sha256"] = digest_of(
        tmp_path / "docs" / "current" / "input.md")
    inputs.write_text(json.dumps(document), encoding="utf-8")
    assert gate.main() == 0


def test_a_cited_test_that_does_not_exist_is_reported(monkeypatch, tmp_path):
    """A row naming a test makes a checkable claim; an invented path must fail.

    This is the mistake the row author made once already -- a filename recalled from an
    audit rather than read from the tree, which collected nothing and looked green.
    """
    gate = wire(monkeypatch, tmp_path)
    ledger = tmp_path / "docs" / "current" / Path(PROGRESS).name
    ledger.write_text(
        "| Q99 | x | cites `crates/archeaxis-api/tests/not_a_real_test.rs` and `--test also_not_real` |\n",
        encoding="utf-8")
    problems = gate.check_ledger_citations()
    assert len(problems) == 2, problems
    assert any("not_a_real_test.rs" in problem for problem in problems)
    assert any("also_not_real" in problem for problem in problems)


def test_every_citation_form_the_ledger_uses_resolves(monkeypatch, tmp_path):
    """Repo path, crate-relative path and bare root module all have to resolve."""
    gate = wire(monkeypatch, tmp_path)
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests" / "test_fixture_target.py").write_text("x\n", encoding="utf-8")
    crate_tests = tmp_path / "crates" / "archeaxis-api" / "tests"
    crate_tests.mkdir(parents=True)
    (crate_tests / "fixture_target.rs").write_text("// fixture\n", encoding="utf-8")
    ledger = tmp_path / "docs" / "current" / Path(PROGRESS).name
    ledger.write_text(
        "`tests/test_fixture_target.py` `crates/archeaxis-api/tests/fixture_target.rs` "
        "`archeaxis-api/tests/fixture_target.rs` `--test fixture_target`\n", encoding="utf-8")
    assert gate.check_ledger_citations() == []


def test_a_second_current_ledger_is_named(monkeypatch, tmp_path, capsys):
    other = "docs/current/AAOS01-Q00-Q15-LEDGER-OTHER.md"
    gate = wire(monkeypatch, tmp_path)
    (tmp_path / "docs" / "current" / Path(other).name).write_text("other\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(f"current ledger {other}\n", encoding="utf-8")
    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "README.md" in out and other in out, out


def test_a_competing_current_pack_is_named(monkeypatch, tmp_path, capsys):
    gate = wire(monkeypatch, tmp_path, pack="taskpack-0001-wrong")
    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "taskpack-0001-wrong" in out and PACK in out, out


def test_a_missing_root_reference_is_named(monkeypatch, tmp_path, capsys):
    gate = wire(monkeypatch, tmp_path,
                authority_extra="see `docs/current/does-not-exist.md`\n")
    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "docs/current/does-not-exist.md" in out, out


def test_a_wrong_input_hash_is_named(monkeypatch, tmp_path, capsys):
    gate = wire(monkeypatch, tmp_path)
    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "recorded" in out and "this host has" in out, out


def test_an_uncovered_identifier_is_named(monkeypatch, tmp_path, capsys):
    gate = wire(monkeypatch, tmp_path)
    matrix = tmp_path / "docs" / "current" / "AAOS-COVERAGE-MATRIX-20261006.md"
    matrix.write_text(matrix.read_text(encoding="utf-8").replace("CAP-0160", ""), encoding="utf-8")
    assert gate.main() == 1
    assert "CAP-0160" in capsys.readouterr().out


def test_a_regrown_conflicting_pointer_is_named(monkeypatch, tmp_path, capsys):
    gate = wire(monkeypatch, tmp_path)
    (tmp_path / "docs" / "taskpacks" / "README.md").write_text(
        "the current ledger is docs/current/AAOS01-Q00-Q15-LEDGER-OTHER.md\n", encoding="utf-8")
    assert gate.main() == 1
    assert "AAOS01-Q00-Q15-LEDGER-OTHER.md" in capsys.readouterr().out


def test_old_aaos01_cannot_claim_current(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path, pack="docs/authority/taskpack-1004-aaos01")
    assert any("taskpack-1004-aaos01" in p for p in gate.check_single_current())


def test_r6_and_m0_cannot_claim_current(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    (tmp_path / "README.md").write_text(
        "current pack taskpack-0919-r6\ncurrent progress docs/current/M0-EXECUTION.md\n", encoding="utf-8")
    problems = gate.check_single_current()
    assert any("taskpack-0919-r6" in p for p in problems)
    assert any("M0-EXECUTION.md" in p for p in problems)


def test_wrong_ui_progress_is_named(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path, ledger="docs/current/AAOS-UI-FIRST-EXECUTION-WRONG.md")
    assert any("EXECUTION-WRONG" in p for p in gate.check_single_current())


def test_missing_active_pointer_is_named(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    (tmp_path / gate.ACTIVE_EXECUTION).unlink()
    assert any("pointer is missing" in p for p in gate.check_single_current())


def test_pointer_traversal_never_reads_outside(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    pointer_path = tmp_path / gate.ACTIVE_EXECUTION
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    for bad in ("../outside", "D:/private", "E:/blocked", ".codex/sessions/current.json"):
        pointer["active_taskpack"] = bad
        pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
        assert gate.check_single_current(), bad


def test_historical_q_and_r6_inheritance_with_ui_current_is_valid(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    (tmp_path / "README.md").write_text(
        f"historical current Q progress {LEDGER}; current UI progress {PROGRESS}\n"
        f"inherited current taskpack-0919-r6; current pack {PACK}\n", encoding="utf-8")
    assert gate.check_single_current() == []


def test_external_and_private_input_paths_are_never_probed(monkeypatch, tmp_path, capsys):
    gate = wire(monkeypatch, tmp_path)
    source = tmp_path / "docs/current/AAOS-INPUT-SOURCES-20261006.json"
    source.write_text(json.dumps({"inputs_read_this_round": [
        {"path_or_locator": bad, "byte_sha256": "0" * 64}
        for bad in ("E:/blocked.txt", "F:/blocked.txt", "D:/private.txt", "../outside.txt", ".codex/sessions/item.json", ".env")]}), encoding="utf-8")
    original = Path.is_file
    def guarded(self):
        assert self == source, f"outside/private locator was probed: {self}"
        return original(self)
    monkeypatch.setattr(Path, "is_file", guarded)
    def no_locator_stat(self):
        raise AssertionError(f"outside/private locator was statted: {self}")
    monkeypatch.setattr(Path, "lstat", no_locator_stat)
    assert gate.check_input_hashes() == []
    assert "UNVERIFIED 6" in capsys.readouterr().out


def test_inherited_q_missing_citations_are_historical_unverified(monkeypatch, tmp_path, capsys):
    gate = wire(monkeypatch, tmp_path)
    (tmp_path / LEDGER).write_text("`tests/test_original_checkout_only.py` `--test original_target`\n", encoding="utf-8")
    assert gate.check_ledger_citations() == []
    out = capsys.readouterr().out
    assert "historical citation UNVERIFIED" in out and "original_target" in out


def test_legacy_state_json_cannot_claim_current(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    (tmp_path / "AGENTS.md").write_text("current state docs/current/R6-STATE.json\n", encoding="utf-8")
    assert any("R6-STATE.json" in p for p in gate.check_single_current())


def test_pointer_cannot_select_old_aaos01_pack(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    old = "docs/taskpacks/taskpack-1004-aaos01"
    (tmp_path / old).mkdir()
    source = tmp_path / gate.ACTIVE_EXECUTION
    pointer = json.loads(source.read_text(encoding="utf-8"))
    pointer["active_taskpack"] = old
    source.write_text(json.dumps(pointer), encoding="utf-8")
    assert any("historical taskpack" in p for p in gate.check_single_current())


def test_annotated_historical_markdown_locator_checks_actual_hash(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    source = tmp_path / "docs/current/AAOS-INPUT-SOURCES-20261006.json"
    target = tmp_path / "docs/current/input.md"
    document = {"inputs_read_this_round": [{
        "path_or_locator": "docs/current/input.md（原件在库，中文原文件名）",
        "byte_sha256": digest_of(target),
    }]}
    source.write_text(json.dumps(document), encoding="utf-8")
    assert gate.check_input_hashes() == []
    target.write_text("changed historical bytes", encoding="utf-8")
    assert any("recorded" in problem for problem in gate.check_input_hashes())


def test_missing_selected_freeze_register_is_named(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    path = tmp_path / gate.ACTIVE_EXECUTION
    pointer = json.loads(path.read_text(encoding="utf-8"))
    pointer["freeze_register"] = PACK + "/FREEZE-REGISTER.md"
    path.write_text(json.dumps(pointer), encoding="utf-8")
    assert any("freeze_register" in problem for problem in gate.check_single_current())
    (tmp_path / pointer["freeze_register"]).write_text("preserved freeze register", encoding="utf-8")
    assert gate.check_single_current() == []


def test_priority_cannot_resume_paused_task(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    path = tmp_path / gate.ACTIVE_EXECUTION
    pointer = json.loads(path.read_text(encoding="utf-8"))
    pointer.update(selected_tasks=["G01", "V01"], paused=["V01"], priority_tasks=["V01"])
    path.write_text(json.dumps(pointer), encoding="utf-8")
    assert any("paused task" in problem for problem in gate.check_single_current())
    pointer["priority_tasks"] = ["G01"]
    path.write_text(json.dumps(pointer), encoding="utf-8")
    assert gate.check_single_current() == []


def test_priority_cannot_expand_selected_scope(monkeypatch, tmp_path):
    gate = wire(monkeypatch, tmp_path)
    path = tmp_path / gate.ACTIVE_EXECUTION
    pointer = json.loads(path.read_text(encoding="utf-8"))
    pointer.update(selected_tasks=["G01"], priority_tasks=["FT01"])
    path.write_text(json.dumps(pointer), encoding="utf-8")
    assert any("owner-selected scope" in problem for problem in gate.check_single_current())
