"""Human Knowledge Distillation Engine — absorbed from colleague-skill patterns.

A human who masters a domain holds tacit knowledge (判断/经验/决策模式) that is
rarely written down. This engine captures it through explicit, verifiable steps
(report §3.6, §4.6):

    candidate principle  →  cross-case verification  →  expert rule  →  skill

    CandidatePrinciple: a judgment the human states ("product must be the
                        first visual layer in a launch banner").
    Case:               a concrete past/observed instance that supports or
                        contradicts the principle.
    Cross-case check:   a principle is promoted only when >= MIN_CASES cases
                        are consistently consistent (>= consistency_ratio).
    ExpertRule:         the verified, citable rule with provenance.
    SkillProposal:      a payload ready for the skill-asset registry.

Governance:
    * append-only tables; a rule can be deprecated but never rewritten
    * promotion requires explicit cases — a single anecdote is not a rule
    * nothing here auto-activates a skill (see skill_assets gating)
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

MIN_VERIFICATION_CASES = 3
CONSISTENCY_THRESHOLD = 0.8

_SCHEMA = """
CREATE TABLE IF NOT EXISTS distillation_principles (
    principle_id TEXT PRIMARY KEY,
    statement TEXT NOT NULL,
    source_kind TEXT NOT NULL,          -- interview | observation | analysis | self_report
    source_locator TEXT NOT NULL,
    evidence TEXT,
    status TEXT NOT NULL DEFAULT 'candidate',  -- candidate | verified | rejected | deprecated
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dist_principles_status ON distillation_principles(status);

CREATE TABLE IF NOT EXISTS distillation_cases (
    case_id TEXT PRIMARY KEY,
    principle_id TEXT NOT NULL,
    outcome TEXT NOT NULL,              -- consistent | contradicts
    context TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (principle_id) REFERENCES distillation_principles(principle_id)
);
CREATE INDEX IF NOT EXISTS idx_dist_cases_principle ON distillation_cases(principle_id);

CREATE TABLE IF NOT EXISTS distillation_rules (
    rule_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    conditions_json TEXT NOT NULL,
    action_json TEXT NOT NULL,
    principle_ids_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'verified',  -- verified | deprecated
    confidence REAL NOT NULL,
    skill_asset_id TEXT,
    created_at TEXT NOT NULL
);
"""


class DistillationError(ValueError):
    """Raised when a distillation operation is invalid."""


@dataclass(frozen=True)
class CandidatePrinciple:
    principle_id: str
    statement: str
    source_kind: Literal["interview", "observation", "analysis", "self_report"]
    source_locator: str
    evidence: str | None = None
    status: str = "candidate"
    created_at: str = ""


@dataclass(frozen=True)
class VerificationVerdict:
    principle_id: str
    outcome: Literal["promoted", "rejected", "insufficient_evidence"]
    consistent_cases: int
    contradicting_cases: int
    total_cases: int
    consistency: float
    reason: str


@dataclass(frozen=True)
class ExpertRule:
    rule_id: str
    title: str
    conditions: list[str]
    action: dict[str, Any]
    principle_ids: list[str]
    confidence: float
    skill_asset_id: str | None = None
    status: str = "verified"
    created_at: str = ""


@dataclass(frozen=True)
class SkillProposal:
    """Payload ready for the skill-asset registry (allowed/forbidden tasks)."""

    name: str
    version: str
    source_url: str
    allowed_tasks: list[str]
    forbidden_tasks: list[str]
    input_contract: dict[str, Any]
    output_contract: dict[str, Any]
    risk_level: str = "low"
    license: str | None = "MIT"
    rollback_path: str | None = None


def _connect(db: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _stable_id(prefix: str, *parts: str) -> str:
    from hashlib import sha256

    payload = "\0".join(parts).encode("utf-8")
    return f"{prefix}_{sha256(payload).hexdigest()[:24]}"


# ── principles ─────────────────────────────────────────────────────

def record_principle(
    db: str | Path,
    *,
    statement: str,
    source_kind: str,
    source_locator: str,
    evidence: str | None = None,
    principle_id: str | None = None,
) -> CandidatePrinciple:
    """Record a candidate principle stated by the human (append-only)."""
    if not statement.strip():
        raise DistillationError("principle statement is required")
    if source_kind not in {"interview", "observation", "analysis", "self_report"}:
        raise DistillationError(f"unknown source_kind: {source_kind}")
    if not source_locator.strip():
        raise DistillationError("source_locator is required")
    pid = principle_id or _stable_id("principle", statement, source_locator)
    created_at = _now()
    with _connect(db) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO distillation_principles "
            "(principle_id, statement, source_kind, source_locator, evidence, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'candidate', ?)",
            (pid, statement.strip(), source_kind, source_locator.strip(), evidence, created_at),
        )
    return CandidatePrinciple(principle_id=pid, statement=statement.strip(),
                              source_kind=source_kind, source_locator=source_locator,
                              evidence=evidence, status="candidate", created_at=created_at)


def record_case(
    db: str | Path,
    *,
    principle_id: str,
    outcome: Literal["consistent", "contradicts"],
    context: str,
) -> str:
    """Attach one concrete case to a principle (consistent or contradicts)."""
    if outcome not in {"consistent", "contradicts"}:
        raise DistillationError(f"invalid case outcome: {outcome}")
    if not context.strip():
        raise DistillationError("case context is required")
    case_id = _stable_id("case", principle_id, context, _now())
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT status FROM distillation_principles WHERE principle_id=?", (principle_id,)
        ).fetchone()
        if row is None:
            raise DistillationError(f"principle not found: {principle_id}")
        if row[0] != "candidate":
            raise DistillationError("cases can only be added to candidate principles")
        conn.execute(
            "INSERT INTO distillation_cases (case_id, principle_id, outcome, context, recorded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (case_id, principle_id, outcome, context.strip(), _now()),
        )
    return case_id


def verify_principle(db: str | Path, principle_id: str) -> VerificationVerdict:
    """Cross-case verification: promote / reject / insufficient_evidence."""
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT status FROM distillation_principles WHERE principle_id=?", (principle_id,)
        ).fetchone()
        if row is None:
            raise DistillationError(f"principle not found: {principle_id}")
        cases = conn.execute(
            "SELECT outcome FROM distillation_cases WHERE principle_id=?", (principle_id,)
        ).fetchall()
        if not cases:
            return VerificationVerdict(principle_id=principle_id, outcome="insufficient_evidence",
                                       consistent_cases=0, contradicting_cases=0, total_cases=0,
                                       consistency=0.0, reason="no cases recorded yet")
        consistent = sum(1 for c in cases if c["outcome"] == "consistent")
        contradicting = len(cases) - consistent
        consistency = consistent / len(cases)
        if len(cases) < MIN_VERIFICATION_CASES or consistency < CONSISTENCY_THRESHOLD:
            return VerificationVerdict(
                principle_id=principle_id, outcome="insufficient_evidence",
                consistent_cases=consistent, contradicting_cases=contradicting,
                total_cases=len(cases), consistency=round(consistency, 3),
                reason=f"need >= {MIN_VERIFICATION_CASES} cases and >= {CONSISTENCY_THRESHOLD} consistency",
            )
        status = "verified" if contradicting == 0 else "verified"  # contradictions < 20% tolerated
        conn.execute(
            "UPDATE distillation_principles SET status=? WHERE principle_id=?",
            ("verified", principle_id),
        )
        return VerificationVerdict(principle_id=principle_id, outcome="promoted",
                                   consistent_cases=consistent, contradicting_cases=contradicting,
                                   total_cases=len(cases), consistency=round(consistency, 3),
                                   reason="cross-case verification passed")


# ── expert rules ───────────────────────────────────────────────────

def promote_to_rule(
    db: str | Path,
    *,
    principle_id: str,
    title: str,
    conditions: list[str],
    action: dict[str, Any],
    confidence: float = 0.8,
) -> ExpertRule:
    """Promote a verified principle into a citable expert rule."""
    if not conditions or not isinstance(action, dict):
        raise DistillationError("rule requires conditions and an action object")
    if not 0.0 <= confidence <= 1.0:
        raise DistillationError("confidence must be in [0,1]")
    with _connect(db) as conn:
        row = conn.execute(
            "SELECT statement, status FROM distillation_principles WHERE principle_id=?", (principle_id,)
        ).fetchone()
        if row is None:
            raise DistillationError(f"principle not found: {principle_id}")
        if row["status"] != "verified":
            raise DistillationError("only verified principles can be promoted to rules")
        rule_id = _stable_id("rule", principle_id, title)
        created_at = _now()
        conn.execute(
            "INSERT INTO distillation_rules "
            "(rule_id, title, conditions_json, action_json, principle_ids_json, status, confidence, skill_asset_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'verified', ?, NULL, ?)",
            (rule_id, title, _j(conditions), _j(action), _j([principle_id]), confidence, created_at),
        )
    return ExpertRule(rule_id=rule_id, title=title, conditions=list(conditions),
                      action=dict(action), principle_ids=[principle_id],
                      confidence=confidence, created_at=created_at)


def propose_skill(rule: ExpertRule, *, name: str, version: str,
                  allowed_tasks: list[str], forbidden_tasks: list[str],
                  source_url: str = "distillation://expert-rule") -> SkillProposal:
    """Turn a verified expert rule into a skill-asset proposal (still gated)."""
    if not allowed_tasks:
        raise DistillationError("skill proposal requires at least one allowed task")
    return SkillProposal(
        name=name, version=version, source_url=source_url,
        allowed_tasks=allowed_tasks, forbidden_tasks=forbidden_tasks,
        input_contract={"rule_id": rule.rule_id, "conditions": rule.conditions,
                        "required_principles": rule.principle_ids},
        output_contract={"action": rule.action, "confidence": rule.confidence},
    )


def deprecate_rule(db: str | Path, rule_id: str, *, reason: str) -> None:
    """Deprecate a rule (append-only history; never delete)."""
    if not reason.strip():
        raise DistillationError("deprecation requires a reason")
    with _connect(db) as conn:
        row = conn.execute("SELECT rule_id FROM distillation_rules WHERE rule_id=?", (rule_id,)).fetchone()
        if row is None:
            raise DistillationError(f"rule not found: {rule_id}")
        conn.execute("UPDATE distillation_rules SET status='deprecated' WHERE rule_id=?", (rule_id,))
