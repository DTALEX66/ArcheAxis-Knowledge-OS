"""A staged runtime must be able to publish capability routes.

Round 3 let the launch declare `routes` on `text_worker`, and the Core registers
exactly what is declared. The staged runtime could not use it: `load_profile`
validated `set(document) == {"schema","python","script","staging"}` exactly, so a
profile carrying routes was rejected outright, and `start()` never forwarded any.

These tests pin the whole staged path: a profile with routes is accepted, each route
script resolves relative to the profile and must exist, an unsafe or missing script
is refused by name, and the launch handed to the Core carries the declared routes as
absolute paths. A profile without routes must keep working byte for byte.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "release" / "backend_launcher.py"


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


launcher = module("backend_launcher_routes", LAUNCHER)


def build_profile(root: Path, document: dict) -> Path:
    """A profile whose python/script exist, so validation reaches the routes."""
    (root / "runtime").mkdir(parents=True, exist_ok=True)
    (root / "runtime" / "python.exe").write_bytes(b"stub")
    (root / "workers" / "transport").mkdir(parents=True, exist_ok=True)
    (root / "workers" / "transport" / "text_ndjson.py").write_bytes(b"stub")
    # `start()` resolves the Core from the staged root before reading the profile.
    (root / "core").mkdir(parents=True, exist_ok=True)
    (root / "core" / "archeaxis-api.exe").write_bytes(b"stub")
    profile = root / "worker-profile.json"
    profile.write_text(json.dumps(document), encoding="utf-8")
    return profile


def base_document() -> dict:
    return {
        "schema": launcher.PROFILE_SCHEMA,
        "python": "runtime/python.exe",
        "script": "workers/transport/text_ndjson.py",
        "staging": "data/worker-staging",
    }


def test_a_profile_without_routes_still_loads_and_means_text_only(tmp_path):
    build_profile(tmp_path, base_document())
    resolved = launcher.load_profile(tmp_path)
    assert set(resolved) == {"python", "script", "staging", "routes"}
    assert resolved["routes"] == [], "an absent declaration registers no extra route"
    assert resolved["script"].name == "text_ndjson.py"


def test_a_profile_with_routes_resolves_each_script(tmp_path):
    worker = tmp_path / "workers" / "document" / "worker_pdf.py"
    worker.parent.mkdir(parents=True)
    worker.write_bytes(b"stub")
    document = base_document()
    document["routes"] = [{"capability": "pdf.extract", "script": "workers/document/worker_pdf.py"}]
    build_profile(tmp_path, document)

    resolved = launcher.load_profile(tmp_path)
    assert resolved["routes"] == [{"capability": "pdf.extract", "script": worker.resolve()}]


def test_an_empty_routes_list_is_accepted_and_means_the_text_route_only(tmp_path):
    document = base_document()
    document["routes"] = []
    build_profile(tmp_path, document)
    assert launcher.load_profile(tmp_path)["routes"] == []


def test_a_routes_script_that_does_not_exist_is_refused_by_name(tmp_path):
    document = base_document()
    document["routes"] = [{"capability": "pdf.extract", "script": "workers/missing.py"}]
    build_profile(tmp_path, document)
    with pytest.raises(launcher.LaunchFailure) as error:
        launcher.load_profile(tmp_path)
    assert "missing.py" in str(error.value)


def test_a_routes_script_that_escapes_the_root_is_refused(tmp_path):
    document = base_document()
    document["routes"] = [{"capability": "pdf.extract", "script": "../outside.py"}]
    build_profile(tmp_path, document)
    with pytest.raises(launcher.LaunchFailure):
        launcher.load_profile(tmp_path)


@pytest.mark.parametrize(
    "routes",
    [
        "not-a-list",
        [{"capability": "", "script": "workers/transport/text_ndjson.py"}],
        [{"capability": "pdf.extract"}],
        [{"script": "workers/transport/text_ndjson.py"}],
        [{"capability": "pdf.extract", "script": ""}],
        [{"capability": "text.extract", "script": "workers/transport/text_ndjson.py"}],
        [
            {"capability": "pdf.extract", "script": "workers/transport/text_ndjson.py"},
            {"capability": "pdf.extract", "script": "workers/transport/text_ndjson.py"},
        ],
    ],
)
def test_a_malformed_route_is_refused(tmp_path, routes):
    document = base_document()
    document["routes"] = routes
    build_profile(tmp_path, document)
    with pytest.raises(launcher.LaunchFailure):
        launcher.load_profile(tmp_path)


def test_the_launch_document_carries_the_declared_routes(tmp_path, monkeypatch):
    """`start()` must forward the declared routes, as absolute paths."""
    worker = tmp_path / "workers" / "document" / "worker_pdf.py"
    worker.parent.mkdir(parents=True)
    worker.write_bytes(b"stub")
    document = base_document()
    document["routes"] = [{"capability": "pdf.extract", "script": "workers/document/worker_pdf.py"}]
    build_profile(tmp_path, document)

    seen: dict = {}

    class FakeChild:
        stdin = None
        stdout = None
        stderr = None

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

        def terminate(self):
            return None

        def kill(self):
            return None

    def fake_popen(argv, **kwargs):
        return FakeChild()

    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)

    def fake_ready(child, port, timeout):
        return "http://127.0.0.1:1234"

    # Capture the launch document by intercepting the readiness wait's caller: the
    # document is written to stdin, which the fake child would otherwise discard.
    class CapturingStdin:
        def write(self, text):
            seen.update(json.loads(text))

        def flush(self):
            return None

        def close(self):
            return None

    fake_child = FakeChild()
    fake_child.stdin = CapturingStdin()
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *a, **k: fake_child)
    monkeypatch.setattr(launcher, "wait_for_readiness", fake_ready)
    # `start()` resolves the Core and the profile from the launcher's own staging
    # root. This test is about the launch document, so that root is pointed at the
    # fixture instead of planting a fake staged runtime inside the repository.
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher, "require_file", lambda path, what: Path(path))

    launcher.start(tmp_path, 1234)
    assert seen["text_worker"]["routes"] == [
        {"capability": "pdf.extract", "script": str(worker.resolve())}
    ]
