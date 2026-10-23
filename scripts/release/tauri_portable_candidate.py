"""Assemble and verify one isolated, unreleased formal Tauri portable candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
if __package__:
    from scripts.runtime import dev, runtime_resources
else:
    import importlib.util
    # Direct CLI: load only these repository-owned modules without sys.path edits.
    for module_name in ('dev', 'runtime_resources'):
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
    if build.get("webview_runtime") is not None:
        if runtime_resources.verify_fixed_webview2(root) != build["webview_runtime"]:
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


def assemble(host: Path, destination: Path, manifest: dict) -> dict:
    destination = checked(destination)
    os.mkdir(native(destination))
    for name, row in manifest["files"].items():
        source = regular(host.parent / name, cargo_host=name == "ArcheAxis.exe")
        target = checked(destination / relative_path(name))
        os.makedirs(native(target.parent), exist_ok=True)
        with open(native(source), "rb") as incoming, open(native(target), "xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
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
    if manifest.get("webview_runtime") is not None:
        if runtime_resources.verify_fixed_webview2(root) != manifest["webview_runtime"]:
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
        manifest = assemble(host, destination, manifest)
    _, after = dev.worktree_identity(REPO)
    result = {"status": "PASS" if after == environment["ARCHEAXIS_SOURCE_PATCH_SHA256"] else "FAIL",
              "action": "verify" if args.verify else "assemble" if args.assemble else "plan", "candidate": str(destination),
              "source_consistent": after == environment["ARCHEAXIS_SOURCE_PATCH_SHA256"],
              "manifest": manifest}
    (paths["artifacts"] / "portable-receipt.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "action", "candidate", "source_consistent")}, ensure_ascii=False))
    print(f"members={len(manifest['files'])}; logical_bytes={manifest['logical_bytes']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
