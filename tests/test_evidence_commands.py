"""The evidence-command checker must be safe by default and honest about what it did not run.

Round 96 executed the recorded commands by hand and found two real defects, so the check is worth
keeping. These tests hold the properties that make it safe to keep: planning executes nothing, a
placeholder command is never run, an unrecognised command shape is refused rather than skipped
quietly, and "not run" is never reported as a pass.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "check_evidence_commands.py"
INDEX = REPO / "docs/authority/taskpack-0910-r3" / "R14-EVIDENCE-INDEX.json"


def _load():
    spec = importlib.util.spec_from_file_location("evidence_commands_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load()


def test_the_plan_covers_every_slice_and_executes_nothing():
    rows = checker.plan(INDEX, runner="python")
    slices = {row["slice"] for row in rows}
    assert {"R00", "R10", "R13", "R16"} <= slices
    assert all("result" not in row for row in rows), "planning must not execute anything"


def test_alternatives_are_split_on_the_double_pipe():
    rows = checker.plan(INDEX, runner="python")
    r11 = [row for row in rows if row["slice"] == "R11"]
    assert len(r11) == 3, r11
    assert [row["class"] for row in r11] == [checker.PROBE_CLASS] * 3


def test_a_placeholder_command_is_never_runnable():
    assert checker.classify("python -X utf8 scripts/release/verify_candidate.py --candidate <bundle>") == checker.PLACEHOLDER_CLASS
    rows = checker.run_plan(
        [{"slice": "X", "command": "python <thing>", "class": checker.PLACEHOLDER_CLASS, "runnable": False}],
        timeout=5,
        execute_heavy=False,
    )
    assert rows[0]["result"] == "NOT_RUN"
    assert "placeholder" in rows[0]["reason"]


def test_a_batch_command_is_run_through_cmd():
    """Found by running it: Windows cannot start a .bat directly, a shell runs it through cmd."""
    rows = checker.plan(INDEX, runner="python")
    heavy = [row for row in rows if row["class"] == checker.HEAVY_CLASS]
    assert heavy, "the index must record at least one cargo command"
    for row in heavy:
        assert row["argv"][:2] == ["cmd", "/c"], row["argv"]
        assert row["argv"][2].endswith("cargo_test.bat")
        assert "/" not in row["argv"][2], "cmd does not accept the forward slashes the index uses"


def test_every_recorded_command_starts_with_a_runner_this_checker_knows():
    """A command using an unknown runner must fail here rather than be skipped in silence."""
    rows = checker.plan(INDEX, runner="python")
    unknown = [row["command"] for row in rows if row["runnable"] and row.get("runner") not in checker.KNOWN_RUNNERS]
    assert unknown == [], f"commands using an unhandled runner: {unknown}"


def test_python_resolves_to_the_repository_interpreter_when_there_is_one():
    resolved = checker.python_for_commands()
    assert resolved, "a runner must always resolve to something"
    if (REPO / ".venv" / "Scripts" / "python.exe").is_file():
        assert resolved.endswith("python.exe")


def test_heavy_commands_are_not_run_unless_asked():
    rows = checker.run_plan(
        [{"slice": "X", "command": "scripts/ci/cargo_test.bat -p pkg --offline", "class": checker.HEAVY_CLASS, "runnable": True, "argv": ["cmd", "/c", "scripts/ci/cargo_test.bat"]}],
        timeout=5,
        execute_heavy=False,
    )
    assert rows[0]["result"] == "NOT_RUN"
    assert "cargo" in rows[0]["reason"]


def test_heavy_commands_are_not_run_when_there_is_no_toolchain(monkeypatch):
    """Without the toolchain the runner refuses by name; a checker must not call that a failure."""
    monkeypatch.delenv("ARCHEAXIS_RUST_TOOLCHAINS", raising=False)
    monkeypatch.delenv("ARCHEAXIS_MSVC_VCVARS", raising=False)
    monkeypatch.setattr(checker.shutil, "which", lambda _name: None)
    assert checker.toolchain_present() is False
    assert "ARCHEAXIS_MSVC_VCVARS" in checker.missing_toolchain()
    rows = checker.run_plan(
        [{"slice": "X", "command": "scripts/ci/cargo_test.bat -p pkg --offline", "class": checker.HEAVY_CLASS, "runnable": True, "argv": ["cmd", "/c", "nope.bat"]}],
        timeout=5,
        execute_heavy=True,
    )
    assert rows[0]["result"] == "NOT_RUN"
    assert "environment gap rather than a failure" in rows[0]["reason"]


def test_both_toolchain_variables_are_required(monkeypatch):
    """Measured: with only the Rust variable the runner fails at the C linker (exit 101)."""
    monkeypatch.setenv("ARCHEAXIS_RUST_TOOLCHAINS", "somewhere")
    monkeypatch.delenv("ARCHEAXIS_MSVC_VCVARS", raising=False)
    assert checker.toolchain_present() is False
    monkeypatch.setenv("ARCHEAXIS_MSVC_VCVARS", "somewhere/vcvars64.bat")
    assert checker.toolchain_present() is True


def test_a_command_that_needs_a_built_core_is_not_a_failure_without_one(monkeypatch):
    """Measured in a fresh clone (round 98): seven commands read as failures when nothing was built."""
    assert checker.needs_build("python -X utf8 scripts/probes/r10_host_panel_smoke.py")
    assert checker.needs_build("python -X utf8 scripts/release/build_candidate.py --zip")
    assert not checker.needs_build("python -X utf8 scripts/check_path_conventions.py")
    monkeypatch.setattr(checker, "built_core", lambda: None)
    rows = checker.run_plan(
        [{"slice": "X", "command": "python -X utf8 scripts/probes/r10_host_panel_smoke.py", "class": checker.PROBE_CLASS, "runnable": True, "argv": ["python", "-c", "print(1)"]}],
        timeout=5,
        execute_heavy=False,
    )
    assert rows[0]["result"] == "NOT_RUN"
    assert "needs a Core binary built in this checkout" in rows[0]["reason"]


def test_a_built_core_is_found_in_the_pinned_target_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("ARCHEAXIS_CARGO_TARGET_DIR", raising=False)
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    assert checker.built_core() is None
    binary = tmp_path / ".project-local" / "build" / "cargo" / "debug" / "archeaxis-api.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"MZ")
    assert checker.built_core() == binary


def test_a_command_that_needs_a_clean_tree_says_so_instead_of_failing(monkeypatch):
    """Measured: mid-edit, the builder's designed refusal (exit 5) read as a failure."""
    assert checker.needs_clean_tree("python -X utf8 scripts/release/build_candidate.py --zip")
    # The verifier does not care about the tree: it only re-hashes a bundle someone else built.
    assert not checker.needs_clean_tree("python -X utf8 scripts/release/verify_candidate.py --candidate x")
    assert not checker.needs_clean_tree("python -X utf8 scripts/check_path_conventions.py")
    monkeypatch.setattr(checker, "built_core", lambda: __import__("pathlib").Path(__file__))
    monkeypatch.setattr(checker, "tracked_tree_is_dirty", lambda: True)
    rows = checker.run_plan(
        [{"slice": "X", "command": "python -X utf8 scripts/release/build_candidate.py --zip", "class": checker.PROBE_CLASS, "runnable": True, "argv": ["python", "-c", "print(1)"]}],
        timeout=5,
        execute_heavy=False,
    )
    assert rows[0]["result"] == "NOT_RUN"
    assert "dirty tracked worktree by design" in rows[0]["reason"]


def test_both_streams_are_reported_so_a_named_refusal_is_visible():
    class Fake:
        stdout = "noise\n"
        stderr = "cargo_test: cargo is not on PATH; set ARCHEAXIS_RUST_TOOLCHAINS\n"

    assert "cargo is not on PATH" in checker.last_meaningful_line(Fake())


def test_a_not_run_command_is_never_counted_as_a_pass():
    summary = checker.summarise(
        [
            {"slice": "A", "command": "x", "result": "PASS"},
            {"slice": "B", "command": "y", "result": "NOT_RUN", "reason": "placeholder"},
        ]
    )
    assert summary["counts"] == {"PASS": 1, "NOT_RUN": 1}
    assert summary["failures"] == []
    assert "not a pass" in summary["note"]


def test_a_failure_is_reported_and_fails_the_run(tmp_path):
    summary = checker.summarise([{"slice": "A", "command": "x", "result": "FAIL", "tail": "boom"}])
    assert summary["failures"] and "boom" in summary["failures"][0]


def test_the_index_this_checker_reads_is_the_tracked_one():
    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    assert payload["slices"], "the index must carry slices"
    assert all(str(row.get("command", "")).strip() for row in payload["slices"]), "every slice needs a command"
