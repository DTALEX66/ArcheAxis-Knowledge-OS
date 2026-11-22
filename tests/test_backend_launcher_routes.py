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

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

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


def test_session_worker_uses_selected_backend_and_preserves_other_routes(tmp_path, monkeypatch):
    kit = tmp_path / "packaged runtime"
    script = "workers/transport/text_ndjson.py"
    document = base_document()
    document["routes"] = [{"capability": name, "script": script}
                          for name in ("machine.answer", "research.public")]
    profile = build_profile(kit, document)
    original = profile.read_bytes()
    selected = tmp_path / "local model.py"
    selected.touch()
    child = MagicMock()
    child.wait.return_value = 0
    popen = MagicMock(return_value=child)
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    monkeypatch.setattr(launcher, "wait_for_readiness", lambda *args: "http://127.0.0.1:1234")
    monkeypatch.setattr(sys, "argv", ["start-backend.py", "--backend-root", str(kit),
                                      "--machine-worker", str(selected), "--port", "1234"])

    assert launcher.main() == 0
    command = popen.call_args.args[0]
    assert command[:2] == [str(kit / launcher.CORE_RELATIVE), str(kit / "data/workspace.sqlite")]
    assert popen.call_args.kwargs["env"]["ARCHEAXIS_WORKER_PROFILE"] == str(profile)
    worker = json.loads(child.stdin.write.call_args.args[0])["text_worker"]
    assert worker["python"] == str(kit / document["python"])
    assert worker["routes"] == [{"capability": "machine.answer", "script": str(selected)},
                                {"capability": "research.public", "script": str(kit / script)}]
    assert profile.read_bytes() == original


