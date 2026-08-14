"""First-run setup wizard HTTP API (AXW-DATA-402).

Prefix: /api/v1/setup
    GET  /status     → readiness steps (id/state/message/action_hint)
    POST /initialize → create the workspace (idempotent)

The setup surface is local-first like the workspace API: only loopback
callers may inspect or initialize the runtime.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.setup.setup_status import initialize_workspace, setup_status
from app.workspace.router import _require_local_request

router = APIRouter(
    prefix="/api/v1/setup",
    tags=["setup"],
    dependencies=[Depends(_require_local_request)],
)


@router.get("/status")
def get_setup_status() -> dict[str, object]:
    """Readiness steps for the first-run wizard (fail-closed, never 500)."""
    return setup_status()


@router.post("/initialize")
def post_setup_initialize() -> dict[str, object]:
    """Create the workspace; idempotent — an existing valid workspace is
    returned as-is with ``already_existed=true``."""
    try:
        return initialize_workspace()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
