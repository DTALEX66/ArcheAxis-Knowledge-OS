"""Governed projections from the learning ledger into workspace Vault domains."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.contracts.v1 import LearningArtifactV1, MachineKnowledgeUnitV1
from shared import knowledge_governance_migration
from shared.approved_paths import ApprovedRoots, ApprovedRootsError
from shared.obsidian_projection import render_learning_artifact, write_projection


def project_learning_artifact(
    artifact_id: str, *, db_path: str | Path, vault_root: str | Path, dry_run: bool = True
) -> dict[str, Any]:
    """Project one explicitly approved learning artifact into a human Vault.

    The artifact remains a candidate by design; its separate card-approval
    event is the governing receipt required before this user-visible projection.
    """
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database, live_wal=True)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT artifact_json FROM knowledge_candidate_learning_artifacts_v1 WHERE id=?",
            (artifact_id,),
        ).fetchone()
        approval = connection.execute(
            "SELECT 1 FROM learning_approval_events_v1 WHERE artifact_id=? AND decision='approved'",
            (artifact_id,),
        ).fetchone()
    if row is None:
        raise ValueError("learning artifact not found")
    if approval is None:
        raise ValueError("learning artifact requires explicit learning approval before projection")
    artifact = LearningArtifactV1.model_validate_json(str(row["artifact_json"]))
    if artifact.artifact_id != artifact_id or artifact.provenance_status != "server_verified":
        raise RuntimeError("learning artifact payload conflicts with governed ledger")
    return write_projection(
        render_learning_artifact(artifact.model_dump(mode="json")),
        vault_root=str(vault_root),
        dry_run=dry_run,
    )


def _trace_machine_evidence_binding(
    connection: sqlite3.Connection, machine_unit_id: str
) -> dict[str, object]:
    machine = connection.execute(
        "SELECT source_signal_id FROM machine_knowledge_candidates_v1 WHERE id=?",
        (machine_unit_id,),
    ).fetchone()
    if machine is None:
        raise ValueError("machine knowledge unit not found")
    signal_id = str(machine["source_signal_id"])
    signal = connection.execute(
        "SELECT card_id FROM mastery_signals_v1 WHERE id=?", (signal_id,)
    ).fetchone()
    if signal is None:
        raise RuntimeError("machine knowledge unit is missing its mastery signal")
    card_id = str(signal["card_id"])
    card = connection.execute(
        "SELECT source_ids_json FROM kb_cards WHERE id=?", (card_id,)
    ).fetchone()
    if card is None:
        raise RuntimeError("machine knowledge evidence is missing its learning card")
    try:
        source_ids = json.loads(str(card["source_ids_json"]))
    except json.JSONDecodeError as exc:
        raise RuntimeError("machine knowledge evidence contains invalid source ids") from exc
    if not isinstance(source_ids, list) or not source_ids or not all(
        isinstance(source_id, str) and source_id for source_id in source_ids
    ):
        raise RuntimeError("machine knowledge evidence has invalid source ids")
    for source_id in source_ids:
        source = connection.execute(
            "SELECT 1 FROM research_sources_v1 WHERE id=?", (source_id,)
        ).fetchone()
        if source is None:
            raise RuntimeError("machine knowledge evidence source is absent from the ledger")
    return {
        "machine_unit_id": machine_unit_id,
        "source_signal_id": signal_id,
        "card_id": card_id,
        "source_record_ids": source_ids,
    }


def project_approved_machine_knowledge_asset(
    unit_id: str, *, db_path: str | Path, asset_root: str | Path, dry_run: bool = True
) -> dict[str, Any]:
    """Write a stable AI-asset receipt only for an approved, traceable unit."""
    database = Path(db_path)
    knowledge_governance_migration.require_applied(db_path=database, live_wal=True)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT unit_json, approval_id, reviewer_id, rationale "
            "FROM machine_knowledge_candidates_v1 WHERE id=? AND lifecycle_status='approved'",
            (unit_id,),
        ).fetchone()
        if row is None:
            raise ValueError("AI asset projection requires an approved machine knowledge unit")
        unit = MachineKnowledgeUnitV1.model_validate_json(str(row["unit_json"]))
        if (
            unit.unit_id != unit_id
            or unit.lifecycle_status != "approved"
            or unit.requires_human_review
            or unit.provenance_status != "server_verified"
            or not row["approval_id"]
            or not row["reviewer_id"]
            or not row["rationale"]
        ):
            raise RuntimeError("approved AI asset payload conflicts with governed ledger")
        binding = _trace_machine_evidence_binding(connection, unit_id)

    payload = {"asset": unit.model_dump(mode="json"), "evidence_binding": binding}
    try:
        target = ApprovedRoots(output_roots=[asset_root]).resolve_output(f"{unit_id}.json")
    except ApprovedRootsError as exc:
        return {"status": "blocked", "reason": str(exc)}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if dry_run:
        return {
            "status": "dry_run",
            "file_path": str(target),
            "target": str(target),
            "asset": payload["asset"],
            "evidence_binding": binding,
            "dry_run": True,
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return {
        "status": "written",
        "file_path": str(target),
        "target": str(target),
        "asset": payload["asset"],
        "evidence_binding": binding,
        "dry_run": False,
        "written": True,
        "size": len(rendered),
    }
