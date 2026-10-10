"""Synthetic portable fixtures verify refusal boundaries, not native qualification."""
import json
import os
from pathlib import Path

import pytest

from scripts.release import tauri_portable_candidate as portable


def fixture_bundle(tmp_path: Path):
    root = tmp_path / "release"
    root.mkdir()
    rows = {
        "runtime/python.exe": b"synthetic-interpreter",
        "core/archeaxis-api.exe": b"synthetic-core",
        "workers/transport/text_ndjson.py": b"text",
        "workers/document/worker.py": b"worker",
        "shared/learning_scheduler.py": b"scheduler",
        "start-backend.py": b"launcher",
        "start-backend.cmd": b"launcher-cmd",
        "workers/routes.json": json.dumps({"schema": "archeaxis.worker-routes/v1",
            "routes": {"document.detect": ["document/worker.py"]}}).encode(),
        "worker-profile.json": json.dumps({"schema": "archeaxis.worker-profile/v1",
            "python": "runtime/python.exe", "script": "workers/transport/text_ndjson.py",
            "staging": "data/worker-staging", "routes": [{"capability": "document.detect",
                "script": "workers/document/worker.py"}]}).encode(),
    }
    files = {}
    for name, payload in rows.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        files[name] = {"bytes": len(payload), "sha256": portable.digest(path)}
    (root / "backend-runtime-manifest.json").write_text(json.dumps({
        "schema": "archeaxis.backend-runtime/v1", "files": files,
        "runtime_source": {"evidence": "ASSERTED_NOT_VERIFIED"}}), encoding="utf-8")
    host = root / "ArcheAxis.exe"
    host.write_bytes(b"synthetic-host")
    build = {"status": "PASS", "source_consistent": True, "host_sha256": portable.digest(host),
             "core_sha256": portable.digest(root / "core/archeaxis-api.exe"),
             "source_patch_sha256": "a" * 64}
    return host, build


def test_complete_copy_keeps_provenance_and_exact_members(tmp_path):
    host, build = fixture_bundle(tmp_path)
    manifest = portable.plan(host, build, portable.RESOURCES)
    destination = tmp_path / "中文便携候选"
    portable.assemble(host, destination, manifest)
    checked = portable.verify(destination)
    assert checked["runtime_provenance"]["evidence"] == "ASSERTED_NOT_VERIFIED"
    assert checked["installed"] is False and checked["published"] is False
    assert (destination / "portable.flag").read_bytes() == b""
    assert checked["files"]["ArcheAxis.exe"]["sha256"] == build["host_sha256"]


@pytest.mark.parametrize("name", ["../private", "/private", "runtime/../private", "runtime\\private",
                                "runtime/a:b", "runtime//private", "runtime/.env", "workers/.codex/state"])
def test_unsafe_or_private_paths_are_rejected_before_reading(name):
    with pytest.raises(ValueError):
        portable.relative_path(name)


def test_only_exact_public_upstream_path_and_identity_are_eligible(tmp_path):
    name = next(iter(portable.PUBLIC_UPSTREAM_FILES))
    assert portable.relative_path(name) == name
    with pytest.raises(ValueError, match="upstream exception bytes changed"):
        portable.verify_members(tmp_path, {name: {"bytes": 1, "sha256": "b" * 64}})
    with pytest.raises(ValueError, match="Private material"):
        portable.relative_path(name.replace("SKILL.md", "private-session.json"))


def test_unknown_runtime_file_is_not_silently_copied(tmp_path):
    host, build = fixture_bundle(tmp_path)
    (host.parent / "runtime/unknown.bin").write_bytes(b"unknown")
    with pytest.raises(ValueError, match="Unmanifested"):
        portable.plan(host, build, portable.RESOURCES)


def test_missing_worker_script_and_corruption_are_rejected(tmp_path):
    host, build = fixture_bundle(tmp_path)
    (host.parent / "workers/document/worker.py").write_bytes(b"broken")
    with pytest.raises(ValueError, match="Member identity mismatch"):
        portable.plan(host, build, portable.RESOURCES)


