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
    for name in ("vcruntime140.dll", "vcruntime140_1.dll"):
        for directory in ("", "core/", "runtime/"):
            rows[directory + name] = ("synthetic " + name).encode()
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


def fixture_fixed_webview(host, build, monkeypatch):
    runtime = host.parent / "runtime/webview2"
    runtime.mkdir()
    rows = []
    for name in ("msedgewebview2.exe", "msedge.dll"):
        path = runtime / name
        path.write_bytes(("synthetic " + name).encode())
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": portable.digest(path)})
    manifest = runtime / "aaos-fixed-runtime-manifest.json"
    manifest.write_text(json.dumps({"schema": "archeaxis.official-fixed-runtime-files/v1",
        "version": "synthetic", "files": rows}), encoding="utf-8")
    monkeypatch.setattr(portable.runtime_resources, "FIXED_WEBVIEW2_MANIFEST_SHA256", portable.digest(manifest))
    backend_file = host.parent / "backend-runtime-manifest.json"
    backend = json.loads(backend_file.read_text(encoding="utf-8"))
    for path in runtime.iterdir():
        backend["files"][path.relative_to(host.parent).as_posix()] = {
            "bytes": path.stat().st_size, "sha256": portable.digest(path)}
    backend_file.write_text(json.dumps(backend), encoding="utf-8")
    build["webview_runtime"] = portable.runtime_resources.verify_fixed_webview2(host.parent)


def test_fixed_webview_remains_bound_after_assembly(tmp_path, monkeypatch):
    host, build = fixture_bundle(tmp_path)
    fixture_fixed_webview(host, build, monkeypatch)
    destination = tmp_path / "fixed-candidate"
    portable.assemble(host, destination, portable.plan(host, build, portable.RESOURCES))
    assert portable.verify(destination)["webview_runtime"] == build["webview_runtime"]


@pytest.mark.parametrize("mutation", ["resealed_executable", "unapproved_manifest", "missing"])
def test_fixed_webview_cannot_hide_tampering_by_resealing_backend(tmp_path, monkeypatch, mutation):
    host, build = fixture_bundle(tmp_path)
    fixture_fixed_webview(host, build, monkeypatch)
    member = "runtime/webview2/msedgewebview2.exe"
    if mutation == "unapproved_manifest":
        member = "runtime/webview2/aaos-fixed-runtime-manifest.json"
    path = host.parent / member
    backend_path = host.parent / "backend-runtime-manifest.json"
    backend = json.loads(backend_path.read_text(encoding="utf-8"))
    if mutation == "missing":
        path.unlink()
        del backend["files"][member]
    else:
        path.write_bytes(b"changed and resealed")
        backend["files"][member] = {"bytes": path.stat().st_size, "sha256": portable.digest(path)}
    backend_path.write_text(json.dumps(backend), encoding="utf-8")
    with pytest.raises((ValueError, FileNotFoundError)):
        portable.plan(host, build, portable.RESOURCES)


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


@pytest.mark.parametrize("member", ["vcruntime140.dll", "vcruntime140_1.dll", "core/vcruntime140.dll", "core/vcruntime140_1.dll"])
def test_app_local_runtime_missing_or_changed_is_not_portable_pass(tmp_path, member):
    host, build = fixture_bundle(tmp_path)
    (host.parent / member).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="identity mismatch"):
        portable.plan(host, build, portable.RESOURCES)
    (host.parent / member).unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        portable.plan(host, build, portable.RESOURCES)


@pytest.mark.parametrize("prefix", ["", "core/", "runtime/"])
@pytest.mark.parametrize("name", ["vcruntime140.dll", "vcruntime140_1.dll"])
def test_omitted_crt_copy_cannot_hide_by_omitting_manifest_entry(tmp_path, prefix, name):
    host, build = fixture_bundle(tmp_path)
    member = prefix + name
    (host.parent / member).unlink()
    manifest_path = host.parent / "backend-runtime-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["files"][member]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="VC runtime copy absent"):
        portable.plan(host, build, portable.RESOURCES)


@pytest.mark.parametrize("prefix", ["", "core/", "runtime/"])
@pytest.mark.parametrize("name", ["vcruntime140.dll", "vcruntime140_1.dll"])
def test_self_consistent_manifest_still_rejects_different_crt_copy(tmp_path, prefix, name):
    host, build = fixture_bundle(tmp_path)
    member = prefix + name
    target = host.parent / member
    payload = b"different but individually inventoried runtime"
    target.write_bytes(payload)
    manifest_path = host.parent / "backend-runtime-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][member] = {"bytes": len(payload), "sha256": portable.digest(target)}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="copies differ"):
        portable.plan(host, build, portable.RESOURCES)


