"""Generate machine-readable current-state reports from Git and v0.6.8 evidence.

These reports deliberately describe evidence available for the current tree;
they do not promote structural inspection or historical receipts into release
claims.  Run from the repository root before a handoff or a release gate.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKPACK_BASELINE = "051ee2d0d14398d9e812e657ad82ad1a44e7ed58"
DEFAULT_OUTPUT_DIR = ROOT / ".hermes" / "task-artifacts" / "current-reports"
DEFAULT_RELEASE_EVIDENCE = (
    ROOT / "reports" / "release" / "v0.6.8" / "release-evidence.json"
)
REQUIRED_DEPENDENCY_LOCKS = {
    "uv.lock",
    "frontend/package-lock.json",
    "src-tauri/Cargo.lock",
}


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= set("0123456789abcdef")
    )


def _is_git_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and set(value) <= set("0123456789abcdef")
    )


def load_release_evidence(path: Path) -> dict[str, Any]:
    """Load a verified release receipt without promoting unrelated capabilities."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "archeaxis.release-evidence.v1":
        raise ValueError("unsupported release evidence schema")

    release = payload.get("release", {})
    if (
        release.get("public") is not True
        or release.get("draft") is not False
        or release.get("prerelease") is not False
        or release.get("channel") != "stable"
    ):
        raise ValueError("release evidence must describe a public stable release")

    source = payload.get("source", {})
    if not _is_git_sha(source.get("commit_sha")):
        raise ValueError("release commit SHA must be 40 lowercase hexadecimal characters")
    if not _is_git_sha(source.get("tree_sha")):
        raise ValueError("release tree SHA must be 40 lowercase hexadecimal characters")

    runs = payload.get("runs", {})
    verification_ci = runs.get("verification_ci", {})
    release_run = runs.get("release", {})
    if verification_ci.get("conclusion") != "success":
        raise ValueError("verification CI evidence must be successful")
    if release_run.get("conclusion") != "success":
        raise ValueError("release workflow evidence must be successful")
    if verification_ci.get("id") == release_run.get("id"):
        raise ValueError("verification CI and release workflow run IDs must differ")
    if not all(
        isinstance(run.get("id"), int) and run["id"] > 0
        for run in (verification_ci, release_run)
    ):
        raise ValueError("release evidence run IDs must be positive integers")

    assets = payload.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("release evidence must include public assets")
    names = [asset.get("name") for asset in assets if isinstance(asset, dict)]
    if len(names) != len(assets) or len(set(names)) != len(names):
        raise ValueError("release evidence asset names must be present and unique")
    if not all(
        isinstance(asset.get("size"), int)
        and asset["size"] > 0
        and _is_sha256(asset.get("sha256"))
        for asset in assets
    ):
        raise ValueError("release evidence assets require size and SHA-256")

    locks = payload.get("dependency_locks", {})
    if set(locks) != REQUIRED_DEPENDENCY_LOCKS or not all(
        _is_sha256(digest) for digest in locks.values()
    ):
        raise ValueError("release evidence dependency lock set is incomplete")

    verification = payload.get("verification", {})
    if (
        verification.get("provider_digest_match") is not True
        or verification.get("downloaded_sha256_match") is not True
        or verification.get("public_asset_count") != len(assets)
        or verification.get("checksum_payload_count") != len(assets) - 1
        or verification.get("identity_schema_version") != "3.0.0"
        or verification.get("three_distribution_lifecycle") != "PASS"
    ):
        raise ValueError("release evidence verification contract is incomplete")
    return payload


def _evidence_reference(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def generate(
    output_dir: Path,
    baseline: str,
    *,
    release_evidence: Path | None = DEFAULT_RELEASE_EVIDENCE,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    origin_main = _git("rev-parse", "origin/main")
    worktree_clean = not bool(_git("status", "--porcelain"))
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    environment = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "generator": "scripts/generate_current_reports.py",
    }
    common = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "commit_sha": head,
        "tree_sha": tree,
        "environment": environment,
        "evidence_level": "STRUCTURAL",
        "worktree_clean": worktree_clean,
    }
    release_receipt = (
        load_release_evidence(release_evidence) if release_evidence is not None else None
    )
    if release_receipt is None:
        release_summary: dict[str, object] = {
            "version": "0.6.9",
            "state": "development",
            "evidence_level": "NOT_EXECUTED",
        }
        release_gate = "NOT_EXECUTED"
        lifecycle_status = "NOT_EXECUTED"
        release_projection: dict[str, object] | None = None
    else:
        release = release_receipt["release"]
        source = release_receipt["source"]
        runs = release_receipt["runs"]
        release_summary = {
            "version": release["version"],
            "state": release["channel"],
            "tag": release["tag"],
            "commit_sha": source["commit_sha"],
            "tree_sha": source["tree_sha"],
            "evidence_level": "PUBLISHED_AND_READ_BACK",
            "evidence_ref": _evidence_reference(release_evidence),
        }
        release_gate = "PASS"
        lifecycle_status = "PASS"
        release_projection = {
            "evidence_ref": _evidence_reference(release_evidence),
            "tag": release["tag"],
            "commit_sha": source["commit_sha"],
            "tree_sha": source["tree_sha"],
            "verification_ci_run_id": runs["verification_ci"]["id"],
            "release_run_id": runs["release"]["id"],
            "asset_count": len(release_receipt["assets"]),
            "evidence_level": "PUBLISHED_AND_READ_BACK",
        }

    _write_json(
        output_dir / "CLOUD_BASELINE.json",
        {
            **common,
            "remote": _git("remote", "get-url", "origin"),
            "branch": _git("branch", "--show-current"),
            "origin_main_sha": origin_main,
            "head_matches_origin_main": head == origin_main and worktree_clean,
            "taskpack_baseline_sha": baseline,
            "taskpack_baseline_matches_head": head == baseline,
            "release": release_summary,
        },
    )
    _write_json(
        output_dir / "EXACT_SHA_VERIFICATION.json",
        {
            **common,
            "origin_main_sha": origin_main,
            "match": head == origin_main and worktree_clean,
            "scope": "local Git refs only; no CI, release, or installed-runtime claim",
            "verified_release": release_projection,
        },
    )
    _write_json(
        output_dir / "CURRENT_CAPABILITY_MATRIX.json",
        {
            **common,
            "overall_status": "PARTIAL",
            "release_gate": release_gate,
            "release_evidence": release_projection,
            "capabilities": {
                "four_library_rebind_and_recovery": "PARTIAL",
                "tier_a_ingestion_matrix": "PARTIAL",
                "identity_bound_evidence_review": "PARTIAL",
                "dual_learning_production_writeback": "PARTIAL",
                "six_space_ui_real_data": "PARTIAL",
                "tauri_supervisor_recovery_and_csp": "PARTIAL",
                "export_import_restart": "PARTIAL",
                "windows_setup_green_portable_lifecycle": lifecycle_status,
            },
            "limitations": [
                "This matrix is a current planning projection, not runtime or CI evidence.",
                "Release PASS does not promote product capabilities without their own executable receipts.",
                "The complete task-pack Golden Journey remains PARTIAL until every named gate executes.",
            ],
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate current-state reports from Git")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--baseline", default=DEFAULT_TASKPACK_BASELINE)
    parser.add_argument(
        "--release-evidence", type=Path, default=DEFAULT_RELEASE_EVIDENCE
    )
    args = parser.parse_args()
    generate(
        args.output_dir.resolve(),
        args.baseline,
        release_evidence=args.release_evidence.resolve(),
    )


if __name__ == "__main__":
    main()
