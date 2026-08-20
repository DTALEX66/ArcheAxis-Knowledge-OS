"""Federation knowledge API router — stable cross-project boundary."""
from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Request

from app.contracts.federation_v1 import (
    CandidateSubmissionV1,
    EvidenceIntakeV1,
    ExternalAssetRecordV1,
    KnowledgeQueryV1,
    LearningRecordV1,
    ProvenanceRecordV1,
    ReviewDecisionV1,
    RightsRecordV1,
)
from app.federation import service
from app.workspace.router import _require_local_request
from shared.config import config, resolve_runtime_path

router = APIRouter(
    prefix="/api/v1/federation",
    tags=["federation"],
    dependencies=[Depends(_require_local_request)],
)


def _db() -> str:
    return str(resolve_runtime_path(str(config.get("database.path", "data/archeaxis.sqlite"))))


def _write_actor(request: Request, required_scope: str) -> str:
    """Require the local desktop launch credential and a resolved actor."""
    expected_token = os.getenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN") or os.getenv(
        "COGNITIVE_DESKTOP_LAUNCH_TOKEN", ""
    )
    supplied_token = request.headers.get("x-archeaxis-launch-token", "")
    if not expected_token or not hmac.compare_digest(supplied_token, expected_token):
        raise HTTPException(status_code=403, detail="valid desktop launch token required")
    actor = request.headers.get("x-archeaxis-actor", "").strip()
    if not actor:
        raise HTTPException(status_code=403, detail="resolved actor identity required")
    scopes = {
        scope.strip()
        for scope in request.headers.get("x-archeaxis-scopes", "").replace(",", " ").split()
    }
    if required_scope not in scopes:
        raise HTTPException(status_code=403, detail=f"missing required scope: {required_scope}")
    return actor


@router.post("/candidates")
def submit_candidates(payload: CandidateSubmissionV1, request: Request) -> dict[str, object]:
    actor = _write_actor(request, "federation.write")
    if payload.submitter != actor:
        raise HTTPException(status_code=403, detail="submitter must match resolved actor identity")
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


@router.post("/candidates/{candidate_id}/review")
def review_candidate(
    candidate_id: str, payload: ReviewDecisionV1, request: Request
) -> dict[str, object]:
    actor = _write_actor(request, "evidence.review")
    if payload.reviewer_id != actor:
        raise HTTPException(status_code=403, detail="reviewer_id must match resolved actor identity")
    try:
        return service.review_candidate(_db(), candidate_id, payload)
    except service.FederationError as exc:
        status_code = 409 if "version conflict" in str(exc) else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


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
def register_asset(payload: ExternalAssetRecordV1, request: Request) -> dict[str, object]:
    _write_actor(request, "federation.write")
    try:
        asset_id = service.register_external_asset(_db(), payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"asset_id": asset_id, "status": "registered"}


@router.get("/external-assets")
def list_assets(limit: int = 50) -> dict[str, object]:
    items = service.list_external_assets(_db(), limit=limit)
    return {"count": len(items), "items": items}


# ── record types: evidence / learning / provenance / rights (AA-P0-002) ──

@router.post("/records/evidence")
def post_evidence(payload: EvidenceIntakeV1, request: Request) -> dict[str, object]:
    _write_actor(request, "federation.write")
    try:
        rid = service.record_evidence(_db(), payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"record_id": rid, "status": "recorded"}


@router.post("/records/learning")
def post_learning(payload: LearningRecordV1, request: Request) -> dict[str, object]:
    _write_actor(request, "federation.write")
    try:
        rid = service.record_learning(_db(), payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"record_id": rid, "status": "recorded"}


@router.post("/records/provenance")
def post_provenance(payload: ProvenanceRecordV1, request: Request) -> dict[str, object]:
    _write_actor(request, "federation.write")
    try:
        rid = service.record_provenance(_db(), payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"record_id": rid, "status": "recorded"}


@router.post("/records/rights")
def post_rights(payload: RightsRecordV1, request: Request) -> dict[str, object]:
    _write_actor(request, "federation.write")
    try:
        rid = service.record_rights(_db(), payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"record_id": rid, "status": "recorded"}


@router.get("/records/{kind}")
def list_records(kind: str, limit: int = 50) -> dict[str, object]:
    if kind not in ("evidence", "learning", "provenance", "rights"):
        raise HTTPException(status_code=400, detail=f"unknown record kind: {kind}")
    try:
        items = service.list_records(_db(), kind, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"kind": kind, "count": len(items), "items": items}
