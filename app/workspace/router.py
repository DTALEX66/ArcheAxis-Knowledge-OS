"""Public boundary for the governed Cognitive Workspace."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from datetime import datetime, timezone
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.evidence.anchor import (
    EvidenceAnchor,
    build_evidence_anchor,
    list_evidence_anchor_page,
    resolve_evidence_anchor,
    store_evidence_anchor,
)
from app.evidence.ledger import (
    EvidenceBundleError,
    get_bundle_inspection,
    list_bundle_summaries,
)
from app.evidence.pdf_serve import PdfServeError, build_pdf_serving_root, resolve_pdf_bytes
from app.workspace import bff, service, vault
from app.workspace.bff import BFFNotFoundError, BFFUnavailableError
from shared.config import resolve_runtime_path
from shared.storage import DB_PATH

# Content-addressed PDF serving root backed by the RawAsset store, under the
# same runtime data directory as the workspace SQLite DB.
PDF_ROOT = build_pdf_serving_root(resolve_runtime_path("data"))

WORKSPACE_PREFIX = "/" + "workspace"
WORKSPACE_UI_ROOT = Path(__file__).resolve().parent / "ui"
WORKSPACE_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; img-src 'self' data:; font-src 'self' data:; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def _is_loopback_host(value: str) -> bool:
    hostname = urlsplit(f"//{value}").hostname or ""
    if hostname.casefold() in {"localhost", "testserver"}:
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def _is_authenticated_tauri_origin(request: Request) -> bool:
    """Allow a packaged or explicitly-enabled dev WebView with its launch token."""
    origin = urlsplit(request.headers.get("origin", ""))
    packaged = origin.scheme.casefold() == "http" and origin.hostname == "tauri.localhost"
    external_dev = (
        os.getenv("ARCHEAXIS_EXTERNAL_DEV") == "1"
        and origin.scheme.casefold() == "http"
        and _is_loopback_host(origin.netloc)
    )
    if not packaged and not external_dev:
        return False
    expected = os.getenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN") or os.getenv(
        "COGNITIVE_DESKTOP_LAUNCH_TOKEN", ""
    )
    supplied = request.headers.get("x-archeaxis-launch-token", "")
    return bool(expected) and hmac.compare_digest(supplied, expected)


def _require_local_request(request: Request) -> None:
    peer = request.client.host if request.client else ""
    if peer != "testclient" and not _is_loopback_host(peer):
        raise HTTPException(status_code=403, detail="workspace is available only locally")
    host = request.headers.get("host", "")
    if not _is_loopback_host(host):
        raise HTTPException(status_code=403, detail="workspace host must be loopback")
    if _is_authenticated_tauri_origin(request):
        return
    if request.headers.get("sec-fetch-site", "").casefold() == "cross-site":
        raise HTTPException(status_code=403, detail="cross-site workspace request rejected")
    origin = request.headers.get("origin", "")
    if origin and urlsplit(origin).netloc.casefold() != host.casefold():
        raise HTTPException(status_code=403, detail="workspace origin must be same-origin")


def _require_desktop_write_request(request: Request) -> None:
    """Require the ephemeral desktop credential on React product writes.

    The desktop launcher injects both the launch token and its issued scopes
    into the Core environment.  A caller may request only a scope the launcher
    issued, and every write needs a bounded idempotency key. TestClient and the
    explicit browser-smoke process are intentionally exempt only when no
    desktop credential has been configured; neither can model a launched
    desktop Core otherwise.
    """
    _require_local_request(request)
    expected_token = os.getenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN") or os.getenv(
        "COGNITIVE_DESKTOP_LAUNCH_TOKEN", ""
    )
    if not expected_token:
        if (
            request.client is not None
            and request.client.host == "testclient"
        ) or os.getenv("ARCHEAXIS_BROWSER_SMOKE_WRITE_BYPASS") == "1":
            return
        raise HTTPException(status_code=503, detail="desktop write authorization is unavailable")
    supplied_token = request.headers.get("x-archeaxis-launch-token", "")
    if not hmac.compare_digest(supplied_token, expected_token):
        raise HTTPException(status_code=403, detail="desktop write authorization rejected")
    issued_scopes = {
        scope for scope in os.getenv("ARCHEAXIS_DESKTOP_WRITE_SCOPES", "").split()
        if scope
    }
    requested_scopes = {
        scope for scope in request.headers.get("x-archeaxis-scopes", "").split()
        if scope
    }
    if (
        "workspace:write" not in issued_scopes
        or "workspace:write" not in requested_scopes
        or not requested_scopes <= issued_scopes
    ):
        raise HTTPException(status_code=403, detail="desktop write scope rejected")
    idempotency_key = request.headers.get("idempotency-key", "")
    if not 1 <= len(idempotency_key) <= 200:
        raise HTTPException(status_code=422, detail="idempotency key is required")


router = APIRouter(
    prefix=WORKSPACE_PREFIX,
    tags=["workspace"],
    dependencies=[Depends(_require_local_request)],
)


class IntakeURL(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2048)


class VaultRootRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str = Field(min_length=1, max_length=4096)


class VaultFileRequest(VaultRootRequest):
    relative_path: str = Field(min_length=1, max_length=4096)


class VaultCanvasWriteRequest(VaultRootRequest):
    relative_path: str = Field(min_length=1, max_length=4096)
    canvas: dict[str, Any] = Field(default_factory=dict)
    expected_hash: str | None = Field(default=None, min_length=40, max_length=128)


class VaultSearchRequest(VaultRootRequest):
    query: str = Field(min_length=1, max_length=256)


class VaultWriteRequest(VaultRootRequest):
    relative_path: str = Field(min_length=1, max_length=4096)
    content: str = Field(min_length=0, max_length=16 * 1024 * 1024)
    expected_hash: str | None = Field(default=None, min_length=64, max_length=64)


class VaultBackupsRequest(VaultRootRequest):
    relative_path: str = Field(min_length=1, max_length=4096)


class VaultRestoreRequest(VaultRootRequest):
    relative_path: str = Field(min_length=1, max_length=4096)
    backup_name: str = Field(min_length=1, max_length=256)


class PlannerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=512)


class EvidenceAnchorRequest(BaseModel):
    """Create a content-addressed EvidenceAnchor pinning raw source content.

    ``locator`` is a free-form dict (page / block / char-region / timestamp)
    describing where in the raw source the evidence lives.
    """

    model_config = ConfigDict(extra="forbid")

    raw_sha256: str = Field(min_length=40, max_length=128)
    source_revision: str = Field(min_length=1, max_length=512)
    locator: dict[str, Any] = Field(default_factory=dict)


class WorkspaceIntakeResult(BaseModel):
    """Ordinary product response without persistence or command identifiers."""

    model_config = ConfigDict(extra="forbid")

    source_type: Literal["file", "web", "github_repository"]
    requires_human_review: bool
    file_name: str | None = None
    format: str | None = None
    engine: str | None = None
    content_preview: str | None = None
    char_count: int | None = Field(default=None, ge=0)
    raw_sha256: str | None = None
    source_count: int | None = Field(default=None, ge=0)
    claim_count: int | None = Field(default=None, ge=0)
    evidence_count: int | None = Field(default=None, ge=0)


def _product_intake_result(result: dict[str, Any]) -> WorkspaceIntakeResult:
    content = result.get("content")
    try:
        return WorkspaceIntakeResult(
            source_type=result.get("source_type"),
            requires_human_review=result.get("requires_human_review"),
            file_name=result.get("file_name"),
            format=result.get("format"),
            engine=result.get("engine"),
            content_preview=content[:400] if isinstance(content, str) and content.strip() else None,
            char_count=result.get("char_count"),
            raw_sha256=result.get("raw_sha256"),
            source_count=result.get("source_count"),
            claim_count=result.get("claim_count"),
            evidence_count=result.get("evidence_count"),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail="workspace intake result is unavailable") from exc


class _Command(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: str = Field(min_length=1, max_length=128)


class PromoteResearchCommand(_Command):
    """Caller intent; reviewer identity is deliberately not a client field."""

    package_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class PromoteResearchSourceCommand(_Command):
    source: str = Field(min_length=1, max_length=2048)


class StartLearningCommand(_Command):
    unit_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class RecordPracticeCommand(_Command):
    artifact_id: str = Field(min_length=1)
    quality: int = Field(ge=0, le=5)


class SourceLearningCommand(_Command):
    source: str = Field(min_length=1, max_length=2048)


class SourcePracticeCommand(_Command):
    source: str = Field(min_length=1, max_length=2048)
    quality: int = Field(ge=0, le=5)


class RuntimeApprovalCommand(_Command):
    title: str = Field(min_length=1, max_length=512)


def _local_principal(request: Request) -> dict[str, str]:
    """Trust only direct loopback requests in the local-first workspace."""
    _require_local_request(request)
    return {"subject": "local-workspace", "role": "local"}


def _command_error(action):
    try:
        return action()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_class=FileResponse)
def workspace_page() -> FileResponse:
    return FileResponse(
        WORKSPACE_UI_ROOT / "index.html",
        media_type="text/html",
        headers=WORKSPACE_SECURITY_HEADERS,
    )


@router.get("/assets/{asset_name}", response_class=FileResponse)
def workspace_asset(
    asset_name: Literal["styles.css", "osui-v3.css", "osui-production.css", "app.js", "production-ui.js", "pdf-loader.mjs", "pdf.mjs", "pdf.worker.mjs"],
) -> FileResponse:
    media_type = "text/css" if asset_name.endswith(".css") else "text/javascript"
    return FileResponse(
        WORKSPACE_UI_ROOT / "assets" / asset_name,
        media_type=media_type,
        headers=WORKSPACE_SECURITY_HEADERS,
    )


@router.get("/api/diagnostics")
def workspace_diagnostics() -> dict[str, object]:
    from app.main import diagnostics

    return diagnostics()


@router.get("/api/status")
def workspace_status(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.workspace_status(db_path=DB_PATH))


@router.get("/api/pdf/{content_key}")
def workspace_pdf(content_key: str, request: Request) -> Response:
    """Serve original PDF bytes to the PDF.js reader by content key (sha256:).

    Content-addressed and read-only: the reader never sees the storage path,
    and empty/oversized/non-sha256 keys are rejected (fail-closed). Only valid
    PDF byte content is served (application/pdf).
    """
    _local_principal(request)
    try:
        blob = resolve_pdf_bytes(PDF_ROOT, content_key)
    except PdfServeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=blob, media_type="application/pdf")


@router.post("/api/evidence/anchor")
def workspace_create_anchor(payload: EvidenceAnchorRequest, request: Request) -> dict[str, object]:
    """Create a content-addressed EvidenceAnchor from a PDF selection.

    Accepts {raw_sha256, source_revision, locator} and returns the stable
    anchor_id so the reader can later jump back to the pinned content.
    """
    _local_principal(request)
    return _command_error(
        lambda: _do_create_anchor(payload)
    )


def _do_create_anchor(payload: EvidenceAnchorRequest) -> dict[str, object]:
    anchor: EvidenceAnchor = build_evidence_anchor(
        raw_sha256=payload.raw_sha256,
        source_revision=payload.source_revision,
        locator=payload.locator,
    )
    store_evidence_anchor(DB_PATH, anchor)
    return {"anchor_id": anchor.anchor_id, "locator": payload.locator}


@router.get("/api/evidence/anchor/{anchor_id}")
def workspace_get_anchor(anchor_id: str, request: Request) -> dict[str, object]:
    """Resolve a stored EvidenceAnchor for jump-back from Claim/Evidence views."""
    _local_principal(request)
    return _command_error(lambda: _do_get_anchor(anchor_id))


def _do_get_anchor(anchor_id: str) -> dict[str, object]:
    anchor: EvidenceAnchor | None = resolve_evidence_anchor(DB_PATH, anchor_id)
    if anchor is None:
        raise HTTPException(status_code=404, detail=f"anchor not found: {anchor_id}")
    return {
        "anchor_id": anchor.anchor_id,
        "raw_sha256": anchor.raw_sha256,
        "source_revision": anchor.source_revision,
        "locator": anchor.locator,
    }


@router.get("/api/evidence/bundles")
def workspace_bundle_summaries(limit: int = 50) -> dict[str, object]:
    """List compact persisted bundle summaries without exposing source paths."""
    try:
        return {"items": list_bundle_summaries(db_path=DB_PATH, limit=limit)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid bundle summary limit") from exc


@router.get("/api/evidence/bundles/{bundle_id}/inspection")
def workspace_bundle_inspection(bundle_id: str) -> dict[str, object]:
    """Read a persisted EvidenceBundle with its human-review and version history."""
    try:
        return get_bundle_inspection(bundle_id, db_path=DB_PATH)
    except EvidenceBundleError as exc:
        raise HTTPException(status_code=404, detail="evidence bundle inspection is unavailable") from exc



@router.get("/api/evidence/anchors")
def list_evidence_anchors_route(
    limit: int = 50, cursor: str | None = None
) -> dict[str, object]:
    """List a bounded, cursor-paginated Evidence-anchor projection."""
    try:
        anchors, next_cursor = list_evidence_anchor_page(
            DB_PATH, limit=limit, cursor=cursor
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid evidence anchor page") from exc
    items = [
        {
            "anchor_id": a.anchor_id,
            "raw_sha256": a.raw_sha256,
            "source_revision": a.source_revision,
            "locator": a.locator,
        }
        for a in anchors
    ]
    return {"count": len(items), "items": items, "next_cursor": next_cursor}

@router.post("/api/vault/inspect")
def workspace_vault_inspect(payload: VaultRootRequest, request: Request) -> dict[str, object]:
    """Inspect an explicitly selected Vault without writing to it."""
    _local_principal(request)
    return _command_error(lambda: vault.inspect_vault(root=payload.root, store=DB_PATH))


@router.post("/api/vault/file")
def workspace_vault_file(payload: VaultFileRequest, request: Request) -> dict[str, object]:
    """Read one Markdown/Canvas file through the approved-root boundary."""
    _local_principal(request)
    return _command_error(
        lambda: vault.read_file(
            root=payload.root, store=DB_PATH, relative_path=payload.relative_path
        )
    )


@router.post("/api/vault/search")
def workspace_vault_search(payload: VaultSearchRequest, request: Request) -> dict[str, object]:
    """Search the selected Vault locally without exposing absolute paths."""
    _local_principal(request)
    return _command_error(
        lambda: vault.search_vault(root=payload.root, store=DB_PATH, query=payload.query)
    )


@router.post("/api/vault/canvas/read")
def workspace_vault_canvas_read(payload: VaultFileRequest, request: Request) -> dict[str, object]:
    """AXW-043B: read + validate a JSON Canvas document (unknown fields kept)."""
    _local_principal(request)
    return _command_error(
        lambda: vault.read_canvas(
            root=payload.root, store=DB_PATH, relative_path=payload.relative_path
        )
    )


@router.post("/api/vault/canvas/write")
def workspace_vault_canvas_write(payload: VaultCanvasWriteRequest, request: Request) -> dict[str, object]:
    """AXW-043B: validate + C3-safe write of a JSON Canvas document."""
    _local_principal(request)
    try:
        return vault.write_canvas(
            root=payload.root,
            store=DB_PATH,
            relative_path=payload.relative_path,
            canvas=payload.canvas,
            expected_hash=payload.expected_hash,
        )
    except vault.VaultWorkbenchConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "current_hash": exc.current_hash},
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/vault/write")
def workspace_vault_write(payload: VaultWriteRequest, request: Request) -> dict[str, object]:
    """H3 C4-safe write: expected-hash optimistic lock + atomic replace + backup.

    Returns 409 (fail-closed) when expected_hash does not match the current
    on-disk source hash — the caller must re-read before retrying.
    """
    _local_principal(request)
    try:
        return vault.write_file(
            root=payload.root,
            store=DB_PATH,
            relative_path=payload.relative_path,
            content=payload.content,
            expected_hash=payload.expected_hash,
        )
    except vault.VaultWorkbenchConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "current_hash": exc.current_hash},
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/vault/backups")
def workspace_vault_backups(
    payload: VaultBackupsRequest, request: Request
) -> dict[str, object]:
    """List revertible backups for one Vault file (newest first)."""
    _local_principal(request)
    return vault.list_backups(store=DB_PATH, relative_path=payload.relative_path)


@router.post("/api/vault/restore")
def workspace_vault_restore(
    payload: VaultRestoreRequest, request: Request
) -> dict[str, object]:
    """Restore a backup over the Vault file; current state is snapshotted first."""
    _local_principal(request)
    return _command_error(
        lambda: vault.restore_backup(
            root=payload.root,
            store=DB_PATH,
            relative_path=payload.relative_path,
            backup_name=payload.backup_name,
        )
    )


@router.post("/api/planner/preview")
def workspace_planner_preview(payload: PlannerRequest, request: Request) -> dict[str, object]:
    """Preview only the bounded, explicitly supported planner grammar."""
    _local_principal(request)
    from app.agent.planner import plan_goal

    steps = plan_goal(payload.goal)
    return {
        "schema_version": "v1",
        "status": "supported" if steps else "unsupported",
        "execution": "preview_only",
        "steps": steps,
    }


def _planner_public_result(step: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Return only bounded, user-facing fields from a low-risk planner tool."""
    public = {
        "tool": result.get("tool"),
        "status": result.get("status"),
        "risk_level": result.get("risk_level"),
    }
    if step["tool"] == "file_read":
        public["path"] = step["path"]
        content = result.get("content")
        if isinstance(content, str):
            public["content_preview"] = content[:400]
    elif step["tool"] == "kb_search":
        public["count"] = result.get("count", 0)
    if result.get("error"):
        public["error"] = str(result["error"])
    return public


