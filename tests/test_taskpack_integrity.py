"""R00/R14: the installed pack is intact; only its live ledger moved.

The shipped `verify_package.py` fails on `EXECUTION.md` as soon as any progress is
recorded, because that file is one of the two the pack designates as live. These
tests pin the separation that makes the failure readable: frozen entries must hash
exactly, the two live progress entries must hash to the install snapshot so their
change is attributable to growth, and the plan structure stays verified.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts/check_taskpack_integrity.py"
PACK = REPO / "docs/authority/taskpack-0910-r3"
SHIPPED = REPO / ".project-local/runs/taskpack-0910-shipped"


def _load():
    spec = importlib.util.spec_from_file_location("taskpack_integrity_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


integrity = _load()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _plan(original_ids: list[str]) -> str:
    return json.dumps(
        {
            "tasks": [
                {"id": "R00", "depends_on": [], "original_tasks": original_ids},
                {"id": "R01", "depends_on": ["R00"], "original_tasks": []},
            ]
        }
    )


def _pack(tmp_path: Path, *, snapshot_hash=None, live_execution: str = "installed ledger\n") -> tuple[Path, Path]:
    """A minimal pack plus its install snapshot."""
    pack = tmp_path / "pack"
    shipped = tmp_path / "shipped"
    frozen = {"TASKPACK.md": "the plan\n", "TASKS.json": _plan([f"X{index:02d}" for index in range(1, 24)])}
    manifest = {name: _sha(text) for name, text in frozen.items()}
    manifest["EXECUTION.md"] = snapshot_hash if snapshot_hash else _sha("installed ledger\n")
    manifest["STATE.json"] = _sha("installed state\n")
    for name, text in frozen.items():
        _write(pack / name, text)
    _write(pack / "EXECUTION.md", live_execution)
    _write(pack / "STATE.json", "installed state\n")
    _write(pack / "reference-r2/TASKS.json", json.dumps({"tasks": [{"id": f"X{index:02d}"} for index in range(1, 24)]}))
    _write(pack / "MANIFEST.json", json.dumps(manifest))
    _write(shipped / "EXECUTION.md", "installed ledger\n")
    _write(shipped / "STATE.json", "installed state\n")
    return pack, shipped


# ------------------------------------------------------------------ synthetic


def test_a_pack_whose_only_change_is_growth_passes(tmp_path):
    pack, shipped = _pack(tmp_path, live_execution="installed ledger\n" + "row\n" * 10)
    failures, detail = integrity.check(pack, shipped)
    assert failures == []
    assert detail["frozen_ok"] == 2
    assert detail["plan_ok"] is True
    grown = {item["path"]: item["delta_bytes"] for item in detail["live_progress"] if item.get("delta_bytes")}
    assert grown == {"EXECUTION.md": 40}


def test_a_changed_frozen_file_is_refused(tmp_path):
    pack, shipped = _pack(tmp_path)
    _write(pack / "TASKPACK.md", "tampered\n")
    failures, _ = integrity.check(pack, shipped)
    assert any("TASKPACK.md: frozen pack file changed" in line for line in failures)


def test_a_missing_install_snapshot_makes_the_divergence_unattributable(tmp_path):
    pack, shipped = _pack(tmp_path, live_execution="changed\n")
    (shipped / "EXECUTION.md").unlink()
    failures, _ = integrity.check(pack, shipped)
    assert any("cannot attribute EXECUTION.md" in line for line in failures)


def test_a_snapshot_that_does_not_match_the_manifest_is_refused(tmp_path):
    """A snapshot is only evidence if it hashes to what the manifest recorded."""
    pack, shipped = _pack(tmp_path, snapshot_hash=_sha("something else\n"))
    failures, _ = integrity.check(pack, shipped)
    assert any("cannot attribute EXECUTION.md" in line for line in failures)


def test_a_dependency_cycle_is_refused(tmp_path):
    pack, shipped = _pack(tmp_path)
    _write(
        pack / "TASKS.json",
        json.dumps(
            {
                "tasks": [
                    {"id": "R00", "depends_on": ["R01"], "original_tasks": [f"X{index:02d}" for index in range(1, 24)]},
                    {"id": "R01", "depends_on": ["R00"], "original_tasks": []},
                ]
            }
        ),
    )
    failures, _ = integrity.check(pack, shipped)
    assert any("cycle or a missing dependency" in line for line in failures)


def test_a_dropped_predecessor_task_is_refused(tmp_path):
    pack, shipped = _pack(tmp_path)
    _write(pack / "TASKS.json", _plan([f"X{index:02d}" for index in range(1, 23)]))  # X23 disappears
    failures, _ = integrity.check(pack, shipped)
    assert any("predecessor tasks are no longer represented" in line for line in failures)


# ----------------------------------------------------------------- real pack


def test_the_installed_pack_is_intact_and_only_the_ledger_grew():
    if not SHIPPED.is_dir():
        # The subject of this assertion - attribution against the install snapshot - cannot exist
        # in a fresh checkout, because that snapshot is an ignored receipt. The checker's refusal
        # in exactly that situation is covered by
        # test_a_missing_install_snapshot_makes_the_divergence_unattributable, which runs anywhere,
        # and the gate itself still fails loudly rather than passing quietly.
        pytest.skip(
            "the install snapshot is an ignored receipt (.project-local/runs/taskpack-0910-shipped); "
            "a fresh checkout cannot attribute the live progress files, and the checker says so"
        )
    failures, detail = integrity.check(PACK, SHIPPED)
    assert failures == []
    assert detail["manifest_entries"] == 23
    assert detail["frozen_ok"] == 21
    assert detail["frozen_changed"] == []
    assert {item["path"] for item in detail["live_progress"]} == {"EXECUTION.md", "STATE.json"}
    for item in detail["live_progress"]:
        assert item["delta_bytes"] > 0, f"{item['path']} should have grown with the work"
        assert item["live_bytes"] == item["installed_bytes"] + item["delta_bytes"]
    assert detail["plan_ok"] is True
    assert detail["state_slices"] == 17


def test_the_shipped_verifier_fails_only_on_the_live_progress_files():
    """The shipped script cannot pass once progress exists; that is its design gap."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(PACK / "verify_package.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 1
    assert "EXECUTION.md" in (result.stderr or "") + (result.stdout or "")
    manifest = json.loads((PACK / "MANIFEST.json").read_text(encoding="utf-8"))
    diverging = [
        name
        for name, expected in manifest.items()
        if hashlib.sha256((PACK / name).read_bytes()).hexdigest() != expected
    ]
    assert sorted(diverging) == ["EXECUTION.md", "STATE.json"]
