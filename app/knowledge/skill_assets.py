"""AXW-052B: low-risk Skill/Prompt asset registry.

Skill/prompt assets are versioned, sourced, and gated: each asset declares
its allowed and forbidden tasks, its input/output contract, a rollback
path, and an evaluation hook. High-risk tools are NEVER auto-activated by
an asset — activation requires an explicit, reviewed activation record.

The registry is append-only: versions are never rewritten; a new version
supersedes the old one and the history stays intact.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS skill_assets (
    asset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    source_url TEXT NOT NULL,
    license TEXT,
    allowed_tasks_json TEXT NOT NULL,
    forbidden_tasks_json TEXT NOT NULL,
    input_contract_json TEXT NOT NULL,
    output_contract_json TEXT NOT NULL,
    rollback_path TEXT,
    risk_level TEXT NOT NULL,
    reviewed INTEGER NOT NULL DEFAULT 0,
    reviewer TEXT,
    superseded_by TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_skill_assets_name ON skill_assets(name);
CREATE TABLE IF NOT EXISTS asset_activations (
    activation_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    activated INTEGER NOT NULL DEFAULT 0,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_asset_activations ON asset_activations(asset_id);
"""

_RISK_LEVELS = frozenset({"low", "medium", "high"})


class SkillAssetError(ValueError):
    """Raised when a skill asset operation is invalid."""


@dataclass(frozen=True)
class SkillAsset:
    asset_id: str
    name: str
    version: str
    source_url: str
    license: str | None
    allowed_tasks: list[str]
    forbidden_tasks: list[str]
    input_contract: dict[str, Any]
    output_contract: dict[str, Any]
    rollback_path: str | None
    risk_level: str
    reviewed: bool
    reviewer: str | None
    superseded_by: str | None
    created_at: str

    @property
    def active(self) -> bool:
        return self.superseded_by is None


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _j(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def register_skill_asset(
    db: str | Path,
    *,
    name: str,
    version: str,
    source_url: str,
    allowed_tasks: list[str],
    forbidden_tasks: list[str],
    input_contract: dict[str, Any],
    output_contract: dict[str, Any],
    risk_level: str = "low",
    license: str | None = None,
    rollback_path: str | None = None,
    supersede: str | None = None,
) -> SkillAsset:
    """Register one version of a skill/prompt asset (candidate by default)."""
    if not name or not version or not source_url:
        raise SkillAssetError("name, version and source_url are required")
    if risk_level not in _RISK_LEVELS:
        raise SkillAssetError(f"invalid risk level: {risk_level}")
    if risk_level == "high":
        raise SkillAssetError("high-risk assets cannot be registered as low-risk skills; use a reviewed pipeline")
    if not allowed_tasks:
        raise SkillAssetError("allowed_tasks must be non-empty")
    if not isinstance(input_contract, dict) or not isinstance(output_contract, dict):
        raise SkillAssetError("input/output contracts must be objects")

    asset_id = f"sk_{abs(hash((name, version, source_url))) % (10**12):012d}"
    created_at = _now()
    with _connect(db) as conn:
        if supersede is not None:
            row = conn.execute(
                "SELECT superseded_by FROM skill_assets WHERE asset_id=?", (supersede,)
            ).fetchone()
            if row is None:
                raise SkillAssetError(f"supersede target not found: {supersede}")
            if row[0] is not None:
                raise SkillAssetError(f"supersede target already superseded: {supersede}")
            conn.execute(
                "UPDATE skill_assets SET superseded_by=? WHERE asset_id=?",
                (asset_id, supersede),
            )
        conn.execute(
            "INSERT INTO skill_assets (asset_id, name, version, source_url, license, "
            "allowed_tasks_json, forbidden_tasks_json, input_contract_json, output_contract_json, "
            "rollback_path, risk_level, reviewed, reviewer, superseded_by, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,0,NULL,NULL,?)",
            (
                asset_id, name, version, source_url, license,
                _j(allowed_tasks), _j(forbidden_tasks), _j(input_contract), _j(output_contract),
                rollback_path, risk_level, created_at,
            ),
        )
        conn.commit()
    return SkillAsset(
        asset_id=asset_id,
        name=name,
        version=version,
        source_url=source_url,
        license=license,
        allowed_tasks=allowed_tasks,
        forbidden_tasks=forbidden_tasks,
        input_contract=input_contract,
        output_contract=output_contract,
        rollback_path=rollback_path,
        risk_level=risk_level,
        reviewed=False,
        reviewer=None,
        superseded_by=None,
        created_at=created_at,
    )


def _row_to_asset(row: sqlite3.Row) -> SkillAsset:
    import json

    return SkillAsset(
        asset_id=row["asset_id"],
        name=row["name"],
        version=row["version"],
        source_url=row["source_url"],
        license=row["license"],
        allowed_tasks=json.loads(row["allowed_tasks_json"]),
        forbidden_tasks=json.loads(row["forbidden_tasks_json"]),
        input_contract=json.loads(row["input_contract_json"]),
        output_contract=json.loads(row["output_contract_json"]),
        rollback_path=row["rollback_path"],
        risk_level=row["risk_level"],
        reviewed=bool(row["reviewed"]),
        reviewer=row["reviewer"],
        superseded_by=row["superseded_by"],
        created_at=row["created_at"],
    )


def review_asset(
    db: str | Path, *, asset_id: str, reviewer: str, approved: bool = True
) -> dict[str, Any]:
    """Approve/reject an asset version (append-only status flip)."""
    if not reviewer:
        raise SkillAssetError("reviewer is required")
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT asset_id FROM skill_assets WHERE asset_id=?", (asset_id,)
        ).fetchone()
        if row is None:
            raise SkillAssetError(f"asset not found: {asset_id}")
        conn.execute(
            "UPDATE skill_assets SET reviewed=?, reviewer=? WHERE asset_id=?",
            (1 if approved else 0, reviewer, asset_id),
        )
        conn.commit()
    return {"asset_id": asset_id, "reviewed": approved, "reviewer": reviewer}