@router.post("/api/planner/execute")
def workspace_planner_execute(payload: PlannerRequest, request: Request) -> dict[str, object]:
    """Execute only the planner's explicit, read-only project/knowledge grammar."""
    _local_principal(request)
    from app.agent.planner import plan_goal
    from app.tools.registry import run_tool

    steps = plan_goal(payload.goal)
    if not steps:
        return {
            "schema_version": "v1",
            "status": "unsupported",
            "execution": "bounded_read_only",
            "results": [],
        }
    results = []
    for step in steps:
        if step["tool"] == "file_read":
            tool_payload = {"path": step["path"]}
        elif step["tool"] == "kb_search":
            tool_payload = {"query": step["query"], "top_k": step["top_k"]}
        else:
            return {
                "schema_version": "v1",
                "status": "blocked",
                "execution": "bounded_read_only",
                "results": [],
            }
        result = run_tool(step["tool"], tool_payload, dry_run=False)
        results.append(_planner_public_result(step, result))
    status = "completed" if all(item["status"] == "ok" for item in results) else "blocked"
    return {
        "schema_version": "v1",
        "status": status,
        "execution": "bounded_read_only",
        "results": results,
    }


def _bff_error(action):
    try:
        return action()
    except BFFNotFoundError as exc:
        raise HTTPException(status_code=404, detail="workspace object was not found") from exc
    except (BFFUnavailableError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="workspace projection is unavailable") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/v1/home")
