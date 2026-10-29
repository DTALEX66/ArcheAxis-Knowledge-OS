"""Non-public packaging of an existing build; never a CI/release qualification.

The input request is an explicit, reviewed trust anchor, not an identity inferred
from current HEAD. No runtime source provenance is rewritten by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from scripts.release import candidate, tauri_portable_candidate as portable

SCHEMA = "local-pinned-packaging/v1"
TOOLS = {"scripts/release/local_pinned_packaging.py", "tests/test_local_pinned_packaging.py",
         "workspace/intake/20261029-local-pinned-packaging-contract.md",
         "desktop/scripts/verify_nsis_install.ps1", "tests/test_local_pinned_installer_identity.py",
         "tests/fixtures/local_pinned_verifier_functions.ps1", "tests/test_release_manifest.py"}
RECONSTRUCTED_INPUTS = {"frontend/src/assets/brand/aaos-logo-light.svg",
                        "workspace/intake/20261025-codex-handoff.md"}
SHA = re.compile(r"[0-9a-f]{64}\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_row(path: Path) -> dict:
    path = candidate.safe_bundle_path(path)
    require(Path(candidate._native_path(path)).is_file(), "missing regular file")
    info = os.stat(candidate._native_path(path))
    require(info.st_nlink == 1, "hardlinked file")
    with open(candidate._native_path(path), "rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": info.st_size, "sha256": digest}


def payload_path(root: Path, name: str) -> Path:
    """Formal portable member rules, plus Windows filename canonicality."""
    relative = portable.relative_path(name)
    require(all(not part.endswith((" ", ".")) for part in relative.split("/"))
            and not any(unicodedata.category(character) == "Cc" for character in relative),
            "noncanonical Windows payload member")
    return portable.checked(root / relative)

def read_pinned(path: Path, expected: str) -> dict:
    require(isinstance(expected, str) and SHA.fullmatch(expected), "invalid pinned digest")
    require(file_row(path)["sha256"] == expected, "pinned evidence changed")
    value = json.loads(Path(portable.native(path)).read_text(encoding="utf-8-sig"))
    require(isinstance(value, dict), "evidence must be an object")
    return value


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def source_path(root: Path, name: str) -> Path:
    """Validate a Git source name, not a restricted distribution member name."""
    require(isinstance(name, str) and bool(name)
            and not any(character in name for character in "\\:")
            and not any(unicodedata.category(character) == "Cc" for character in name)
            and all(part not in {"", ".", ".."} for part in name.split("/"))
            and not Path(name).is_absolute(), "unsafe source relative path")
    # With no relative argument this checks every ancestor for links/reparse
    # points without rejecting legitimate .github/.gitattributes source names.
    return candidate.safe_bundle_path(root / name)


def source_inventory(root: Path, excluded: list[str]) -> dict:
    """Inventory ALL tracked and non-ignored untracked files, including frontend.

    Private exclusions are path-only and must match the frozen snapshot exactly.
    Ignored inputs are represented separately by the complete candidate payload.
    """
    require(Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel").strip())).resolve() == root,
            "foreign Git root")
    paths = set()
    for args in (("ls-files", "--cached", "-z"), ("ls-files", "--others", "--exclude-standard", "-z")):
        paths.update(os.fsdecode(p) for p in git(root, *args).split(b"\0") if p)
    require(set(excluded).issubset(paths), "private exclusion inventory changed")
    result = {}
    for name in sorted(paths - set(excluded)):
        path = source_path(root, name)
        parts = {part.casefold() for part in name.split("/")}
        require(not (parts & candidate._PRIVATE_COMPONENTS)
                and not candidate._PRIVATE_NAME.fullmatch(Path(name).name), "new private input needs explicit review")
        result[name] = file_row(path)
    return result


def compare_sources(snapshot: dict, current: dict, docs: dict, tools: dict) -> dict:
    require(snapshot.get("schema") == "aaos.per-file-source-snapshot/v1", "wrong source snapshot")
    before = snapshot["files"]
    require(isinstance(before, dict) and before, "empty source snapshot")
    require(not (set(docs) & set(tools)) and set(tools) <= TOOLS, "invalid tool delta")
    changes = {}
    for name in sorted(set(before) | set(current)):
        old = {k: before[name][k] for k in ("bytes", "sha256")} if name in before else None
        new = current.get(name)
        if old != new:
            changes[name] = {"before": old, "after": new}
    require(set(changes) == set(docs) | set(tools), "undeclared source delta or stale allowance")
    for name, row in docs.items():
        require(name.startswith("docs/") and name in before
                and before[name].get("class") == "documentation", "not an existing documentation input")
        require(row == changes[name] and row["after"] is not None, "documentation delta differs")
    for name, row in tools.items():
        require(row == changes[name] and row["after"] is not None, "tool delta differs")
    return changes


def reconstructed_coverage(root: Path, pin: dict, snapshot_pin: dict, snapshot: dict, current: dict) -> dict:
    """Supplement two historical omissions only with exact original full-patch evidence."""
    require(set(pin) == {"path", "sha256"}, "invalid reconstruction pin")
    path = owned_path(root, Path(pin["path"]))
    evidence = read_pinned(path, pin["sha256"])
    require(evidence.get("schema") == "aaos.frozen-worktree-reconstruction/v1"
            and evidence.get("status") == "PASS_EXACT_ORIGINAL_FULL_WORKTREE_IDENTITY"
            and evidence.get("source_commit") == snapshot["source_commit"]
            and evidence.get("expected_patch") == snapshot["source_patch_sha256"]
            and evidence.get("reconstructed_patch") == snapshot["source_patch_sha256"]
            and evidence.get("snapshot") == {k: snapshot_pin[k] for k in ("path", "sha256")}
            and evidence.get("real_index_unchanged") is True and evidence.get("source_consistent") is True
            and evidence.get("candidate_built_again") is False
            and evidence.get("install_qualification") == "NOT_GRANTED_BY_THIS_RECEIPT",
            "reconstruction does not prove original frozen identity")
    rows = evidence.get("historical_untracked_inputs")
    require(isinstance(rows, list) and len(rows) == len(RECONSTRUCTED_INPUTS)
            and {row.get("path") for row in rows} == RECONSTRUCTED_INPUTS,
            "unexpected reconstructed input coverage")
    supplemental = {}
    for row in rows:
        require(set(row) == {"path", "bytes", "sha256", "historical_individual_snapshot"}
                and row["historical_individual_snapshot"] is False
                and type(row["bytes"]) is int and row["bytes"] >= 0
                and isinstance(row["sha256"], str) and SHA.fullmatch(row["sha256"]),
                "invalid historical untracked row")
        name = row["path"]
        source_path(root, name)
        expected = {key: row[key] for key in ("bytes", "sha256")}
        require(name not in snapshot["files"] and current.get(name) == expected,
                "historical omitted bytes changed or coverage conflicts")
        supplemental[name] = expected
    tracked = evidence.get("reconstructed_tracked")
    require(isinstance(tracked, list), "missing reconstructed tracked evidence")
    seen = set()
    for row in tracked:
        name = row.get("path")
        require(name not in seen and name in snapshot["files"]
                and row.get("sha256") == snapshot["files"][name]["sha256"]
                and row.get("method") == "FROZEN_BYTES_IN_TEMP_INDEX", "invalid reconstructed tracked row")
        seen.add(name)
    require(isinstance(evidence.get("current_tool_delta"), list)
            and set(evidence["current_tool_delta"]) <= TOOLS, "unexpected reconstruction tool delta")
    return {"receipt": pin, "basis": "EXACT_ORIGINAL_FULL_WORKTREE_IDENTITY",
            "historical_individual_snapshot": False, "supplemental_inputs": supplemental}


def owned_path(root: Path, path: Path, *, fresh=False) -> Path:
    path = Path(os.path.abspath(path))
    require(path == Path(path.resolve()), "noncanonical output path")
    local = candidate.project_local_root(root)
    require(path != local and path.is_relative_to(local / "runs"), "output outside owned runs")
    candidate.safe_bundle_path(path)
    require(subprocess.run(["git", "-C", str(root), "check-ignore", "-q", str(path)],
                           check=False).returncode == 0, "output is not ignored")
    require(not fresh or not Path(portable.native(path)).exists(), "output already exists")
    return path


def verify_build(root: Path, build: dict, snapshot: dict, payload: dict) -> dict:
    source = {k: build.get(k) for k in ("source_commit", "source_tree", "source_patch_sha256")}
    require(all(isinstance(source[k], str) and re.fullmatch(pattern, source[k]) for k, pattern in
                (("source_commit", "[0-9a-f]{40}"), ("source_tree", "[0-9a-f]{40}"),
                 ("source_patch_sha256", "[0-9a-f]{64}"))), "invalid build source")
    require(build.get("schema") == "archeaxis.frontend-build/v1" and build.get("mode") == "tauri"
            and build.get("status") == "PASS" and build.get("exit_code") == 0
            and build.get("source_consistent") is True and build.get("worktree_root") == str(root)
            and build.get("portable_build_arguments") == ["build", "--no-bundle", "--", "--offline", "--locked"]
            and build.get("source_patch_sha256_after") == source["source_patch_sha256"]
            and all(snapshot.get(k) == source[k] for k in ("source_commit", "source_patch_sha256")),
            "not a pinned completed Host build")
    for key, name in (("host_sha256", "ArcheAxis.exe"), ("core_sha256", "core/archeaxis-api.exe"),
                      ("backend_manifest_sha256", "backend-runtime-manifest.json")):
        require(build.get(key) == payload["files"][name]["sha256"], "build/payload mismatch")
    evidence = {}
    for key in ("core_build_receipt", "build_timings"):
        row = build[key]
        path = owned_path(root, Path(row["path"]))
        require(file_row(path) == {k: row[k] for k in ("bytes", "sha256")}, "build dependency changed")
        evidence[key] = json.loads(Path(portable.native(path)).read_text(encoding="utf-8"))
    core = evidence["core_build_receipt"]
    require(core.get("status") == "LOCAL_PASS" and core.get("exit_code") == 0
            and core.get("source_consistent") is True
            and all(core.get(k) == v for k, v in source.items())
            and core.get("source_commit_after") == source["source_commit"]
            and core.get("source_patch_sha256_after") == source["source_patch_sha256"]
            and core.get("core_build", {}).get("schema") == "archeaxis.core-build/v1"
            and core["core_build"]["artifact"]["sha256"] == build["core_sha256"], "invalid Core build")
    timing = evidence["build_timings"]
    require(timing.get("schema") == "archeaxis.build-timings/v1"
            and all(timing.get("source", {}).get("ARCHEAXIS_" + k.upper()) == v for k, v in source.items())
            and [s.get("name") for s in timing.get("stages", [])] in
            (["tauri-with-bundle"], ["tauri-compile-with-frontend-hook", "nsis-bundle"])
            and all(s.get("status") == "PASS" and s.get("exit_code") == 0 and s.get("ended_at")
                    for s in timing["stages"]), "invalid build timing")
    return source


def qualify(root: Path, request: dict) -> dict:
    """Validate a reviewed request. No CI-shaped fields accepted at any level."""
    required = {"snapshot", "snapshot_count", "host_receipt", "candidate", "candidate_manifest", "docs_delta", "tools_delta"}
    require(required <= set(request) <= required | {"source_reconstruction"},
            "unknown request fields (CI identities forbidden)")
    root = Path(root).resolve()
    snapshot = read_pinned(owned_path(root, Path(request["snapshot"]["path"])), request["snapshot"]["sha256"])
    require(len(snapshot["files"]) == request["snapshot_count"], "snapshot member count differs")
    current = source_inventory(root, snapshot["excluded_private_paths"])
    coverage = None
    comparison = snapshot
    if "source_reconstruction" in request:
        coverage = reconstructed_coverage(root, request["source_reconstruction"], request["snapshot"], snapshot, current)
        comparison = {**snapshot, "files": {**snapshot["files"], **coverage["supplemental_inputs"]}}
    changes = compare_sources(comparison, current, request["docs_delta"], request["tools_delta"])
    candidate_root = owned_path(root, Path(request["candidate"]))
    manifest = read_pinned(candidate_root / "candidate-manifest.json", request["candidate_manifest"])
    require(portable.verify(candidate_root) == manifest, "portable verification mismatch")
    build_path = owned_path(root, Path(request["host_receipt"]["path"]))
    require(Path(request["snapshot"]["path"]).parent == build_path.parent,
            "snapshot must be the frozen Host receipt sibling")
    build = read_pinned(build_path, request["host_receipt"]["sha256"])
    original_source = verify_build(root, build, snapshot, manifest)
    return {"schema": SCHEMA, "status": "PINNED_INPUTS_VERIFIED", "public": False,
            "release_status": "unreleased", "installed_qualification": "NOT_RUN",
            "data_restore": "NOT_RUN", "rollback": "NOT_RUN", "ci_qualification": "NOT_CLAIMED",
            "source_coverage": {"original_snapshot_count": len(snapshot["files"]), "reconstruction": coverage},
            "build_source": original_source, "packaging_source": {
                "commit": os.fsdecode(git(root, "rev-parse", "HEAD").strip()),
                "tree": os.fsdecode(git(root, "rev-parse", "HEAD^{tree}").strip()),
                "inventory_sha256": hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest(),
                "delta": changes}, "inputs": request, "payload": manifest}


def bundle_command(node: Path, cli: Path, overlay: Path) -> list[str]:
    return [str(node), str(cli), "bundle", "--config", str(overlay), "--no-sign",
            "--no-binary-patching", "--bundles", "nsis"]


def tree_inventory(root: Path) -> dict:
    root = candidate.safe_bundle_path(root)
    require(Path(portable.native(root)).is_dir(), "missing consumer tool directory")
    result = {}
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(candidate._native_path(root), onerror=fail, followlinks=False):
        parent = candidate._plain_path(str(directory))
        for name in dirs:
            candidate.safe_bundle_path(parent / name)
        for name in files:
            path = parent / name
            result[path.relative_to(root).as_posix()] = file_row(path)
    require(result, "empty consumer tool inventory")
    return result


def bundle_consumer_inventory(root: Path, node: Path) -> dict:
    """Actual bundle-only inputs; frontendDist is not a bundler consumer.

    A reviewed pinned copy of this result is REQUIRED by bundle(). This does
    not assert historical dist preservation or requalify the compiled UI.
    """
    config_path = root / "src-tauri/tauri.conf.json"
    require(not any(Path(portable.native(root / "src-tauri" / name)).exists() for name in
                    ("tauri.windows.conf.json", "tauri.windows.conf.json5", "Tauri.windows.toml")),
            "unbound platform configuration")
    config = json.loads(Path(portable.native(config_path)).read_text(encoding="utf-8"))
    require(config.get("build", {}).get("beforeBundleCommand") in (None, ""), "nonempty bundle hook")
    require(not config.get("bundle", {}).get("externalBin"), "unbound external binaries")
    require(config.get("bundle", {}).get("useLocalToolsDir") is True, "project-local bundler tools required")
    windows = config.get("bundle", {}).get("windows", {})
    require(windows.get("webviewInstallMode", {}).get("type") == "skip", "unexpected WebView downloader")
    require(not windows.get("signCommand") and not windows.get("nsis", {}).get("template")
            and not windows.get("nsis", {}).get("installerHooks"), "unbound signing/template/hooks")
    icons = config.get("bundle", {}).get("icon", [])
    require(isinstance(icons, list) and icons, "missing icons")
    tools = {"cli": root / "frontend/node_modules/@tauri-apps/cli",
             "native_cli": root / "frontend/node_modules/@tauri-apps/cli-win32-x64-msvc",
             "nsis": root / ".project-local/build/tauri/.tauri/NSIS"}
    return {"schema": "local-pinned-bundle-consumers/v1", "config": file_row(config_path),
            "icons": {name: file_row(source_path(root / "src-tauri", name)) for name in icons},
            "node": {"path": str(node), **file_row(node)},
            "tool_trees": {name: {"path": str(path), "files": tree_inventory(path)} for name, path in tools.items()},
            "resources": "EXACT_PINNED_PAYLOAD_WITHOUT_HOST_AND_PORTABLE_FLAG",
            "frontendDist": "CONFIG_PATH_ONLY_NOT_REBUILT", "beforeBundleCommand": ""}


def bundle_overlay(root: Path, resources: dict, frontend_dist: str) -> dict:
    base = json.loads(Path(portable.native(root / "src-tauri/tauri.conf.json")).read_text(encoding="utf-8"))
    old = base.get("bundle", {}).get("resources", {})
    require(isinstance(old, (dict, list)), "unsupported resource configuration")
    # CLI 2.12.3 helpers/config.rs:149-160 applies json_patch::merge.
    # Null removes old map keys; without this, old mutable .project-local/rt
    # members would survive recursive merging alongside the pinned copies.
    cleared = {name: None for name in old} if isinstance(old, dict) else {}
    return {"build": {"beforeBuildCommand": "", "beforeBundleCommand": "", "frontendDist": frontend_dist},
            "bundle": {"resources": {**cleared, **resources}, "targets": ["nsis"], "useLocalToolsDir": True}}


def bundle(root: Path, request: dict, output: Path, node: Path, consumers: dict) -> dict:
    """Bundle an exact copy; every post-mkdir failure leaves a failed receipt."""
    root = Path(root).resolve()
    require(node.is_absolute() and node == Path(os.path.abspath(node))
            and node.name.casefold() == "node.exe", "explicit canonical Node executable required")
    identity = qualify(root, request)
    require(bundle_consumer_inventory(root, node) == consumers, "bundle consumer inputs differ")
    output = owned_path(root, output, fresh=True)
    cli = root / "frontend/node_modules/@tauri-apps/cli/tauri.js"
    os.makedirs(portable.native(output))
    receipt = {"schema": SCHEMA, "status": "FAIL", "stage": "PREPARING",
               "exit_code": None, "cli_started": False,
               "installed_qualification": "NOT_RUN", "consumers": consumers}
    try:
        target = output / "target"
        release = target / "release"
        os.makedirs(portable.native(release))
        nsis = consumers["tool_trees"]["nsis"]
        receipt["stage"] = "NSIS_COPY"
        for name, row in nsis["files"].items():
            source_tool = portable.regular(payload_path(Path(nsis["path"]), name))
            target_tool = payload_path(target / ".tauri/NSIS", name)
            os.makedirs(portable.native(target_tool.parent), exist_ok=True)
            with open(portable.native(source_tool), "rb") as incoming, open(portable.native(target_tool), "xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            require(file_row(target_tool) == row, "NSIS tool copy mismatch")
        source = Path(request["candidate"])
        members = identity["payload"]["files"]
        receipt["stage"] = "PAYLOAD_COPY"
        for name, row in members.items():
            incoming_path = portable.regular(payload_path(source, name))
            destination = payload_path(release, name)
            os.makedirs(portable.native(destination.parent), exist_ok=True)
            with open(portable.native(incoming_path), "rb") as incoming, open(portable.native(destination), "xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            require(file_row(destination) == row, "copy mismatch")
        receipt["stage"] = "CONFIG"
        identity_path = output / "local-pinned-identity.json"
        Path(portable.native(identity_path)).write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
        resources = {str(payload_path(release, name)): name for name in members
                     if name not in {"ArcheAxis.exe", "portable.flag"}}
        overlay = output / "bundle-config.json"
        config = bundle_overlay(root, resources, build_frontend_dist(root, request))
        Path(portable.native(overlay)).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        overlay_identity = file_row(overlay)
        command = bundle_command(node, cli, overlay)
        env = {k: v for k, v in os.environ.items() if not k.startswith("TAURI_")}
        env["CARGO_TARGET_DIR"] = str(target)
        receipt.update(identity=file_row(identity_path), overlay=overlay_identity, command=command,
                       cache={"mechanism": "useLocalToolsDir", "path": str(target / ".tauri")})
        require(qualify(root, request) == identity, "inputs changed before bundle")
        require(bundle_consumer_inventory(root, node) == consumers, "bundle consumer inputs changed before execution")
        require(file_row(overlay) == overlay_identity, "bundle config changed before execution")
        receipt["stage"] = "BUNDLE"
        with open(portable.native(output / "bundle.log"), "xb") as log:
            receipt["cli_started"] = True
            result = subprocess.run(command, cwd=root / "src-tauri", env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
        receipt["exit_code"] = result.returncode
        require(result.returncode == 0, "bundle failed; original failure retained")
        receipt["stage"] = "POSTCHECK"
        require(qualify(root, request) == identity, "inputs changed during bundle")
        require(bundle_consumer_inventory(root, node) == consumers, "bundle consumer inputs changed")
        require(file_row(overlay) == overlay_identity, "bundle config changed")
        require(file_row(identity_path) == receipt["identity"], "pinned identity changed")
        require(tree_inventory(target / ".tauri/NSIS") == nsis["files"], "copied NSIS tools changed")
        require(all(file_row(payload_path(release, name)) == row for name, row in members.items()), "bundle patched payload")
        installers = [candidate._plain_path(str(path)) for path in
                      Path(portable.native(release / "bundle/nsis")).glob("*.exe")]
        require(len(installers) == 1, "expected one new NSIS installer")
        receipt.update(status="LOCAL_PACKAGING_PASS", stage="COMPLETE",
                       installer={"path": str(installers[0]), **file_row(installers[0])})
        return receipt
    except Exception as error:
        receipt["error_type"] = type(error).__name__
        receipt["error"] = str(error)
        raise
    finally:
        with open(portable.native(output / "packaging-receipt.json"), "x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")

def build_frontend_dist(root: Path, request: dict) -> str:
    """CONFIG_PATH_ONLY_NOT_REBUILT: bundle-only does not read these assets."""
    build = read_pinned(Path(request["host_receipt"]["path"]), request["host_receipt"]["sha256"])
    path = owned_path(root, Path(build["frontend_dist"]))
    return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node", type=Path)
    parser.add_argument("--execute-bundle", action="store_true")
    parser.add_argument("--consumers", type=Path)
    parser.add_argument("--consumers-sha256")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    request = read_pinned(owned_path(root, args.request), args.request_sha256)
    if args.execute_bundle:
        require(args.node is not None, "explicit existing node executable required")
        require(args.consumers is not None and args.consumers_sha256 is not None, "pinned bundle consumers required")
        consumers = read_pinned(owned_path(root, args.consumers), args.consumers_sha256)
        bundle(root, request, args.output, args.node, consumers)
    else:
        identity = qualify(root, request)
        output = owned_path(root, args.output, fresh=True)
        os.makedirs(portable.native(output))
        Path(portable.native(output / "local-pinned-identity.json")).write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