def test_wrong_host_and_changed_resource_contract_are_rejected(tmp_path):
    host, build = fixture_bundle(tmp_path)
    with pytest.raises(ValueError, match="contract changed"):
        portable.plan(host, build, portable.RESOURCES | {"new-resource"})
    host.write_bytes(b"other-host")
    with pytest.raises(ValueError, match="qualified build"):
        portable.plan(host, build, portable.RESOURCES)


def test_target_is_never_overwritten(tmp_path):
    host, build = fixture_bundle(tmp_path)
    manifest = portable.plan(host, build, portable.RESOURCES)
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "user.txt"
    sentinel.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        portable.assemble(host, destination, manifest)
    assert sentinel.read_bytes() == b"preserve"


def test_output_corruption_and_unmanifested_data_are_not_static_pass(tmp_path):
    host, build = fixture_bundle(tmp_path)
    destination = tmp_path / "candidate"
    portable.assemble(host, destination, portable.plan(host, build, portable.RESOURCES))
    (destination / "unexpected.txt").write_bytes(b"unexpected")
    with pytest.raises(ValueError, match="Unexpected"):
        portable.verify(destination)
    (destination / "unexpected.txt").unlink()
    (destination / "ArcheAxis.exe").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="identity mismatch"):
        portable.verify(destination)


def test_hardlinked_input_is_refused(tmp_path):
    host, build = fixture_bundle(tmp_path)
    os.link(host.parent / "core/archeaxis-api.exe", tmp_path / "linked-core")
    with pytest.raises(ValueError, match="independent regular file"):
        portable.plan(host, build, portable.RESOURCES)


def test_exact_cargo_host_pair_copies_to_independent_output(tmp_path):
    host, build = fixture_bundle(tmp_path)
    (host.parent / "deps").mkdir()
    os.link(host, host.parent / "deps/ArcheAxis.exe")
    manifest = portable.plan(host, build, portable.RESOURCES)
    destination = tmp_path / "independent-candidate"
    portable.assemble(host, destination, manifest)
    assert os.stat(portable.native(destination / "ArcheAxis.exe")).st_nlink == 1
    os.link(host, tmp_path / "third-alias")
    with pytest.raises(ValueError, match="independent regular file"):
        portable.plan(host, build, portable.RESOURCES)


def test_profile_route_drift_is_refused_even_with_matching_hash(tmp_path):
    host, build = fixture_bundle(tmp_path)
    path = host.parent / "worker-profile.json"
    profile = json.loads(path.read_text())
    profile["routes"] = []
    path.write_text(json.dumps(profile), encoding="utf-8")
    manifest_path = host.parent / "backend-runtime-manifest.json"
    backend = json.loads(manifest_path.read_text())
    backend["files"]["worker-profile.json"] = {"bytes": path.stat().st_size, "sha256": portable.digest(path)}
    manifest_path.write_text(json.dumps(backend), encoding="utf-8")
    with pytest.raises(ValueError, match="routes differ"):
        portable.plan(host, build, portable.RESOURCES)


def test_long_windows_member_is_copied_and_verified(tmp_path):
    host, build = fixture_bundle(tmp_path)
    relative = "runtime/" + "/".join(["long-package-member"] * 9) + "/payload.txt"
    source = host.parent / relative
    os.makedirs(portable.native(source.parent))
    with open(portable.native(source), "xb") as stream:
        stream.write(b"public-long-path-fixture")
    manifest_path = host.parent / "backend-runtime-manifest.json"
    backend = json.loads(manifest_path.read_text())
    backend["files"][relative] = {"bytes": 24, "sha256": portable.digest(source)}
    manifest_path.write_text(json.dumps(backend), encoding="utf-8")
    destination = tmp_path / "long-path-candidate"
    portable.assemble(host, destination, portable.plan(host, build, portable.RESOURCES))
    assert portable.verify(destination)["files"][relative]["sha256"] == portable.digest(source)
