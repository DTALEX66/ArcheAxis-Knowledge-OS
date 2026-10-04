"""The toolchain routing the runbook tells a reader to use, checked against the scripts.

This host has three Rust toolchains and only the GNU one links, so the runbook has to name an
exact invocation rather than "set up Rust". That instruction is only useful if the scripts agree
with it, and two of the claims are easy to get backwards:

* `scripts/ci/cargo_test.bat` must honour `ARCHEAXIS_CARGO_TARGET_DIR`, because that is the
  explicit override the runbook relies on rather than the shared bare fallback;
* `scripts/runtime/dev.py` must resolve a **per-worktree** cargo target, which is what makes
  "linked worktrees keep independent outputs" true rather than aspirational.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CARGO_TEST = REPO / "scripts/ci/cargo_test.bat"
DEV = REPO / "scripts/runtime/dev.py"
RUNBOOK = REPO / "docs/current/AAOS-BACKEND-ACCEPTANCE-RUNBOOK-20261001.md"
CARGO_CONFIG = REPO / ".cargo/config.toml"


def test_the_official_entry_point_honours_the_explicit_target_override():
    text = CARGO_TEST.read_text(encoding="utf-8")
    assert "ARCHEAXIS_CARGO_TARGET_DIR" in text, (
        "the runbook's invocation depends on this override existing")
    assert re.search(
        r'if defined ARCHEAXIS_CARGO_TARGET_DIR set "CARGO_TARGET_DIR=%ARCHEAXIS_CARGO_TARGET_DIR%"',
        text), "the override no longer sets CARGO_TARGET_DIR, so the runbook's command is wrong"
    # and the fallback must still be the bare checkout-local directory, which is what the runbook
    # warns is shared
    assert r".project-local\build\cargo" in text, (
        "the bare fallback changed; the runbook's warning about a shared directory may be stale")


def test_dev_resolves_a_per_worktree_cargo_target():
    text = DEV.read_text(encoding="utf-8")
    assert 'paths["cargo_build"]' in text, "dev.py no longer publishes a cargo build root"
    assert re.search(r'dev / "build" / "cargo" if root == owner\s*\n?\s*else paths\["build"\] / "cargo"',
                     text), (
        "dev.py's main-checkout versus linked-worktree split changed; the runbook's description "
        "of which target a worktree gets needs rewriting")


def test_the_checked_in_cargo_config_still_redirects_the_bare_target():
    text = CARGO_CONFIG.read_text(encoding="utf-8")
    assert "target-dir" in text and ".project-local/build/cargo" in text, (
        "the checked-in cargo config no longer redirects target/, so a bare cargo entry would "
        "write into the worktree root and the runbook's note would be misleading")


def test_the_runbook_names_the_toolchain_that_actually_works():
    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "stable-x86_64-pc-windows-gnu" in runbook, (
        "the runbook must name the GNU toolchain, which is the only one that links here")
    assert "ARCHEAXIS_CARGO_TARGET_DIR" in runbook, (
        "the runbook must use the official override rather than an ad-hoc variable")
    assert "cargo_test.bat" in runbook, "the runbook must name the official entry point"
    # the two failure modes that look like something else are worth keeping written down
    assert "link.exe" in runbook, (
        "the runbook must record that the complete external toolchain fails to link on MSVC")
    assert "own** `.project-local`" in runbook or "own" in runbook, (
        "the runbook must say a linked worktree keeps its build output local")
