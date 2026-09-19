"""R6 A10 courseware artifact contract tests."""
from __future__ import annotations

import json
from pathlib import Path

from app.contracts.courseware_v1 import CoursewareArtifactV1


def _artifact(**overrides):
    payload = {
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "title": "Source grounded lesson",
        "domain_pack_id": "general",
        "source_ids": ["src-1"],
        "knowledge_ids": ["k-1"],
        "renderer": "native-lesson",
        "renderer_version": "1.0.0",
        "status": "candidate",
        "interactive": True,
    }
    payload.update(overrides)
    return payload


def test_courseware_artifact_preserves_source_and_derived_boundary():
    artifact = CoursewareArtifactV1.model_validate(_artifact(artifact_type="coding_activity"))
    assert artifact.source_ids == ["src-1"]
    assert artifact.derived_only is True
    assert artifact.human_review_required is True


def test_all_courseware_types_are_supported_by_one_contract():
    types = {"lesson", "slide", "quiz", "visual", "simulation", "pbl", "coding_activity", "audio_video"}
    assert {CoursewareArtifactV1.model_validate(_artifact(artifact_type=t)).artifact_type for t in types} == types


def test_versioned_schema_is_present_and_requires_sources():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "packages/contracts/v1/courseware-artifact.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.courseware-artifact/v1"
    assert "source_ids" in schema["required"]
