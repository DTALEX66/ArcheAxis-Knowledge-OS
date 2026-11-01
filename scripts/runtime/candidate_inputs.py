"""Preserve the three reviewed cppcand1 Host inputs in a fresh canonical run.

Only the historical Host donor role is covered. No assembler/Host is executed,
no whole candidate is retired, and no source, hash or output override is accepted.
Run through scripts/runtime/dev.py with --role cppcand1-host. A consumer must
require a complete SOURCE-MAP, no INCOMPLETE/FAILURE.json, and reverify all three payloads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

if __package__:
    from . import dev
    from . import runtime_resources as resources
    from . import sandbox_inputs as inputs
else:
    import dev
    import runtime_resources as resources
    import sandbox_inputs as inputs

ROLE = "cppcand1-host"
# Exact registered public objects, independently rehashed by cpphost-final1.
# These are authority-selected identities, never caller-provided hashes.
FILES = (
    ("host", ".project-local/runs/be268a2d33/cppcand1/artifacts/p/ArcheAxis.exe", "ArcheAxis.exe",
     49999360, "ac4c399b34ce3bbeab2a8f82e9f1d039b03c04b82f537ebdb99e6cd4863de145"),
    ("candidate_manifest", ".project-local/runs/be268a2d33/cppcand1/artifacts/p/candidate-manifest.json",
     "candidate-manifest.original.json", 3669060,
     "3aa6bfd864c792bff7081998f349cad16f875a73ca7854ed798a11e363f41031"),
    ("donor_pin", ".project-local/runs/be268a2d33/zc1c8/package/proof/host-donor-pin.json",
     "host-donor-pin.original.json", 553,
     "d7bb3f61e473809a94ea9283c0ecef42143cdddc668374b20917a8ffe2bbaff3"),
)


def _observe(path: Path, expected: dict) -> dict:
    path = resources.regular(path)
    info = os.lstat(resources.native(path))
    metadata = resources.file_metadata(info)
    if info.st_size != expected["bytes"]:
        raise ValueError("Reviewed candidate input length changed")
    digest = hashlib.sha256()
    with open(resources.native(path), "rb") as stream:
        if not resources.opened_file_matches(stream, metadata):
            raise ValueError("Candidate input identity changed while opening")
        remaining = expected["bytes"]
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise ValueError("Candidate input shorter than reviewed length")
            digest.update(chunk)
            remaining -= len(chunk)
        if stream.read(1):
            raise ValueError("Candidate input grew beyond reviewed length")
    resources.regular(path)
    if (digest.hexdigest() != expected["sha256"]
            or resources.file_metadata(os.lstat(resources.native(path))) != metadata):
        raise ValueError("Reviewed candidate input bytes or identity changed")
    return metadata


def _copy(source: Path, destination: Path, expected: dict, metadata: dict, progress: dict) -> None:
    resources.regular(source)
    resources.checked(destination)
    if resources.file_metadata(os.lstat(resources.native(source))) != metadata:
        raise ValueError("Candidate source changed after preflight")
    with open(resources.native(source), "rb") as incoming, open(resources.native(destination), "xb") as outgoing:
        if not resources.opened_file_matches(incoming, metadata):
            raise ValueError("Candidate source changed while opening for copy")
        remaining = expected["bytes"]
        while remaining:
            chunk = incoming.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise ValueError("Candidate source shorter than planned")
            written = outgoing.write(chunk)
            progress["written_bytes"] += written
            if written != len(chunk):
                raise OSError("Candidate destination short write")
            remaining -= written
        if incoming.read(1):
            raise ValueError("Candidate source grew beyond planned length")
        outgoing.flush()
        os.fsync(outgoing.fileno())
    _observe(destination, expected)
    if _observe(source, expected) != metadata:
        raise ValueError("Candidate source identity changed during copy")


def _save(path: Path, body: dict) -> dict:
    raw = (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(raw) > 64 * 1024:
        raise ValueError("Candidate source map exceeds its bounded metadata size")
    resources.checked(path)
    with open(resources.native(path), "xb") as stream:
        if stream.write(raw) != len(raw):
            raise OSError("Candidate evidence short write")
        stream.flush()
        os.fsync(stream.fileno())
    expected = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    _observe(path, expected)
    return expected


def prepare(paths: dict) -> dict:
    if paths["root"] != paths["dev"].parent:
        raise ValueError("Candidate inputs currently require the main checkout's canonical run")
    run = inputs.caller_run(paths)
    output = inputs.contained(paths["artifacts"] / "cpphost-input", run)
    if os.path.lexists(resources.native(output)):
        raise ValueError("Fresh candidate input root required; existing evidence preserved")
    sources = []
    # Validate all selected lexical boundaries before reading any source payload.
    for role, relative, name, size, sha in FILES:
        source = inputs.contained(paths["root"] / relative, paths["dev"] / "runs")
        if source.is_relative_to(run) or run.is_relative_to(source):
            raise ValueError("Candidate source overlaps the writable caller run")
        sources.append((role, source, output / name, {"bytes": size, "sha256": sha}))
    before = {role: _observe(source, expected) for role, source, _, expected in sources}
    # All failures before this exclusive claim leave the caller's artifacts alone.
    Path(resources.native(output)).mkdir()
    copied = []
    try:
        incomplete = output / "INCOMPLETE"
        claim_identity = _save(incomplete, {"schema": "aaos.candidate-input-claim/v1", "role": ROLE,
                                            "status": "INCOMPLETE_NOT_CONSUMABLE"})
        for role, source, destination, expected in sources:
            member = {"role": role, "source": str(source), "destination": str(destination),
                      **expected, "source_metadata": before[role], "written_bytes": 0}
            copied.append(member)
            _copy(source, destination, expected, before[role], member)
        # Recheck early members too, after the last copy and before success evidence.
        for role, source, destination, expected in sources:
            if _observe(source, expected) != before[role]:
                raise ValueError("Candidate source changed before source-map completion")
            _observe(destination, expected)
        pin = inputs.read_manifest(sources[2][2])
        if (not isinstance(pin, dict) or pin.get("host_sha256") != sources[0][3]["sha256"]
                or not isinstance(pin.get("donor_path"), str)):
            raise ValueError("Original donor pin differs from its historical Host contract")
        expected_names = {destination.name for _, _, destination, _ in sources}
        if set(os.listdir(resources.native(output))) != expected_names | {incomplete.name}:
            raise ValueError("Unexpected member in the exclusive candidate input root")
        run_meta = inputs.read_manifest(run / "run-metadata.json")
        argv = ["--host-exe", str(sources[0][2]), "--donor-manifest", str(sources[2][2])]
        document = {"schema": "aaos.candidate-host-inputs/v1", "role": ROLE,
                    "status": "COMPLETE_HOST_INPUT_ONLY", "whole_package": "HOLD_NOT_RETIRED",
                    "execution": "NOT_EXECUTED", "run_root": str(run), "members": copied,
                    "source_identity": {key: run_meta.get(key) for key in ("source_commit", "source_patch_sha256")},
                    "copied_bytes": sum(member["written_bytes"] for member in copied),
                    "original_donor_path": pin["donor_path"], "consumer_argv": argv,
                    "consumer_contract": "Frozen mixed assembler --host-exe/--donor-manifest only; not run or edited",
                    "lineage": "HISTORICAL_MIXED_COMPONENT_HOST_NOT_CURRENT_SOURCE_BUILD",
                    "required_before_use": "Complete parseable source map, no INCOMPLETE/FAILURE.json, reverify all three independent payload sizes/SHA"}
        receipt = output / "SOURCE-MAP.json"
        identity = _save(receipt, document)
        if set(os.listdir(resources.native(output))) != expected_names | {receipt.name, incomplete.name}:
            raise ValueError("Candidate input changed during source-map completion")
        _observe(incomplete, claim_identity)
        Path(resources.native(incomplete)).unlink()  # Last fallible step; no cleanup on failure.
        return {"status": document["status"], "source_map": str(receipt), "source_map_identity": identity,
                "consumer_argv": argv, "whole_package": document["whole_package"], "execution": "NOT_EXECUTED"}
    except Exception as error:
        try:
            _save(output / "FAILURE.json", {"schema": "aaos.candidate-input-failure/v1",
                "status": "FAIL_CLOSED_PARTIAL_PRESERVED", "role": ROLE, "members": copied,
                "error_type": type(error).__name__, "error": str(error), "execution": "NOT_EXECUTED"})
        except Exception as failure:
            error.add_note("Candidate failure evidence also failed: " + str(failure))
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=[ROLE], required=True,
                        help="preserve exactly the three reviewed Host donor objects; no execution or deletion")
    parser.parse_args(argv)
    try:
        run_value = os.environ.get("ARCHEAXIS_RUN_ROOT", "")
        if not run_value:
            raise ValueError("Run through scripts/runtime/dev.py")
        paths = dev.layout(Path(__file__).resolve().parents[2], Path(run_value).name)
        if Path(run_value) != paths["run"]:
            raise ValueError("Caller differs from the canonical current run")
        result = prepare(paths)
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"status": "FAIL_CLOSED", "error_type": type(error).__name__, "error": str(error)}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