# All payloads stay tiny: lower only the synthetic threshold, never allocate GiB.
def growth_fixture(tmp_path, monkeypatch):
    import copy
    import hashlib
    host, build = fixture_bundle(tmp_path)
    manifest = portable.plan(host, build, portable.RESOURCES)
    monkeypatch.setattr(portable, "REPO", tmp_path)
    monkeypatch.setattr(portable, "LARGE_COPY_BYTES", 1)
    run = tmp_path / ".project-local/runs/0123456789/growth"
    artifacts = run / "artifacts"
    artifacts.mkdir(parents=True)
    paths = {"root": tmp_path, "run": run, "artifacts": artifacts}
    monkeypatch.setattr(portable.dev, "layout", lambda root, run_id: paths)
    context = {"paths": paths, "purpose": "finite synthetic packaging", "sharing": "existing backend reused",
               "retention_reason": "bounded qualification evidence"}
    report = {"schema": "aaos.storage-footprint/v2", "repository": str(tmp_path),
              "measured_at": "2026-10-31T00:00:00+00:00", "readable_bytes": 3 * 1024 ** 3,
              "measurement_status": "PARTIAL", "measurement_errors": [{"path": "unknown", "error": "denied"}],
              "excluded_private": ["private-preserved"], "excluded_checkouts": [], "out_of_layout": ["old/"],
              "dev_root": [{"name": "runs/", "bytes": 3 * 1024 ** 3, "budget_gb": 2.0,
                            "over_budget": True, "budgeted_bytes": 3 * 1024 ** 3}]}
    baseline_path = tmp_path / ".project-local/runs/0123456789/checkpoint/artifacts/footprint.json"
    baseline_path.parent.mkdir(parents=True)
    raw = json.dumps(report).encode()
    baseline_path.write_bytes(raw)
    descriptor = {"schema": portable.CHECKPOINT_SCHEMA, "path": baseline_path.relative_to(tmp_path).as_posix(),
                  "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                  "report_schema": report["schema"], "recorded_by": "Codex authorized governance batch",
                  "measurement_scope": "synthetic lower-bound snapshot; partial exclusions retained"}
    pointer = tmp_path / "docs/current/AAOS-ACTIVE-EXECUTION.json"
    pointer.parent.mkdir(parents=True)
    pointer.write_text(json.dumps({"execution_control": {"owner_priority_20261030": {
        "operator_storage_checkpoint": descriptor}}}), encoding="utf-8")
    calls = []
    def measure(root):
        calls.append(root)
        return copy.deepcopy(report)
    monkeypatch.setattr(portable.storage_report, "measure", measure)
    return host, manifest, artifacts / "candidate", context, report, calls, pointer, baseline_path


def test_large_direct_api_missing_declarations_never_copies(tmp_path, monkeypatch):
    # Uses only the old public API, so the original implementation fails with
    # DID NOT RAISE rather than a missing new helper/constant/import.
    host, build = fixture_bundle(tmp_path)
    manifest = portable.plan(host, build, portable.RESOURCES)
    dest = tmp_path / "requires-declarations"
    monkeypatch.setattr(portable, "LARGE_COPY_BYTES", 1, raising=False)
    with pytest.raises(ValueError, match="requires run paths"):
        portable.assemble(host, dest, manifest)
    assert not dest.exists()


@pytest.mark.parametrize("mutation", ["missing", "sha", "bytes_bool", "foreign", "path"])
def test_checkpoint_identity_fail_closed(tmp_path, monkeypatch, mutation):
    host, manifest, dest, context, report, calls, pointer, baseline = growth_fixture(tmp_path, monkeypatch)
    obj = json.loads(pointer.read_bytes())
    d = obj["execution_control"]["owner_priority_20261030"]["operator_storage_checkpoint"]
    if mutation == "missing":
        del obj["execution_control"]["owner_priority_20261030"]["operator_storage_checkpoint"]
    elif mutation == "sha":
        d["sha256"] = "0" * 64
    elif mutation == "bytes_bool":
        d["bytes"] = True
    elif mutation == "path":
        d["path"] = "../external.json"
    else:
        import hashlib
        foreign = json.loads(baseline.read_bytes())
        foreign["repository"] = "foreign"
        raw = json.dumps(foreign).encode()
        baseline.write_bytes(raw)
        d["bytes"] = len(raw)
        d["sha256"] = hashlib.sha256(raw).hexdigest()
    pointer.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(ValueError):
        portable.assemble(host, dest, manifest, storage_context=context)
    assert not dest.exists() and not calls


