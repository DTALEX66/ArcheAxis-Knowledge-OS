"""First-run setup wizard HTTP API (AXW-DATA-402).

Prefix: /api/v1/setup
    GET  /status     → readiness steps (id/state/message/action_hint)
    POST /preflight  → validate selected library paths without creating them
    POST /initialize → create the workspace (idempotent)

The setup surface is local-first like the workspace API: only loopback
callers may inspect or initialize the runtime.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.setup.setup_status import (
    SetupRequest,
    SetupValidationError,
    initialize_workspace,
    preflight_workspace,
    setup_status,
)
from app.workspace.router import _require_desktop_write_request, _require_local_request

router = APIRouter(
    prefix="/api/v1/setup",
    tags=["setup"],
    dependencies=[Depends(_require_local_request)],
)


class SetupInitializeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["quick", "advanced"] = "quick"
    root: str | None = Field(default=None, min_length=1, max_length=4096)
    domains: dict[str, str] | None = None


@router.get("/status")
def get_setup_status() -> dict[str, object]:
    """Readiness steps for the first-run wizard (fail-closed, never 500)."""
    return setup_status()


def _setup_request(payload: SetupInitializeRequest | None) -> SetupRequest:
    if payload is None:
        return SetupRequest(mode="quick")
    return SetupRequest(mode=payload.mode, root=payload.root, domains=payload.domains)


@router.post("/preflight")
def post_setup_preflight(payload: SetupInitializeRequest | None = None) -> dict[str, object]:
    """Check a selected four-library layout without creating user directories."""
    try:
        return preflight_workspace(_setup_request(payload))
    except SetupValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/initialize", dependencies=[Depends(_require_desktop_write_request)])
def post_setup_initialize(payload: SetupInitializeRequest | None = None) -> dict[str, object]:
    """Create the workspace; idempotent — an existing valid workspace is
    returned as-is with ``already_existed=true``."""
    try:
        return initialize_workspace(_setup_request(payload))
    except SetupValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_setup", "message": str(exc)}) from exc
