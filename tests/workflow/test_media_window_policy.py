"""The policy drift gate is falsified, not assumed: each mirror is mutated and must be named.

A gate that only ever passes proves nothing about whether it can fail. Each case below writes a
drifted copy of one artefact into a temp file, points the check at it, and asserts the exact
artefact and field are reported — so a broken comparison cannot masquerade as agreement.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "contracts" / "check_media_window_policy.py"


def load_check():
    spec = importlib.util.spec_from_file_location("media_window_policy_check", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_real_tree_is_consistent_and_the_rust_literal_is_read_whole():
    check = load_check()
    assert check.check() == []
    # Rust writes the cap as `300_000`; reading only `\\d+` would compare 300 and report a drift
    # that does not exist, which is what the first version of the check did.
    caps = check.core_caps()
    assert caps, "no Core cap site found"
    assert all(cap == 300_000 for _, cap in caps), caps


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_a_drifted_interface_constant_is_named(monkeypatch, tmp_path):
    check = load_check()
    source = (REPO / "frontend" / "src" / "presentation" / "mediaEstimate.ts").read_text(encoding="utf-8")
    monkeypatch.setattr(check, "ESTIMATE", _write(
        tmp_path / "mediaEstimate.ts", source.replace("MEDIA_OVERHEAD_MS = 20_000", "MEDIA_OVERHEAD_MS = 25_000")))
    problems = check.check()
    assert len(problems) == 1, problems
    assert "mediaEstimate.ts" in problems[0] and "overhead_ms" in problems[0]
    assert "25000" in problems[0] and "20000" in problems[0]


def test_a_drifted_worker_constant_is_named(monkeypatch, tmp_path):
    check = load_check()
    source = (REPO / "services" / "python-workers" / "media" / "window_plan.py").read_text(encoding="utf-8")
    monkeypatch.setattr(check, "PLANNER", _write(
        tmp_path / "window_plan.py", source.replace("REALTIME_FACTOR = 2.0", "REALTIME_FACTOR = 1.5")))
    problems = check.check()
    assert len(problems) == 1, problems
    assert "window_plan.py" in problems[0] and "realtime_factor" in problems[0]


def test_a_core_cap_that_disagrees_with_the_declared_ceiling_is_named(monkeypatch, tmp_path):
    check = load_check()
    source = (REPO / "crates" / "archeaxis-application" / "src" / "executor.rs").read_text(encoding="utf-8")
    drifted = _write(tmp_path / "executor.rs", source.replace("deadline_ms > 300_000", "deadline_ms > 600_000"))
    monkeypatch.setattr(check, "CORE", [drifted])
    problems = check.check()
    assert len(problems) == 1, problems
    assert "executor.rs" in problems[0] and "600000" in problems[0]


def test_a_ceiling_nothing_enforces_is_a_problem(monkeypatch):
    check = load_check()
    monkeypatch.setattr(check, "CORE", [])
    problems = check.check()
    assert any("not enforced anywhere" in problem for problem in problems), problems


def test_a_policy_missing_a_constant_is_refused(monkeypatch, tmp_path):
    check = load_check()
    monkeypatch.setattr(check, "DEFAULTS", _write(
        tmp_path / "defaults.yaml", "media:\n  window_policy:\n    ceiling_ms: 300000\n"))
    with pytest.raises(ValueError, match="missing"):
        check.declared()