@pytest.mark.parametrize("mutation", ["sum", "bool", "understated_source"])
def test_manifest_cannot_lower_threshold_by_false_totals(tmp_path, monkeypatch, mutation):
    host, manifest, dest, context, report, calls, _, _ = growth_fixture(tmp_path, monkeypatch)
    first = next(iter(manifest["files"].values()))
    # Keep the falsified plan below threshold: size validation must still run.
    monkeypatch.setattr(portable, "LARGE_COPY_BYTES", manifest["logical_bytes"] + 1)
    monkeypatch.setattr(portable, "_copy_candidate", lambda *args: pytest.fail("copy invoked"))
    if mutation == "sum":
        manifest["logical_bytes"] = 0
    elif mutation == "bool":
        first["bytes"] = True
    else:
        first["bytes"] -= 1
        manifest["logical_bytes"] -= 1
    with pytest.raises(ValueError):
        portable.assemble(host, dest, manifest, storage_context=context)
    assert not dest.exists() and not calls


def test_unchanged_old_debt_partial_is_not_storage_pass(tmp_path, monkeypatch):
    host, manifest, dest, context, report, calls, _, _ = growth_fixture(tmp_path, monkeypatch)
    portable.assemble(host, dest, manifest, storage_context=context)
    receipt = json.loads((dest.parent / "portable-storage-receipt.json").read_bytes())
    assert len(calls) == 2 and dest.is_dir()
    assert receipt["measurement_status"] == "PARTIAL"
    assert receipt["pre_review"]["status"] == receipt["projected_review"]["status"] == "NO_NEW_GROWTH_TRIGGER"
    pre = json.loads((dest.parent / "portable-storage-pre.json").read_bytes())
    assert pre == report
    assert receipt["pre"]["measurement_started_at"] <= receipt["pre"]["measurement_ended_at"]
    assert receipt["pre"]["measurement_ended_at"] <= receipt["post"]["measurement_started_at"]


def test_existing_growth_stops_copy_but_still_seals_post(tmp_path, monkeypatch):
    host, manifest, dest, context, report, calls, _, _ = growth_fixture(tmp_path, monkeypatch)
    report["readable_bytes"] += 2 * 1024 ** 3 + 1
    report["dev_root"][0]["bytes"] += 2 * 1024 ** 3 + 1
    monkeypatch.setattr(portable, "_copy_candidate", lambda *a: pytest.fail("copy invoked"))
    with pytest.raises(portable.GrowthReviewRequiredError):
        portable.assemble(host, dest, manifest, storage_context=context)
    receipt = json.loads((dest.parent / "portable-storage-receipt.json").read_bytes())
    assert len(calls) == 2 and not dest.exists()
    assert receipt["copy_outcome"] == "NOT_STARTED"
    assert receipt["pre_review"]["status"] == "REVIEW_REQUIRED"


def test_projected_growth_uses_same_checkpoint_and_cannot_be_offset(tmp_path, monkeypatch):
    host, manifest, dest, context, report, calls, _, _ = growth_fixture(tmp_path, monkeypatch)
    total = manifest["logical_bytes"]
    # Current remains just below the fixed 2GiB class-growth line. Payload crosses it.
    report["dev_root"][0]["bytes"] += 2 * 1024 ** 3 - total + 1
    # Other class reductions hide total growth but cannot hide over-budget class growth.
    report["readable_bytes"] -= 1
    monkeypatch.setattr(portable, "_copy_candidate", lambda *a: pytest.fail("copy invoked"))
    with pytest.raises(portable.GrowthReviewRequiredError):
        portable.assemble(host, dest, manifest, storage_context=context)
    receipt = json.loads((dest.parent / "portable-storage-receipt.json").read_bytes())
    assert receipt["pre_review"]["status"] == "NO_NEW_GROWTH_TRIGGER"
    assert receipt["projected_review"]["status"] == "REVIEW_REQUIRED"
    assert not dest.exists()


