"""Reject historical, partial or failed in-process journey receipts.

This gate qualifies the named test only, not the desktop or real worker pipeline.

CI passes the run identity through the runner-owned ``GITHUB_ENV`` file. A local
shell has no such file, so ``scripts/runtime/dev.py --env-file`` records the same
mapping and ``--env-file`` here reads it back. Only the three identity names are
accepted from that file, and an already-set operator value always wins, so this
option adds a local entry point without relaxing a single check below.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

IDENTITY_NAMES = ("ARCHEAXIS_RUN_ROOT", "VNEXT_RECEIPT_OUT", "ARCHEAXIS_SOURCE_COMMIT")


def validate(receipt: dict, commit: str, run_id: str) -> None:
    if (not re.fullmatch(r"[0-9a-f]{40}", commit) or not run_id
            or receipt.get("schema") != "archeaxis.vnext/v01-closed-loop-receipt"
            or receipt.get("schema_version") != 2
            or receipt.get("source_commit") != commit
            or receipt.get("run_id") != run_id):
        raise ValueError("receipt source/run identity mismatch")
    steps = receipt.get("steps", {})
    if (not isinstance(steps, dict) or len(steps) != 12
            or receipt.get("total_steps") != 12
            or {key.split("_")[0] for key in steps} != {f"{i:02}" for i in range(1, 13)}
            or any(not isinstance(v, str) or not v.startswith("PASS:") for v in steps.values())
            or not re.fullmatch(r"[0-9a-f]{64}", receipt.get("manifest_sha256", ""))):
        raise ValueError("receipt has incomplete or failed steps")


def load_identity(path: Path, environ: "os._Environ[str] | dict[str, str]") -> None:
    """Fill only the identity names this process does not already define."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or name not in IDENTITY_NAMES:
            continue
        if not environ.get(name):
            environ[name] = value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path,
                        help="same-run identity written by "
                             "scripts/runtime/dev.py --env-file")
    args = parser.parse_args()
    if args.env_file is not None:
        try:
            load_identity(args.env_file, os.environ)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"vNext receipt rejected: run environment unreadable: {exc}")
            return 1
    try:
        run = Path(os.environ["ARCHEAXIS_RUN_ROOT"])
        path = Path(os.environ["VNEXT_RECEIPT_OUT"])
        if not path.is_absolute() or path.parent != run / "artifacts":
            raise ValueError("receipt must be inside this run's artifacts")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        validate(receipt, os.environ["ARCHEAXIS_SOURCE_COMMIT"], run.name)
    except (KeyError, ValueError, OSError, TypeError, AttributeError) as exc:
        print(f"vNext receipt rejected: {exc}")
        return 1
    print("vNext current-run in-process journey receipt PASS (not installed qualification)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
