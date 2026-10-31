"""Finite zero-copy preparation for the reviewed cnprep3 native tooling capsule.

Only public retained inputs are mapped; no installer, native parent or UI is run.
The proposed native replay preserves the historical command but remains unqualified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

if __package__:
    from . import dev, sandbox_inputs as inputs
else:
    import dev
    import sandbox_inputs as inputs

APPROVED_MANIFEST = "f5e1b73674dd9110d51d7b81912c50b7ad46b18af2e8df068bac3dbd25754d0f"
APPROVED_PREPARATION = "fda74f8ca243ea7c1ff9a29129a6fbcddf8366980c71a5d3080037e48f91a9a1"
APPROVED_CONFIG = "503f01854f36be0eb7fd4d85fedd949902581ba133e4172f98f3ebd27471b7c7"
COUNTS = {"package": 14, "input": 5806, "tools": 657}
SIZES = {"package": 452771641, "input": 1275305976, "tools": 256592821}
GUEST = {folder: str(inputs.GUEST_FOLDERS[name]) for name, folder in inputs.ROOTS.items()}
PARENT = "native-correction/guest-parent.ps1"
LAUNCHER = "native-correction/guest-launch.py"
INNER_MANIFEST = "native-correction/inputs.json"
INSTALLER = "ArcheAxis Knowledge_0.6.14_x64-setup.exe"
PREP_INSTALLER = "target/release/bundle/nsis/" + INSTALLER
DISABLED = ("VGpu", "Networking", "AudioInput", "VideoInput", "PrinterRedirection", "ClipboardRedirection")


def declaration(body: dict) -> dict:
    """Validate every name before any declared payload is inspected."""
    if not isinstance(body, dict) or set(body) != set(COUNTS):
        raise ValueError("Exactly the three native capsule groups required")
    for group in COUNTS:
        rows = body[group]
        if not isinstance(rows, dict) or not rows:
            raise ValueError("Native group must be a nonempty member map")
        seen = set()
        for relative, row in rows.items():
            if not isinstance(relative, str) or not relative or "\\" in relative:
                raise ValueError("Noncanonical native relative member")
            parsed = PurePosixPath(relative)
            if parsed.as_posix() != relative or parsed.is_absolute():
                raise ValueError("Noncanonical native relative member")
            if any(part.casefold() == ".git" for part in parsed.parts):
                raise ValueError("Git state is not a native public input")
            folder, checked = inputs.member(GUEST[group] + "\\" + relative.replace("/", "\\"))
            if folder != group or checked != relative or relative.casefold() in seen:
                raise ValueError("Native member alias or duplicate")
            seen.add(relative.casefold())
            if (not isinstance(row, dict) or set(row) != {"bytes", "sha256"}
                    or type(row["bytes"]) is not int or row["bytes"] < 0
                    or not isinstance(row["sha256"], str) or not inputs.SHA.fullmatch(row["sha256"])):
                raise ValueError("Malformed native member identity")
    return body


def tree_identity(rows: dict) -> dict:
    # UTF-16 ordinal sorting matches the guest's .NET StringComparer.Ordinal.
    ordered = sorted(rows, key=lambda name: name.encode("utf-16-be"))
    digest = hashlib.sha256()
    for relative in ordered:
        row = rows[relative]
        digest.update((relative + "\0" + str(row["bytes"]) + "\0" + row["sha256"] + "\n").encode("utf-8"))
    return {"members": len(rows), "bytes": sum(row["bytes"] for row in rows.values()),
            "sha256": digest.hexdigest()}


def source_roots(stage: Path) -> dict:
    return {"package": stage / "artifacts/package", "input": stage / "input", "tools": stage / "artifacts/pwsh"}


def reviewed(stage: Path, dev_root: Path, pin: str) -> tuple[dict, dict, dict, dict]:
    stage = inputs.contained(stage, dev_root / "runs")
    key = hashlib.sha256(str(dev_root.parent).casefold().encode()).hexdigest()[:10]
    if stage != dev_root / "runs" / key / "cnprep3" or pin != APPROVED_MANIFEST:
        raise ValueError("Only the exact reviewed cnprep3 capsule is supported")
    manifest = stage / "artifacts/full-inputs.json"
    before = inputs.identity(manifest)
    if before != {"bytes": 1361472, "sha256": pin}:
        raise ValueError("Native source manifest changed")
    body = declaration(inputs.read_manifest(manifest))
    if any(len(body[name]) != COUNTS[name] or sum(row["bytes"] for row in body[name].values()) != SIZES[name]
           for name in COUNTS):
        raise ValueError("Native capsule inventory differs from reviewed 6477 members")
    preparation_path = stage / "artifacts/native-preparation.json"
    if inputs.identity(preparation_path)["sha256"] != APPROVED_PREPARATION:
        raise ValueError("Historical preparation identity changed")
    prep = inputs.read_manifest(preparation_path)
    config = stage / "native-correction.wsb"
    if (prep.get("schema") != "aaos.corrected-installed-native-preparation/v1"
            or prep.get("source_label") != "HISTORICAL_PUBLIC_TOOLING_CAPSULE_NOT_PRODUCT_BUILD"
            or prep.get("inputs") != str(stage / "input" / INNER_MANIFEST)
            or prep.get("config") != str(config)
            or prep.get("full_inputs_identity") != before
            or prep.get("source_members") != 5793 or prep.get("tool_members") != 9
            or prep.get("inputs_identity") != body["input"].get(INNER_MANIFEST)
            or inputs.identity(config) != prep.get("config_identity")
            or prep["config_identity"]["sha256"] != APPROVED_CONFIG):
        raise ValueError("Historical native preparation/schema/config binding differs")
    for relative, sha in prep["package_pins"].items():
        packaged = INSTALLER if relative == PREP_INSTALLER else relative
        if body["package"].get(packaged, {}).get("sha256") != sha:
            raise ValueError("Native package pin mismatch")
    required = {"input": (PARENT, LAUNCHER, INNER_MANIFEST, "verify_nsis_install.ps1"),
                "tools": ("pwsh.exe",), "package": (INSTALLER,)}
    if any(relative not in body[group] for group, names in required.items() for relative in names):
        raise ValueError("Complete native guest entry and tools are required")
    roots = source_roots(stage)
    config_body = ET.fromstring(config.read_bytes())
    expected_tags = [*DISABLED, "MemoryInMB", "MappedFolders", "LogonCommand"]
    if ([child.tag for child in config_body] != expected_tags or config_body.tag != "Configuration"
            or any(config_body.findtext(name) != "Disable" for name in DISABLED)
            or config_body.findtext("MemoryInMB") != "8192"):
        raise ValueError("Native config security boundary differs")
    mappings = config_body.findall("./MappedFolders/MappedFolder")
    expected = [(str(roots[group]), GUEST[group], "true") for group in COUNTS]
    expected.append((str(stage / "output"), str(inputs.GUEST_FOLDERS["AAOSOutput"]), "false"))
    actual = [(m.findtext("HostFolder"), m.findtext("SandboxFolder"), m.findtext("ReadOnly")) for m in mappings]
    if (actual != expected or any([c.tag for c in m] != ["HostFolder", "SandboxFolder", "ReadOnly"] for m in mappings)):
        raise ValueError("Original four native virtual mappings differ")
    command = (GUEST["tools"] + "\\pwsh.exe -NoLogo -NoProfile -NonInteractive -File "
               + GUEST["input"] + "\\" + PARENT.replace("/", "\\")
               + " -ExpectedSelfSha256 " + body["input"][PARENT]["sha256"]
               + " -ExpectedPackagingSha256 " + prep["package_pins"]["packaging-receipt.json"]
               + " -ExpectedInstallerSha256 " + prep["package_pins"][PREP_INSTALLER]
               + " -ExpectedIdentitySha256 " + prep["package_pins"]["runtime-correction-identity.json"]
               + " -NativeInput " + GUEST["input"] + "\\native-correction"
               + " -ExpectedInputsSha256 " + body["input"][INNER_MANIFEST]["sha256"]
               + " -Work " + str(inputs.GUEST_FOLDERS["AAOSOutput"] / "native-correction-v1-result"))
    if (config_body.findtext("./LogonCommand/Command") != command
            or [c.tag for c in config_body.find("LogonCommand")] != ["Command"]):
        raise ValueError("Original pinned native guest command differs")
    return body, before, roots, {"command": command, "preparation_sha256": APPROVED_PREPARATION,
                                 "original_config": inputs.identity(config)}


def inventory(root: Path, group: str) -> set:
    actual = set()
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(inputs.native(inputs.checked(root)), followlinks=False, onerror=fail):
        relative = Path(directory).relative_to(Path(inputs.native(root)))
        for name in dirs + files:
            rel = (relative / name).as_posix()
            # Reject private directory metadata before traversal into it.
            if any(part.casefold() == ".git" for part in PurePosixPath(rel).parts):
                raise ValueError("Git state is not a native public input")
            inputs.member(GUEST[group] + "\\" + rel.replace("/", "\\"))
            inputs.checked(root / relative / name)
        for name in files:
            inputs.regular(root / relative / name)
            actual.add((relative / name).as_posix())
    return actual


def inspect_trees(roots: dict, body: dict) -> dict:
    # Complete declaration and all directory inventories precede all payload hashes.
    declaration(body)
    for group in COUNTS:
        expected = set(body[group])
        actual = inventory(roots[group], group)
        if expected != actual:
            raise ValueError("Native inventory differs; unexpected/missing input preserved")
    for group in COUNTS:
        for relative, row in body[group].items():
            if inputs.identity(roots[group] / relative) != row:
                raise ValueError("Native input member bytes/hash changed")
    return {group: {"root": GUEST[group], **tree_identity(body[group])} for group in COUNTS}


def inspect_stage(stage: Path, dev_root: Path, pin: str) -> dict:
    body, before, roots, provenance = reviewed(stage, dev_root, pin)
    groups = inspect_trees(roots, body)
    # Re-read metadata anchors after full member verification.
    _, after, after_roots, after_provenance = reviewed(stage, dev_root, pin)
    if before != after or roots != after_roots or provenance != after_provenance:
        raise ValueError("Native provenance changed during verification")
    return {"schema": "aaos.native-shared-inputs/v1", "status": "NATIVE_INPUTS_VERIFIED_HOST_ONLY",
            "source_stage": str(stage), "source_manifest": before,
            "source_roots": {name: str(path) for name, path in roots.items()},
            "source_scope": "HISTORICAL_PUBLIC_TOOLING_CAPSULE_NOT_PRODUCT_BUILD",
            "members": sum(group["members"] for group in groups.values()),
            "shared_logical_bytes": sum(group["bytes"] for group in groups.values()), "groups": groups,
            "payload_bytes_copied": 0, "guest_write_isolation": "NOT_EXECUTED",
            "native_business": "NOT_EXECUTED_REQUIRES_SEPARATE_QUALIFICATION",
            "host_inputs": "MUTABLE_REVERIFY_BEFORE_LAUNCH", "provenance": provenance}


def proposal(stage: Path, output: Path, pin: str, roots: dict | None = None) -> bytes:
    # Native command is recovered only from the exact pinned historical configuration.
    _, _, expected, provenance = reviewed(stage, stage.parents[2], pin)
    if roots != {key: str(value) for key, value in expected.items()}:
        raise ValueError("Native source root redirection rejected")
    config = ET.fromstring(inputs.proposal(stage, output, pin, roots))
    config.find("./LogonCommand/Command").text = provenance["command"]
    ET.indent(config, space=" ")
    return ET.tostring(config, encoding="utf-8", xml_declaration=True) + b"\n"


def save(path: Path, body: dict) -> None:
    with open(inputs.native(path), "x", encoding="utf-8", newline="\n") as stream:
        json.dump(body, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def prepare(paths: dict, stage: Path, pin: str, *, mapping_probe: bool = False) -> dict:
    run = inputs.caller_run(paths)
    stage = inputs.contained(stage, paths["dev"] / "runs")
    if stage == run or stage.is_relative_to(run) or run.is_relative_to(stage):
        raise ValueError("Native source overlaps the writable caller")
    result = inspect_stage(stage, paths["dev"], pin)
    for value in result["source_roots"].values():
        source = Path(value)
        if source == run or source.is_relative_to(run) or run.is_relative_to(source):
            raise ValueError("Native source overlaps the writable caller")
    artifacts = paths["artifacts"]
    config = artifacts / "native-retry.wsb.proposed"
    output = artifacts / "native-output"
    receipt = artifacts / "native-shared-inputs.json"
    probe_output = artifacts / "sandbox-output"
    selected = [config, output, receipt] + ([probe_output] if mapping_probe else [])
    if any(os.path.lexists(inputs.native(value)) for value in selected):
        raise ValueError("Fresh native proposal required")
    output.mkdir()
    with open(inputs.native(config), "xb") as stream:
        stream.write(proposal(stage, output, pin, result["source_roots"]))
        stream.flush()
        os.fsync(stream.fileno())
    result.update(status="SHARED_INPUT_PROPOSAL_ONLY", run_root=str(run), config=str(config),
                  config_identity=inputs.identity(config), output=str(output), output_empty=True,
                  native_replay={"config": str(config), "config_identity": inputs.identity(config),
                                 "output": str(output), "qualification": "PREPARED_ONLY_NOT_EXECUTED",
                                 "required_next_use": "FRESH_ALL_INPUT_SHA_AND_EMPTY_OUTPUT_THEN_NATIVE_BUSINESS_QUALIFICATION"},
                  source_copies_avoided=result["members"], source_copy_bytes_avoided=result["shared_logical_bytes"])
    if mapping_probe:
        probe_output.mkdir()
        result["output"] = str(probe_output)
    save(receipt, result)
    return result


def probe_binding(stage: Path, pin: str, nonce: str, roots: dict, sandbox_id: str) -> dict:
    body, _, expected, _ = reviewed(stage, stage.parents[2], pin)
    if roots != {key: str(value) for key, value in expected.items()}:
        raise ValueError("Native probe source roots changed")
    if str(uuid.UUID(sandbox_id)) != sandbox_id or uuid.UUID(nonce).hex != nonce:
        raise ValueError("Invalid native owned ID or nonce")
    probes = [GUEST["package"] + "\\" + INSTALLER.replace("/", "\\"),
              GUEST["input"] + "\\" + PARENT.replace("/", "\\"), GUEST["tools"] + "\\pwsh.exe"]
    for guest in probes:
        folder, relative = inputs.member(guest)
        if getattr(os.stat(inputs.native(Path(roots[folder]) / relative)), "st_file_attributes", 0) & 1:
            raise ValueError("Native write probe host file already has readonly attribute")
    return {"nonce": nonce, "sandbox_id": sandbox_id, "manifest_sha256": pin,
            "manifest_provenance": "HOST_PINNED_NOT_GUEST_READ",
            "groups": {group: {"root": GUEST[group], **tree_identity(body[group])} for group in COUNTS},
            "probes": probes, "output_marker": str(inputs.GUEST_FOLDERS["AAOSOutput"] / "shared-probe-marker.txt"),
            "receipt": str(inputs.GUEST_FOLDERS["AAOSOutput"] / "shared-probe.json")}


def verify_guest(plan: dict) -> dict:
    output = Path(plan["output"])
    body = inputs.read_manifest(output / "shared-probe.json")
    if (not isinstance(body, dict) or body.get("schema") != "aaos.shared-native-inputs-guest-probe/v1"
            or body.get("status") != "PASS_NATIVE_COMPLETE_TREES_READONLY_AND_FRESH_OUTPUT"
            or body.get("context") != "SYSTEM_MAPPING_PROBE_ONLY"
            or body.get("nonce") != plan["nonce"] or body.get("sandbox_id") != plan["sandbox_id"]
            or body.get("manifest_sha256") != plan["source_manifest_sha256"]
            or body.get("manifest_provenance") != "HOST_PINNED_NOT_GUEST_READ"
            or body.get("groups") != plan["binding"]["groups"]
            or type(body.get("members_verified")) is not int or body["members_verified"] != plan["members"]
            or body.get("error") is not None
            or not isinstance(body.get("readonly"), list) or len(body["readonly"]) != 3
            or any(not isinstance(row, dict) for row in body["readonly"])
            or [row.get("path") for row in body["readonly"]] != plan["binding"]["probes"]
            or any(row.get("write_open_access_denied") is not True for row in body["readonly"])):
        raise ValueError("Native guest full-tree/owned-ID/write proof missing, stale or failed")
    for group in COUNTS:
        proof = body["groups"][group]
        if (type(proof.get("members")) is not int or type(proof.get("bytes")) is not int
                or proof["members"] < 1 or proof["bytes"] < 0):
            raise ValueError("Native tree counts must be explicit integers")
    marker = inputs.regular(output / "shared-probe-marker.txt")
    if marker.read_bytes() != ("aaos-shared-probe:" + plan["nonce"]).encode():
        raise ValueError("Native fresh output marker differs")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--prepare-proposal", action="store_true")
    args = parser.parse_args()
    try:
        run = os.environ.get("ARCHEAXIS_RUN_ROOT", "")
        paths = dev.layout(Path(__file__).resolve().parents[2], Path(run).name)
        if not run or Path(run) != paths["run"]:
            raise ValueError("Run through scripts/runtime/dev.py")
        result = prepare(paths, args.stage, args.manifest_sha256) if args.prepare_proposal else inspect_stage(
            args.stage, paths["dev"], args.manifest_sha256)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(json.dumps({"status": "FAIL_CLOSED", "error_type": type(error).__name__,
                          "error": str(error), "native_business": "NOT_EXECUTED"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
