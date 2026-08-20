"""Generate the machine-readable v0.6.0 current-state reports from Git.

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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKPACK_BASELINE = "051ee2d0d14398d9e812e657ad82ad1a44e7ed58"


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def generate(output_dir: Path, baseline: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    origin_main = _git("rev-parse", "origin/main")
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
    }

    _write_json(
        output_dir / "CLOUD_BASELINE.json",
        {
            **common,
            "remote": _git("remote", "get-url", "origin"),
            "branch": _git("branch", "--show-current"),
            "origin_main_sha": origin_main,
            "head_matches_origin_main": head == origin_main,
            "taskpack_baseline_sha": baseline,
            "taskpack_baseline_matches_head": head == baseline,
            "release": {"version": "0.6.0", "state": "development"},
        },
    )
    _write_json(
        output_dir / "EXACT_SHA_VERIFICATION.json",
        {
            **common,
            "origin_main_sha": origin_main,
            "match": head == origin_main,
            "scope": "local Git refs only; no CI, release, or installed-runtime claim",
        },
    )
    _write_json(
        output_dir / "CURRENT_CAPABILITY_MATRIX.json",
        {
            **common,
            "overall_status": "PARTIAL",
            "release_gate": "NOT_EXECUTED",
            "capabilities": {
                "four_library_rebind_and_recovery": "PARTIAL",
                "tier_a_ingestion_matrix": "PARTIAL",
                "identity_bound_evidence_review": "PARTIAL",
                "dual_learning_production_writeback": "PARTIAL",
                "six_space_ui_real_data": "PARTIAL",
                "tauri_supervisor_recovery_and_csp": "PARTIAL",
                "export_import_restart": "PARTIAL",
                "windows_setup_green_portable_lifecycle": "NOT_EXECUTED",
            },
            "limitations": [
                "This matrix is a current planning projection, not runtime or CI evidence.",
                "A v0.6.0 release requires exact-SHA CI and the Golden Journey receipts.",
            ],
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate current-state reports from Git")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "current")
    parser.add_argument("--baseline", default=DEFAULT_TASKPACK_BASELINE)
    args = parser.parse_args()
    generate(args.output_dir.resolve(), args.baseline)


if __name__ == "__main__":
    main()
