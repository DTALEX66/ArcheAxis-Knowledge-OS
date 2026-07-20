"""Server-owned orchestration for one governed Cognitive Workspace case."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from app.facades.research import research_github_repository
from app.ingestion.multi_format import convert_file, convert_url, detect_format
from app.knowledge.closed_loop import (
    approve_learning_artifact,
    audit_closed_loop,
    record_practice_evidence,
    start_learning_candidate,
)
from app.knowledge.promotion import (
    ResearchKnowledgeApproval,
    promote_research_package_to_candidates,
)
from app.research.document import persist_workspace_document

MAX_INTAKE_UPLOAD_BYTES = 25 * 1024 * 1024


def intake_url(*, url: str, db_path: str | Path, fetcher=None) -> dict:
    parsed = urlsplit(url)
    if parsed.hostname and parsed.hostname.rstrip(".").casefold() == "github.com":
        graph = research_github_repository(url, fetcher=fetcher, db_path=db_path)
        return {
            "source_type": "github_repository",
            "source": graph.canonical_url,
            "package_id": graph.package.package_id,
            "status": graph.package.status,
            "requires_human_review": graph.package.requires_human_review,
            "source_count": len(graph.sources),
            "claim_count": len(graph.claims),
            "evidence_count": len(graph.evidence),
        }
    content, engine = convert_url(url)
    graph = persist_workspace_document(
        title=url,
        content=content,
        source_format="html",
        extractor_identity=engine,
        source_locator=url,
        db_path=db_path,
    )
    return {
        "source_type": "web",
        "source": url,
        "package_id": graph.package.package_id,
        "status": graph.package.status,
        "requires_human_review": graph.package.requires_human_review,
        "source_count": len(graph.sources),
        "claim_count": len(graph.claims),
        "evidence_count": len(graph.evidence),
    }


def intake_upload(*, file_name: str, content: bytes, db_path: str | Path) -> dict:
    if not file_name:
        raise ValueError("uploaded file requires a name")
    if not content:
        raise ValueError("uploaded file is empty")
    if len(content) > MAX_INTAKE_UPLOAD_BYTES:
        raise ValueError("uploaded file exceeds the 25 MB local intake limit")
    safe_name = Path(file_name).name
    if safe_name != file_name:
        raise ValueError("uploaded file name must not include a path")
    upload_dir = Path(db_path).parent / "intake_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{uuid4().hex}_{safe_name}"
    stored_path.write_bytes(content)
    try:
        markdown, engine = convert_file(stored_path)
    except RuntimeError:
        stored_path.unlink(missing_ok=True)
        raise
    source_format = detect_format(stored_path)
    graph = persist_workspace_document(
        title=safe_name,
        content=markdown,
        source_format=source_format,
        extractor_identity=engine,
        db_path=db_path,
    )
    return {
        "source_type": "file",
        "file_name": safe_name,
        "format": source_format,
        "engine": engine,
        "content": markdown,
        "char_count": len(markdown),
        "package_id": graph.package.package_id,
        "status": graph.package.status,
        "requires_human_review": graph.package.requires_human_review,
    }


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_matching_promotion_command(
    *, command_id: str, package_id: str, reviewer_id: str, rationale: str, db_path: str | Path
) -> None:
    with sqlite3.connect(Path(db_path)) as connection:
        row = connection.execute(
            "SELECT package_id, reviewer_id, decision, rationale "
            "FROM knowledge_candidate_governance_events_v1 WHERE approval_id=?",
            (command_id,),
        ).fetchone()
    if row is None:
        return
    recorded = tuple(str(item) for item in row)
    requested = (package_id, reviewer_id, "approved", rationale)
    if recorded != requested:
        raise RuntimeError("workspace command id conflicts with an existing promotion receipt")


def _require_matching_learning_command(
    *, command_id: str, unit_id: str, reviewer_id: str, rationale: str, db_path: str | Path
) -> None:
    with sqlite3.connect(Path(db_path)) as connection:
        row = connection.execute(
            "SELECT source_unit_id, reviewer_id, rationale "
            "FROM knowledge_candidate_learning_artifacts_v1 WHERE approval_id=?",
            (command_id,),
        ).fetchone()
    if row is None:
        return
    if tuple(str(item) for item in row) != (unit_id, reviewer_id, rationale):
        raise RuntimeError("workspace command id conflicts with an existing learning receipt")


def _require_matching_practice_command(
    *, command_id: str, quality: int, db_path: str | Path
) -> None:
    review_id = "practice_" + sha256(command_id.encode()).hexdigest()[:24]
    with sqlite3.connect(Path(db_path)) as connection:
        row = connection.execute("SELECT quality FROM kb_reviews WHERE id=?", (review_id,)).fetchone()
    if row is not None and int(row[0]) != quality:
        raise RuntimeError("workspace command id conflicts with an existing practice receipt")


def promote_research(*, command_id: str, package_id: str, reviewer_id: str, rationale: str, db_path: str | Path) -> dict:
    _require_matching_promotion_command(
        command_id=command_id,
        package_id=package_id,
        reviewer_id=reviewer_id,
        rationale=rationale,
        db_path=db_path,
    )
    receipt = promote_research_package_to_candidates(
        ResearchKnowledgeApproval(
            approval_id=command_id,
            package_id=package_id,
            reviewer_id=reviewer_id,
            decision="approved",
            rationale=rationale,
            reviewed_at=now_utc(),
        ),
        db_path=db_path,
    )
    return {
        "command_id": command_id,
        "promotion_id": receipt.promotion_id,
        "package_id": receipt.package_id,
        "unit_ids": [unit.unit_id for unit in receipt.units],
        "status": receipt.lifecycle_status,
    }


def start_learning(*, command_id: str, unit_id: str, reviewer_id: str, rationale: str, db_path: str | Path) -> dict:
    _require_matching_learning_command(
        command_id=command_id,
        unit_id=unit_id,
        reviewer_id=reviewer_id,
        rationale=rationale,
        db_path=db_path,
    )
    artifact = start_learning_candidate(
        unit_id=unit_id,
        approval_id=command_id,
        reviewer_id=reviewer_id,
        rationale=rationale,
        reviewed_at=now_utc(),
        db_path=db_path,
    )
    card_ids = approve_learning_artifact(
        artifact_id=artifact.artifact_id,
        command_id=f"local-approval-{command_id}",
        reviewer_id=reviewer_id,
        reviewed_at=now_utc(),
        db_path=db_path,
    )
    return {
        "command_id": command_id,
        "artifact_id": artifact.artifact_id,
        "card_ids": card_ids,
        "status": "approved",
    }


def approve_learning(*, command_id: str, artifact_id: str, reviewer_id: str, db_path: str | Path) -> dict:
    card_ids = approve_learning_artifact(
        artifact_id=artifact_id,
        command_id=command_id,
        reviewer_id=reviewer_id,
        reviewed_at=now_utc(),
        db_path=db_path,
    )
    return {"command_id": command_id, "artifact_id": artifact_id, "card_ids": card_ids, "status": "approved"}


def record_practice(*, command_id: str, artifact_id: str, quality: int, db_path: str | Path) -> dict:
    _require_matching_practice_command(command_id=command_id, quality=quality, db_path=db_path)
    result = record_practice_evidence(
        artifact_id=artifact_id,
        command_id=command_id,
        quality=quality,
        recorded_at=now_utc(),
        db_path=db_path,
    )
    return {
        "command_id": command_id,
        "artifact_id": artifact_id,
        "mastered": result.mastery_signal.is_mastered,
        "machine_candidate_id": result.machine_knowledge.unit_id if result.machine_knowledge else None,
    }


def case_audit(*, artifact_id: str, db_path: str | Path) -> dict:
    return {
        "artifact_id": artifact_id,
        "events": [
            {"event_type": event.event_type, "occurred_at": event.occurred_at}
            for event in audit_closed_loop(artifact_id, db_path=db_path)
        ],
    }
