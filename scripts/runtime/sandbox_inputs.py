"""Verify retained sandbox inputs and propose shared read-only mappings.

No payload copy, VM launch, installation, cleanup, ACL or host setting change.
The frozen per-run launcher does not support shared mappings. Proposals need a
separately qualified launcher and fresh verification before any future launch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import os
import re
import stat
from pathlib import Path, PureWindowsPath
from xml.etree import ElementTree as ET

if __package__:
    from . import dev
    from .runtime_resources import checked, digest, native, regular
else:
    import dev
    from runtime_resources import checked, digest, native, regular

ROOTS = {"AAOSInstall": "package", "AAOSInput": "input", "AAOSTools": "tools"}
PRIVATE = {".codex", ".hermes", ".zcode", ".mimosa", ".trae", ".dsh",
           ".ui-task-tree", ".hilo", ".ssh", ".agents", ".env", ".npmrc", ".pypirc"}
RUN_STATE = {".project-local", ".venv", "node_modules", "__pycache__"}
SHA = re.compile(r"[0-9a-f]{64}\Z")
is_reserved = getattr(ntpath, "isreserved", lambda value: PureWindowsPath(value).is_reserved())


def guest_folders() -> dict[str, PureWindowsPath]:
    # These are the frozen template's virtual guest namespace, never host roots.
    profile = regular(Path(__file__).resolve().parents[2] / "config/sandbox/shared-inputs.v1.json")
    with open(native(profile), encoding="utf-8") as stream:
        body = json.load(stream)
    if (not isinstance(body, dict) or body.get("schema") != "aaos.sandbox-guest-mappings/v1"
            or body.get("namespace") != "GUEST_VIRTUAL_PATHS_NOT_HOST_FILESYSTEM_ROOTS"
            or not isinstance(body.get("folders"), dict)
            or set(body["folders"]) != {*ROOTS, "AAOSOutput"}):
        raise ValueError("Unsupported guest mapping profile")
    result = {}
    for name, value in body["folders"].items():
        if not isinstance(value, str):
            raise ValueError("Guest mapping must be a string")
        path = PureWindowsPath(value)
        if (path.drive != "C:" or path.root != "\\" or len(path.parts) != 2
                or path.name != name or str(path) != value):
            raise ValueError("Guest profile differs from the reviewed mapping namespace")
        result[name] = path
    return result


GUEST_FOLDERS = guest_folders()
ENTRY = str(GUEST_FOLDERS["AAOSInput"] / "guest-local-pinned-lifecycle.ps1")
MANIFEST = str(GUEST_FOLDERS["AAOSInput"] / "inputs.json")


def contained(path: Path, parent: Path) -> Path:
    # Check the lexical boundary before accessing ancestors or file contents.
    path = Path(os.path.abspath(path))
    parent = Path(os.path.abspath(parent))
    if path == parent or not path.is_relative_to(parent):
        raise ValueError("Input/output outside the declared project run boundary")
    if any(part.casefold() in PRIVATE or part.casefold().startswith(".env.")
           for part in path.relative_to(parent).parts):
        raise ValueError("Private input/output path rejected before access")
    return checked(path)


def member(value: str) -> tuple[str, str]:
    """Canonical Windows guest path, checked before inspecting any source file."""
    if not isinstance(value, str):
        raise ValueError("Guest member path must be a string")
    parsed = PureWindowsPath(value)
    parts = parsed.parts
    if (len(parts) < 3 or parts[0] != GUEST_FOLDERS["AAOSInput"].anchor or parts[1] not in ROOTS
            or str(parsed) != value or "/" in value):
        raise ValueError("Noncanonical guest member or unknown mapping")
    for part in parts[2:]:
        if (part in {".", ".."} or part.rstrip(" .") != part
                or any(ord(c) < 32 or c in '<>:"|?*' for c in part)
                or is_reserved(part)):
            raise ValueError("Unsafe Windows guest member")
        if (part.casefold() in PRIVATE or part.casefold().startswith(".env.")
                or part.casefold() in RUN_STATE):
            raise ValueError("Private or development-state member rejected before access")
    return ROOTS[parts[1]], "/".join(parts[2:])


def identity(path: Path) -> dict:
    path = regular(path)
    return {"bytes": os.stat(native(path)).st_size, "sha256": digest(path)}


def read_manifest(path: Path) -> dict:
    regular(path)
    if os.stat(native(path)).st_size > 32 * 1024 * 1024:
        raise ValueError("Input manifest exceeds the bounded review size")
    # Duplicate keys are ambiguous even if the last value happens to match.
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    with open(native(path), encoding="utf-8-sig") as stream:
        return json.load(stream, object_pairs_hook=unique)


def inventory(root: Path, guest_root: str) -> set[str]:
    actual = set()

    def fail(error):
        raise error

    for directory, dirs, files in os.walk(native(checked(root)), followlinks=False, onerror=fail):
        relative = Path(directory).relative_to(Path(native(root)))
        for name in dirs + files:
            rel = (relative / name).as_posix()
            member(str(GUEST_FOLDERS[guest_root] / PureWindowsPath(rel)))
            # Do not enter a private directory or follow a reparse point.
            checked(root / relative / name)
        for name in files:
            regular(root / relative / name)
            actual.add((relative / name).as_posix())
    return actual


def inspect_stage(stage: Path, dev_root: Path, expected_sha256: str) -> dict:
    if not SHA.fullmatch(expected_sha256):
        raise ValueError("A full lowercase input-manifest SHA-256 is required")
    stage = contained(stage, dev_root / "runs")
    if not Path(native(stage)).is_dir():
        raise ValueError("Retained input stage missing")
    manifest = stage / "input/inputs.json"
    before = identity(manifest)
    if before["sha256"] != expected_sha256:
        raise ValueError("Pinned input manifest changed")
    document = read_manifest(manifest)
    if (not isinstance(document, dict)
            or document.get("approval") != "ROOT_REVIEWED_FOR_THIS_FRESH_RUN"
            or not isinstance(document.get("scope"), str) or not document["scope"]
            or not isinstance(document.get("files"), list) or not document["files"]):
        raise ValueError("Unsupported or incomplete input manifest")
    expected = {name: {} for name in ROOTS.values()}
    seen = set()
    # Validate the ENTIRE declaration before reading any declared payload.
    for row in document["files"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid input member declaration")
        folder, relative = member(row.get("path"))
        key = row["path"].casefold()
        if key in seen or key == MANIFEST.casefold():
            raise ValueError("Duplicate or self-declared input manifest member")
        seen.add(key)
        if (type(row.get("bytes")) is not int or row["bytes"] < 0
                or not isinstance(row.get("sha256"), str) or not SHA.fullmatch(row["sha256"])):
            raise ValueError("Invalid input member identity")
        expected[folder][relative] = {k: row[k] for k in ("bytes", "sha256")}
    if ENTRY.casefold() not in seen or str(GUEST_FOLDERS["AAOSTools"] / "pwsh.exe").casefold() not in seen:
        raise ValueError("Required guest entry point or PowerShell missing")
    for guest, folder in ROOTS.items():
        actual = inventory(stage / folder, guest)
        if folder == "input":
            actual.discard("inputs.json")
        if actual != set(expected[folder]):
            raise ValueError("Input inventory differs from the complete pinned declaration")
    for folder, values in expected.items():
        for relative, row in values.items():
            if identity(stage / folder / relative) != row:
                raise ValueError("Input member bytes/hash changed")
    if identity(manifest) != before:
        raise ValueError("Manifest changed during verification")
    return {"schema": "aaos.sandbox-shared-inputs/v1", "status": "INPUTS_VERIFIED_HOST_ONLY",
            "source_stage": str(stage), "source_manifest": before,
            "source_scope": document["scope"], "source_approval_is_provenance_only": True,
            "members": len(seen), "shared_logical_bytes": sum(
                row["bytes"] for values in expected.values() for row in values.values()),
            "payload_bytes_copied": 0, "guest_write_isolation": "NOT_EXECUTED",
            "launch": "NOT_EXECUTED", "host_inputs": "MUTABLE_REVERIFY_BEFORE_LAUNCH"}


def proposal(stage: Path, output: Path, manifest_sha256: str) -> bytes:
    config = ET.Element("Configuration")
    for name in ("VGpu", "Networking", "AudioInput", "VideoInput",
                 "PrinterRedirection", "ClipboardRedirection"):
        ET.SubElement(config, name).text = "Disable"
    ET.SubElement(config, "MemoryInMB").text = "8192"
    mappings = ET.SubElement(config, "MappedFolders")
    for guest, folder in (*ROOTS.items(), ("AAOSOutput", None)):
        mapping = ET.SubElement(mappings, "MappedFolder")
        ET.SubElement(mapping, "HostFolder").text = str(stage / folder if folder else output)
        ET.SubElement(mapping, "SandboxFolder").text = str(GUEST_FOLDERS[guest])
        ET.SubElement(mapping, "ReadOnly").text = "true" if folder else "false"
    logon = ET.SubElement(config, "LogonCommand")
    ET.SubElement(logon, "Command").text = (
        str(GUEST_FOLDERS["AAOSTools"] / "pwsh.exe")
        + " -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "
        + ENTRY + " -ApprovedInputManifestSha256 " + manifest_sha256)
    ET.indent(config, space=" ")
    return ET.tostring(config, encoding="utf-8", xml_declaration=True) + b"\n"


def prepare(paths: dict, stage: Path, manifest_sha256: str) -> dict:
    run = contained(paths["run"], paths["dev"] / "runs")
    # The caller is a dev.py-allocated run, never an arbitrary existing folder.
    run_meta = read_manifest(run / "run-metadata.json")
    identity_key = hashlib.sha256(str(paths["root"]).casefold().encode()).hexdigest()[:10]
    if (not isinstance(run_meta, dict)
            or run != paths["dev"] / "runs" / identity_key / run.name
            or run_meta.get("owner") != "ArcheAxis-Knowledge-OS"
            or run_meta.get("worktree_root") != str(paths["root"])
            or run_meta.get("run_id") != run.name):
        raise ValueError("Caller run ownership/identity mismatch")
    stage = contained(stage, paths["dev"] / "runs")
    if stage == run or stage.is_relative_to(run) or run.is_relative_to(stage):
        raise ValueError("Shared input stage overlaps the writable caller run")
    artifacts = contained(paths["artifacts"], run)
    if artifacts != run / "artifacts":
        raise ValueError("Canonical run artifacts required")
    receipt_path = artifacts / "sandbox-shared-inputs.json"
    config = artifacts / "lifecycle.wsb.proposed"
    output = artifacts / "sandbox-output"
    if any(os.path.lexists(native(p)) for p in (receipt_path, config, output)):
        raise ValueError("Fresh proposal required; prior evidence is preserved")
    result = {"schema": "aaos.sandbox-shared-inputs/v1", "status": "FAIL_CLOSED", "run_root": str(run),
              "launch": "NOT_EXECUTED", "payload_bytes_copied": 0}
    try:
        result.update(inspect_stage(stage, paths["dev"], manifest_sha256))
        output.mkdir()
        data = proposal(stage, output, manifest_sha256)
        with open(native(config), "xb") as stream:
            stream.write(data)
        result.update(status="SHARED_INPUT_PROPOSAL_ONLY", config=str(config),
                      config_identity=identity(config), output=str(output),
                      output_empty=True, launcher="SHARED_MAPPING_LAUNCHER_NOT_QUALIFIED")
    except (OSError, ValueError, TypeError) as error:
        # A failed verification never yields an executable .wsb; partial evidence stays.
        result.update(status="FAIL_CLOSED", error_type=type(error).__name__, error=str(error))
    with open(native(receipt_path), "x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--prepare-proposal", action="store_true")
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parents[2]
        run_value = os.environ.get("ARCHEAXIS_RUN_ROOT", "")
        paths = dev.layout(root, Path(run_value).name)
        if not run_value or Path(run_value) != paths["run"]:
            raise ValueError("Run through scripts/runtime/dev.py")
        if args.prepare_proposal:
            result = prepare(paths, args.stage, args.manifest_sha256)
        else:
            result = inspect_stage(args.stage, paths["dev"], args.manifest_sha256)
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"status": "FAIL_CLOSED", "error_type": type(error).__name__,
                          "error": str(error), "launch": "NOT_EXECUTED"}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
