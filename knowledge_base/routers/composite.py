"""Stable composite Knowledge-Base endpoints.

These surfaces consolidate legacy one-action routes without adding another group
of scattered endpoints.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["composite"])


class PipelineRequest(BaseModel):
    source: str = "text"
    input: str = ""
    actions: list[str] = Field(default_factory=list)
    auto_ingest: bool = True


@router.post("/pipeline")
def pipeline_run(req: PipelineRequest):
    from shared.pipeline import run_pipeline

    try:
        return run_pipeline(
            req.source,
            req.input,
            actions=req.actions or None,
            auto_ingest=req.auto_ingest,
        )
    except RuntimeError as exc:
        detail = str(exc)
        if "external pipeline auto-ingest is disabled" in detail:
            raise HTTPException(status_code=409, detail=detail) from exc
        if "requires COGNITIVE_APPROVED_SOURCE_ROOTS" in detail:
            raise HTTPException(status_code=503, detail=detail) from exc
        if detail.startswith("file pipeline source"):
            raise HTTPException(status_code=422, detail=detail) from exc
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/garden")
def garden(action: str = "gaps", doc_id: str = "", top_k: int = 5):
    if action == "orphans":
        from shared.knowledge_gardener import find_orphans

        return find_orphans()
    if action == "suggest" and doc_id:
        from shared.knowledge_gardener import suggest_connections

        return suggest_connections(doc_id, top_k)
    if action == "evergreen" and doc_id:
        from shared.knowledge_gardener import score_evergreen

        return score_evergreen(doc_id)
    from shared.knowledge_gardener import detect_gaps

    return detect_gaps()


@router.get("/analytics")
def analytics(action: str = "streak", days: int = 30, limit: int = 20):
    if action == "heatmap":
        from shared.learning_analytics import topic_heatmap

        return topic_heatmap(limit=limit)
    from shared.learning_analytics import review_streak

    return review_streak(days=days)


@router.get("/mermaid")
def mermaid(
    type: str = "graph",
    title: str = "",
    card_id: str = "",
    steps: str = "[]",
    max_nodes: int = 20,
):
    if type == "flowchart":
        from shared.mermaid_gen import flowchart

        try:
            parsed_steps = json.loads(steps)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="steps must be valid JSON") from exc
        return flowchart(title, parsed_steps)
    if type == "timeline" and card_id:
        from shared.mermaid_gen import review_timeline_mermaid

        return review_timeline_mermaid(card_id)
    from shared.mermaid_gen import knowledge_graph_mermaid

    return knowledge_graph_mermaid(card_id, max_nodes)


@router.get("/evidence")
def evidence(doc_id: str = "", action: str = "get"):
    if action == "radar" or not doc_id:
        from shared.evidence_index import vault_health_radar

        return vault_health_radar()
    from shared.evidence_index import evidence_health, get_evidence

    return {"evidence": get_evidence(doc_id), "health": evidence_health(doc_id)}


@router.post("/evidence")
def evidence_add(
    doc_id: str = "",
    source_type: str = "manual",
    source_path: str = "",
    confidence: str = "medium",
    caption: str = "",
):
    from shared.evidence_index import index_evidence

    try:
        return index_evidence(
            doc_id,
            source_type,
            source_path,
            confidence,
            caption=caption,
        )
    except ValueError as exc:
        if "server-owned Phase 5 review provenance" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise


@router.get("/retro")
def retro(action: str = "weekly", days: int = 7):
    if action == "missions":
        from shared.retro_summary import generate_daily_missions

        return generate_daily_missions()
    from shared.retro_summary import weekly_summary

    return weekly_summary(days=days)


@router.get("/projects")
def projects(action: str = "suggest", topic: str = "", limit: int = 5):
    if action == "generate" and topic:
        from shared.project_generator import generate_project_from_topic

        return generate_project_from_topic(topic)
    from shared.project_generator import suggest_projects

    return suggest_projects(limit=limit)


@router.post("/sources")
def sources(
    action: str = "discover",
    root_dir: str = "",
    source_dir: str = "",
    max_files: int = 100,
):
    selected = source_dir or root_dir
    if action == "match":
        from shared.source_discovery import match_sources_to_cards

        return match_sources_to_cards(selected)
    if action == "inventory":
        from shared.media_extractor import media_inventory

        return media_inventory(selected)
    from shared.source_discovery import discover_sources

    return discover_sources(root_dir, max_files=max_files)


@router.get("/diversity")
def diversity(doc_id: str = "", limit: int = 20):
    if doc_id:
        from shared.diversity_audit import analyze_diversity

        return analyze_diversity(doc_id)
    from shared.diversity_audit import diversity_radar

    return diversity_radar(limit=limit)


@router.post("/bulk/import")
def bulk_import(items: str = "[]"):
    from shared.bulk_ops import bulk_import as run_bulk_import

    try:
        payload = json.loads(items)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="items must be valid JSON") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="items must be a JSON array")
    try:
        return run_bulk_import(payload)
    except RuntimeError as exc:
        if "external pipeline auto-ingest is disabled" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise


@router.get("/export")
def export_kb(format: str = "json", tables: str = ""):
    from shared.bulk_ops import export_kb as run_export

    table_list = [item.strip() for item in tables.split(",") if item.strip()] if tables else None
    try:
        return run_export(format=format, tables=table_list)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cron/discover")
def cron_discover():
    """Reject the retired scheduled external collection bypass."""
    raise HTTPException(
        status_code=409,
        detail="Legacy cron discovery is disabled; use a governed candidate path",
    )
