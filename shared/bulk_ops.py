"""Bulk operations + export — batch import, export formats, cron trigger."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

ALLOWED_EXPORT_TABLES = frozenset(
    {
        "kb_documents",
        "kb_cards",
        "kb_reviews",
        "kb_mistakes",
        "machine_knowledge_units",
        "kb_taskpacks",
        "kb_context_packs",
    }
)


def bulk_import(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Batch import multiple items via pipeline.

    Args:
        items: [{source, input, actions}, ...]

    Returns:
        {total, succeeded, failed, results}.
    """
    from shared.pipeline import run_pipeline

    external_sources = {"url", "youtube", "rss", "search"}
    if any(
        item.get("source", "text") in external_sources and item.get("auto_ingest", True)
        for item in items
    ):
        raise RuntimeError(
            "external pipeline auto-ingest is disabled; use a governed candidate path"
        )

    results = []
    succeeded = 0
    failed = 0

    for item in items:
        try:
            r = run_pipeline(
                source=item.get("source", "text"),
                input_data=item.get("input", ""),
                actions=item.get("actions"),
                auto_ingest=item.get("auto_ingest", True),
            )
            if r.get("kb_id"):
                succeeded += 1
            results.append(r)
        except Exception as e:
            failed += 1
            results.append({"error": str(e), "input": item.get("input", "")[:100]})

    return {"total": len(items), "succeeded": succeeded, "failed": failed, "results": results}


def export_kb(format: str = "json", tables: list[str] | None = None) -> dict[str, Any]:
    """Export KB data in various formats.

    Args:
        format: 'json' | 'markdown' | 'csv'.
        tables: list of table names to export (default: all KB tables).

    Returns:
        Exported data dict with format-specific structure.
    """
    from shared.storage import select_all

    if tables is None:
        tables = sorted(ALLOWED_EXPORT_TABLES)

    unsupported = sorted(set(tables) - ALLOWED_EXPORT_TABLES)
    if unsupported:
        raise ValueError(f"unsupported export table(s): {', '.join(unsupported)}")

    export: dict[str, Any] = {"format": format, "tables": {}}

    for table in tables:
        rows = select_all(table, limit=500)
        if format == "markdown":
            md_lines = [f"# {table}", ""]
            for row in rows[:50]:
                title = row.get("title") or row.get("pattern") or row.get("id", "")
                content = row.get("content", "")[:200]
                md_lines.append(f"## {title}\n\n{content}\n")
            export["tables"][table] = "\n".join(md_lines)
        elif format == "csv":
            if rows:
                import csv
                import io

                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=list(rows[0].keys())[:10])
                writer.writeheader()
                for row in rows[:200]:
                    # Flatten JSON fields
                    flat = {}
                    for k, v in row.items():
                        if isinstance(v, (list, dict)):
                            flat[k] = str(v)[:100]
                        else:
                            flat[k] = v
                    writer.writerow({k: flat.get(k, "") for k in list(rows[0].keys())[:10]})
                export["tables"][table] = output.getvalue()
            else:
                export["tables"][table] = ""
        else:
            export["tables"][table] = rows[:100]

    return export


def cron_discover() -> dict[str, Any]:
    """Reject the retired scheduled external collection bypass."""
    raise RuntimeError(
        "legacy cron discovery is disabled; external material must use a governed candidate path"
    )
