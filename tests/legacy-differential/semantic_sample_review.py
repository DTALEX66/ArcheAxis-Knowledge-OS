#!/usr/bin/env python3
"""T17 slice2: bounded semantic sample review over P0 legacy categories.

Deterministic stride sampling across the categories that the taskpack maps
to absorption lanes (parsing-conversion -> T05/T06, knowledge-dual-learning
-> T09/T10/T11, legacy-business-store -> T03/T09/T13, legacy-ui-shell ->
T18/T12). For each sampled asset this reads its current file head (first
non-comment docstring/line) and records a recommendation mapping; it does
NOT delete or move anything, and every entry stays
INVENTORIED_NOT_SEMANTICALLY_REVIEWED until T13 closes it.

Output: docs/authority/legacy/T17-semantic-review-samples-<date>.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# category -> recommended absorption lanes (taskpack mapping)
LANE_MAP = {
    "parsing-conversion": "T05/T06 worker engine absorption (worker_office/worker_text/worker_ocr lanes)",
    "knowledge-dual-learning": "T09/T10/T11 domain semantics source-of-behavior",
    "legacy-business-store": "T03/T09/T13 migration/behavior oracle (never dual-write)",
    "legacy-ui-shell": "T18/T12 design/UX reference only",
    "tests-golden-fixtures": "T07 goldens (reuse as evaluation goldens after audit)",
    "research-evidence": "T08 behavior oracle for research lanes",
    "config-tooling": "T01/T14 governance reference",
    "history-docs": "T14 history index (keep, no code absorption)",
    "other-repo-assets": "T17/T14 verify and keep",
}

STRIDE = 12
MAX_PER_CATEGORY = 6
MAX_TOTAL = 30


def _sample_categories(manifest: dict) -> list[dict]:
    selected: list[dict] = []
    counts: dict[str, int] = {}
    for entry in manifest["full_entries"]:
        category = entry["category"]
        if category not in LANE_MAP:
            continue
        index = counts.get(category, 0)
        counts[category] = index + 1
        if index % STRIDE == 0 and counts.get(f"kept:{category}", 0) < MAX_PER_CATEGORY:
            counts[f"kept:{category}"] = counts.get(f"kept:{category}", 0) + 1
            selected.append(entry)
            if len(selected) >= MAX_TOTAL:
                break
    return selected


def _head_snippet(path: Path) -> str:
    try:
        raw = path.read_bytes()[:4000]
        text = raw.decode("utf-8", errors="replace")
    except OSError as exc:
        return f"<unreadable: {exc}>"
    lines = [line for line in text.splitlines() if line.strip()]
    snippet = ""
    for line in lines[:6]:
        stripped = line.strip()
        if stripped.startswith(("#", "//", "\"\"\"", "/*", "*", "<!--")) or not snippet:
            snippet += stripped[:160] + " | "
        else:
            break
    return snippet[:600]


def main() -> int:
    manifest_path = ROOT / "LEGACY_MANIFEST.yaml"
    import yaml

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    samples = []
    for entry in _sample_categories(manifest):
        path = ROOT / entry["path"]
        samples.append(
            {
                "asset_id": entry["asset_id"],
                "path": entry["path"],
                "category": entry["category"],
                "head_change": entry["head_change"],
                "recommended_lane": LANE_MAP[entry["category"]],
                "head_snippet": _head_snippet(path) if path.exists() else "<missing at head>",
                "review_status": "INVENTORIED_NOT_SEMANTICALLY_REVIEWED",
            }
        )
    payload = {
        "schema": "archeaxis.legacy-manifest/v1",
        "kind": "semantic-review-samples",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "stride": STRIDE,
        "count": len(samples),
        "note": "snippets are metadata evidence only; absorption decisions belong to T13",
        "samples": samples,
    }
    out = ROOT / "docs" / "authority" / "legacy" / (
        f"T17-semantic-review-samples-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    )
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"sampled {len(samples)} assets -> {out.relative_to(ROOT)}")
    for sample in samples:
        print(f"  {sample['asset_id']} {sample['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
