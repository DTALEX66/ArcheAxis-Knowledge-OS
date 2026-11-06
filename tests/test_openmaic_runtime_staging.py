"""Synthetic OpenMAIC packaging; no real Node, Core, network or user data."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from desktop.scripts import prepare_bundle as producer
from scripts.release import backend_launcher as launcher
from scripts.release import stage_backend_runtime as stager
from scripts.runtime import runtime_resources
from tests.test_backend_in_place import prepared, run_stager  # noqa: F401 - shared fixture


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "services/learning-providers/openmaic"
PREFIX = "workers/openmaic/"


def synthetic_closure():
    """The scene-build core only; the full 671-file closure is checked by
    ``test_openmaic_runtime_closure`` without copying it into every fixture."""
    return {name: stager.OPENMAIC_FILES[name] for name in stager.OPENMAIC_CORE_FILES}


def test_the_python_worker_tree_does_not_collide_with_the_node_output():
    """The staged Node provider is ``workers/openmaic``; a Python worker directory
    of the same name makes ``stage_backend_runtime`` refuse every OpenMAIC
    staging with "OpenMAIC output conflicts with worker donor". The synthetic
    fixtures never copy the real worker tree, so this guards the real shape."""
    assert not (ROOT / "services/python-workers/openmaic").exists()
    assert (ROOT / "services/python-workers/course/worker_outline_local_model.py").is_file()


def synthetic_provider(case):
    # These tiny test donors are added after the fixture seals its synthetic
    # run metadata. Exclude only these fixture paths from that fake Git repo;
    # the real growth plan still pins and rechecks every selected byte.
    with (case["repo"] / ".git/info/exclude").open("a", encoding="utf-8") as exclude:
        exclude.write("\n/services/learning-providers/openmaic/\n/fixture-node.exe\n/fixture-node-license.txt\n")
    donor = case["repo"] / "services/learning-providers/openmaic"
    for relative, identity in stager.OPENMAIC_FILES.items():
        raw = (SOURCE / relative).read_bytes()
        assert {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} == identity
        target = stager.filesystem_path(donor / relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    node = case["repo"] / "fixture-node.exe"
    licence = case["repo"] / "fixture-node-license.txt"
    node.write_bytes(b"synthetic Node bytes; never executed\n")
    licence.write_bytes(b"synthetic Node licence\n")
    digest = hashlib.sha256(node.read_bytes()).hexdigest()
    options = ["--openmaic-node", str(node), "--openmaic-node-sha256", digest,
               "--openmaic-node-license", str(licence)]
    return donor, node, licence, digest, options


def capture_launch(monkeypatch, root):
    seen = {}

    class Input:
        def write(self, value):
            seen.update(json.loads(value))
        def flush(self):
            pass
        def close(self):
            pass

    class Child:
        stdin = Input()

    monkeypatch.setattr(launcher, "ROOT", root)
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: Child())
    monkeypatch.setattr(launcher, "wait_for_readiness", lambda *args: "http://127.0.0.1:1234")
    launcher.start(root / "data", 1234)
    return seen


def test_selected_openmaic_growth_plan_manifest_and_launch(prepared, monkeypatch):
    case = prepared
    monkeypatch.setattr(stager, "OPENMAIC_FILES", synthetic_closure())
    donor, node, licence, digest, options = synthetic_provider(case)
    called = []
    stage = stager.stage_openmaic_provider

    def check_plan(root, plan):
        active = stager.growth._batch.get()
        assert active is not None
        for name in stager.OPENMAIC_FILES:
            assert active["inputs"][stager.growth.plain(donor / name)] == stager.OPENMAIC_FILES[name]
        for path in (node, licence):
            assert active["inputs"][stager.growth.plain(path)] == stager.growth.row(path)
        assert active["total"] >= sum(row["bytes"] for row in active["inputs"].values())
        called.append(True)
        stage(root, plan)

    monkeypatch.setattr(stager, "stage_openmaic_provider", check_plan)
    assert run_stager(case, extra=options) == 0
    assert called == [True]
    root = case["output"]
    manifest = json.loads(stager.filesystem_path(root / "backend-runtime-manifest.json").read_bytes())
    assert manifest["openmaic_scene_build"] == {"status": "INCLUDED", "node_sha256": digest}
    members = manifest["files"]
    expected = {**{name: donor / name for name in stager.OPENMAIC_FILES},
                "node.exe": node, "NODE-LICENSE": licence}
    for relative, source in expected.items():
        target = stager.filesystem_path(root / PREFIX / relative)
        raw = stager.filesystem_path(source).read_bytes()
        assert target.read_bytes() == raw
        assert members[PREFIX + relative] == {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    runtime_resources.verify_members(root, {PREFIX + name: members[PREFIX + name] for name in expected})
    runtime_resources.verify_openmaic_contract(manifest, members)
    launch = capture_launch(monkeypatch, root)
    assert launch["openmaic_node_worker"] == {
        "executable": str(root / PREFIX / "node.exe"), "executable_sha256": digest,
        "script": str(root / PREFIX / "scene-build-worker.mjs")}
    assert all(route["capability"] != "course.openmaic.scene-build"
               for route in launch["text_worker"].get("routes", []))


def test_openmaic_input_bytes_can_trigger_growth_review_before_copy(prepared, monkeypatch):
    case = prepared
    monkeypatch.setattr(stager, "OPENMAIC_FILES", synthetic_closure())
    *_, options = synthetic_provider(case)
    args = SimpleNamespace(runtime=case["output"] / "runtime", workers=case["repo"] / "services/python-workers",
                           core=case["core"], shared=case["repo"] / "shared/learning_scheduler.py",
                           vc_runtime=case["vc"], asr_model=None, webview2_runtime=None, dep=[])
    _, without_openmaic = stager.runtime_copy_plan(args, True, repository=case["repo"])
    # With the ordinary plan plus its generation allowance still one byte
    # under the boundary, the selected provider must make projection fail.
    case["storage_report"]["dev_root"][0]["bytes"] += 2 * 1024 ** 3 - without_openmaic - 256 - 1
    with pytest.raises(stager.growth.portable.GrowthReviewRequiredError):
        run_stager(case, extra=options)
    assert not stager.filesystem_path(case["output"]).exists()
    receipt = json.loads(stager.filesystem_path(
        case["context"]["paths"]["artifacts"] / "portable-storage-receipt.json").read_bytes())
    assert receipt["projected_review"]["status"] == "REVIEW_REQUIRED"


def test_missing_openmaic_options_keep_old_launch_available(prepared, monkeypatch):
    case = prepared
    assert run_stager(case) == 0
    root = case["output"]
    manifest = json.loads(stager.filesystem_path(root / "backend-runtime-manifest.json").read_bytes())
    assert manifest["openmaic_scene_build"] == {"status": "NOT_INCLUDED", "node_sha256": None}
    runtime_resources.verify_openmaic_contract(manifest, manifest["files"])
    assert not stager.filesystem_path(root / PREFIX).exists()
    assert "openmaic_node_worker" not in capture_launch(monkeypatch, root)


@pytest.mark.parametrize("indices", [(0,), (2,), (4,), (0, 2), (0, 4), (2, 4)])
def test_partial_openmaic_options_fail_before_output(prepared, indices, monkeypatch):
    case = prepared
    monkeypatch.setattr(stager, "OPENMAIC_FILES", synthetic_closure())
    *_, options = synthetic_provider(case)
    partial = [value for index in indices for value in options[index:index + 2]]
    with pytest.raises(ValueError, match="OpenMAIC requires"):
        run_stager(case, extra=partial)
    assert not stager.filesystem_path(case["output"]).exists()


@pytest.mark.parametrize("mutation", ["wrong_digest", "source", "license_empty"])
def test_invalid_explicit_openmaic_inputs_fail_before_output(prepared, mutation):
    case = prepared
    donor, node, licence, _, options = synthetic_provider(case)
    if mutation == "wrong_digest":
        options[3] = "0" * 64
    elif mutation == "source":
        stager.filesystem_path(donor / "scene-build-worker.mjs").write_bytes(b"wrong source")
    else:
        licence.write_bytes(b"")
    with pytest.raises(ValueError, match="OpenMAIC"):
        run_stager(case, extra=options)
    assert not stager.filesystem_path(case["output"]).exists()


@pytest.mark.parametrize("member", ["node", "license", "source"])
def test_selected_inputs_that_drift_after_planning_abort(prepared, member):
    case = prepared
    donor, node, licence, _, options = synthetic_provider(case)
    changed = {"node": node, "license": licence, "source": donor / "scene-build-worker.mjs"}[member]

    def mutate(root):
        path = stager.filesystem_path(changed)
        original = path.read_bytes()
        path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        return case["prepare"](repository=case["repo"], destination=root, _backend_in_place=True,
                               _environment=case["env"])

    with pytest.raises(ValueError, match="OpenMAIC input changed"):
        run_stager(case, callback=mutate, extra=options)
    assert not stager.filesystem_path(case["output"] / "backend-runtime-manifest.json").exists()


def test_changed_staged_openmaic_copy_aborts(prepared, monkeypatch):
    case = prepared
    *_, options = synthetic_provider(case)
    stage = stager.stage_openmaic_provider

    def mutate_copy(root, plan):
        stage(root, plan)
        stager.filesystem_path(root / PREFIX / "node.exe").write_bytes(b"changed staged Node")

    monkeypatch.setattr(stager, "stage_openmaic_provider", mutate_copy)
    with pytest.raises(ValueError, match="OpenMAIC staged input changed"):
        run_stager(case, extra=options)
    assert not stager.filesystem_path(case["output"] / "backend-runtime-manifest.json").exists()


def test_invalid_optional_manifest_or_staged_bytes_disable_only_node(prepared, monkeypatch):
    case = prepared
    *_, options = synthetic_provider(case)
    assert run_stager(case, extra=options) == 0
    root = case["output"]
    manifest_path = stager.filesystem_path(root / "backend-runtime-manifest.json")
    original = manifest_path.read_bytes()
    node = stager.filesystem_path(root / PREFIX / "node.exe")
    node_bytes = node.read_bytes()
    document = json.loads(original)
    bad_documents = [b"{", b'{"schema":"one","schema":"two"}',
                     json.dumps({**document, "openmaic_scene_build": {"status": "INCLUDED", "node_sha256": "x"}}).encode(),
                     json.dumps({**document, "openmaic_scene_build": {"status": "NOT_INCLUDED", "node_sha256": None}}).encode()]
    for raw in bad_documents:
        manifest_path.write_bytes(raw)
        assert launcher.openmaic_node_worker(root) is None
    manifest_path.write_bytes(original)
    node.write_bytes(b"X" * len(node_bytes))
    assert launcher.openmaic_node_worker(root) is None
    assert "openmaic_node_worker" not in capture_launch(monkeypatch, root)
    node.write_bytes(node_bytes)
    for relative in ("NODE-LICENSE", "scene-build-worker.mjs", "vendor/generation-0.3.28/LICENSE"):
        target = stager.filesystem_path(root / PREFIX / relative)
        original_bytes = target.read_bytes()
        target.write_bytes(bytes([original_bytes[0] ^ 1]) + original_bytes[1:])
        assert launcher.openmaic_node_worker(root) is None
        target.write_bytes(original_bytes)
    manifest_path.unlink()
    assert launcher.openmaic_node_worker(root) is None
    manifest_path.write_bytes(original)
    assert launcher.openmaic_node_worker(root) is not None


def test_oversized_manifest_disables_only_optional_node(prepared, monkeypatch):
    case = prepared
    *_, options = synthetic_provider(case)
    assert run_stager(case, extra=options) == 0
    root = case["output"]
    manifest = stager.filesystem_path(root / "backend-runtime-manifest.json")
    size = manifest.stat().st_size
    assert size > 1
    assert launcher.OPENMAIC_MANIFEST_MAX_BYTES == 16 * 1024 * 1024
    # Keep the fixture tiny while checking both sides of the real size guard.
    monkeypatch.setattr(launcher, "OPENMAIC_MANIFEST_MAX_BYTES", size)
    assert launcher.openmaic_node_worker(root) is not None
    monkeypatch.setattr(launcher, "OPENMAIC_MANIFEST_MAX_BYTES", size - 1)
    assert launcher.openmaic_node_worker(root) is None
    assert "openmaic_node_worker" not in capture_launch(monkeypatch, root)


@pytest.mark.parametrize("constant", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_manifest_disables_only_optional_node(prepared, monkeypatch, constant):
    case = prepared
    *_, options = synthetic_provider(case)
    assert run_stager(case, extra=options) == 0
    root = case["output"]
    manifest = stager.filesystem_path(root / "backend-runtime-manifest.json")
    document = json.loads(manifest.read_bytes())
    document["synthetic_nonfinite"] = constant
    manifest.write_text(json.dumps(document), encoding="utf-8")
    assert launcher.openmaic_node_worker(root) is None
    assert "openmaic_node_worker" not in capture_launch(monkeypatch, root)


def test_linked_manifest_is_not_read_and_does_not_block_core(prepared, monkeypatch):
    case = prepared
    *_, options = synthetic_provider(case)
    assert run_stager(case, extra=options) == 0
    root = case["output"]
    manifest = root / "backend-runtime-manifest.json"
    alias = case["repo"] / ".project-local/manifest-hardlink.json"
    os.link(stager.filesystem_path(manifest), stager.filesystem_path(alias))
    original_open = Path.open

    def no_manifest_read(path, *args, **kwargs):
        if path == manifest:
            pytest.fail("linked manifest must be rejected before opening")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_manifest_read)
    try:
        assert launcher.openmaic_node_worker(root) is None
        assert "openmaic_node_worker" not in capture_launch(monkeypatch, root)
    finally:
        stager.filesystem_path(alias).unlink()


def test_node_linked_after_stat_is_rejected_before_read(prepared, monkeypatch):
    case = prepared
    *_, options = synthetic_provider(case)
    assert run_stager(case, extra=options) == 0
    root = case["output"]
    node = root / PREFIX / "node.exe"
    alias = case["repo"] / ".project-local/node-hardlink.exe"
    original_open = Path.open
    opened = []

    def link_before_open(path, *args, **kwargs):
        if path == node:
            os.link(stager.filesystem_path(node), stager.filesystem_path(alias))
            opened.append(True)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", link_before_open)
    try:
        assert launcher.openmaic_node_worker(root) is None
        assert opened == [True]
    finally:
        if stager.filesystem_path(alias).exists():
            stager.filesystem_path(alias).unlink()


def test_manifest_linked_after_stat_is_rejected_before_read(prepared, monkeypatch):
    case = prepared
    *_, options = synthetic_provider(case)
    assert run_stager(case, extra=options) == 0
    root = case["output"]
    manifest = root / "backend-runtime-manifest.json"
    alias = case["repo"] / ".project-local/manifest-race-hardlink.json"
    original_open = Path.open
    opened = []

    def link_before_open(path, *args, **kwargs):
        if path == manifest:
            os.link(stager.filesystem_path(manifest), stager.filesystem_path(alias))
            opened.append(True)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", link_before_open)
    try:
        assert launcher.openmaic_node_worker(root) is None
        assert opened == [True]
    finally:
        if stager.filesystem_path(alias).exists():
            stager.filesystem_path(alias).unlink()


def test_prepare_bundle_forwards_explicit_openmaic_through_real_growth_plan(prepared):
    case = prepared
    _, node, licence, digest, _ = synthetic_provider(case)
    result = producer.prepare_backend_candidate(
        repository=case["repo"], destination=case["output"], core=case["core"],
        openmaic_node=node, openmaic_node_sha256=digest, openmaic_node_license=licence,
        storage_context=case["context"], storage_generated_bytes=256)
    assert result == case["output"] / "runtime/python.exe"
    manifest = json.loads(stager.filesystem_path(case["output"] / "backend-runtime-manifest.json").read_bytes())
    assert manifest["openmaic_scene_build"] == {"status": "INCLUDED", "node_sha256": digest}
    runtime_resources.verify_openmaic_contract(manifest, manifest["files"])


def test_prepare_bundle_rejects_partial_openmaic_before_preparation(prepared):
    case = prepared
    _, node, _, _, _ = synthetic_provider(case)
    with pytest.raises(ValueError, match="OpenMAIC requires"):
        producer.prepare_backend_candidate(repository=case["repo"], destination=case["output"],
                                           core=case["core"], openmaic_node=node)
    assert not stager.filesystem_path(case["output"]).exists()


def test_prepare_bundle_cli_forwards_node_options(prepared, monkeypatch):
    case = prepared
    _, node, licence, digest, options = synthetic_provider(case)
    observed = {}

    def capture(**kwargs):
        observed.update(kwargs)
        return case["output"] / "runtime/python.exe"

    monkeypatch.setattr(producer, "prepare_backend_candidate", capture)
    monkeypatch.setattr(producer, "declared_asr_model", lambda _: None)
    monkeypatch.setattr(producer.sys, "argv", ["prepare_bundle", "--repository", str(case["repo"]),
                        "--destination", str(case["output"]), "--core", str(case["core"]),
                        "--backend-candidate", *options])
    assert producer.main() == 0
    assert (observed["openmaic_node"], observed["openmaic_node_sha256"], observed["openmaic_node_license"]) == (
        node, digest, licence)


@pytest.mark.parametrize("options", [["--openmaic-node", "node.exe"],
                                     ["--openmaic-node", "node.exe", "--openmaic-node-sha256", "a" * 64,
                                      "--openmaic-node-license", "license.txt"]])
def test_prepare_bundle_cli_rejects_partial_or_non_candidate_inputs(prepared, monkeypatch, options):
    case = prepared
    monkeypatch.setattr(producer.sys, "argv", ["prepare_bundle", "--repository", str(case["repo"]),
                        "--destination", str(case["output"]), *options])
    with pytest.raises(SystemExit) as caught:
        producer.main()
    assert caught.value.code == 2
    assert not stager.filesystem_path(case["output"]).exists()
