"""Composite quality/evidence API absorbed from Obsidian-Assistance."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from shared.accuracy_benchmark import evaluate_golden_pairs
from shared.content_quality import audit_markdown_quality
from shared.evidence_verification import match_evidence, verification_status
from shared.oer_crosswalk import build_crosswalk
from shared.processing_manifest import ProcessingManifest

router = APIRouter(tags=["quality"])
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class QualityRequest(BaseModel):
    action: str = Field(
        description="accuracy|manifest|evidence_match|verification|oer_crosswalk|content_audit"
    )
    content: str = ""
    golden_dir: str = ""
    manifest_path: str = ""
    terms: list[str] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    known_targets: list[str] = Field(default_factory=list)


def _project_path(raw: str, label: str) -> Path:
    if not raw:
        raise HTTPException(status_code=400, detail=f"{label} is required")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = _PROJECT_ROOT / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(_PROJECT_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{label} must be inside project root") from exc
    return resolved


@router.post("/quality")
def quality(request: QualityRequest):
    """Run one conservative quality action through a single stable endpoint."""
    if request.action == "accuracy":
        return evaluate_golden_pairs(_project_path(request.golden_dir, "golden_dir"))
    if request.action == "manifest":
        return ProcessingManifest(_project_path(request.manifest_path, "manifest_path")).summary()
    if request.action == "evidence_match":
        return match_evidence(request.terms, request.candidates)
    if request.action == "verification":
        return verification_status(request.evidence)
    if request.action == "oer_crosswalk":
        return build_crosswalk(request.content, request.terms)
    if request.action == "content_audit":
        targets = set(request.known_targets) if request.known_targets else None
        return audit_markdown_quality(request.content, targets)
    raise HTTPException(status_code=400, detail=f"unsupported quality action: {request.action}")
