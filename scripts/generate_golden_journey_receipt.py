"""Run the local Golden Journey evidence slice and write a SHA-bound receipt.

The receipt is deliberately narrower than a release attestation.  Passing its
tests proves only the named local product journeys for the checked-out tree;
the remaining clean-Windows, UI, desktop-restart and publication gates stay
explicitly incomplete.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / ".hermes" / "task-artifacts" / "golden-journey"
DEFAULT_TEST_TARGETS = (
    "integration-tests/test_axw_main_chain_e2e.py::test_axw_main_chain_pdf_records_page_anchored_conversion",
    "integration-tests/test_r1_four_library_e2e.py::test_r1_four_library_initialize_and_restart_readback",
    "tests/test_axw094a_export.py::test_verified_exchange_imports_into_fresh_four_library_workspace",
)


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _failure_summary(output: str) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    return "\n".join(lines[-30:])


def _run_pytest(target: str) -> dict[str, object]:
    command = [sys.executable, "-m", "pytest", target, "-q"]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return {
            "target": target,
            "command": command,
            "status": "ERROR",
            "duration_seconds": round(time.monotonic() - started, 3),
            "failure_summary": str(error),
        }

    result: dict[str, object] = {
        "target": target,
        "command": command,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "exit_code": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
    }
    if completed.returncode:
        result["failure_summary"] = _failure_summary(
            "\n".join((completed.stdout, completed.stderr))
        )
    return result


def _validated_output(output_path: Path, artifact_root: Path) -> Path:
    resolved_root = artifact_root.resolve()
    resolved_output = output_path.resolve()
    try:
        resolved_output.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(
            f"Golden Journey receipts must be stored below {resolved_root}"
        ) from error
    return resolved_output


def generate(
    output_path: Path,
    test_targets: Sequence[str] = DEFAULT_TEST_TARGETS,
    *,
    runner: Callable[[str], dict[str, object]] = _run_pytest,
    artifact_root: Path = ARTIFACT_ROOT,
) -> dict[str, Any]:
    """Run selected local journeys and persist a truthful, SHA-bound receipt."""
    output = _validated_output(output_path, artifact_root)
    started_at = _now()
    results = [runner(target) for target in test_targets]
    tests_passed = bool(results) and all(result["status"] == "PASS" for result in results)
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "receipt_kind": "golden_journey_local_evidence",
        "generated_at": _now(),
        "started_at": started_at,
        "commit_sha": _git("rev-parse", "HEAD"),
        "tree_sha": _git("rev-parse", "HEAD^{tree}"),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "runner": "scripts/generate_golden_journey_receipt.py",
        },
        "local_journey_tests": results,
        "local_journey_status": "PASS" if tests_passed else "FAIL",
        "overall_status": "PARTIAL",
        "release_gate": "NOT_EXECUTED",
        "release_authorization": "NOT_GRANTED_BY_THIS_RECEIPT",
        "limitations": [
            "This is local test evidence only; it is not exact-SHA CI evidence.",
            "Windows Setup, Green and Portable clean-machine lifecycle evidence is not recorded.",
            "The six-space UI journey has no browser Golden receipt here.",
            "Installed desktop restart identity and release publication are not verified here.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run local Golden Journey tests and write a SHA-bound PARTIAL receipt"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    head = _git("rev-parse", "HEAD")
    output = args.output or ARTIFACT_ROOT / f"receipt-{head}.json"
    receipt = generate(output)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["local_journey_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
