#!/usr/bin/env python3
"""T17 slice1: legacy inventory audit pipeline (deterministic).

Reads the taskpack inventory CSV (10-LEGACY-INVENTORY.csv), verifies every
asset path exists at HEAD with the recorded blob, canonicalizes categories,
and emits:

- LEGACY_MANIFEST.yaml            (registration + disposition summary)
- docs/authority/legacy/T17-inventory-audit-*.json  (full audit evidence)

No deletion or move is performed: inventory rows are metadata only and
semantic absorption is owned by T13 (CODEX) per task card.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    ROOT / ".hermes" / "task-runtime" / "taskpack-0905" / "ARCHEAXIS-FAST-FULL-LOOP" / "10-LEGACY-INVENTORY.csv"
)
MANIFEST_OUT = ROOT / "LEGACY_MANIFEST.yaml"
EVIDENCE_DIR = ROOT / "docs" / "authority" / "legacy"

# Category strings observed in the CSV (UTF-8 Chinese) -> canonical English id.
CATEGORY_MAP = {
    "配置/工程/工作流": "config-tooling",
    "其他仓库资产": "other-repo-assets",
    "旧界面/运行壳": "legacy-ui-shell",
    "旧业务/存储/兼容能力": "legacy-business-store",
    "研究/来源/核查": "research-evidence",
    "解析与转换": "parsing-conversion",
    "知识与双侧学习": "knowledge-dual-learning",
    "历史/决策/文档/任务资料": "history-docs",
    "测试/金标/fixture": "tests-golden-fixtures",
}


def _git_blob(path: str) -> str:
    out = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path}"], capture_output=True, text=True, cwd=ROOT
    )
    return out.stdout.strip() if out.returncode == 0 else ""


def _head_blobs() -> dict[str, str]:
    """Single ls-tree walk: path -> blob sha256 at HEAD (UTF-8 safe)."""
    out = subprocess.run(
        ["git", "-c", "core.quotePath=false", "ls-tree", "-r", "HEAD"],
        capture_output=True,
        cwd=ROOT,
    )
    result: dict[str, str] = {}
    if out.returncode != 0:
        return result
    text = out.stdout.decode("utf-8", errors="surrogateescape")
    for line in text.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            meta = parts[0].split()
            if len(meta) >= 3:
                result[parts[1]] = meta[2]
    return result


def main() -> int:
    rows: list[dict[str, str]] = []
    with open(INVENTORY_CSV, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)

    observed_categories = sorted({row.get("category", "").strip() for row in rows})
    head_blobs = _head_blobs()
    categories: Counter[str] = Counter()
    head_changes: Counter[str] = Counter()
    by_top_dir: Counter[str] = Counter()
    problems: list[dict[str, str]] = []
    missing_paths: list[str] = []

    for row in rows:
        path = row["source_path"]
        raw_category = row.get("category", "").strip()
        canonical = CATEGORY_MAP.get(raw_category, "unclassified")
        categories[canonical] += 1
        head_changes[row.get("head_change", "unknown")] += 1
        top = path.split("/")[0] if "/" in path else "(root)"
        by_top_dir[top] += 1
        blob = head_blobs.get(path, "")
        if not blob:
            missing_paths.append(path)
        elif blob != row.get("head_blob", "") and row.get("head_change") != "modified_at_head":
            # Rows the inventory itself flagged as modified_at_head (baseline
            # e9a7d2d vs source commit) are expected to differ at a later head;
            # only unexpected drift on 'unchanged' rows counts as a problem.
            problems.append({"path": path, "recorded": row.get("head_blob", ""), "actual": blob})

    stats = {
        "total_rows": len(rows),
        "observed_category_values": observed_categories,
        "categories": dict(categories),
        "head_changes": dict(head_changes),
        "top_directories": dict(by_top_dir.most_common(25)),
        "missing_at_head": len(missing_paths),
        "blob_mismatches_at_head": len(problems),
        "sample_mismatch_paths": problems[:20],
        "sample_missing_paths": missing_paths[:20],
    }

    manifest = {
        "schema": "archeaxis.legacy-manifest/v1",
        "manifest_version": 1,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "inventory_source": str(INVENTORY_CSV.relative_to(ROOT)),
        "baseline_sha": "e9a7d2db854da157138111dc1c772cee95c16647",
        "head_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "status_vocabulary": {
            "INVENTORIED_NOT_SEMANTICALLY_REVIEWED": "recorded with source object and proposed disposition; semantic absorption review owned by T13",
            "ABSORBED": "verified integrated into a vNext module with differential samples",
            "MAINTENANCE_ONLY": "kept as legacy maintenance-only/history",
            "DEFERRED": "explicitly deferred with reason",
        },
        "disposition_rules": {
            "deletion": "no asset may be deleted without a registered retirement entry and user-confirmed scope",
            "reuse": "absorbed capabilities land behind vNext modules with provenance notes; no dual writers",
        },
        "category_counts": dict(categories),
        "head_change_counts": dict(head_changes),
        "verification": stats,
        "full_entries": [
            {
                "asset_id": row["asset_id"],
                "path": row["source_path"],
                "category": CATEGORY_MAP.get(row.get("category", "").strip(), "unclassified"),
                "source_commit": row["source_commit"],
                "source_blob": row["source_blob"],
                "head_change": row.get("head_change", ""),
                "owner_tasks": row.get("owner_tasks", ""),
                "proposed_target": row.get("proposed_target", ""),
                "review_status": row.get("status", "INVENTORIED_NOT_SEMANTICALLY_REVIEWED"),
            }
            for row in rows
        ],
    }

    with open(MANIFEST_OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "# ArcheAxis legacy asset manifest (generated by tests/legacy-differential/"
            "audit_legacy_inventory.py; do not hand-edit counts)\n\n"
        )
        fh.write(_yaml_dump(manifest))
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence = EVIDENCE_DIR / f"T17-inventory-audit-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    with open(evidence, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    # Missing paths contradict the inventory and fail; blob drift since the
    # baseline is informational (recorded as changed_since_baseline for the
    # next inventory refresh).
    return 0 if not missing_paths else 2


def _yaml_dump(data: dict) -> str:
    import yaml

    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=200)


if __name__ == "__main__":
    sys.exit(main())
