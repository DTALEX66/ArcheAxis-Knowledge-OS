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
PACK = "taskpack-1004-aaos01"


def build_repo(root: Path, *, ledger=LEDGER, pack=PACK, authority_extra="") -> None:
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
    ledger = tmp_path / "docs" / "current" / Path(LEDGER).name
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
    ledger = tmp_path / "docs" / "current" / Path(LEDGER).name
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
