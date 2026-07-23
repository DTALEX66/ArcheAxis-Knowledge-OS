"""Public boundary for the governed Cognitive Workspace."""
from __future__ import annotations

import hmac
import os
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.workspace import service
from shared.storage import DB_PATH

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


def _require_local_request(request: Request) -> None:
    peer = request.client.host if request.client else ""
    if peer != "testclient" and not _is_loopback_host(peer):
        raise HTTPException(status_code=403, detail="workspace is available only locally")
    host = request.headers.get("host", "")
    if not _is_loopback_host(host):
        raise HTTPException(status_code=403, detail="workspace host must be loopback")
    if request.headers.get("sec-fetch-site", "").casefold() == "cross-site":
        raise HTTPException(status_code=403, detail="cross-site workspace request rejected")
    origin = request.headers.get("origin", "")
    if origin and urlsplit(origin).netloc.casefold() != host.casefold():
        raise HTTPException(status_code=403, detail="workspace origin must be same-origin")


router = APIRouter(
    prefix=WORKSPACE_PREFIX,
    tags=["workspace"],
    dependencies=[Depends(_require_local_request)],
)


class IntakeURL(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2048)


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
def workspace_asset(asset_name: Literal["styles.css", "app.js"]) -> FileResponse:
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


@router.get("/api/_desktop/ready")
def desktop_readiness(request: Request) -> dict[str, str]:
    launch_token = os.getenv("COGNITIVE_DESKTOP_LAUNCH_TOKEN", "")
    if not launch_token:
        raise HTTPException(status_code=404, detail="not found")
    supplied_token = request.headers.get("x-archeaxis-launch-token", "")
    if not hmac.compare_digest(supplied_token, launch_token):
        raise HTTPException(status_code=403, detail="invalid desktop launch token")
    return {
        "schema_version": "v1",
        "product": "ArcheAxis OS",
        "workspace": "ArcheAxis Cognitive Workspace",
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


@router.get("/api/research")
def workspace_research_queue(request: Request) -> dict[str, object]:
    _local_principal(request)
    return _command_error(lambda: service.research_review_queue(db_path=DB_PATH))


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


@router.post("/api/research/approve")
def promote_research_source(command: PromoteResearchSourceCommand, request: Request) -> dict[str, Any]:
    principal = _local_principal(request)
    return _command_error(lambda: service.promote_research_source(
        command_id=command.command_id, source=command.source, reviewer_id=principal["subject"],
        rationale="", db_path=DB_PATH,
    ))


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
