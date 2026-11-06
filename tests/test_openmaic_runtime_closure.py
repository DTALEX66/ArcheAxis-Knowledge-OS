"""The committed OpenMAIC closure manifest must match the sources it pins.

A staging manifest that lists fewer files than the adapters import would ship a
runtime whose chains fail at launch, so both the drift and the adapter coverage
are checked from source rather than from any list describing itself.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.release import openmaic_closure
from scripts.release import stage_backend_runtime as stager

SOURCE = Path(__file__).resolve().parents[1] / "services/learning-providers/openmaic"


def test_the_committed_manifest_equals_the_selected_source_bytes():
    assert openmaic_closure.load() == openmaic_closure.rows()


def test_every_core_resolvable_adapter_and_its_guard_is_in_the_closure():
    files = openmaic_closure.load()
    for name in openmaic_closure.WORKERS:
        assert name in files, name
        assert files[name]["bytes"] == (SOURCE / name).stat().st_size
    # Core resolves these by fixed sibling name; a missing one is a named
    # unavailability at launch rather than a silently different provider.
    assert "outline-prompt-guard.mjs" in files
    for directory in openmaic_closure.VENDORS:
        members = [name for name in files if name.startswith(directory + "/")]
        assert members, directory


def test_the_scene_build_core_files_are_pinned_and_not_derived():
    for relative, identity in stager.OPENMAIC_CORE_FILES.items():
        assert stager.OPENMAIC_FILES[relative] == identity
        raw = (SOURCE / relative).read_bytes()
        assert len(raw) == identity["bytes"]


def test_the_manifest_declares_its_selection_and_schema():
    document = json.loads(openmaic_closure.MANIFEST.read_text(encoding="utf-8"))
    assert document["schema"] == openmaic_closure.SCHEMA
    assert document["workers"] == list(openmaic_closure.WORKERS)
    assert document["vendors"] == list(openmaic_closure.VENDORS)
    assert len(document["files"]) == len(openmaic_closure.selected_files())
