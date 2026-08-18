"""Learner-state API — absorbed from Tutor MCP patterns (report §3.5).

Learning state belongs to ArcheAxis, not to any LLM: models are temporary
teachers, and the learner model is the durable record. This router exposes a
neutral, provider-agnostic learner state surface:

    GET  /api/v1/learning/mastery/{card_id}   — dual-mastery three-axis state
    GET  /api/v1/learning/review-queue        — FSRS due cards
    POST /api/v1/learning/teach-back          — record + rubric-evaluate a teach-back
    POST /api/v1/learning/distill             — record a human candidate principle
    POST /api/v1/learning/trajectory          — save a trajectory + reflect a principle
    GET  /api/v1/learning/principles          — retrieve reasoning principles

All writes are append-only and gated by their modules; nothing here auto-
activates a skill or asserts verified truth.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from shared.config import config, resolve_runtime_path

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


def _db_path() -> Path:
    return Path(resolve_runtime_path(str(config.get("database.path", "data/cognitive_os.sqlite"))))


# ── dual mastery ────────────────────────────────────────────────────

@router.get("/mastery/{card_id}")
def get_mastery(card_id: str) -> dict[str, object]:
    """Three-axis knowledge-node state for one card (human/machine/evidence)."""
    from app.adapters.mastery_signal import from_learning_snapshots
    from app.knowledge.dual_mastery import HumanEvidence, MachineEvidence, evaluate_node

    db = _db_path()
    import sqlite3

    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        card = conn.execute("SELECT * FROM kb_cards WHERE id=?", (card_id,)).fetchone()
        if card is None:
            raise HTTPException(status_code=404, detail=f"card not found: {card_id}")
        reviews = conn.execute(
            "SELECT * FROM kb_reviews WHERE card_id=? ORDER BY created_at, id", (card_id,)
        ).fetchall()
        mistakes = conn.execute(
            "SELECT * FROM kb_mistakes WHERE card_id=? ORDER BY created_at, id", (card_id,)
        ).fetchall()
        conn.close()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — fail closed with a clean 4xx
        raise HTTPException(status_code=400, detail=f"mastery lookup failed: {exc}") from exc

    signal = from_learning_snapshots(dict(card), [dict(r) for r in reviews],
                                     [dict(m) for m in mistakes])
    human = HumanEvidence(
        reviewed=signal.review_count > 0,
        review_state=str(card.get("review_status", "new")),
        stability_days=float(card.get("stability_days") or 0.0),
        bkt_mastery=float(card.get("bkt_mastery") or 0.0),
    )
    machine = MachineEvidence(has_raw_source=True, indexed=True, structured=True)
    node = evaluate_node(card_id, human, machine)
    return {
        "card_id": card_id,
        "state": node.to_display(),
        "signal": signal.model_dump(),
    }


# ── review queue (FSRS) ─────────────────────────────────────────────

@router.get("/review-queue")
def review_queue(limit: int = 20) -> dict[str, object]:
    """FSRS due cards (learner-agnostic schedule data)."""
    from app.knowledge.due_queue import due_queue

    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be in [1, 200]")
    try:
        due = due_queue(_db_path(), tz_offset_minutes=0)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"review queue failed: {exc}") from exc
    return {"due_count": len(due), "due": due[:limit]}


# ── teach-back ──────────────────────────────────────────────────────

@router.post("/teach-back")
def submit_teach_back(payload: dict[str, object]) -> dict[str, object]:
    """Record + rubric-evaluate a teach-back restatement (M3 evidence)."""
    from app.knowledge.teach_back_eval import score_teach_back

    try:
        record_id = str(payload["record_id"])
        concept = str(payload["concept"])
        restatement = str(payload["restatement"])
        reference = str(payload["reference"])
        key_terms = [str(t) for t in (payload.get("key_terms") or [])]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing field: {exc}") from exc
    try:
        evaluation = score_teach_back(record_id=record_id, concept=concept,
                                      restatement=restatement, reference=reference,
                                      key_terms=key_terms)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "record_id": record_id,
        "concept": concept,
        "evaluation": {
            "accuracy": evaluation.accuracy, "coverage": evaluation.coverage,
            "paraphrase": evaluation.paraphrase, "organization": evaluation.organization,
            "overall": evaluation.overall, "passes": evaluation.passes(),
            "missing_terms": evaluation.missing_terms,
            "extra_claims": evaluation.extra_claims,
        },
    }


# ── human distillation ──────────────────────────────────────────────

@router.post("/distill")
def record_distill(payload: dict[str, object]) -> dict[str, object]:
    """Record a candidate human principle for cross-case verification."""
    from app.knowledge.distillation import record_principle

    try:
        statement = str(payload["statement"])
        source_kind = str(payload["source_kind"])
        source_locator = str(payload["source_locator"])
        evidence = payload.get("evidence")
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing field: {exc}") from exc
    try:
        principle = record_principle(_db_path(), statement=statement,
                                     source_kind=source_kind,
                                     source_locator=source_locator,
                                     evidence=str(evidence) if evidence else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"principle_id": principle.principle_id, "status": principle.status}


# ── reasoning memory ────────────────────────────────────────────────

@router.post("/trajectory")
def save_trajectory(payload: dict[str, object]) -> dict[str, object]:
    """Save a trajectory and distill a reasoning principle from it."""
    from app.memory.reasoning_memory import reflect, save_trajectory as save_traj

    try:
        goal = str(payload["goal"])
        steps = [str(s) for s in payload["steps"]]
        outcome = str(payload["outcome"])
        error_pattern = payload.get("error_pattern")
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing field: {exc}") from exc
    try:
        trajectory = save_traj(_db_path(), goal=goal, steps=steps, outcome=outcome,  # type: ignore[arg-type]
                               error_pattern=str(error_pattern) if error_pattern else None)
        principle = reflect(_db_path(), trajectory.trajectory_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"trajectory_id": trajectory.trajectory_id,
            "principle_id": principle.principle_id,
            "principle": principle.statement,
            "category": principle.category}


@router.get("/principles")
def list_principles(query: str = "", top_k: int = 5) -> dict[str, object]:
    """Retrieve reasoning principles by query."""
    from app.memory.reasoning_memory import retrieve_principles

    if top_k < 1 or top_k > 50:
        raise HTTPException(status_code=400, detail="top_k must be in [1, 50]")
    try:
        results = retrieve_principles(_db_path(), query or " ", top_k=top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"count": len(results), "principles": results}
