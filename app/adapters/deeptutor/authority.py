"""DeepTutor downstream-product authority firewall and projection builder."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


class AuthorityBoundaryError(ValueError):
    """Raised when a downstream product attempts to write ArcheAxis truth."""


_TRUTH_FIELDS = {
    "verified",
    "verification_status",
    "knowledge_status",
    "machine_level",
    "machine_competence",
    "human_mastery",
    "human_learning_state",
    "claim_status",
}
_ALLOWED_EVENT_FIELDS = {
    "event_id",
    "learner_id",
    "source_ref",
    "kind",
    "outcome",
    "recorded_at",
}


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


class DeepTutorAuthorityAdapter:
    """Build/delete a derived DeepTutor projection and accept proposal events only."""

    def __init__(self, projection_root: str | Path) -> None:
        self.projection_root = Path(projection_root)

    def rebuild_projection(self, records: list[dict[str, object]]) -> dict[str, object]:
        ordered = sorted(records, key=lambda record: str(record.get("source_id", "")))
        content = _canonical_bytes({"schema_version": "archeaxis/deeptutor-projection/v1", "records": ordered})
        projection_sha256 = hashlib.sha256(content).hexdigest()
        projection_path = self.projection_root / "authority-projection.json"
        _atomic_write(projection_path, content)
        manifest = {
            "schema_version": "archeaxis/deeptutor-projection-manifest/v1",
            "data_scope": "derived-rebuildable",
            "record_count": len(ordered),
            "projection_file": projection_path.name,
            "projection_sha256": projection_sha256,
            "authority": "ArcheAxis",
        }
        _atomic_write(self.projection_root / "projection-manifest.json", _canonical_bytes(manifest))
        return manifest

    def delete_projection(self) -> None:
        """Delete only this adapter's replaceable projection files."""
        for name in ("authority-projection.json", "projection-manifest.json"):
            path = self.projection_root / name
            path.unlink(missing_ok=True)

    def accept_learning_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        asserted = sorted(_TRUTH_FIELDS.intersection(payload))
        if asserted:
            raise AuthorityBoundaryError(
                "truth-bearing fields are not accepted from DeepTutor: " + ", ".join(asserted)
            )
        unknown = sorted(set(payload) - _ALLOWED_EVENT_FIELDS)
        if unknown:
            raise AuthorityBoundaryError("unsupported DeepTutor result fields: " + ", ".join(unknown))
        missing = [field for field in ("event_id", "learner_id", "source_ref", "kind", "outcome") if field not in payload]
        if missing:
            raise AuthorityBoundaryError("missing DeepTutor result fields: " + ", ".join(missing))
        if not isinstance(payload["outcome"], dict):
            raise AuthorityBoundaryError("outcome must be an object")
        return {
            "event_id": str(payload["event_id"]),
            "learner_id": str(payload["learner_id"]),
            "source_ref": str(payload["source_ref"]),
            "kind": str(payload["kind"]),
            "outcome": dict(payload["outcome"]),
            "recorded_at": payload.get("recorded_at"),
            "status": "candidate",
        }
