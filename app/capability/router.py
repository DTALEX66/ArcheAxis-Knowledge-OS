"""Capability Store v1 HTTP API (AXW-CAP-501).

Prefix: /api/v1/capabilities
    GET  /                    → list installed capabilities
    POST /stage               → stage a pack directory {path}
    POST /activate/{id}       → hash-verify + atomically install a staged pack
    POST /disable/{id}        → move installed → disabled
    POST /enable/{id}         → move disabled → installed
    POST /quarantine/{id}     → move to quarantine with {reason}

All store refusals (missing/invalid manifest, hash mismatch, unknown id)
surface as 400 with the fail-closed detail message.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.capability.store import CapabilityStore, CapabilityStoreError
from shared.config import resolve_runtime_path

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


class StageRequest(BaseModel):
    path: str


class QuarantineRequest(BaseModel):
    reason: str


def get_store() -> CapabilityStore:
    """Per-request store bound to ARCHEAXIS_CAPABILITY_ROOT (or the runtime
    data dir). Reading the env per request keeps tests hermetic."""
    override = os.getenv("ARCHEAXIS_CAPABILITY_ROOT", "").strip()
    if override:
        root = Path(override)
    else:
        root = resolve_runtime_path("data") / "capabilities"
    return CapabilityStore(root)


def _store_error(exc: CapabilityStoreError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/")
def list_capabilities(store: CapabilityStore = Depends(get_store)) -> dict:
    records = store.list_installed()
    return {"count": len(records), "capabilities": [record.to_dict() for record in records]}


@router.post("/stage")
def stage_pack(payload: StageRequest, store: CapabilityStore = Depends(get_store)) -> dict:
    try:
        record = store.stage(payload.path)
    except CapabilityStoreError as exc:
        raise _store_error(exc) from exc
    return {"staged": record.to_dict()}


@router.post("/activate/{staged_id}")
def activate_pack(staged_id: str, store: CapabilityStore = Depends(get_store)) -> dict:
    try:
        record = store.activate(staged_id)
    except CapabilityStoreError as exc:
        raise _store_error(exc) from exc
    return {"activated": record.to_dict()}


@router.post("/disable/{plugin_id}")
def disable_pack(plugin_id: str, store: CapabilityStore = Depends(get_store)) -> dict:
    try:
        record = store.disable(plugin_id)
    except CapabilityStoreError as exc:
        raise _store_error(exc) from exc
    return {"disabled": record.to_dict()}


@router.post("/enable/{plugin_id}")
def enable_pack(plugin_id: str, store: CapabilityStore = Depends(get_store)) -> dict:
    try:
        record = store.enable(plugin_id)
    except CapabilityStoreError as exc:
        raise _store_error(exc) from exc
    return {"enabled": record.to_dict()}


@router.post("/quarantine/{plugin_id}")
def quarantine_pack(
    plugin_id: str, payload: QuarantineRequest, store: CapabilityStore = Depends(get_store)
) -> dict:
    try:
        record = store.quarantine(plugin_id, payload.reason)
    except CapabilityStoreError as exc:
        raise _store_error(exc) from exc
    return {"quarantined": record.to_dict()}
