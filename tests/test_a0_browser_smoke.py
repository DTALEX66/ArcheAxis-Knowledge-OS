from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

def _load_smoke_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "a0_browser_smoke.py"
    spec = importlib.util.spec_from_file_location("a0_browser_smoke_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _install_vite_entrypoint_fixture(smoke, monkeypatch, tmp_path):
    """Provide the only local prerequisite that Windows start_vite validates."""
    vite = tmp_path / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    vite.parent.mkdir(parents=True)
    vite.write_text("// unit-test Vite entrypoint\n", encoding="utf-8")
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    return vite


def test_windows_starts_vite_with_the_direct_node_entrypoint(monkeypatch, tmp_path):
    """The tracked Node process must be Vite itself, not a transient cmd/npm wrapper."""
    smoke = _load_smoke_module()
    captured: dict[str, object] = {}

    class _Process:
        pid = 4242

        def poll(self):
            return None

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _Process()

    vite = _install_vite_entrypoint_fixture(smoke, monkeypatch, tmp_path)
    monkeypatch.setattr(smoke.os, "name", "nt")
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "C:/node.exe")
    monkeypatch.setattr(smoke.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(smoke, "urlopen", lambda *_args, **_kwargs: _Response())

    process, log = smoke.start_vite(tmp_path / "vite.log")
    log.close()

    assert process.pid == 4242
    command = captured["command"]
    assert command[0] == "C:/node.exe"
    assert str(vite) in command
    assert "cmd.exe" not in command
    assert "npm" not in command
    assert captured["kwargs"]["cwd"] == smoke.ROOT / "frontend"


def test_windows_readiness_timeout_reclaims_the_started_vite_process(monkeypatch, tmp_path):
    smoke = _load_smoke_module()
    calls: list[tuple[object, object]] = []

    class _Process:
        pid = 4242
        waited = False
        terminated = False

        def poll(self):
            return None

        def wait(self, timeout):
            self.waited = True
            return 0

        def terminate(self):
            self.terminated = True

    process = _Process()
    clocks = iter((0.0, 31.0))

    _install_vite_entrypoint_fixture(smoke, monkeypatch, tmp_path)
    monkeypatch.setattr(smoke.os, "name", "nt")
    monkeypatch.setattr(smoke.shutil, "which", lambda name: "C:/node.exe")
    monkeypatch.setattr(smoke.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(
        smoke.subprocess,
        "run",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )
    monkeypatch.setattr(smoke, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(smoke.time, "monotonic", lambda: next(clocks))

    with pytest.raises(RuntimeError, match="readiness timed out"):
        smoke.start_vite(tmp_path / "vite.log")

    assert process.waited
    assert process.terminated
    assert calls == []


def test_browser_smoke_records_the_dirty_candidate_without_writing_the_worktree_index(monkeypatch):
    smoke = _load_smoke_module()
    captured: list[object] = []

    def fake_check_output(command, **kwargs):
        captured.append(command)
        if command == ["git", "rev-parse", "HEAD"]:
            return "abc123\n"
        if command == ["git", "diff", "--no-ext-diff", "--binary"]:
            return b"diff --git a/a b/a\n"
        raise AssertionError(command)

    monkeypatch.setattr(smoke.subprocess, "check_output", fake_check_output)

    assert smoke.source_revision() == {
        "base_commit": "abc123",
        "worktree_dirty": True,
        "worktree_diff_sha256": "9e3e63fac9c92100f0f15e616e1abf395028edc8912bebfc42044c65eb17e114",
    }
    assert ["git", "write-tree"] not in captured


def test_the_viewport_matrix_covers_the_stylesheets_own_breakpoints():
    """The matrix must render both sides of every width the shell actually branches on.

    The phone end was retired by owner decision on 2026-10-07, so this no longer asks for a
    sub-600 viewport. It asks for the stronger thing instead: that no phone block survived the
    retirement, and that each remaining breakpoint has a matrix entry on both sides of it.
    """
    import re

    root = Path(__file__).resolve().parents[1]
    smoke = (root / "scripts" / "a0_browser_smoke.py").read_text(encoding="utf-8")
    styles = "".join((root / "frontend" / "src" / "design-system" / name).read_text(encoding="utf-8")
                     for name in ("tokens.css", "themes.css"))

    entries = re.findall(r"\(\"[^\"]+\", (\d+), \d+, [\d.]+\)", smoke)
    assert entries, "the desktop viewport matrix could not be read"
    widths = [int(value) for value in entries]

    # Only what a @media condition branches on; a plain `max-width: 120px` declaration on an
    # element is a size, not a breakpoint, and the first draft of this check confused the two.
    breakpoints = sorted({int(value) for value in re.findall(r"@media[^{]*max-width: (\d+)px", styles)})
    assert breakpoints, "the stylesheet declares no width breakpoint at all"
    for limit in breakpoints:
        assert any(width <= limit for width in widths), (limit, widths)
        assert any(width > limit for width in widths), (limit, widths)

    assert not re.search(r"@media \(max-width: \d+px\) \{[^@]*?\.context-subnav \{\s*display: none;", styles, re.S), \
        "a phone block that hides the context strip came back after the owner retired that end"
    # A conditional branch is legitimate (the reading-column floor uses one); a branch at phone
    # width is not, because that end was retired.
    branches = [int(value) for value in re.findall(r"if width <= (\d+):", smoke)]
    assert all(branch > 600 for branch in branches), branches

    # The band between them asserts the reading column keeps its declared minimum.
    assert re.search(
        r"if width <= 1200:\s*\n(?:\s*#[^\n]*\n)*\s*assert geometry\[\"main\"\]\[\"width\"\] >= 280",
        smoke,
    )
