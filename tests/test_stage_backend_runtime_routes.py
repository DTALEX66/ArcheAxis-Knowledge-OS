"""A staged runtime must declare exactly the routes it can actually serve.

Round 3 gave the Core an optional `routes` declaration; round 4 taught
`backend_launcher.load_profile` to read one. This pins the producing side: the
stager declares a capability only when its worker script is present in the staged
tree, so a candidate never advertises a route that will fail at job time, and never
advertises one whose script is absent (which the Core refuses outright).

The profile the stager writes must also load through the launcher's own reader, so
the two halves cannot drift apart.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


stager = module("stage_backend_runtime_routes", ROOT / "scripts" / "release" / "stage_backend_runtime.py")
launcher = module("backend_launcher_stager_routes", ROOT / "scripts" / "release" / "backend_launcher.py")


def test_no_worker_present_declares_no_routes(tmp_path):
    assert stager.present_routes(tmp_path) == []


def test_only_present_workers_are_declared(tmp_path):
    for name in ("worker_pdf.py", "worker_ocr.py"):
        target = tmp_path / "workers" / "document" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"stub")
    ocr = tmp_path / "workers" / "vision" / "worker_ocr.py"
    ocr.parent.mkdir(parents=True, exist_ok=True)
    ocr.write_bytes(b"stub")

    declared = {entry["capability"]: entry["script"] for entry in stager.present_routes(tmp_path)}
    assert declared == {
        "image.ocr": "workers/vision/worker_ocr.py",
        "pdf.extract": "workers/document/worker_pdf.py",
    }


def test_every_declared_script_resolves_to_a_real_file(tmp_path):
    for relative in {path for paths in stager.ROUTE_SCRIPTS.values() for path in paths}:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"stub")
    for entry in stager.present_routes(tmp_path):
        assert (tmp_path / entry["script"]).is_file(), entry


def test_the_declared_script_is_the_preferred_one(tmp_path):
    """When several scripts could serve a capability, the first present one wins."""
    for capability, paths in stager.ROUTE_SCRIPTS.items():
        if len(paths) < 2:
            continue
        target = tmp_path / paths[1]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"stub")
        declared = {e["capability"]: e["script"] for e in stager.present_routes(tmp_path)}
        assert declared[capability] == paths[1]


def test_a_written_profile_loads_through_the_launcher(tmp_path):
    """The producer and the consumer must agree on the profile shape."""
    (tmp_path / "runtime").mkdir(parents=True)
    (tmp_path / "runtime" / "python.exe").write_bytes(b"stub")
    (tmp_path / "workers" / "transport").mkdir(parents=True)
    (tmp_path / "workers" / "transport" / "text_ndjson.py").write_bytes(b"stub")
    (tmp_path / "workers" / "document").mkdir(parents=True)
    (tmp_path / "workers" / "document" / "worker_pdf.py").write_bytes(b"stub")

    profile = {
        "schema": stager.PROFILE_SCHEMA,
        "python": "runtime/python.exe",
        "script": stager.TEXT_WORKER_RELATIVE,
        "staging": "data/worker-staging",
        "routes": stager.present_routes(tmp_path),
    }
    (tmp_path / "worker-profile.json").write_text(json.dumps(profile), encoding="utf-8")

    resolved = launcher.load_profile(tmp_path)
    assert resolved["routes"] == [
        {"capability": "pdf.extract", "script": (tmp_path / "workers" / "document" / "worker_pdf.py").resolve()}
    ]
