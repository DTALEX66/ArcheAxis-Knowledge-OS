"""Source/Anchor/Provenance V2 contracts and OCFL-compatible export."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.archive.ocfl import export_object, validate_object
from app.contracts.source_anchor_v2 import (
    AnchorV2,
    ProvenanceActivityV2,
    SourceObjectV2,
    TextQuoteSelector,
)


def _source(version: int = 1) -> SourceObjectV2:
    return SourceObjectV2(
        source_id="src-1",
        version=version,
        sha256=hashlib.sha256(b"content").hexdigest(),
        byte_size=7,
        media_type="text/plain",
        rights_status="owned",
        original_retained=True,
        created_at="2026-08-27T00:00:00+00:00",
    )


def test_source_object_requires_fixity_rights_and_original_retention():
    source = _source()
    assert source.sha256 == hashlib.sha256(b"content").hexdigest()
    with pytest.raises(ValidationError):
        SourceObjectV2(
            source_id="src-1",
            version=1,
            sha256="bad",
            byte_size=7,
            media_type="text/plain",
            rights_status="unknown",
            original_retained=False,
            created_at="2026-08-27T00:00:00+00:00",
        )


def test_anchor_becomes_stale_when_source_version_changes():
    anchor = AnchorV2(
        anchor_id="anchor-1",
        source_id="src-1",
        source_version=1,
        selector=TextQuoteSelector(exact="BKT", prefix="关于", suffix="模型"),
        created_at="2026-08-27T00:00:00+00:00",
    )
    assert anchor.state_for(_source(version=1)) == "CURRENT"
    assert anchor.state_for(_source(version=2)) == "STALE"


def test_provenance_is_prov_o_shaped_and_fail_closed():
    activity = ProvenanceActivityV2(
        activity_id="act-1",
        activity_type="conversion",
        used=["src-1@1"],
        generated=["derivative-1"],
        agent="adapter:docling",
        started_at="2026-08-27T00:00:00+00:00",
        ended_at="2026-08-27T00:01:00+00:00",
    )
    assert activity.as_prov()["prov:used"] == ["src-1@1"]
    with pytest.raises(ValidationError):
        ProvenanceActivityV2(
            activity_id="act-bad",
            activity_type="conversion",
            used=[],
            generated=["derivative-1"],
            agent="adapter:docling",
            started_at="2026-08-27T00:00:00+00:00",
            ended_at="2026-08-27T00:01:00+00:00",
        )


def test_ocfl_compatible_export_validates_and_detects_tamper(tmp_path: Path):
    root = tmp_path / "object"
    receipt = export_object(
        root,
        source=_source(),
        content=b"content",
        anchors=[
            AnchorV2(
                anchor_id="anchor-1",
                source_id="src-1",
                source_version=1,
                selector=TextQuoteSelector(exact="content"),
                created_at="2026-08-27T00:00:00+00:00",
            )
        ],
    )
    assert receipt["valid"] is True
    assert validate_object(root)["valid"] is True

    (root / "v1/content/original.bin").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="fixity"):
        validate_object(root)