def workspace_bff_home(request: Request) -> dict[str, object]:
    """Read-only v1 home projection; persistence IDs never cross this boundary."""
    _local_principal(request)
    return _bff_error(lambda: bff.home(db_path=DB_PATH))


@router.get("/api/v1/activity")
def workspace_bff_activity(
    request: Request, limit: int = 20, cursor: str | None = None
) -> dict[str, object]:
    """Stable cursor-paginated activity projection."""
    _local_principal(request)
    return _bff_error(lambda: bff.activity(db_path=DB_PATH, limit=limit, cursor=cursor))


@router.get("/api/v1/objects/{public_ref}")
def workspace_bff_object(public_ref: str, request: Request) -> dict[str, object]:
    """Resolve only opaque public references to read-only object DTOs."""
    _local_principal(request)
    return _bff_error(lambda: bff.object_by_ref(db_path=DB_PATH, reference=public_ref))


@router.get("/api/_desktop/ready")
def desktop_readiness(request: Request) -> dict[str, str]:
    launch_token = os.getenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN") or os.getenv("COGNITIVE_DESKTOP_LAUNCH_TOKEN", "")
    if not launch_token:
        raise HTTPException(status_code=404, detail="not found")
    supplied_token = request.headers.get("x-archeaxis-launch-token", "")
    if not hmac.compare_digest(supplied_token, launch_token):
        raise HTTPException(status_code=403, detail="invalid desktop launch token")
    return {
        "schema_version": "v1",
        "product": "ArcheAxis Knowledge",
        "workspace": "Human–AI Learning Workspace",
    }