def build_fast_local_runtime(root: Path):
    machine = "workers/machine/worker_machine_answer.py"
    document = base_document()
    document["routes"] = [{"capability": name, "script": machine}
                          for name in ("machine.answer", "research.public")]
    profile = build_profile(root, document)
    files = {}
    for name in (
        machine, launcher.FAST_LOCAL_WORKER, "workers/machine/lmstudio_structured.mjs",
        "workers/transport/text_ndjson.py", "runtime/python.exe",
        launcher.FAST_LOCAL_NODE, "workers/openmaic/NODE-LICENSE",
        f"{launcher.FAST_LOCAL_SDK}/package.json", f"{launcher.FAST_LOCAL_SDK}/dist/index.mjs",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        content = name.encode("utf-8")
        path.write_bytes(content)
        files[name] = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    (root / "backend-runtime-manifest.json").write_text(json.dumps({
        "schema": "archeaxis.backend-runtime/v1", "files": files,
        "lmstudio_sdk": {"status": "included", "version": "2.0.0",
                         "sdk_root": launcher.FAST_LOCAL_SDK, "node": launcher.FAST_LOCAL_NODE},
    }), encoding="utf-8")
    return profile, machine


def test_fast_local_cli_selects_answer_only(tmp_path, monkeypatch, capsys):
    kit = tmp_path / "kit dir"
    profile, default_machine = build_fast_local_runtime(kit)
    original_profile = profile.read_bytes()
    child = MagicMock()
    child.wait.return_value = 0
    popen = MagicMock(return_value=child)
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    monkeypatch.setattr(launcher, "wait_for_readiness", lambda *args: "http://127.0.0.1:1234")
    monkeypatch.setattr(sys, "argv", ["start-backend.py", "--backend-root", str(kit),
                                      "--machine-profile", "fast-local", "--port", "1234"])

    assert launcher.main() == 0
    receipt = json.loads(capsys.readouterr().out)
    routes = json.loads(child.stdin.write.call_args.args[0])["text_worker"]["routes"]
    assert receipt["machine_profile"] == "fast-local"
    assert routes == [{"capability": "machine.answer", "script": str(kit / launcher.FAST_LOCAL_WORKER)},
                      {"capability": "research.public", "script": str(kit / default_machine)}]
    assert profile.read_bytes() == original_profile
    launcher.start(tmp_path / "ordinary", 1234, backend_root=kit)
    ordinary = json.loads(child.stdin.write.call_args.args[0])["text_worker"]["routes"]
    assert all(route["script"] == str(kit / default_machine) for route in ordinary)


def test_fast_local_missing_sdk(tmp_path, monkeypatch):
    build_fast_local_runtime(tmp_path)
    manifest = tmp_path / "backend-runtime-manifest.json"
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["lmstudio_sdk"] = {"status": "not_included"}
    manifest.write_text(json.dumps(value), encoding="utf-8")
    popen = MagicMock()
    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    with pytest.raises(launcher.LaunchFailure, match="LM Studio SDK bundled"):
        launcher.start(Path("unused"), 1234, backend_root=tmp_path, machine_profile="fast-local")
    popen.assert_not_called()
    assert not (tmp_path / "unused").exists()


@pytest.mark.parametrize("change", ["replace", "extra"])
def test_fast_local_sdk_drift(tmp_path, change):
    build_fast_local_runtime(tmp_path)
    sdk = tmp_path / launcher.FAST_LOCAL_SDK
    if change == "replace":
        (sdk / "dist/index.mjs").write_bytes(b"changed")
    else:
        (sdk / "unlisted.mjs").touch()
    with pytest.raises(launcher.LaunchFailure, match="packaged (member changed|SDK contains unlisted files)"):
        launcher.fast_local_worker(tmp_path, python=tmp_path / "runtime/python.exe")


def build_fast_local_supplement(kit: Path, supplement: Path):
    build_fast_local_runtime(kit)
    backend = kit / "backend-runtime-manifest.json"
    document = json.loads(backend.read_text(encoding="utf-8"))
    selection = document["lmstudio_sdk"]
    component_files = {}
    for name in tuple(document["files"]):
        if not name.startswith(("workers/machine/", "workers/transport/")):
            continue
        source, target = kit / name, supplement / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        source.unlink()
        component_files[name] = document["files"].pop(name)
    # The old package still supplies its ordinary machine worker and transport.
    for ordinary in ("workers/machine/worker_machine_answer.py", "workers/transport/text_ndjson.py"):
        (kit / ordinary).write_bytes((supplement / ordinary).read_bytes())
        document["files"][ordinary] = component_files[ordinary]
    document.pop("lmstudio_sdk")
    backend.write_text(json.dumps(document), encoding="utf-8")
    launcher_file = b"launcher"
    (supplement / "start-backend.py").write_bytes(launcher_file)
    component_files["start-backend.py"] = {"bytes": len(launcher_file),
                                         "sha256": hashlib.sha256(launcher_file).hexdigest()}
    manifest = supplement / launcher.FAST_LOCAL_PROFILE_MANIFEST
    manifest.write_text(json.dumps({
        "schema": "archeaxis.fast-local-supplement/v1", "profile": "fast-local",
        "backend_manifest_sha256": hashlib.sha256(backend.read_bytes()).hexdigest(),
        "lmstudio_sdk": selection, "files": component_files,
    }), encoding="utf-8")
    return backend


@pytest.mark.parametrize("explicit", [False, True])
def test_fast_local_split_root(tmp_path, monkeypatch, explicit):
    kit, supplement = tmp_path / "kit", tmp_path / "add"
    backend = build_fast_local_supplement(kit, supplement)
    before = backend.read_bytes()
    child = MagicMock()
    monkeypatch.setattr(launcher.subprocess, "Popen", MagicMock(return_value=child))
    monkeypatch.setattr(launcher, "wait_for_readiness", lambda *args: "http://127.0.0.1:1234")
    if not explicit:
        monkeypatch.setattr(launcher, "ROOT", supplement)
    _, _, receipt, _ = launcher.start(
        tmp_path / "own-data", 1234, backend_root=kit, machine_profile="fast-local",
        machine_profile_root=supplement if explicit else None,
    )
    launch = json.loads(child.stdin.write.call_args.args[0])
    assert launch["text_worker"]["python"] == str(kit / "runtime/python.exe")
    assert launch["text_worker"]["routes"][0]["script"] == str(supplement / launcher.FAST_LOCAL_WORKER)
    assert receipt["machine_profile_source"] == "supplement" and receipt["machine_profile_root"] == str(supplement)
    assert backend.read_bytes() == before


def test_fast_local_split_binding(tmp_path):
    kit, supplement = tmp_path / "kit", tmp_path / "add"
    backend = build_fast_local_supplement(kit, supplement)
    backend.write_bytes(backend.read_bytes() + b"\n")
    with pytest.raises(launcher.LaunchFailure, match="does not match the selected backend manifest"):
        launcher.fast_local_worker(kit, python=kit / "runtime/python.exe", supplement=supplement)


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
