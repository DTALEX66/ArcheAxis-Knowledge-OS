"""Standard response models — unified API response envelope.

All endpoints return consistent structures:
    Success: {"status":"ok", "data": {...}}
    Error:   {"status":"error", "error":"...", "detail":"..."}
    List:    {"status":"ok", "data": [...], "count": N, "total": N}

Usage:
    from shared.schemas import APIResponse, ListResponse, ErrorResponse
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard success response."""
    status: str = "ok"
    data: T | None = None
    message: str = ""


class ListResponse(BaseModel, Generic[T]):
    """Standard list response with pagination."""
    status: str = "ok"
    data: list[T] = []
    count: int = 0
    total: int = 0
    offset: int = 0
    limit: int = 100


class ErrorResponse(BaseModel):
    """Standard error response."""
    status: str = "error"
    error: str = ""
    detail: str = ""
    code: int = 400


# ── Reusable request models ──────────────────────────────


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    mode: str = "hybrid"  # hybrid | vector | keyword


class PipelineRequest(BaseModel):
    source: str = "text"  # url | text | youtube | file | rss | search
    input: str
    actions: list[str] | None = None
    auto_ingest: bool = True


class PaginationParams(BaseModel):
    offset: int = 0
    limit: int = 50


class IDParam(BaseModel):
    id: str


class DateRangeParams(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    days: int = 7


# ── Domain-specific request models ────────────────────────


class DocumentCreate(BaseModel):
    title: str
    content: str
    source: str = "unknown"
    tags: list[str] = []


class CardCreate(BaseModel):
    title: str
    content: str
    source_ids: list[str] = []
    tags: list[str] = []


class ReviewCreate(BaseModel):
    card_id: str
    quality: int  # 0-5
    error_type: str = ""
    error_detail: str = ""
    source_topic: str = ""


class MKUCreate(BaseModel):
    title: str
    content: str = ""
    unit_type: str = "rule"
    tags: list[str] = []
    confidence: float = 0.5


class EvidenceCreate(BaseModel):
    doc_id: str
    source_type: str = "manual"
    source_path: str = ""
    confidence: str = "medium"
    caption: str = ""


class TranslateRequest(BaseModel):
    card_id: str
    unit_type: str = "rule"
    override_title: str = ""
    override_content: str = ""


class ObsidianScanRequest(BaseModel):
    vault_root: str = ""
    max_files: int = 200


class ObsidianImportRequest(BaseModel):
    vault_root: str = ""
    folders: list[str] = []
    max_files: int = 50


class CanvasCreateRequest(BaseModel):
    name: str
    description: str = ""


class CanvasAddCardRequest(BaseModel):
    object_id: str
    object_type: str = "card"
    x: float = 0
    y: float = 0


class CanvasConnectRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    label: str = ""


class DailyAppendRequest(BaseModel):
    content: str
    day: str = ""
    heading: str = ""


class ExportRequest(BaseModel):
    format: str = "json"  # json | markdown | csv
    tables: list[str] | None = None
