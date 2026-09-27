"""Reject historical, partial or failed in-process journey receipts.

This gate qualifies the named test only, not the desktop or real worker pipeline.

Two independent questions are answered here, and they are deliberately not merged:

* **identity** - which source, run and working state produced this receipt. The commit
  alone cannot answer it, because ``git rev-parse HEAD`` is identical for a clean
  checkout and for one carrying uncommitted edits. A receipt that recorded only the
  commit therefore asserted an identity the run had never tested, and this gate
  accepted it. ``source_dirty`` and ``source_patch_sha256`` now travel with the commit
  and are bound here.
* **ordinary configuration precedence** - a caller-supplied value wins for plain
  configuration, but an *identity* name that differs between the environment and the
  run file is a conflict and is refused, never silently resolved.

CI passes the run identity through the runner-owned ``GITHUB_ENV`` file. A local shell
has no such file, so ``scripts/runtime/dev.py --env-file`` records the same mapping and
``--env-file`` here reads it back. Only identity names are accepted from that file, and
every check below stays in force.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 3
IDENTITY_NAMES = (
    "ARCHEAXIS_RUN_ROOT",
    "VNEXT_RECEIPT_OUT",
    "ARCHEAXIS_SOURCE_COMMIT",
    "ARCHEAXIS_SOURCE_DIRTY",
    "ARCHEAXIS_SOURCE_PATCH_SHA256",
)


def validate(receipt: dict, commit: str, run_id: str, dirty: bool,
             patch_sha256: str) -> None:
    # Each guard names its own failure: an exit code alone does not show which check
    # fired, and "rejected" for the wrong reason is not evidence.
    if receipt.get("schema") != "archeaxis.vnext/v01-closed-loop-receipt":
        raise ValueError("not a vNext closed-loop receipt")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"receipt schema_version {receipt.get('schema_version')!r} is not "
            f"{SCHEMA_VERSION}; it cannot bind the tested working state")
    if (not re.fullmatch(r"[0-9a-f]{40}", commit) or not run_id
            or receipt.get("source_commit") != commit
            or receipt.get("run_id") != run_id):
        raise ValueError("receipt source/run identity mismatch")
    # The working state is part of the identity. A receipt that predates these fields,
    # or that disagrees with the run it is offered for, is not evidence about the source
    # it names.
    if "source_dirty" not in receipt:
        raise ValueError("receipt does not record the tested working state")
    if bool(receipt["source_dirty"]) != dirty:
        raise ValueError(
            "receipt working state does not match this run "
            f"(receipt dirty={bool(receipt['source_dirty'])}, run dirty={dirty})")
    # The digest of an empty delta is a real value for a clean tree, so it is bound the
    # same way in both cases rather than being special-cased into absence.
    recorded_patch = receipt.get("source_patch_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", patch_sha256 or ""):
        raise ValueError("this run recorded no patch identity to bind against")
    if recorded_patch != patch_sha256:
        raise ValueError(
            "receipt patch identity does not match this run "
            f"(receipt {recorded_patch!r}, run {patch_sha256!r})")
    steps = receipt.get("steps", {})
    if (not isinstance(steps, dict) or len(steps) != 12
            or receipt.get("total_steps") != 12
            or {key.split("_")[0] for key in steps} != {f"{i:02}" for i in range(1, 13)}
            or any(not isinstance(v, str) or not v.startswith("PASS:") for v in steps.values())
            or not re.fullmatch(r"[0-9a-f]{64}", receipt.get("manifest_sha256", ""))):
        raise ValueError("receipt has incomplete or failed steps")


def load_identity(path: Path, environ: "os._Environ[str] | dict[str, str]") -> None:
    """Take identity names from the run file, refusing any disagreement.

    An operator value used to win silently. For identity that is wrong: silently
    preferring one of two different run roots - or commits, or patch digests - is how a
    receipt ends up bound to a run that did not produce it. Agreement is fine, absence
    is fine, disagreement is an error.
    """
    conflicts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or name not in IDENTITY_NAMES:
            continue
        current = environ.get(name)
        if current and current != value:
            conflicts.append(f"{name}: environment={current!r} run-file={value!r}")
            continue
        environ[name] = value
    if conflicts:
        raise ValueError("run identity conflict (refused, not resolved): " + "; ".join(conflicts))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path,
                        help="same-run identity written by "
                             "scripts/runtime/dev.py --env-file")
    args = parser.parse_args()
    if args.env_file is not None:
        try:
            load_identity(args.env_file, os.environ)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            print(f"vNext receipt rejected: run environment unusable: {exc}")
            return 1
    try:
        run = Path(os.environ["ARCHEAXIS_RUN_ROOT"])
        path = Path(os.environ["VNEXT_RECEIPT_OUT"])
        if not path.is_absolute() or path.parent != run / "artifacts":
            raise ValueError("receipt must be inside this run's artifacts")
        dirty = os.environ.get("ARCHEAXIS_SOURCE_DIRTY", "") == "1"
        patch_sha256 = os.environ.get("ARCHEAXIS_SOURCE_PATCH_SHA256", "")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("receipt is not a JSON object")
        validate(receipt, os.environ["ARCHEAXIS_SOURCE_COMMIT"], run.name,
                 dirty, patch_sha256)
    except (KeyError, ValueError, OSError, TypeError, AttributeError) as exc:
        print(f"vNext receipt rejected: {exc}")
        return 1
    commit = os.environ["ARCHEAXIS_SOURCE_COMMIT"]
    if dirty:
        print("vNext current-run in-process journey receipt PASS "
              f"(UNCOMMITTED working state on {commit[:12]}, patch {patch_sha256[:12]}) "
              "- not a committed-source qualification, not installed qualification")
    else:
        print("vNext current-run in-process journey receipt PASS "
              f"(committed {commit[:12]}) (not installed qualification)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
