"""Assemble and verify one isolated, unreleased formal Tauri portable candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts/runtime"))
import dev

RESOURCES = {"runtime", "core", "workers", "shared", "worker-profile.json",
             "start-backend.py", "start-backend.cmd", "backend-runtime-manifest.json"}
SHA = re.compile(r"[0-9a-f]{64}\Z")
SCHEMA = "archeaxis.tauri-portable-candidate/v1"
# Public file shipped by the already qualified locked FastAPI distribution.
# This exception never authorizes a native agent directory or changed bytes.
PUBLIC_UPSTREAM_FILES = {
    "runtime/Lib/site-packages/fastapi/.agents/skills/fastapi/SKILL.md": {
        "bytes": 13665, "sha256": "833e99b101b657690f44e9d6cab5d77b6b31dbf477e1fb64b5b7b8da27095917"},
}


def native(path: Path) -> str:
    text = os.fspath(path)
    return "\\\\?\\" + text if os.name == "nt" and not text.startswith("\\\\?\\") else text


def checked(path: Path) -> Path:
    path = dev.safe_path(path)
    for part in (*reversed(path.parents), path):
        try:
            info = os.lstat(native(part))
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked candidate path rejected")
    return path


def digest(path: Path) -> str:
    with open(native(path), "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Invalid relative member path")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or parsed.as_posix() != value or any(p in {".", ".."} for p in parsed.parts):
        raise ValueError("Unsafe or noncanonical member path")
    if value not in PUBLIC_UPSTREAM_FILES and any(
            p.casefold() in {".git", ".codex", ".hermes", ".ssh", ".agents", ".env"}
            or p.casefold().startswith(".env.") for p in parsed.parts):
        raise ValueError("Private material is not a candidate input")
    return value


def regular(path: Path, *, cargo_host: bool = False) -> Path:
    path = checked(path)
    info = os.lstat(native(path))
    cargo_pair = False
    if cargo_host and info.st_nlink == 2 and path.parent.name == "release":
        alias = checked(path.parent / "deps" / path.name)
        try:
            cargo_pair = os.path.samestat(info, os.lstat(native(alias)))
        except FileNotFoundError:
            pass
    if not stat.S_ISREG(info.st_mode) or (info.st_nlink != 1 and not cargo_pair):
        raise ValueError(f"Expected an independent regular file: {path}")
    return path


def inventory(root: Path) -> set[str]:
    checked(root)
    result = set()
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(native(root), onerror=fail, followlinks=False):
        relative = Path(directory).relative_to(Path(native(root)))
        for name in dirs:
            checked(root / relative / name)
        for name in files:
            path = regular(root / relative / name)
            result.add(path.relative_to(root).as_posix())
    return result


def verify_members(root: Path, members: dict) -> None:
    if not isinstance(members, dict) or not members:
        raise ValueError("Missing member manifest")
    folded = set()
    for name, row in members.items():
        relative_path(name)
        if name.casefold() in folded:
            raise ValueError("Case-insensitive duplicate member")
        folded.add(name.casefold())
        if (not isinstance(row, dict) or type(row.get("bytes")) is not int
                or row["bytes"] < 0 or not isinstance(row.get("sha256"), str)
                or not SHA.fullmatch(row["sha256"])):
            raise ValueError("Invalid member identity")
        if name in PUBLIC_UPSTREAM_FILES and row != PUBLIC_UPSTREAM_FILES[name]:
            raise ValueError("Public upstream exception bytes changed")
        path = regular(root / name)
        if os.stat(native(path)).st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise ValueError(f"Member identity mismatch: {name}")


def plan(host: Path, build: dict, configured_resources: set[str]) -> dict:
    if configured_resources != RESOURCES:
        raise ValueError("Formal resource contract changed; update the adapter explicitly")
    host = regular(host, cargo_host=True)
    if (build.get("status") != "PASS" or not build.get("source_consistent")
            or digest(host) != build.get("host_sha256")):
        raise ValueError("Host is not bound to a qualified build")
    root = host.parent
    runtime_manifest = regular(root / "backend-runtime-manifest.json")
    backend = json.loads(runtime_manifest.read_text(encoding="utf-8"))
    if backend.get("schema") != "archeaxis.backend-runtime/v1":
        raise ValueError("Unrecognized backend manifest")
    members = backend["files"]
    for name in members:
        relative_path(name)
        if PurePosixPath(name).parts[0] not in RESOURCES:
            raise ValueError("Backend member outside declared runtime resources")
    verify_members(root, members)
    verify_worker_contract(root, members)
    expected = set(members) | {"backend-runtime-manifest.json"}
    observed = set()
    for resource in RESOURCES:
        path = checked(root / resource)
        if path.is_dir():
            observed.update(resource + "/" + name for name in inventory(path))
        else:
            regular(path)
            observed.add(resource)
    if observed != expected:
        raise ValueError("Unmanifested or missing runtime resources")
    if digest(regular(root / "core/archeaxis-api.exe")) != build.get("core_sha256"):
        raise ValueError("Core differs from qualified build")
    all_members = {name: {"bytes": row["bytes"], "sha256": row["sha256"]}
                   for name, row in members.items()}
    for name, path in (("ArcheAxis.exe", host), ("backend-runtime-manifest.json", runtime_manifest)):
        all_members[name] = {"bytes": os.stat(native(path)).st_size, "sha256": digest(path)}
    return {"schema": SCHEMA, "status": "PLAN", "installed": False, "published": False,
            "source_patch_sha256": build["source_patch_sha256"],
            "host_sha256": build["host_sha256"], "core_sha256": build["core_sha256"],
            "runtime_provenance": backend.get("runtime_source"),
            "runtime_provenance_note": "Original staging provenance retained; member hashes are verified here",
            "files": all_members, "logical_bytes": sum(row["bytes"] for row in all_members.values()),
            "optional_models": "Referenced separately; not copied or claimed offline available",
            "qualification": "Static member qualification; runtime journey required separately"}


def verify_worker_contract(root: Path, members: dict) -> None:
    profile = json.loads(regular(root / "worker-profile.json").read_text(encoding="utf-8"))
    routes = json.loads(regular(root / "workers/routes.json").read_text(encoding="utf-8"))
    if (profile.get("schema") != "archeaxis.worker-profile/v1"
            or routes.get("schema") != "archeaxis.worker-routes/v1"
            or profile.get("python") not in {"runtime/python.exe", "runtime/python/python.exe"}
            or profile.get("script") != "workers/transport/text_ndjson.py"
            or profile.get("staging") != "data/worker-staging"):
        raise ValueError("Invalid formal worker launch contract")
    required = {profile["python"], profile["script"], "core/archeaxis-api.exe", "workers/routes.json"}
    mapping = routes.get("routes")
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Missing native worker routes")
    expected = {}
    for capability, scripts in mapping.items():
        if not isinstance(capability, str) or not isinstance(scripts, list) or not scripts:
            raise ValueError("Invalid native worker route")
        for script in scripts:
            required.add("workers/" + relative_path(script))
        expected[capability] = "workers/" + scripts[0]
    observed = {}
    for row in profile["routes"]:
        if row["capability"] in observed:
            raise ValueError("Duplicate worker profile route")
        observed[row["capability"]] = relative_path(row["script"])
    if observed != expected or not required.issubset(members):
        raise ValueError("Native/profile routes differ or worker input absent")


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
    if inventory(root) != set(manifest["files"]) | {"candidate-manifest.json"}:
        raise ValueError("Unexpected or missing candidate files (runtime data is verified separately)")
    required = RESOURCES | {"ArcheAxis.exe", "portable.flag"}
    if not required.issubset({PurePosixPath(name).parts[0] for name in manifest["files"]}):
        raise ValueError("Required formal resources absent")
    if (manifest["files"]["ArcheAxis.exe"]["sha256"] != manifest["host_sha256"]
            or manifest["files"]["core/archeaxis-api.exe"]["sha256"] != manifest["core_sha256"]):
        raise ValueError("Candidate host/Core binding mismatch")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--run-id")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--assemble", action="store_true", help="Otherwise write only the verified member plan")
    action.add_argument("--verify", type=Path, help="Verify an existing pristine project-local candidate against its build")
    args = parser.parse_args()
    paths = dev.layout(REPO, args.run_id)
    environment = dev.prepare(paths)
    receipt_path = dev.safe_path(args.build_receipt)
    receipt_path.relative_to(paths["dev"] / "runs")
    build = json.loads(regular(receipt_path).read_text(encoding="utf-8"))
    if build["source_patch_sha256"] != environment["ARCHEAXIS_SOURCE_PATCH_SHA256"]:
        raise ValueError("Build does not qualify the current frozen source")
    host = dev.safe_path(Path(build["host"]))
    host.relative_to(paths["cargo_build"] / "release")
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
