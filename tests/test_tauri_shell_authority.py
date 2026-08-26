"""The recovery shell must never collide with the canonical product installer."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_recovery_shell_has_distinct_identity_and_no_release_bundle():
    primary = json.loads((ROOT / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    recovery = json.loads(
        (ROOT / "desktop/src-tauri/tauri.conf.json").read_text(encoding="utf-8")
    )

    assert primary["productName"] == "ArcheAxis Knowledge"
    assert primary["identifier"] == "com.archeaxis.workspace"
    assert primary["bundle"]["active"] is True
    assert recovery["productName"] == "ArcheAxis Knowledge Recovery"
    assert recovery["identifier"] == "com.archeaxis.workspace.recovery"
    assert recovery["bundle"]["active"] is False
    assert primary["identifier"] != recovery["identifier"]