@router.post(
    "/api/intake/url",
    response_model=WorkspaceIntakeResult,
    response_model_exclude_none=True,
)
def intake_url(payload: IntakeURL, request: Request) -> WorkspaceIntakeResult:
    _local_principal(request)
    return _command_error(
        lambda: _product_intake_result(service.intake_url(url=payload.url, db_path=DB_PATH))
    )


@router.post(
    "/api/intake/upload",
    response_model=WorkspaceIntakeResult,
    response_model_exclude_none=True,
)
async def intake_upload(
    request: Request,
    file: UploadFile = File(...),
) -> WorkspaceIntakeResult:
    _local_principal(request)
    try:
        content = await file.read(service.MAX_INTAKE_UPLOAD_BYTES + 1)
        if len(content) > service.MAX_INTAKE_UPLOAD_BYTES:
            raise ValueError("uploaded file exceeds the 25 MB local intake limit")
        return _product_intake_result(
            service.intake_upload(
                file_name=file.filename or "",
                content=content,
                db_path=DB_PATH,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/jobs")
def workspace_jobs(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.workspace_jobs(db_path=DB_PATH))


@router.get("/api/library")
def workspace_library(request: Request) -> dict[str, object]:
    """List retained originals as a path-free Source Archive projection."""
    _local_principal(request)
    return _command_error(lambda: service.workspace_library(db_path=DB_PATH))


@router.get("/api/library/{raw_sha256}/content", response_class=FileResponse)
def workspace_library_content(raw_sha256: str, request: Request) -> FileResponse:
    """Open one retained original by content identity, never by caller path."""
    _local_principal(request)
    try:
        path, safe_name, media_type = service.source_archive_content(
            raw_sha256=raw_sha256, db_path=DB_PATH
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type=media_type,
        filename=safe_name,
        content_disposition_type="inline",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


@router.get("/api/delivery")
def workspace_delivery(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.workspace_delivery(db_path=DB_PATH))


def _audit_snapshot() -> tuple[str, dict[str, object]]:
    payload = {
        "schema_version": "v1",
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "projection": service.workspace_delivery(db_path=DB_PATH),
    }
    fingerprint_payload = {key: value for key, value in payload.items() if key != "observed_at"}
    event_id = hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:24]
    return event_id, payload


def _audit_event(*, event_id: str, payload: dict[str, object]) -> str:
    return (
        f"id: {event_id}\n"
        "event: audit\n"
        "data: "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "\n\n"
    )


@router.get("/api/audit/stream")
def workspace_audit_stream(request: Request, once: bool = False) -> StreamingResponse:
    """Stream durable projection snapshots with resumable event fingerprints."""
    _local_principal(request)
    last_event_id = request.headers.get("last-event-id", "").strip()

    def events():
        event_id, payload = _audit_snapshot()
        if event_id == last_event_id:
            yield ": heartbeat\n\n"
        else:
            yield _audit_event(event_id=event_id, payload=payload)
        if once:
            return
        deadline = time.monotonic() + 25.0
        previous_id = event_id
        while time.monotonic() < deadline:
            time.sleep(1.0)
            event_id, payload = _audit_snapshot()
            if event_id == previous_id:
                yield ": heartbeat\n\n"
                continue
            previous_id = event_id
            yield _audit_event(event_id=event_id, payload=payload)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/api/delivery/dispatch", dependencies=[Depends(_require_desktop_write_request)])
def dispatch_delivery(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.dispatch_delivery_once(db_path=DB_PATH))


@router.post("/api/delivery/retry", dependencies=[Depends(_require_desktop_write_request)])
def retry_delivery(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.retry_failed_delivery(db_path=DB_PATH))


@router.get("/api/research")
def workspace_research_queue(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.research_review_queue(db_path=DB_PATH))


@router.get("/api/knowledge")
def workspace_knowledge(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.workspace_knowledge(db_path=DB_PATH))


@router.get("/api/learning")
def workspace_learning(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.workspace_learning(db_path=DB_PATH))


@router.get("/api/evolution")
def workspace_evolution(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.workspace_evolution(db_path=DB_PATH))


@router.get("/api/lifecycle")
def workspace_lifecycle(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.workspace_lifecycle(db_path=DB_PATH))


@router.get("/api/runtime/knowledge")
def workspace_runtime_knowledge(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.workspace_runtime_knowledge(db_path=DB_PATH))


@router.get("/api/runtime/candidates")
def workspace_runtime_candidates(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.workspace_runtime_candidates(db_path=DB_PATH))


@router.post("/api/knowledge/start-learning")
def start_learning_from_knowledge(command: SourceLearningCommand, request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(
        lambda: service.start_learning_source(
            command_id=command.command_id, source=command.source, db_path=DB_PATH
        )
    )


@router.post("/api/learning/practice")
def practice_from_learning(command: SourcePracticeCommand, request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(
        lambda: service.record_practice_source(
            command_id=command.command_id,
            source=command.source,
            quality=command.quality,
            db_path=DB_PATH,
        )
    )


@router.post("/api/runtime/approve", dependencies=[Depends(_require_desktop_write_request)])
def approve_runtime_candidate(command: RuntimeApprovalCommand, request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(
        lambda: service.approve_runtime_title(
            command_id=command.command_id, title=command.title, db_path=DB_PATH
        )
    )


@router.post("/api/runtime/deprecate", dependencies=[Depends(_require_desktop_write_request)])
def deprecate_runtime_asset(command: RuntimeApprovalCommand, request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(
        lambda: service.deprecate_runtime_title(
            command_id=command.command_id, title=command.title, db_path=DB_PATH
        )
    )


@router.get("/api/jobs/{job_id}")
def workspace_job(job_id: str, request: Request) -> dict[str, object]:
    _local_principal(request)
    try:
        return service.intake_job(job_id=job_id, db_path=DB_PATH)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/commands/promote-research")
def promote_research(command: PromoteResearchCommand, request: Request) -> dict[str, Any]:
    principal = _local_principal(request)
    return _command_error(
        lambda: service.promote_research(
            command_id=command.command_id, package_id=command.package_id,
            reviewer_id=principal["subject"], rationale=command.rationale, db_path=DB_PATH,
        )
    )


@router.post("/api/research/approve", dependencies=[Depends(_require_desktop_write_request)])
def promote_research_source(command: PromoteResearchSourceCommand, request: Request) -> dict[str, Any]:
    principal = _local_principal(request)
    result = _command_error(lambda: service.promote_research_source(
        command_id=command.command_id, source=command.source, reviewer_id=principal["subject"],
        rationale="local workspace governed research approval", db_path=DB_PATH,
    ))
    return {"source": command.source, "status": result.get("status", "candidate")}


@router.post("/api/commands/start-learning")
def start_learning(command: StartLearningCommand, request: Request) -> dict[str, Any]:
    principal = _local_principal(request)
    return _command_error(
        lambda: service.start_learning(
            command_id=command.command_id, unit_id=command.unit_id,
            reviewer_id=principal["subject"], rationale=command.rationale, db_path=DB_PATH,
        )
    )


@router.post("/api/commands/record-practice")
def record_practice(command: RecordPracticeCommand, request: Request) -> dict[str, Any]:
    _local_principal(request)
    return _command_error(
        lambda: service.record_practice(
            command_id=command.command_id, artifact_id=command.artifact_id,
            quality=command.quality, db_path=DB_PATH,
        )
    )


@router.get("/api/cases/{artifact_id}")
def workspace_case(artifact_id: str, request: Request) -> dict[str, Any]:
    _local_principal(request)
    return _command_error(lambda: service.case_audit(artifact_id=artifact_id, db_path=DB_PATH))


# ---------------------------------------------------------------------------
# AXW-094A/B + AXW-096C operational surface: open-exchange export, verifiable
# backup/restore, and controllable batch import. These make the library-level
# implementations reachable from the Workspace API (022B lesson: a feature
# that cannot be reached is not a feature).
# ---------------------------------------------------------------------------

class ExchangeExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="exchange", min_length=1, max_length=128)
    overwrite: bool = False


class BackupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="backup", min_length=1, max_length=128)


class BackupRestoreRequest(BackupRequest):
    dry_run: bool = True


class BatchImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str = Field(min_length=1, max_length=128)
    source_dir: str = Field(min_length=1, max_length=4096)
    pattern: str = Field(default="**/*", min_length=1, max_length=512)
    max_files: int = Field(default=200, ge=1, le=10_000)
    rate_per_second: float | None = Field(default=None, gt=0)
    max_retries: int = Field(default=1, ge=0, le=5)


def _exchange_root() -> Path:
    return resolve_runtime_path("data") / "exchange"


def _workspace_domain_root(domain: str, fallback: Path) -> Path:
    """Return a configured four-library domain without making setup mandatory."""
    try:
        from app.setup.setup_status import manifest_path
        from shared.workspace_manifest import load

        return Path(load(manifest_path()).domains[domain].path)
    except (KeyError, OSError, ValueError):
        return fallback


def _backup_root() -> Path:
    return resolve_runtime_path("data") / "backups"


def _batch_ledger(batch_id: str) -> Path:
    return resolve_runtime_path("data") / "batch" / f"{batch_id}.jsonl"


# Active background batch controllers (AXW-096C pause/resume/shutdown).
_ACTIVE_BATCHES: dict[str, Any] = {}
_BATCH_LOCK = threading.Lock()


@router.post("/api/exchange/export")
def workspace_exchange_export(payload: ExchangeExportRequest, request: Request) -> dict[str, Any]:
    """Export raw/evidence/learning artifacts as an open exchange directory."""
    _local_principal(request)
    from app.exchange.export import export_knowledge_exchange, extract_exchange_items

    def run() -> dict[str, Any]:
        data_root = resolve_runtime_path("data")
        items = extract_exchange_items(
            raw_root=_workspace_domain_root("source_archive", data_root),
            evidence_db=DB_PATH,
            learning_root=_workspace_domain_root("human_learning_vault", data_root / "learning"),
            ai_asset_root=_workspace_domain_root("ai_asset_vault", data_root / "ai-assets"),
        )
        destination = _exchange_root() / payload.name
        manifest = export_knowledge_exchange(
            destination=destination,
            overwrite=payload.overwrite,
            **items,
        )
        return {
            "destination": str(destination),
            "item_count": manifest["item_count"],
            "manifest_sha256": manifest["manifest_sha256"],
        }

    return _command_error(run)


@router.get("/api/exchange/verify")
def workspace_exchange_verify(request: Request, name: str = "exchange") -> dict[str, Any]:
    """Verify an exchange directory (hash + coverage + schema)."""
    _local_principal(request)
    from app.exchange.export import verify_export

    return _command_error(lambda: verify_export(_exchange_root() / name))


@router.post("/api/backup/create", dependencies=[Depends(_require_desktop_write_request)])
def workspace_backup_create(payload: BackupRequest, request: Request) -> dict[str, Any]:
    """Snapshot the runtime data dir into a verifiable backup."""
    _local_principal(request)
    from app.exchange.backup import create_backup

    def run() -> dict[str, Any]:
        data_root = resolve_runtime_path("data")
        data_root.mkdir(parents=True, exist_ok=True)
        manifest = create_backup(
            source=data_root,
            backup_dir=_backup_root() / payload.name,
        )
        return {"destination": str(_backup_root() / payload.name), "file_count": manifest["file_count"]}

    return _command_error(run)


@router.get("/api/backup/verify")
def workspace_backup_verify(request: Request, name: str = "backup") -> dict[str, Any]:
    """Verify a backup snapshot (hashes + completeness + version)."""
    _local_principal(request)
    from app.exchange.backup import verify_backup

    return _command_error(lambda: verify_backup(_backup_root() / name))


@router.post("/api/backup/restore")
def workspace_backup_restore(payload: BackupRestoreRequest, request: Request) -> dict[str, Any]:
    """Restore a backup into the runtime data dir (dry-run by default)."""
    _local_principal(request)
    from app.exchange.backup import restore_backup

    def run() -> dict[str, Any]:
        return restore_backup(
            backup_dir=_backup_root() / payload.name,
            target=resolve_runtime_path("data"),
            dry_run=payload.dry_run,
        )

    return _command_error(run)


@router.post("/api/batch/import")
def workspace_batch_import(payload: BatchImportRequest, request: Request) -> dict[str, Any]:
    """Start a controlled batch import in the background.

    Returns immediately with the batch id; progress is polled via
    GET /api/batch/{id}/status and the batch can be paused, resumed or
    safely shut down mid-run (AXW-096C: no orphan workers — daemon
    threads die with the process, checkpoint ledger survives).
    """
    _local_principal(request)
    from app.ingestion.batch_controller import BatchImportController
    from app.ingestion.multi_format import convert_directory_resumable

    if payload.batch_id in _ACTIVE_BATCHES:
        raise HTTPException(status_code=409, detail=f"batch already active: {payload.batch_id}")

    controller = BatchImportController(
        checkpoint_path=_batch_ledger(payload.batch_id),
        max_retries=payload.max_retries,
    )
    source_root = Path(payload.source_dir)
    if not source_root.is_dir():
        raise HTTPException(status_code=400, detail=f"source_dir not found: {source_root}")
    files = sorted(p for p in source_root.rglob(payload.pattern) if p.is_file())[: payload.max_files]
    rel_tasks = [p.relative_to(source_root).as_posix() for p in files]
    if not rel_tasks:
        raise HTTPException(status_code=400, detail="no files matched the import pattern")
    controller.add_tasks(rel_tasks)

    artifacts_root = resolve_runtime_path("data") / "batch-artifacts" / payload.batch_id
    artifacts_root.mkdir(parents=True, exist_ok=True)

    def convert_worker(rel_path: str) -> dict[str, str]:
        result = convert_directory_resumable(
            directory=source_root,
            manifest_path=artifacts_root / "manifest.json",
            output_dir=artifacts_root,
            pattern=f"**/{rel_path}",
            max_files=1,
        )
        return {"result_digest": f"converted:{result.get('processed', 0)}"}

    def run_batch() -> None:
        try:
            controller.run(convert_worker, max_concurrent=2, rate_per_second=payload.rate_per_second)
        finally:
            with _BATCH_LOCK:
                _ACTIVE_BATCHES.pop(payload.batch_id, None)

    with _BATCH_LOCK:
        _ACTIVE_BATCHES[payload.batch_id] = controller
    thread = threading.Thread(target=run_batch, name=f"batch-{payload.batch_id}", daemon=True)
    thread.start()

    return {
        "batch_id": payload.batch_id,
        "state": "running",
        "total": controller.status()["total"],
        "note": "poll /api/batch/{id}/status for progress; POST pause/resume/shutdown to control",
    }


@router.get("/api/batch/{batch_id}/status")
def workspace_batch_status(batch_id: str, request: Request) -> dict[str, Any]:
    """Read a batch ledger (results + attempts + counts)."""
    _local_principal(request)
    from app.ingestion.batch_controller import BatchImportController

    with _BATCH_LOCK:
        active = _ACTIVE_BATCHES.get(batch_id)
    if active is not None:
        return active.status()
    ledger = _batch_ledger(batch_id)
    if not ledger.is_file():
        raise HTTPException(status_code=404, detail=f"no such batch: {batch_id}")
    return BatchImportController.from_checkpoint(ledger).status()


@router.post("/api/batch/{batch_id}/pause")
def workspace_batch_pause(batch_id: str, request: Request) -> dict[str, Any]:
    """Pause task pickup; in-flight tasks finish, nothing is lost."""
    _local_principal(request)
    with _BATCH_LOCK:
        active = _ACTIVE_BATCHES.get(batch_id)
    if active is None:
        raise HTTPException(status_code=404, detail=f"no active batch: {batch_id}")
    active.pause()
    return {"batch_id": batch_id, "state": active.status()["state"]}


@router.post("/api/batch/{batch_id}/resume")
def workspace_batch_resume(batch_id: str, request: Request) -> dict[str, Any]:
    """Resume a paused batch."""
    _local_principal(request)
    with _BATCH_LOCK:
        active = _ACTIVE_BATCHES.get(batch_id)
    if active is None:
        raise HTTPException(status_code=404, detail=f"no active batch: {batch_id}")
    active.resume()
    return {"batch_id": batch_id, "state": active.status()["state"]}


@router.post("/api/batch/{batch_id}/shutdown")
def workspace_batch_shutdown(batch_id: str, request: Request) -> dict[str, Any]:
    """Safe exit: stop accepting tasks, join workers, persist the ledger."""
    _local_principal(request)
    with _BATCH_LOCK:
        active = _ACTIVE_BATCHES.get(batch_id)
    if active is None:
        raise HTTPException(status_code=404, detail=f"no active batch: {batch_id}")
    active.shutdown()
    with _BATCH_LOCK:
        _ACTIVE_BATCHES.pop(batch_id, None)
    return {"batch_id": batch_id, "state": "shutdown"}
