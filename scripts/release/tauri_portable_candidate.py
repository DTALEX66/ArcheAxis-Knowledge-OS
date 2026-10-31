"""Assemble and verify one isolated, unreleased formal Tauri portable candidate."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
if __package__:
    from scripts.runtime import dev, runtime_resources, storage_report
else:
    import importlib.util
    # Direct CLI: load only these repository-owned modules without sys.path edits.
    for module_name in ('dev', 'runtime_resources', 'storage_report'):
        spec = importlib.util.spec_from_file_location(module_name, REPO / "scripts/runtime" / (module_name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        globals()[module_name] = module

# Preserve the assembler's public validation helpers for existing consumers.
RESOURCES = runtime_resources.RESOURCES
SHA = runtime_resources.SHA
PUBLIC_UPSTREAM_FILES = runtime_resources.PUBLIC_UPSTREAM_FILES
native = runtime_resources.native
checked = runtime_resources.checked
digest = runtime_resources.digest
relative_path = runtime_resources.relative_path
regular = runtime_resources.regular
inventory = runtime_resources.inventory
verify_members = runtime_resources.verify_members
verify_worker_contract = runtime_resources.verify_worker_contract
verify_runtime_resources = runtime_resources.verify_runtime_resources
SCHEMA = "archeaxis.tauri-portable-candidate/v1"


def plan(host: Path, build: dict, configured_resources: set[str]) -> dict:
    if configured_resources != RESOURCES:
        raise ValueError("Formal resource contract changed; update the adapter explicitly")
    host = regular(host, cargo_host=True)
    if (build.get("status") != "PASS" or not build.get("source_consistent")
            or digest(host) != build.get("host_sha256")):
        raise ValueError("Host is not bound to a qualified build")
    root = host.parent
    backend = verify_runtime_resources(root, configured_resources)
    if (build.get("webview_runtime") is not None
            and runtime_resources.verify_fixed_webview2(root) != build["webview_runtime"]):
        raise ValueError("Fixed WebView2 differs from qualified build")
    members = backend["files"]
    runtime_manifest = regular(root / "backend-runtime-manifest.json")
    if digest(regular(root / "core/archeaxis-api.exe")) != build.get("core_sha256"):
        raise ValueError("Core differs from qualified build")
    all_members = {name: {"bytes": row["bytes"], "sha256": row["sha256"]}
                   for name, row in members.items()}
    for name, path in (("ArcheAxis.exe", host), ("backend-runtime-manifest.json", runtime_manifest)):
        all_members[name] = {"bytes": os.stat(native(path)).st_size, "sha256": digest(path)}
    return {"schema": SCHEMA, "status": "PLAN", "installed": False, "published": False,
            "source_patch_sha256": build["source_patch_sha256"],
            "host_sha256": build["host_sha256"], "core_sha256": build["core_sha256"],
            "webview_runtime": build.get("webview_runtime"),
            "runtime_provenance": backend.get("runtime_source"),
            "runtime_provenance_note": "Original staging provenance retained; member hashes are verified here",
            "files": all_members, "logical_bytes": sum(row["bytes"] for row in all_members.values()),
            "optional_models": "Referenced separately; not copied or claimed offline available",
            "qualification": "Static member qualification; runtime journey required separately"}


LARGE_COPY_BYTES = 1024 ** 3
CHECKPOINT_SCHEMA = "aaos.operator-storage-checkpoint/v1"


class GrowthReviewRequiredError(ValueError):
    """Exit 2 means review; no implicit permission or automatic cleanup."""


def _uint(value):
    if type(value) is not int or value < 0:
        raise ValueError("storage byte count must be a nonnegative integer")
    return value


def _plan_bytes(manifest):
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("portable plan requires member byte identities")
    total = 0
    for name, row in files.items():
        relative_path(name)
        if not isinstance(row, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256", ""))):
            raise ValueError("invalid member identity")
        total += _uint(row.get("bytes"))
    if _uint(manifest.get("logical_bytes")) != total:
        raise ValueError("portable plan byte total differs from members")
    return total


def _footprint(report):
    if (not isinstance(report, dict) or report.get("schema") != "aaos.storage-footprint/v2"
            or report.get("repository") != str(REPO)
            or report.get("measurement_status") not in {"PASS", "PARTIAL"}
            or not isinstance(report.get("measured_at"), str)):
        raise ValueError("storage report must be same-repository v2, including coverage")
    datetime.fromisoformat(report["measured_at"])
    _uint(report.get("readable_bytes"))
    for key in ("out_of_layout", "measurement_errors", "excluded_private", "excluded_checkouts", "dev_root"):
        if not isinstance(report.get(key), list):
            raise ValueError("storage report lacks coverage/class records")
    if report["measurement_status"] == "PASS" and any(report[k] for k in
            ("measurement_errors", "excluded_private", "excluded_checkouts")):
        raise ValueError("storage coverage contradicts PASS")
    seen = set()
    for row in report["dev_root"]:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or row["name"] in seen:
            raise ValueError("invalid or duplicate storage class")
        seen.add(row["name"])
        _uint(row.get("bytes"))
        if type(row.get("over_budget")) is not bool:
            raise ValueError("missing class budget state")
    runs = [row for row in report["dev_root"] if row["name"] == "runs/"]
    if len(runs) != 1 or runs[0].get("budget_gb") != storage_report.DEV_BUDGET_GB["runs"]:
        raise ValueError("storage report lacks canonical runs budget")
    return report


def _identity(path):
    raw = path.read_bytes()
    return raw, {"path": path.relative_to(REPO).as_posix(), "bytes": len(raw),
                 "sha256": hashlib.sha256(raw).hexdigest()}


def _checkpoint():
    pointer = dev.safe_path(REPO / "docs/current/AAOS-ACTIVE-EXECUTION.json")
    raw, pointer_identity = _identity(pointer)
    try:
        descriptor = json.loads(raw)["execution_control"]["owner_priority_20261030"]["operator_storage_checkpoint"]
    except (KeyError, TypeError) as error:
        raise ValueError("large copy requires this repository's registered operator_storage_checkpoint; initialize only in an authorized governance batch") from error
    required = {"schema", "path", "bytes", "sha256", "report_schema", "recorded_by", "measurement_scope"}
    if not isinstance(descriptor, dict) or set(descriptor) != required:
        raise ValueError("invalid operator checkpoint descriptor fields")
    if (descriptor["schema"] != CHECKPOINT_SCHEMA or descriptor["report_schema"] != "aaos.storage-footprint/v2"
            or not re.fullmatch(r"[0-9a-f]{64}", str(descriptor["sha256"]))
            or any(not isinstance(descriptor[k], str) or not descriptor[k].strip()
                   for k in ("recorded_by", "measurement_scope"))):
        raise ValueError("invalid operator checkpoint descriptor identity")
    _uint(descriptor["bytes"])
    rel = PurePosixPath(relative_path(descriptor["path"]))
    parts = rel.parts
    if any(storage_report.protected_name(part) for part in parts):
        raise ValueError("private checkpoint path rejected")
    if (len(parts) != 6 or parts[:2] != (".project-local", "runs")
            or not re.fullmatch(r"[0-9a-f]{10}", parts[2])
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", parts[3])
            or parts[4] != "artifacts" or not parts[5].endswith(".json")):
        raise ValueError("checkpoint must be a canonical repository run artifact")
    path = dev.safe_path(REPO / rel)
    if not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError("checkpoint must be a regular unlinked report")
    raw, identity = _identity(path)
    if any(identity[k] != descriptor[k] for k in ("path", "bytes", "sha256")):
        raise ValueError("checkpoint raw bytes differ from registered identity")
    return _footprint(json.loads(raw)), {"descriptor": descriptor, "pointer": pointer_identity}


def _evidence(artifacts, name, value):
    path = dev.safe_path(artifacts / name)
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(raw)
    return {"path": path.relative_to(REPO).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def _measure(artifacts, phase):
    started = datetime.now(timezone.utc).isoformat()
    report = _footprint(storage_report.measure(REPO))
    ended = datetime.now(timezone.utc).isoformat()
    identity = _evidence(artifacts, "portable-storage-" + phase + ".json", report)
    return report, {**identity, "measurement_started_at": started, "measurement_ended_at": ended}


def _storage_pre(destination, total, context):
    if not isinstance(context, dict) or set(context) != {"paths", "purpose", "sharing", "retention_reason"}:
        raise ValueError("large copy requires run paths, purpose, sharing and retention_reason")
    if any(not isinstance(context[k], str) or not context[k].strip()
           for k in ("purpose", "sharing", "retention_reason")):
        raise ValueError("large copy declarations must be nonempty")
    paths = context["paths"]
    canonical = dev.layout(REPO, paths["run"].name)
    if any(paths[k] != canonical[k] for k in ("root", "run", "artifacts")):
        raise ValueError("foreign portable storage run context")
    artifacts = dev.safe_path(paths["artifacts"])
    if not artifacts.is_relative_to(REPO):
        raise ValueError("large portable copy requires this checkout's in-root canonical artifacts; linked checkout evidence cannot silently inherit the main checkpoint")
    if not artifacts.is_dir() or destination.parent != artifacts:
        raise ValueError("large copy must use its canonical allocated run artifacts")
    # Check exclusive evidence names before measuring or copying; never overwrite.
    for name in ("pre", "post", "receipt"):
        if (artifacts / ("portable-storage-" + name + ".json")).exists():
            raise ValueError("portable storage evidence already exists; use a fresh run")
    baseline, checkpoint = _checkpoint()
    current, identity = _measure(artifacts, "pre")
    projected = copy.deepcopy(current)
    projected["readable_bytes"] += total
    runs = next(row for row in projected["dev_root"] if row["name"] == "runs/")
    runs["bytes"] += total
    runs["budgeted_bytes"] = runs["bytes"]
    runs["over_budget"] = runs["total_over_budget"] = runs["bytes"] > runs["budget_gb"] * 1024 ** 3
    runs["gb"] = round(runs["bytes"] / 1024 ** 3, 2)
    return {"schema": "aaos.portable-storage-review/v1", "artifacts": artifacts,
            "baseline_report": baseline, "checkpoint": checkpoint, "pre": identity,
            "pre_review": storage_report.growth_review(current, baseline),
            "projected_review": storage_report.growth_review(projected, baseline),
            "measurement_status": current["measurement_status"], "planned_payload_bytes": total,
            "projection_scope": "payload lower bound; excludes new evidence/manifest bytes; non-atomic measurement windows",
            "declarations": {k: context[k] for k in ("purpose", "sharing", "retention_reason")},
            "copy_outcome": "NOT_STARTED", "deletion_authorized": False}


def _storage_post(state, original_error):
    post_error = None
    try:
        post, identity = _measure(state["artifacts"], "post")
        state["post"] = identity
        state["post_review"] = storage_report.growth_review(post, state["baseline_report"])
        if post["measurement_status"] != "PASS":
            state["measurement_status"] = "PARTIAL"
        if state["post_review"]["status"] == "REVIEW_REQUIRED":
            post_error = GrowthReviewRequiredError("post-copy storage growth requires review; preserve candidate")
    except Exception as error:
        state["post_error"] = {"type": type(error).__name__, "message": str(error)}
        state["measurement_status"] = "PARTIAL"
        post_error = error
    if original_error is not None:
        state["original_error"] = {"type": type(original_error).__name__, "message": str(original_error)}
    try:
        _evidence(state["artifacts"], "portable-storage-receipt.json",
                  {k: v for k, v in state.items() if k not in {"artifacts", "baseline_report"}})
    except Exception as error:
        if original_error is not None:
            original_error.add_note("storage receipt could not be sealed: " + str(error))
        else:
            raise
    if original_error is not None:
        if post_error is not None:
            original_error.add_note("storage post measurement/review: " + str(post_error))
    elif post_error is not None:
        raise post_error


def assemble(host: Path, destination: Path, manifest: dict, *, storage_context=None) -> dict:
    destination = checked(destination)
    total = _plan_bytes(manifest)
    # Do not let a caller lower both totals while the real source is larger.
    for name, row in manifest["files"].items():
        source = regular(host.parent / name, cargo_host=name == "ArcheAxis.exe")
        if os.stat(native(source)).st_size != row["bytes"]:
            raise ValueError("member size differs from source before copying")
    # No target overwrite, even before the potentially expensive large-copy review.
    if destination.exists():
        raise FileExistsError(destination)
    state = None
    try:
        if total >= LARGE_COPY_BYTES:
            state = _storage_pre(destination, total, storage_context)
            if any(state[key]["status"] == "REVIEW_REQUIRED" for key in ("pre_review", "projected_review")):
                raise GrowthReviewRequiredError("portable growth requires review before copying")
            state["copy_outcome"] = "STARTED"
        result = _copy_candidate(host, destination, manifest)
        if state is not None:
            state["copy_outcome"] = "ASSEMBLED_STATIC_MEMBERS_VERIFIED"
        return result
    finally:
        if state is not None:
            _storage_post(state, sys.exc_info()[1])


def _copy_candidate(host: Path, destination: Path, manifest: dict) -> dict:
    os.mkdir(native(destination))
    for name, row in manifest["files"].items():
        source = regular(host.parent / name, cargo_host=name == "ArcheAxis.exe")
        target = checked(destination / relative_path(name))
        os.makedirs(native(target.parent), exist_ok=True)
        with open(native(source), "rb") as incoming, open(native(target), "xb") as outgoing:
            # The pre-copy stat is not a lock. Never write beyond the bound plan.
            remaining = row["bytes"]
            while remaining:
                chunk = incoming.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise ValueError(f"Source shorter than planned: {name}; partial candidate retained")
                outgoing.write(chunk)
                remaining -= len(chunk)
            # Detect extra input with one byte, without writing it to the target.
            if incoming.read(1):
                raise ValueError(f"Source grew beyond planned size: {name}; partial candidate retained")
        if os.stat(native(target)).st_size != row["bytes"] or digest(target) != row["sha256"]:
            raise ValueError(f"Copied member mismatch: {name}; partial candidate retained")
    marker = destination / "portable.flag"
    marker.write_bytes(b"")
    result = {**manifest, "status": "ASSEMBLED",
              "files": {**manifest["files"], "portable.flag": {"bytes": 0, "sha256": digest(marker)}}}
    (destination / "candidate-manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verify(destination)
    return result


def verify(root: Path) -> dict:
    root = dev.safe_path(root)
    manifest = json.loads(regular(root / "candidate-manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("schema") != SCHEMA or manifest.get("status") != "ASSEMBLED"
            or manifest.get("installed") is not False or manifest.get("published") is not False):
        raise ValueError("Not an unreleased formal candidate")
    verify_members(root, manifest["files"])
    verify_worker_contract(root, manifest["files"])
    if (manifest.get("webview_runtime") is not None
            and runtime_resources.verify_fixed_webview2(root) != manifest["webview_runtime"]):
        raise ValueError("Candidate fixed WebView2 binding mismatch")
    if inventory(root) != set(manifest["files"]) | {"candidate-manifest.json"}:
        raise ValueError("Unexpected or missing candidate files (runtime data is verified separately)")
    required = RESOURCES | {"ArcheAxis.exe", "portable.flag"}
    if not required.issubset({PurePosixPath(name).parts[0] for name in manifest["files"]}):
        raise ValueError("Required formal resources absent")
    if (manifest["files"]["ArcheAxis.exe"]["sha256"] != manifest["host_sha256"]
            or manifest["files"]["core/archeaxis-api.exe"]["sha256"] != manifest["core_sha256"]):
        raise ValueError("Candidate host/Core binding mismatch")
    return manifest


def qualified_host(receipt_path: Path, build: dict, paths: dict, environment: dict) -> Path:
    """Accept canonical completed builder evidence, not a hand-authored PASS row."""
    receipt_path = dev.safe_path(receipt_path)
    run = dev.safe_path(Path(build.get("run_root", "")))
    if (run != dev.layout(paths["root"], run.name)["run"]
            or receipt_path.parent.name != "artifacts"
            or receipt_path.parent.parent.parent != paths["run"].parent):
        raise ValueError("Host receipt has foreign run ownership")
    if (build.get("schema") != "archeaxis.frontend-build/v1" or build.get("mode") != "tauri"
            or build.get("status") != "PASS" or build.get("exit_code") != 0
            or build.get("portable_build_arguments") != ["build", "--no-bundle", "--", "--offline", "--locked"]
            or build.get("source_consistent") is not True
            or build.get("worktree_root") != str(paths["root"])
            or build.get("source_commit") != environment["ARCHEAXIS_SOURCE_COMMIT"]
            or build.get("source_tree") != environment["ARCHEAXIS_SOURCE_TREE"]
            or build.get("source_patch_sha256") != environment["ARCHEAXIS_SOURCE_PATCH_SHA256"]
            or build.get("source_patch_sha256_after") != environment["ARCHEAXIS_SOURCE_PATCH_SHA256"]):
        raise ValueError("Host is not bound to a completed canonical build of this source")
    host = paths["tauri_build"] / "release/ArcheAxis.exe"
    core = host.parent / "core/archeaxis-api.exe"
    if build.get("host") != str(host) or build.get("core") != str(core):
        raise ValueError("Host/Core path differs from canonical Tauri target")
    for key, path in (("host_sha256", regular(host, cargo_host=True)),
                      ("core_sha256", regular(core)),
                      ("backend_manifest_sha256", regular(host.parent / "backend-runtime-manifest.json"))):
        if build.get(key) != digest(path):
            raise ValueError("Host/runtime bytes changed after build")
    evidence = build.get("core_build_receipt", {})
    core_receipt = dev.safe_path(Path(evidence.get("path", "")))
    measured = dev.read_core_build(core_receipt, paths, environment)
    regular(core_receipt)
    if dev.build_file_identity(core_receipt) != evidence:
        raise ValueError("Core build receipt identity changed")
    if measured["sha256"] != build["core_sha256"]:
        raise ValueError("Bundled Core is not the qualified Core output")
    timing_identity = build.get("build_timings", {})
    timing_path = dev.safe_path(Path(timing_identity.get("path", "")))
    if timing_path.parent != run / "artifacts" or not re.fullmatch(r"bt-[a-f0-9]{8}\.json", timing_path.name):
        raise ValueError("Build timing has foreign run ownership")
    if dev.build_file_identity(regular(timing_path)) != timing_identity:
        raise ValueError("Build timing identity changed")
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    stages = timing.get("stages", [])
    if (timing.get("schema") != "archeaxis.build-timings/v1"
            or any(timing.get("source", {}).get(key) != environment[key] for key in (
                "ARCHEAXIS_SOURCE_COMMIT", "ARCHEAXIS_SOURCE_TREE", "ARCHEAXIS_SOURCE_PATCH_SHA256"))
            or [stage.get("name") for stage in stages] not in (
                ["tauri-with-bundle"], ["tauri-compile-with-frontend-hook", "nsis-bundle"])
            or any(stage.get("status") != "PASS" or stage.get("exit_code") != 0
                   or not stage.get("ended_at") for stage in stages)):
        raise ValueError("Tauri build stages are incomplete or unqualified")
    return host


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-receipt", type=Path, required=True,
                        help="canonical frontend tauri receipt qualified with --core-build-receipt")
    parser.add_argument("--run-id")
    parser.add_argument("--storage-purpose", help="required for >=1GiB assembly")
    parser.add_argument("--storage-sharing", help="payload reuse/sharing method for >=1GiB assembly")
    parser.add_argument("--storage-retention-reason", help="retention reason for >=1GiB assembly")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--assemble", action="store_true", help="Otherwise write only the verified member plan")
    action.add_argument("--verify", type=Path, help="Verify an existing pristine project-local candidate against its build")
    args = parser.parse_args()
    paths = dev.layout(REPO, args.run_id)
    environment = dev.prepare(paths)
    receipt_path = dev.safe_path(args.build_receipt)
    if (receipt_path.suffix != ".json" or receipt_path.name.startswith(".")
            or receipt_path.parent.name != "artifacts"
            or receipt_path.parent.parent.parent != paths["run"].parent):
        raise ValueError("Host receipt is outside this worktree's artifacts")
    build = json.loads(regular(receipt_path).read_text(encoding="utf-8"))
    host = qualified_host(receipt_path, build, paths, environment)
    config = json.loads((REPO / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    manifest = plan(host, build, set(config["bundle"]["resources"].values()))
    manifest["build_receipt"] = {"path": str(receipt_path), "sha256": digest(receipt_path)}
    destination = paths["artifacts"] / "星环便携候选"
    if args.verify:
        destination = dev.safe_path(args.verify)
        destination.relative_to(paths["dev"] / "runs")
        checked = verify(destination)
        expected_files = {**manifest["files"], "portable.flag": {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()}}
        if checked["files"] != expected_files or checked["source_patch_sha256"] != manifest["source_patch_sha256"]:
            raise ValueError("Candidate members/source differ from the qualified build")
        if checked.get("build_receipt") != manifest["build_receipt"]:
            raise ValueError("Candidate build receipt binding differs")
        manifest = checked
    elif args.assemble:
        try:
            manifest = assemble(host, destination, manifest, storage_context={
                "paths": paths, "purpose": args.storage_purpose, "sharing": args.storage_sharing,
                "retention_reason": args.storage_retention_reason})
        except GrowthReviewRequiredError as error:
            print(str(error), file=sys.stderr)
            return 2
    _, after = dev.worktree_identity(REPO)
    result = {"status": "PASS" if after == environment["ARCHEAXIS_SOURCE_PATCH_SHA256"] else "FAIL",
              "action": "verify" if args.verify else "assemble" if args.assemble else "plan", "candidate": str(destination),
              "source_consistent": after == environment["ARCHEAXIS_SOURCE_PATCH_SHA256"],
              "manifest": manifest}
    storage_receipt = paths["artifacts"] / "portable-storage-receipt.json"
    if args.assemble and storage_receipt.is_file():
        _, result["storage_review_receipt"] = _identity(storage_receipt)
        result["storage_measurement_status"] = json.loads(storage_receipt.read_bytes())["measurement_status"]
    (paths["artifacts"] / "portable-receipt.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "action", "candidate", "source_consistent")}, ensure_ascii=False))
    print(f"members={len(manifest['files'])}; logical_bytes={manifest['logical_bytes']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
