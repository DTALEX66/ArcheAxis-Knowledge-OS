#!/usr/bin/env python3
"""Write the non-public identity embedded in a CI-qualified installer.

The candidate identity records only facts available during CI qualification.
The tag's public Release identity remains a separate artifact generated after
the exact candidate is promoted and read back from GitHub.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path, PurePosixPath

_HEX_40 = re.compile(r"[0-9a-f]{40}")
_REPOSITORY_URL = "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS"


def _positive_run(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def inject_staged_identity(manifest_path: Path, output: Path, identity: dict) -> None:
    """Update the one authoritative staged file table after bounded identity injection."""
    spec = importlib.util.spec_from_file_location(
        "identity_authority_stage", Path(__file__).parent / "release/stage_backend_runtime.py"
    )
    assert spec and spec.loader
    stage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage)
    manifest_path = manifest_path.absolute()
    output = output.absolute()
    root = manifest_path.parent
    if (
        manifest_path.name != "backend-runtime-manifest.json"
        or output != root / "runtime/release-identity.json"
    ):
        raise ValueError("identity must be the exact staged runtime member")
    for path in (manifest_path, output):
        stage.reject_links_along(path)
    stage.reject_reparse(manifest_path)
    if (
        identity.get("schema_version") != "candidate-1.0.0"
        or _HEX_40.fullmatch(str(identity.get("source", {}).get("commit"))) is None
    ):
        raise ValueError("invalid candidate identity schema or commit")
    data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if data.get("schema") != "archeaxis.backend-runtime/v1":
        raise ValueError("invalid staged manifest schema")
    if data.get("runtime_source", {}).get("commit") != identity["source"]["commit"]:
        raise ValueError("identity commit differs from staged runtime commit")
    tree = identity.get("source", {}).get("tree")
    if _HEX_40.fullmatch(str(tree)) is None or data.get("runtime_source", {}).get("tree") != tree:
        raise ValueError("identity tree differs from staged runtime tree")
    built_from = data.get("built_from")
    if built_from is not None:
        if not isinstance(built_from, dict) or any(
            built_from.get(field) != identity["source"][key]
            for field, key in (("source_commit", "commit"), ("source_tree", "tree"))
        ):
            raise ValueError("identity differs from staged build source")
    files = data.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("empty staged file table")
    for name, metadata in files.items():
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in name
            or ":" in name
            or not relative.parts
            or (
                relative.parts[0] != "runtime"
                and any(
                    part.lower() in stage.PRIVATE_NAMES or part.lower().startswith(".env")
                    for part in relative.parts
                )
            )
        ):
            raise ValueError("unsafe staged member")
        if (
            not isinstance(metadata, dict)
            or type(metadata.get("bytes")) is not int
            or metadata["bytes"] < 0
            or re.fullmatch(r"[0-9a-f]{64}", str(metadata.get("sha256"))) is None
        ):
            raise ValueError("invalid staged file identity")
    actual = {
        stage.ordinary_path(path).relative_to(root).as_posix()
        for path in stage.filesystem_path(root).rglob("*")
        if path.is_file()
    }
    if actual != set(files) | {manifest_path.name}:
        raise ValueError("unmanifested or missing staged member before injection")
    for name, metadata in files.items():
        path = root / name
        stage.reject_links_along(path)
        if (
            stage.filesystem_path(path).stat().st_size != metadata["bytes"]
            or stage.sha256(path) != metadata["sha256"]
        ):
            raise ValueError("staged member identity mismatch")
    if not (root / "runtime").is_dir():
        raise ValueError("missing staged runtime directory")
    encoded = (json.dumps(identity, indent=2) + "\n").encode("utf-8")
    if len(encoded) > 16384:
        raise ValueError("candidate identity exceeds budget")
    stage.filesystem_path(output).write_bytes(encoded)
    files["runtime/release-identity.json"] = {"bytes": len(encoded), "sha256": stage.sha256(output)}
    manifest_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--verification-ci-run-id", required=True, type=_positive_run)
    parser.add_argument("--verification-ci-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, help="Explicit authoritative staged manifest")
    args = parser.parse_args()

    commit = args.commit.strip()
    tree = args.tree.strip()
    if _HEX_40.fullmatch(commit) is None or _HEX_40.fullmatch(tree) is None:
        print("ERROR: commit and tree must be 40-character lowercase SHA-1 values", file=sys.stderr)
        return 1
    if args.tag != f"v{args.version}" or not args.version:
        print("ERROR: tag must be v<version>", file=sys.stderr)
        return 1
    expected_url = f"{_REPOSITORY_URL}/actions/runs/{args.verification_ci_run_id}"
    if args.verification_ci_url != expected_url:
        print(
            "ERROR: verification CI URL must be the canonical repository run URL", file=sys.stderr
        )
        return 1

    identity = {
        "schema_version": "candidate-1.0.0",
        "candidate": {
            "tag": args.tag,
            "version": args.version,
            "channel": "stable",
            "public": False,
        },
        "source": {
            "commit": commit,
            "tree": tree,
            "verification_ci_run_id": args.verification_ci_run_id,
            "verification_ci_url": args.verification_ci_url,
        },
    }
    if args.manifest is not None:
        try:
            inject_staged_identity(args.manifest, args.output, identity)
        except (ValueError, OSError, KeyError, TypeError):
            print("ERROR: staged candidate identity registration failed", file=sys.stderr)
            return 1
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
