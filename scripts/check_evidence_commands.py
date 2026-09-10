"""Run the commands the evidence index records, and say what could not be run.

`check_evidence_index.py` verifies that each slice cites a tracked script and that every named
path exists. It does not verify that the recorded command still **runs** - which is the first
thing an independent auditor will try. Round 96 did that by hand and found two real defects.

This checker makes that repeatable. It reads the index, splits each recorded command on ``||``
(the index lists alternatives that way), classifies every alternative, and then:

* **without ``--run``** it prints the table and executes nothing at all;
* **with ``--run``** it executes everything it can, with a timeout, and reports the exit code and
  the last line of output for each.

It never executes anything it did not read out of the tracked index, it never runs a command in
the ``placeholder`` class (a command carrying ``<...>`` is not runnable and is reported as such),
and it never treats "not run" as a pass.

``python`` in a recorded command resolves to, in order: ``$ARCHEAXIS_PYTHON``, the repository's
own ``.venv`` interpreter when it exists, or the interpreter running this file - so the checker
works both in this working tree and in a fresh checkout.

Exit codes: 0 nothing failed, 2 the index cannot be read, 3 at least one executed command failed.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs/authority/taskpack-0910-r3" / "R14-EVIDENCE-INDEX.json"

# The runners a recorded command may start with. A command using anything else is a shape this
# checker does not know how to run, and a test refuses it rather than letting it pass unnoticed.
KNOWN_RUNNERS = ("python", "scripts/ci/cargo_test.bat")

PLACEHOLDER_CLASS = "placeholder"
HEAVY_CLASS = "workspace-suite"
PROBE_CLASS = "probe"
CHECKER_CLASS = "checker-or-test"

# Commands that need a Core binary built in this checkout: the probes spawn one and the candidate
# builder bundles one. Measured in a fresh clone (round 98): without knowing this, seven commands
# were reported as FAILURES when the truth was that nothing had been built there yet.
BUILD_REQUIRED_MARKERS = ("scripts/probes/", "scripts/release/")


def built_core() -> Path | None:
    """The built Core binary in this checkout, if there is one.

    The tracked Rust runner pins ``CARGO_TARGET_DIR`` under ``.project-local/build/cargo``; the
    environment variable is honoured first, so a run against a different target directory is not
    misreported as unbuilt.
    """
    bases: list[Path] = []
    configured = os.environ.get("ARCHEAXIS_CARGO_TARGET_DIR", "").strip()
    if configured:
        bases.append(Path(configured))
    bases.append(ROOT / ".project-local" / "build" / "cargo")
    for base in bases:
        for profile in ("release", "debug"):
            for name in ("archeaxis-api.exe", "archeaxis-api"):
                binary = base / profile / name
                if binary.is_file():
                    return binary
    return None


def needs_build(command: str) -> bool:
    """Whether this recorded command needs a Core binary that has been built in this checkout."""
    return any(marker in command for marker in BUILD_REQUIRED_MARKERS)


def needs_clean_tree(command: str) -> bool:
    """Whether this recorded command refuses to run on a dirty tracked worktree.

    The candidate builder does, by design (exit 5): a bundle may only be bound to a commit. A
    checker running mid-edit must say that, not report the refusal as a failure.
    """
    return "build_candidate.py" in command


def tracked_tree_is_dirty() -> bool:
    done = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=str(ROOT), capture_output=True, text=True)
    if done.returncode != 0:
        return False
    return bool(done.stdout.strip())


def python_for_commands() -> str:
    configured = os.environ.get("ARCHEAXIS_PYTHON", "").strip()
    if configured and Path(configured).is_file():
        return configured
    venv = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv.is_file():
        return str(venv)
    venv_posix = ROOT / ".venv" / "bin" / "python"
    if venv_posix.is_file():
        return str(venv_posix)
    return sys.executable


def classify(command: str) -> str:
    """What kind of command this is, by shape. Unknown shapes are refused by a test, not ignored."""
    if "<" in command or ">" in command:
        return PLACEHOLDER_CLASS
    if "cargo_test.bat" in command:
        return HEAVY_CLASS
    if "scripts/probes/" in command:
        return PROBE_CLASS
    return CHECKER_CLASS


def alternatives(command: str) -> list[str]:
    """The commands a recorded command lists, in order."""
    return [part.strip() for part in str(command).split("||") if part.strip()]


def plan(index_path: Path = INDEX, *, runner: str | None = None) -> list[dict]:
    """Every recorded command with its class and the argv this checker would run.

    Pure: building the plan executes nothing, which is what makes the default mode safe.
    """
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    resolved = runner or python_for_commands()
    rows: list[dict] = []
    for slice_row in payload["slices"]:
        for command in alternatives(slice_row["command"]):
            kind = classify(command)
            row = {
                "slice": slice_row["slice"],
                "command": command,
                "class": kind,
                "runnable": kind != PLACEHOLDER_CLASS,
            }
            if row["runnable"]:
                argv = shlex.split(command)
                if argv and argv[0] == "python":
                    argv[0] = resolved
                elif argv and argv[0].lower().endswith((".bat", ".cmd")):
                    # Windows cannot start a batch file directly, a shell runs it through cmd -
                    # and cmd does not accept the forward slashes the index uses (a shell does),
                    # so the path is normalised here. Measured: without this, cmd answers
                    # "... is not recognized as an internal or external command".
                    argv = ["cmd", "/c", *[part.replace("/", "\\") if part is argv[0] else part for part in argv]]
                row["argv"] = argv
                row["runner"] = command.split()[0]
            else:
                row["reason"] = "the recorded command carries a placeholder rather than a concrete path"
            rows.append(row)
    return rows


def toolchain_present() -> bool:
    """Whether the environment the cargo commands need is here at all.

    Both variables are required, and that was measured: with only ARCHEAXIS_RUST_TOOLCHAINS the
    runner starts and then fails at the C toolchain (exit 101, "linker `link.exe` not found"),
    because the bundled SQLite is compiled from source. Without the Rust variable it refuses by
    name first. A checker cannot invent a toolchain, so it says what is missing instead.
    """
    rust = bool(os.environ.get("ARCHEAXIS_RUST_TOOLCHAINS", "").strip()) or shutil.which("cargo") is not None
    msvc = bool(os.environ.get("ARCHEAXIS_MSVC_VCVARS", "").strip())
    return rust and msvc


def missing_toolchain() -> list[str]:
    missing = []
    if not os.environ.get("ARCHEAXIS_RUST_TOOLCHAINS", "").strip() and shutil.which("cargo") is None:
        missing.append("ARCHEAXIS_RUST_TOOLCHAINS (or cargo on PATH)")
    if not os.environ.get("ARCHEAXIS_MSVC_VCVARS", "").strip():
        missing.append("ARCHEAXIS_MSVC_VCVARS")
    return missing


def run_plan(rows: list[dict], *, timeout: int, execute_heavy: bool) -> list[dict]:
    """Execute a plan. Every row gets a result, including the ones deliberately not run."""
    heavy_ok = execute_heavy and toolchain_present()
    for row in rows:
        if not row["runnable"]:
            row["result"] = "NOT_RUN"
            # A row that is not run must always say why, even when a caller built it by hand.
            row.setdefault("reason", f"not runnable: {row['class']}")
            continue
        if row["class"] == HEAVY_CLASS and not heavy_ok:
            missing = missing_toolchain()
            row["reason"] = (
                "a per-package cargo run; not executed. Missing: "
                + ", ".join(missing)
                + ". The runner refuses by name without the Rust variable and fails at the C "
                "toolchain without the MSVC one, so this is an environment gap rather than a failure."
                if missing and execute_heavy
                else "a per-package cargo run; pass --execute-heavy to run it (needs ARCHEAXIS_RUST_TOOLCHAINS and ARCHEAXIS_MSVC_VCVARS)"
            )
            row["result"] = "NOT_RUN"
            continue
        if needs_build(row["command"]) and built_core() is None:
            # Nothing has been built in this checkout, so a probe or the bundle builder cannot run.
            # Reporting that as a failure would be wrong: it is a prerequisite, not a defect.
            row["result"] = "NOT_RUN"
            row["reason"] = (
                "needs a Core binary built in this checkout: run scripts/ci/cargo_test.bat once "
                "(or cargo build) before expecting this command to run here"
            )
            continue
        if needs_clean_tree(row["command"]) and tracked_tree_is_dirty():
            row["result"] = "NOT_RUN"
            row["reason"] = (
                "this command refuses a dirty tracked worktree by design (exit 5), because a bundle "
                "may only be bound to a commit: commit first, or expect the refusal"
            )
            continue
        started = time.time()
        try:
            done = subprocess.run(
                row["argv"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            row["exit"] = done.returncode
            row["tail"] = last_meaningful_line(done)
            row["result"] = "PASS" if done.returncode == 0 else "FAIL"
        except subprocess.TimeoutExpired:
            row["result"] = "TIMEOUT"
        finally:
            row["seconds"] = round(time.time() - started, 1)
    return rows


def last_meaningful_line(done: subprocess.CompletedProcess) -> str:
    """The last line of stdout and of stderr, so a named refusal is not hidden by shell noise.

    Measured defect: reporting only one stream showed cmd's wording ("... operable program or
    batch file") instead of the runner's own named refusal.
    """
    parts = []
    for stream in (done.stdout, done.stderr):
        lines = [line.strip() for line in (stream or "").strip().splitlines() if line.strip()]
        if lines:
            parts.append(lines[-1][:160])
    return " | ".join(parts[:2])


def summarise(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["result"]] = counts.get(row["result"], 0) + 1
    return {
        "commands": len(rows),
        "counts": counts,
        "failures": [f"{row['slice']}: {row['command']} -> {row['result']} {row.get('tail', '')}" for row in rows if row["result"] not in {"PASS", "NOT_RUN"}],
        "note": "a command that was not run is not a pass; a placeholder command cannot be run at all",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run the commands the evidence index records")
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--run", action="store_true", help="execute the commands; without it nothing is run")
    parser.add_argument("--execute-heavy", action="store_true", help="also run the per-package cargo commands")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        rows = plan(args.index)
    except (OSError, json.JSONDecodeError, KeyError) as error:
        print(f"cannot read the evidence index: {error}", file=sys.stderr)
        return 2

    if not args.run:
        for row in rows:
            print(f"{row['slice']:4s} {row['class']:16s} {'runnable' if row['runnable'] else 'NOT RUNNABLE'}  {row['command'][:80]}")
        print(f"{len(rows)} recorded command(s); nothing was executed (pass --run to execute)")
        return 0

    rows = run_plan(rows, timeout=args.timeout, execute_heavy=args.execute_heavy)
    summary = summarise(rows)
    if args.json:
        print(json.dumps({"rows": rows, **summary}, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(f"{row['slice']:4s} {row['result']:6s} {str(row.get('seconds', '')):>7s}  {row['command'][:70]}")
            if row["result"] in {"FAIL", "TIMEOUT"}:
                print("        ->", row.get("tail", ""))
        print(f"{summary['commands']} command(s): " + ", ".join(f"{name} {count}" for name, count in summary["counts"].items()))
    return 0 if not summary["failures"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