def test_original_copy_error_survives_post_failure_and_partial_is_preserved(tmp_path, monkeypatch):
    host, manifest, dest, context, report, calls, _, _ = growth_fixture(tmp_path, monkeypatch)
    original = OSError("original-copy-failure")
    def fail_copy(*args):
        dest.mkdir()
        (dest / "partial").write_bytes(b"preserve")
        raise original
    monkeypatch.setattr(portable, "_copy_candidate", fail_copy)
    original_measure = portable.storage_report.measure
    def measure(root):
        if calls:
            raise OSError("post-measure-failure")
        return original_measure(root)
    monkeypatch.setattr(portable.storage_report, "measure", measure)
    with pytest.raises(OSError, match="original-copy-failure") as caught:
        portable.assemble(host, dest, manifest, storage_context=context)
    assert caught.value is original and (dest / "partial").read_bytes() == b"preserve"
    receipt = json.loads((dest.parent / "portable-storage-receipt.json").read_bytes())
    assert receipt["post_error"]["message"] == "post-measure-failure"
    assert receipt["original_error"]["message"] == "original-copy-failure"


def test_small_assembly_never_scans(tmp_path, monkeypatch):
    host, build = fixture_bundle(tmp_path)
    manifest = portable.plan(host, build, portable.RESOURCES)
    monkeypatch.setattr(portable.storage_report, "measure", lambda *args: pytest.fail("small copy scanned"))
    portable.assemble(host, tmp_path / "small", manifest)


def test_refuses_overwrite_before_large_measurement(tmp_path, monkeypatch):
    host, manifest, dest, context, report, calls, _, _ = growth_fixture(tmp_path, monkeypatch)
    dest.mkdir()
    with pytest.raises(FileExistsError):
        portable.assemble(host, dest, manifest, storage_context=context)
    assert not calls


@pytest.mark.parametrize("change", ["grow", "short"])
def test_source_changes_after_pre_stat_copy_is_bounded(tmp_path, monkeypatch, change):
    import builtins

    from scripts.runtime import storage_report
    host, build = fixture_bundle(tmp_path)
    manifest = portable.plan(host, build, portable.RESOURCES)
    # Small plan sits below threshold; the grown source would cross it.
    threshold = manifest["logical_bytes"] + 8
    monkeypatch.setattr(portable, "LARGE_COPY_BYTES", threshold, raising=False)
    monkeypatch.setattr(storage_report, "measure", lambda *args: pytest.fail("small plan scanned"))
    name = next(iter(manifest["files"]))
    source = host.parent / name
    declared = manifest["files"][name]["bytes"]
    original = source.read_bytes()
    opened = []
    def open_after_stat(path, mode="r", *args, **kwargs):
        if os.fspath(path) == portable.native(source) and mode == "rb":
            assert not opened
            opened.append(True)
            if change == "grow":
                # This occurs only at input open, after every pre-copy stat.
                source.write_bytes(original + b"g" * 64)
            else:
                source.write_bytes(original[:max(0, declared - 1)])
        return builtins.open(path, mode, *args, **kwargs)
    monkeypatch.setattr(portable, "open", open_after_stat, raising=False)
    destination = tmp_path / "changed-after-stat"
    with pytest.raises(ValueError):
        portable.assemble(host, destination, manifest)
    target = destination / name
    assert opened and target.is_file()
    assert target.stat().st_size <= declared
    assert target.read_bytes() == source.read_bytes()[:target.stat().st_size]
    assert source.is_file()  # Preserve source and partial candidate on failure.
    if change == "grow":
        assert manifest["logical_bytes"] + 64 > threshold
        assert target.stat().st_size == declared
        assert source.read_bytes() == original + b"g" * 64



def test_linked_common_owner_artifacts_are_explicitly_unsupported(tmp_path, monkeypatch):
    host, manifest, dest, context, report, calls, _, _ = growth_fixture(tmp_path, monkeypatch)
    linked = tmp_path / "linked-checkout"
    linked.mkdir()
    # Simulate dev.layout's common-owner routing without Git or product calls.
    context["paths"]["root"] = linked
    monkeypatch.setattr(portable, "REPO", linked)
    monkeypatch.setattr(portable, "_copy_candidate", lambda *a: pytest.fail("copy invoked"))
    monkeypatch.setattr(portable, "_checkpoint", lambda: pytest.fail("checkpoint cannot lift root restriction"))
    with pytest.raises(ValueError, match="linked checkout evidence cannot silently inherit"):
        portable.assemble(host, dest, manifest, storage_context=context)
    assert not calls and not dest.exists()
