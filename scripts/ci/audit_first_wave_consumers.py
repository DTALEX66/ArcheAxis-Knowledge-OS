"""Report source-only consumers of G0 first-wave candidate writers.

The audit never imports product modules or opens a database.  It distinguishes
the module that defines a candidate writer from production files that name it;
it is structural migration evidence, not proof of runtime reachability.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


AUDIT_ROOTS = ("app", "shared", "knowledge_base", "inspiration_research")
EXCLUDED_PATH_PARTS = {"tests", "docs", "__pycache__"}
TARGETS: dict[str, tuple[re.Pattern[str], frozenset[str]]] = {
    "source_anchor_provenance_v2": (
        re.compile(r"\bSourceStoreV2\b"),
        frozenset({"app/evidence/source_store_v2.py"}),
    ),
    "evidence_bundle_store": (
        re.compile(r"\bstore_bundle\s*\("),
        frozenset({"app/evidence/ledger.py"}),
    ),
    "evidence_bundle_review": (
        re.compile(r"\breview_bundle\s*\("),
        frozenset({"app/evidence/ledger.py"}),
    ),
    "human_learning_event": (
        re.compile(r"\bappend_event\s*\("),
        frozenset({"app/learning/event_store.py"}),
    ),
    "machine_competence_receipt": (
        re.compile(r"\brecord_machine_receipt\s*\("),
        frozenset({"app/learning/event_store.py"}),
    ),
}


def audit_first_wave_consumers(project_root: Path) -> dict[str, list[str]]:
    """Return sorted non-definition production paths for every candidate API."""

    consumers = {name: [] for name in TARGETS}
    for root_name in AUDIT_ROOTS:
        source_root = project_root / root_name
        if not source_root.is_dir():
            continue
        for source in source_root.rglob("*.py"):
            relative = source.relative_to(project_root).as_posix()
            if EXCLUDED_PATH_PARTS.intersection(Path(relative).parts):
                continue
            text = source.read_text(encoding="utf-8")
            for name, (pattern, definition_paths) in TARGETS.items():
                if relative not in definition_paths and pattern.search(text):
                    consumers[name].append(relative)
    return {name: sorted(paths) for name, paths in sorted(consumers.items())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root to scan (default: this script's repository)",
    )
    args = parser.parse_args()
    root = args.project_root.resolve()
    print(
        json.dumps(
            {"project_root": str(root), "consumers": audit_first_wave_consumers(root)},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
