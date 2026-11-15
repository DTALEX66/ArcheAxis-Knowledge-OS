"""New stage identity guards using tiny real formal-resource fixtures; no execution."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scripts.probes import colearning_asset_revision_smoke as probe
from scripts.runtime import dev, runtime_resources


@pytest.fixture
def staged(tmp_path_factory, monkeypatch):
    # Keep the real formal suffix while avoiding Windows MAX_PATH in pytest names.
    repo = tmp_path_factory.mktemp("s")
    stage = repo / ".project-local/runs/w/s/artifacts/r"
    source_worker = repo / "services/python-workers/machine/worker_machine_answer.py"
    source_worker.parent.mkdir(parents=True)
    source_worker.write_bytes(b"# synthetic non-executable worker identity\n")
    monkeypatch.setattr(probe, "REPO", repo)
    profile = {"schema": "archeaxis.worker-profile/v1", "python": "runtime/python.exe",
               "script": "workers/transport/text_ndjson.py", "staging": "data/worker-staging",
               "routes": [{"capability": "machine.answer", "script": "workers/machine/worker_machine_answer.py"}]}
    files = {"core/archeaxis-api.exe": b"synthetic Core identity", "runtime/python.exe": b"synthetic Python identity",
             "workers/machine/worker_machine_answer.py": source_worker.read_bytes(),
             "workers/transport/text_ndjson.py": b"# synthetic transport identity\n",
             "workers/routes.json": json.dumps({"schema": "archeaxis.worker-routes/v1", "routes": {
                 "machine.answer": ["machine/worker_machine_answer.py"]}}).encode(),
             "worker-profile.json": json.dumps(profile).encode(),
             "start-backend.py": b"# synthetic launcher identity\n", "start-backend.cmd": b"rem synthetic\n"}
    for name in ("vcruntime140.dll", "vcruntime140_1.dll"):
        for prefix in ("", "core/", "runtime/"):
            files[prefix + name] = b"synthetic VC runtime identity"
    for name, content in files.items():
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (stage / "shared").mkdir()
    manifest = stage / "backend-runtime-manifest.json"

    def publish():
        rows = {name: {key: dev.build_file_identity(stage / name)[key] for key in ("bytes", "sha256")}
                for name in files}
        manifest.write_text(json.dumps({"schema": "archeaxis.backend-runtime/v1", "files": rows}), encoding="utf-8")
        return dev.build_file_identity(manifest)["sha256"]

    core = dev.build_file_identity(stage / "core/archeaxis-api.exe")
    paths = {"run": repo / ".project-local/runs/w/p"}
    return SimpleNamespace(root=stage, profile=profile, manifest=manifest, publish=publish,
                           core=core, paths=paths)


def test_formal_stage_binds_the_actual_python_profile_worker_and_launcher(staged):
    pin = staged.publish()
    before = {path.relative_to(staged.root).as_posix(): path.read_bytes()
              for path in staged.root.rglob("*") if path.is_file()}
    actual = probe.bind_staged_runtime(staged.root, pin, staged.core, staged.paths, dev, runtime_resources)
    assert actual["mode"] == "FORMAL_STAGED_RUNTIME"
    assert actual["python"]["path"] == str(staged.root / "runtime/python.exe")
    assert actual["worker"]["sha256"] == actual["current_source_worker"]["sha256"]
    assert actual["manifest"]["sha256"] == pin
    assert probe.bind_staged_runtime(staged.root, pin, staged.core, staged.paths, dev, runtime_resources) == actual
    assert before == {path.relative_to(staged.root).as_posix(): path.read_bytes()
                      for path in staged.root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("fault", ["wrong_pin", "changed_worker_repinned", "developer_python_repinned",
                                  "extra_member", "changed_python", "changed_core_repinned"])
def test_stage_refuses_runtime_or_source_rebinding_before_any_launch(staged, fault):
    pin = staged.publish()
    if fault == "wrong_pin":
        pin = "0" * 64
    elif fault == "changed_worker_repinned":
        (staged.root / "workers/machine/worker_machine_answer.py").write_bytes(b"# stale source\n")
        pin = staged.publish()
    elif fault == "developer_python_repinned":
        staged.profile["python"] = "../developer-venv/python.exe"
        (staged.root / "worker-profile.json").write_text(json.dumps(staged.profile), encoding="utf-8")
        pin = staged.publish()
    elif fault == "extra_member":
        (staged.root / "workers/unmanifested.py").write_bytes(b"# not declared\n")
    elif fault == "changed_python":
        (staged.root / "runtime/python.exe").write_bytes(b"changed interpreter, same old manifest")
    else:
        (staged.root / "core/archeaxis-api.exe").write_bytes(b"unqualified Core")
        pin = staged.publish()
    with pytest.raises(ValueError):
        probe.bind_staged_runtime(staged.root, pin, staged.core, staged.paths, dev, runtime_resources)


@pytest.mark.parametrize("args", [["--runtime-root", "unused"], ["--runtime-manifest-sha256", "a" * 64]])
def test_runtime_selection_requires_both_explicit_arguments_before_io(args):
    with pytest.raises(SystemExit) as error:
        probe.main(["--core-build-receipt", "unused.json", *args])
    assert error.value.code == 2
