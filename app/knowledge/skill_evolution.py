"""Skill evolution loop — absorbed from Hermes Agent Self-Evolution / SkillRL.

A skill is not a static file. After real usage, the loop decides whether to
keep, patch or retire it (report §3.8, "SKILL.md is not the end point"):

    usage → evaluate → (keep | propose patch) → verify patch → apply (new version)

    record_usage     — one observed execution (task, outcome, failure analysis)
    evaluate_skill   — verdict from >= min_usages observations
    propose_patch    — a candidate change (statement, payload, rationale)
    verify_patch     — gate: test results must pass; payload must be bounded
    apply_patch      — supersede the skill with the verified new version

Governance:
    * a patch is NEVER applied without passing the verification gate
    * high-risk skills cannot be patched by this loop (they need human review)
    * version history is append-only; old versions stay queryable
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

MIN_EVALUATION_USAGES = 3
RETIRE_SUCCESS_RATE = 0.4
PATCH_SUCCESS_RATE = 0.8
MAX_PATCH_PAYLOAD_BYTES = 64 * 1024

_SCHEMA = """
CREATE TABLE IF NOT EXISTS skill_usages (
    usage_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    task TEXT NOT NULL,
    outcome TEXT NOT NULL,             -- success | failure
    failure_analysis TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_su_skill ON skill_usages(skill_id);

CREATE TABLE IF NOT EXISTS skill_patches (
    patch_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    analysis TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    rationale TEXT,
    status TEXT NOT NULL DEFAULT 'proposed',  -- proposed | approved | rejected | applied
    test_results_json TEXT,
    reviewer TEXT,
    created_at TEXT NOT NULL
);
"""


class SkillEvolutionError(ValueError):
    """Raised when a skill-evolution operation is invalid."""


@dataclass(frozen=True)
class SkillUsageRecord:
    usage_id: str
    skill_id: str
    task: str
    outcome: Literal["success", "failure"]
    failure_analysis: str | None
    created_at: str


@dataclass(frozen=True)
class SkillEvaluation:
    skill_id: str
    total_usages: int
    successes: int
    success_rate: float
    verdict: Literal["keep", "needs_patch", "retire", "insufficient_data"]


@dataclass(frozen=True)
class SkillPatch:
    patch_id: str
    skill_id: str
    analysis: str
    payload: dict[str, Any]
    rationale: str | None
    status: str
    created_at: str


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: str) -> str:
    from hashlib import sha256

    payload = "\0".join(parts).encode("utf-8")
    return f"{prefix}_{sha256(payload).hexdigest()[:24]}"


# ── usage ───────────────────────────────────────────────────────────

def record_usage(
    db: str | Path,
    *,
    skill_id: str,
    task: str,
    outcome: Literal["success", "failure"],
    failure_analysis: str | None = None,
) -> SkillUsageRecord:
    """Record one observed skill execution (append-only)."""
    if not skill_id.strip() or not task.strip():
        raise SkillEvolutionError("skill_id and task are required")
    if outcome not in {"success", "failure"}:
        raise SkillEvolutionError(f"invalid outcome: {outcome}")
    if outcome == "failure" and not failure_analysis:
        raise SkillEvolutionError("failure usages require a failure_analysis")
    usage_id = _stable_id("usage", skill_id, task, _now())
    created_at = _now()
    with _connect(db) as conn:
        conn.execute(
            "INSERT INTO skill_usages (usage_id, skill_id, task, outcome, failure_analysis, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (usage_id, skill_id, task.strip(), outcome, failure_analysis, created_at),
        )
    return SkillUsageRecord(usage_id=usage_id, skill_id=skill_id, task=task.strip(),
                            outcome=outcome, failure_analysis=failure_analysis,
                            created_at=created_at)


def evaluate_skill(db: str | Path, skill_id: str) -> SkillEvaluation:
    """Verdict from the observed usage history."""
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT outcome FROM skill_usages WHERE skill_id=?", (skill_id,)
        ).fetchall()
    if len(rows) < MIN_EVALUATION_USAGES:
        return SkillEvaluation(skill_id=skill_id, total_usages=len(rows), successes=0,
                               success_rate=0.0, verdict="insufficient_data")
    successes = sum(1 for r in rows if r["outcome"] == "success")
    rate = successes / len(rows)
    if rate <= RETIRE_SUCCESS_RATE:
        verdict = "retire"
    elif rate < PATCH_SUCCESS_RATE:
        verdict = "needs_patch"
    else:
        verdict = "keep"
    return SkillEvaluation(skill_id=skill_id, total_usages=len(rows), successes=successes,
                           success_rate=round(rate, 3), verdict=verdict)


# ── patch lifecycle ─────────────────────────────────────────────────

def propose_patch(
    db: str | Path,
    *,
    skill_id: str,
    analysis: str,
    payload: dict[str, Any],
    rationale: str | None = None,
    risk_level: str = "low",
) -> SkillPatch:
    """Propose a candidate change to a skill (still gated)."""
    if not analysis.strip() or not isinstance(payload, dict) or not payload:
        raise SkillEvolutionError("analysis and a non-empty payload object are required")
    if risk_level == "high":
        raise SkillEvolutionError("high-risk skills cannot be patched by the automated loop")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_PATCH_PAYLOAD_BYTES:
        raise SkillEvolutionError("patch payload exceeds the size limit")
    patch_id = _stable_id("patch", skill_id, analysis, _now())
    created_at = _now()
    with _connect(db) as conn:
        conn.execute(
            "INSERT INTO skill_patches (patch_id, skill_id, analysis, payload_json, rationale, "
            "status, test_results_json, reviewer, created_at) VALUES (?, ?, ?, ?, ?, 'proposed', NULL, NULL, ?)",
            (patch_id, skill_id, analysis.strip(), json.dumps(payload, ensure_ascii=False),
             rationale, created_at),
        )
    return SkillPatch(patch_id=patch_id, skill_id=skill_id, analysis=analysis.strip(),
                      payload=payload, rationale=rationale, status="proposed",
                      created_at=created_at)


def verify_patch(
    db: str | Path,
    patch_id: str,
    *,
    test_results: dict[str, Any],
    reviewer: str = "evolution-loop",
) -> Literal["approved", "rejected"]:
    """Gate a patch: all tests must pass before it can be applied."""
    with _connect(db) as conn:
        row = conn.execute("SELECT * FROM skill_patches WHERE patch_id=?", (patch_id,)).fetchone()
        if row is None:
            raise SkillEvolutionError(f"patch not found: {patch_id}")
        if row["status"] not in {"proposed", "approved", "rejected"}:
            raise SkillEvolutionError(f"patch is already applied: {patch_id}")
        tests = test_results.get("tests", [])
        if not isinstance(tests, list) or not tests:
            raise SkillEvolutionError("verification requires a non-empty tests list")
        passed = all(isinstance(t, dict) and t.get("passed") is True for t in tests)
        status = "approved" if passed else "rejected"
        conn.execute(
            "UPDATE skill_patches SET status=?, test_results_json=?, reviewer=? WHERE patch_id=?",
            (status, json.dumps(test_results, ensure_ascii=False), reviewer, patch_id),
        )
        return status


def apply_patch(
    db: str | Path,
    patch_id: str,
    *,
    new_version: str,
) -> dict[str, Any]:
    """Apply an approved patch: mark applied and return the new-version payload.

    Returns a payload ready for the skill-asset registry (skill_assets v2),
    which owns the actual supersede/register mechanics.
    """
    with _connect(db) as conn:
        row = conn.execute("SELECT * FROM skill_patches WHERE patch_id=?", (patch_id,)).fetchone()
        if row is None:
            raise SkillEvolutionError(f"patch not found: {patch_id}")
        if row["status"] != "approved":
            raise SkillEvolutionError("only approved patches can be applied")
        payload = json.loads(row["payload_json"])
        conn.execute("UPDATE skill_patches SET status='applied' WHERE patch_id=?", (patch_id,))
    return {
        "skill_id": row["skill_id"],
        "version": new_version,
        "patch_id": patch_id,
        "supersedes": row["skill_id"],
        "payload": payload,
        "reviewer": row["reviewer"],
    }
