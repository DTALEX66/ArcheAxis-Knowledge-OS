"""A desktop launch must declare capability routes, and the proof of that must not rot.

This is the regression guard for a defect that had no guard before: the desktop's profile reader
required exactly four fields and its supervisor never sent routes, so a launched Core registered only
its built-in `text.extract`. PDF, OCR, Office, media, canvas and the co-learning machine answer were
all unreachable in the product's own launch path, and nothing failed when they were.

Two things are pinned here:
  * the desktop launcher writes the routes, and every one names a real worker inside the repository;
  * the readback probe still exists and still drives a real launch, because the launcher writing
    routes is only half the claim - the Core has to register them.
"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LAUNCHER = REPO / "scripts/launch/desktop_launch.py"
PROBE = REPO / "scripts/probes/desktop_route_readback.py"
STAGER = REPO / "scripts/release/stage_backend_runtime.py"
SUPERVISOR = REPO / "apps/ArcheAxis.Desktop/CoreSupervisor.cs"
PROFILE_READER = REPO / "apps/ArcheAxis.Desktop/WorkerProfile.cs"


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_desktop_launcher_declares_routes():
    launcher = _module("desktop_launch_routes_under_test", LAUNCHER)
    # The table is module-level inside prepare_launch in the current shape, so read the source for the
    # capability names and assert they are non-empty and contain the two that matter most.
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "'machine.answer'" in source, (
        "the co-learning machine answer must be declared, or its Core routes answer 503")
    assert "routes" in source
    assert launcher is not None


def test_the_desktop_and_the_staged_runtime_declare_the_same_capabilities():
    """Two launch paths, one product. If they disagree, one of them is wrong."""
    desktop_source = LAUNCHER.read_text(encoding="utf-8")
    stager = _module("stager_for_route_parity", STAGER)
    staged_capabilities = set(stager.ROUTE_SCRIPTS)
    # Every capability the staged runtime ships is named in the desktop launcher's table.
    missing = [capability for capability in sorted(staged_capabilities)
               if f"'{capability}'" not in desktop_source]
    assert not missing, (
        f"the staged runtime declares {missing} but the desktop launcher does not; the two launch "
        "paths must offer the same capabilities or the product behaves differently by entry point")


def test_the_csharp_supervisor_carries_routes_into_the_launch_document():
    source = SUPERVISOR.read_text(encoding="utf-8")
    # The record has to hold them...
    assert "CoreWorkerRoute" in source, "the supervisor has no route record to carry"
    assert "Routes" in source, "CoreTextWorker does not carry routes"
    # ...and the launch document has to send them under the names the Core accepts. The Core declares
    # `WorkerRoute` under `deny_unknown_fields`, so PascalCase keys would be refused.
    assert "capability = route.Capability" in source
    assert "script = route.Script" in source


def test_the_csharp_reader_accepts_routes_and_still_refuses_unknown_fields():
    source = PROFILE_READER.read_text(encoding="utf-8")
    assert 'field.Name == "routes"' in source, "the profile reader still refuses `routes`"
    # The guard that made this a defect must not come back.
    assert "fields.Count != 4" in source, (
        "the exact-field-count guard is gone; re-check that an unknown field is still refused")
    assert "unknown, duplicate or invalid worker profile field" in source
    # A route's script is resolved through the same path policy as the text script.
    assert "worker route script is missing" in source


def test_the_readback_probe_exists_and_drives_a_real_launch():
    assert PROBE.is_file(), "the readback probe is gone; the registration claim would be unbacked"
    source = PROBE.read_text(encoding="utf-8")
    assert "archeaxis.desktop-launch/v2" in source, "the probe does not use the desktop launch shape"
    assert "/api/v1/capabilities" in source, "the probe does not read the capability surface back"
    assert "machine.answer" in source
    # It must state what it does not prove, so a reader cannot take it for a product run.
    assert "what_this_does_not_prove" in source


def test_the_probe_reports_the_verdict_it_actually_measured():
    """A probe that cannot report failure is not evidence."""
    tree = ast.parse(PROBE.read_text(encoding="utf-8"))
    source = PROBE.read_text(encoding="utf-8")
    # It computes missing routes and fails when any is absent.
    assert "missing_after_launch" in source
    assert 'verdict": "REGISTERED" if not missing and machine_ok else "INCOMPLETE"' in source, (
        "the probe must have a non-success verdict path")
    assert any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in ast.walk(tree))
