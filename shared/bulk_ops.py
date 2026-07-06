"""Bulk operations + export — batch import, export formats, cron trigger."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))


def bulk_import(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Batch import multiple items via pipeline.

    Args:
        items: [{source, input, actions}, ...]

    Returns:
        {total, succeeded, failed, results}.
    """
    from shared.pipeline import run_pipeline

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
        tables = ["kb_documents", "kb_cards", "kb_reviews", "kb_mistakes",
                  "machine_knowledge_units", "kb_taskpacks", "kb_context_packs"]

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
                import io, csv
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
    """One-shot discovery pipeline for cron/scheduled execution.

    Searches multiple sources, collects feeds, and returns new items.
    Designed to be called from a cron job.
    """
    from shared.feed_collector import collect_and_ingest
    from shared.web_search import search_web

    results = {
        "feeds": collect_and_ingest([
            "https://arxiv.org/rss/cs.AI",
            "https://huggingface.co/blog/feed.xml",
        ], max_items=3),
        "search": search_web("new AI knowledge management tool 2026", limit=3),
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }

    return results