def active_assets(db: str | Path, *, name: str | None = None) -> list[SkillAsset]:
    """Reviewed, non-superseded assets for projection (fail-closed)."""
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        where = "superseded_by IS NULL AND reviewed = 1"
        params: tuple = ()
        if name is not None:
            where += " AND name = ?"
            params = (name,)
        rows = conn.execute(
            f"SELECT * FROM skill_assets WHERE {where} ORDER BY created_at, asset_id", params
        ).fetchall()
    return [_row_to_asset(r) for r in rows]


def authorize_tool(
    db: str | Path,
    *,
    asset_id: str,
    tool_name: str,
    actor: str,
    auto: bool = False,
) -> dict[str, Any]:
    """Explicitly activate a tool for an asset.

    ``auto`` must be False for high/medium risk tools: auto-activation is
    forbidden. Only a reviewed, active asset can be authorized.
    """
    if not tool_name or not actor:
        raise SkillAssetError("tool_name and actor are required")
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM skill_assets WHERE asset_id=?", (asset_id,)
        ).fetchone()
        if row is None:
            raise SkillAssetError(f"asset not found: {asset_id}")
        asset = _row_to_asset(row)
        if not asset.reviewed or not asset.active:
            raise SkillAssetError("only reviewed, active assets can authorize tools")
        if asset.risk_level in ("medium", "high") and auto:
            raise SkillAssetError("auto-activation is forbidden for medium/high-risk assets")
        activation_id = f"act_{abs(hash((asset_id, tool_name, actor))) % (10**12):012d}"
        conn.execute(
            "INSERT INTO asset_activations (activation_id, asset_id, tool_name, activated, actor, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (activation_id, asset_id, tool_name, 1, actor, _now()),
        )
        conn.commit()
    return {"activation_id": activation_id, "asset_id": asset_id, "tool_name": tool_name, "actor": actor}


def task_is_allowed(asset: SkillAsset, task: str) -> bool:
    """A task is allowed only when explicitly listed and not forbidden."""
    if any(task in f or f in task for f in asset.forbidden_tasks):
        return False
    return any(task in a or a in task for a in asset.allowed_tasks)
