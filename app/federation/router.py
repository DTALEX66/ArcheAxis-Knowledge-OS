"""Federation knowledge API router — stable cross-project boundary."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.contracts.federation_v1 import (
    CandidateSubmissionV1,
    ExternalAssetRecordV1,
    KnowledgeQueryV1,
)
from app.federation import service
from shared.config import config, resolve_runtime_path

router = APIRouter(prefix="/api/v1/federation", tags=["federation"])


def _db() -> str:
    return str(resolve_runtime_path(str(config.get("database.path", "data/cognitive_os.sqlite"))))


@router.post("/candidates")
def submit_candidates(payload: CandidateSubmissionV1) -> dict[str, object]:
    try:
        result = service.submit_candidates(_db(), payload)
    except service.FederationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"receipt": result.receipt.model_dump(), "duplicate": result.duplicate}


@router.get("/candidates/{submission_id}/receipt")
def candidate_receipt(submission_id: str) -> dict[str, object]:
    try:
        receipt = service.get_receipt(_db(), submission_id)
    except service.FederationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"receipt": receipt.model_dump()}


@router.post("/candidates/{candidate_id}/verify")
def promote_candidate(candidate_id: str, payload: dict[str, str]) -> dict[str, object]:
    reviewer = str(payload.get("reviewer") or "federation-reviewer")
    try:
        service.promote_to_verified(_db(), candidate_id, reviewer=reviewer)
    except service.FederationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"candidate_id": candidate_id, "status": "verified", "reviewer": reviewer}


@router.get("/knowledge")
def query_knowledge(query: str = "", page: int = 1, page_size: int = 20,
                    kind: str = "verified") -> dict[str, object]:
    request = KnowledgeQueryV1(query=query.strip(), page=page, page_size=page_size,
                               kind=kind)  # type: ignore[arg-type]
    try:
        projection = service.query_verified(_db(), request)
    except service.FederationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return projection.model_dump()


@router.get("/records/{entity_id}/hash")
def record_hash(entity_id: str) -> dict[str, object]:
    try:
        return service.hash_readback(_db(), entity_id)
    except service.FederationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/external-assets")
def register_asset(payload: ExternalAssetRecordV1) -> dict[str, object]:
    try:
        asset_id = service.register_external_asset(_db(), payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"asset_id": asset_id, "status": "registered"}


@router.get("/external-assets")
def list_assets(limit: int = 50) -> dict[str, object]:
    return {"count": 0, "items": service.list_external_assets(_db(), limit=limit)}
