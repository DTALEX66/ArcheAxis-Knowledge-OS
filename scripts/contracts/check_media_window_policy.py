#!/usr/bin/env python3
"""Check that every copy of the bounded-window transcription policy agrees.

`config/defaults.yaml` declares the policy once. Four places act on it, and each holds its own copy
for a good reason — the worker plans from it, the interface shows the user an estimate from it, and
the Core refuses an over-ceiling deadline before either of those runs. Copies drift, and a drifted
copy is the worst kind of defect here: the number shown to a user would no longer be the number the
worker splits by, and nothing in a run would say so.

This is the drift gate. It is the same shape as `generate_vocabulary.py --check`: the declared
source is the truth, and every mirror is compared to it, with each disagreement named.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULTS = REPO / "config" / "defaults.yaml"
PLANNER = REPO / "services" / "python-workers" / "media" / "window_plan.py"
ESTIMATE = REPO / "frontend" / "src" / "presentation" / "mediaEstimate.ts"
CORE = [REPO / "crates" / "archeaxis-api" / "src" / "runtime" / "mod.rs",
        REPO / "crates" / "archeaxis-application" / "src" / "executor.rs"]
# Rust writes long literals with `_` separators (`300_000`), so the digits are joined before the
# comparison; matching only `\d+` read that cap as 300 and reported a drift that did not exist.
CORE_CAP = re.compile(r"deadline_ms > ([0-9][0-9_]*)")
TS_CONSTANTS = {
    "ceiling_ms": re.compile(r"MEDIA_CEILING_MS\s*=\s*([0-9_.]+)"),
    "overhead_ms": re.compile(r"MEDIA_OVERHEAD_MS\s*=\s*([0-9_.]+)"),
    "realtime_factor": re.compile(r"MEDIA_REALTIME_FACTOR\s*=\s*([0-9_.]+)"),
}


def declared() -> dict[str, float]:
    """The policy as declared, read with the same YAML parser the rest of the tooling uses."""
    import yaml

    document = yaml.safe_load(DEFAULTS.read_text(encoding="utf-8")) or {}
    policy = (document.get("media") or {}).get("window_policy")
    if not isinstance(policy, dict):
        raise ValueError("config/defaults.yaml has no media.window_policy")
    missing = [name for name in TS_CONSTANTS if name not in policy]
    if missing:
        raise ValueError(f"media.window_policy is missing {', '.join(missing)}")
    return {name: policy[name] for name in TS_CONSTANTS}


def planner_values() -> dict[str, float]:
    spec = importlib.util.spec_from_file_location("media_window_policy_planner", PLANNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        "ceiling_ms": module.CEILING_MS,
        "overhead_ms": module.OVERHEAD_MS,
        "realtime_factor": module.REALTIME_FACTOR,
    }


def estimate_values() -> dict[str, float]:
    text = ESTIMATE.read_text(encoding="utf-8")
    values: dict[str, float] = {}
    for name, pattern in TS_CONSTANTS.items():
        match = pattern.search(text)
        if not match:
            raise ValueError(f"mediaEstimate.ts does not define {name}")
        values[name] = float(match.group(1).replace("_", ""))
    return values


def label(path: Path) -> str:
    """A report-ready path, absolute when the file is outside the project root."""
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def core_caps() -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for path in CORE:
        text = path.read_text(encoding="utf-8")
        for match in CORE_CAP.finditer(text):
            found.append((label(path), int(match.group(1).replace("_", ""))))
    return found


def check() -> list[str]:
    policy = declared()
    problems: list[str] = []

    for label, values in (("services/python-workers/media/window_plan.py", planner_values()),
                          ("frontend/src/presentation/mediaEstimate.ts", estimate_values())):
        for name, expected in policy.items():
            if values[name] != expected:
                problems.append(f"{label}: {name} is {values[name]}, declared {expected}")

    caps = core_caps()
    if not caps:
        problems.append("no Core deadline cap found; the declared ceiling is not enforced anywhere")
    for where, cap in caps:
        if cap != int(policy["ceiling_ms"]):
            problems.append(f"{where}: refuses a deadline above {cap}, declared {int(policy['ceiling_ms'])}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="compare only; the default already writes nothing")
    args = parser.parse_args()
    policy = declared()
    problems = check()
    if problems:
        print(f"media window policy drift (declared {policy}):")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"media window policy consistent: {policy} "
          f"({len(core_caps())} Core cap site(s) agree)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
