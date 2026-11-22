"""The optional offline SDK through the formal backend candidate producer."""
import json
from pathlib import Path

import pytest
import yaml

from desktop.scripts import prepare_bundle as producer
from scripts.release import stage_backend_runtime as stager
from scripts.release import stage_fast_local_profile as supplement
from tests.test_backend_in_place import prepared  # noqa: F401 - shared fixture
from tests.test_deeptutor_runtime_staging import add_synthetic_provider
from tests.test_openmaic_runtime_staging import synthetic_provider


@pytest.mark.parametrize("private_practice", [False, True])
def test_sdk_candidate(request, tmp_path, monkeypatch, private_practice):
    case = request.getfixturevalue("prepared")
    _, node, license_file, node_sha, _ = synthetic_provider(case)
    resources = stager.runtime_resources
    donor = tmp_path / "sdk"
    config = Path(stager.__file__).resolve().parents[2] / "config/model-profiles/lm-studio-sdk"
    lock = json.loads((config / "package-lock.json").read_bytes())
    rows = {}
    for package, metadata in lock["packages"].items():
        if not package:
            continue
        rel = package + "/package.json"
        path = donor / rel
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"name": package.removeprefix("node_modules/"),
                                    "version": metadata["version"]}), encoding="utf-8")
        rows[rel] = stager.growth.row(path)
    # Only this fixture replaces the upstream byte identities with its small synthetic packages.
    monkeypatch.setattr(resources, "LMSTUDIO_NPM_TREE", resources.npm_tree_digest(rows))
    worker = case["repo"] / "services/python-workers/machine"
    worker.mkdir()
    with (case["repo"] / ".git/info/exclude").open("a", encoding="utf-8") as ignore:
        ignore.write("\n/services/python-workers/machine/\n")
        ignore.write("/services/python-workers/routes.json\n/services/python-workers/document/\n/services/learning-providers/deeptutor/\n")
    for name in ("worker_machine_answer.py", "worker_machine_fast_local.py", "worker_machine_bundled.py", "lmstudio_structured.mjs"):
        (worker / name).write_bytes(b"# fixture")
    source_routes = worker.parent / "routes.json"
    native = {"schema": "archeaxis.worker-routes/v1", "routes": {}}
    if private_practice:
        add_synthetic_provider(case)
        native = json.loads(source_routes.read_bytes())
    native["routes"]["machine.answer"] = ["machine/worker_machine_answer.py"]
    native["routes"]["research.public"] = ["missing/preferred.py", "machine/worker_machine_answer.py"]
    native["routes"]["absent.capability"] = ["missing/worker.py"]
    source_routes.write_text(json.dumps(native), encoding="utf-8")
    args = dict(repository=case["repo"], destination=case["output"], core=case["core"],
                storage_context=case["context"], storage_generated_bytes=256, lmstudio_sdk_dir=donor)
    with pytest.raises(ValueError, match="app-local OpenMAIC Node"):
        producer.prepare_backend_candidate(**args)
    producer.prepare_backend_candidate(**args, openmaic_node=node, openmaic_node_sha256=node_sha,
                                       openmaic_node_license=license_file)
    manifest = json.loads((case["output"] / "backend-runtime-manifest.json").read_bytes())
    claim = manifest["lmstudio_sdk"]
    assert claim["status"] == "included" and claim["node"] == "workers/openmaic/node.exe"
    assert json.loads(source_routes.read_bytes()) == native
    staged = json.loads((case["output"] / "workers/routes.json").read_bytes())["routes"]
    profile = json.loads((case["output"] / "worker-profile.json").read_bytes())
    assert staged["machine.answer"] == [resources.BUNDLED_MACHINE]
    assert claim["default_machine_worker"] == "workers/" + resources.BUNDLED_MACHINE
    assert staged["research.public"] == ["machine/worker_machine_answer.py"]
    assert "absent.capability" not in staged
    assert (stager.PRACTICE_CAPABILITY in staged) == private_practice
    assert {r["capability"]: r["script"] for r in profile["routes"]} == {
        name: "workers/" + scripts[0] for name, scripts in staged.items()}
    old = {**manifest, "lmstudio_sdk": resources.lmstudio_sdk_manifest(True)}
    resources.verify_lmstudio_sdk_contract(old, {k: v for k, v in manifest["files"].items()
                                                 if k != claim["default_machine_worker"]})
    with pytest.raises(ValueError, match="differs from SDK declaration"):
        resources.verify_worker_contract(case["output"], manifest["files"], old)
    staged_lock = stager.filesystem_path(case["output"] / claim["npm_lock"])
    assert staged_lock.read_bytes() == (config / "package-lock.json").read_bytes()
    resources.verify_lmstudio_sdk_contract(manifest, manifest["files"])
    del manifest["files"][claim["sdk_root"] + "/package.json"]
    with pytest.raises(ValueError, match="Incomplete or modified"):
        resources.verify_lmstudio_sdk_contract(manifest, manifest["files"])
    (donor / "node_modules/chalk/extra.js").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="locked npm tarballs"):
        stager.lmstudio_sdk_plan(donor)


def test_old_and_optional_manifests():
    resources = stager.runtime_resources
    resources.verify_lmstudio_sdk_contract({}, {})
    resources.verify_lmstudio_sdk_contract({"lmstudio_sdk": {"status": "not_included"}}, {})
    with pytest.raises(ValueError, match="without SDK files"):
        resources.verify_lmstudio_sdk_contract({"lmstudio_sdk": resources.lmstudio_sdk_manifest(True)}, {})


def test_supplement_owns_only_profile_files(tmp_path, monkeypatch):
    backend, donor, output = (tmp_path / name for name in ("backend", "donor", "profile"))
    backend.mkdir()
    borrowed = {}
    for name in supplement.BORROWED:
        path = backend / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
        borrowed[name] = stager.growth.row(path)
    manifest = backend / "backend-runtime-manifest.json"
    manifest.write_text(json.dumps({"files": borrowed}), encoding="utf-8")
    monkeypatch.setattr(supplement, "PUBLISHED_MANIFEST", stager.sha256(manifest))
    donor.mkdir()
    entry = donor / "index.mjs"
    entry.write_text("export const test = true", encoding="utf-8")
    monkeypatch.setattr(stager, "lmstudio_sdk_plan", lambda _: {"node_modules/@lmstudio/sdk/dist/index.mjs":
                                                               (entry, stager.growth.row(entry))})
    package = json.loads(supplement.stage_profile(backend, donor, output).read_bytes())
    assert package["borrowed_backend_members"] == borrowed
    assert not (set(borrowed) & package["files"].keys())
    owned = {p.relative_to(output).as_posix(): stager.growth.row(p) for p in output.rglob("*")
             if p.is_file() and p.name != supplement.MANIFEST}
    assert owned == package["files"]
    assert {"start-fast-local.cmd", "README.zh-CN.md", "workers/machine/worker_machine_fast_local.py"} <= owned.keys()
    config = "config/environment/capability-requirements.yaml"
    assert yaml.safe_load((output / "workers/capability-requirements.yaml").read_bytes()) == yaml.safe_load(
        (supplement.REPOSITORY / config).read_bytes())
    with pytest.raises(ValueError, match="fresh supplement"):
        supplement.stage_profile(backend, donor, output)
    (backend / "workers/openmaic/node.exe").write_bytes(b"changed")
    with pytest.raises(ValueError, match="resource changed"):
        supplement.stage_profile(backend, donor, tmp_path / "tampered")
    assert not (tmp_path / "tampered").exists()
