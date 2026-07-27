"""Typed runtime intent, permission, and recovery contracts.

Combines three concerns:
  1. RuntimeIntent — what the runtime intends to do (goal, type, risk, timeout).
  2. RuntimePermission — typed permission decision with timeout and recovery.
  3. RuntimeRecovery — how to recover on failure (retry, rollback, fail-closed, escalate).

High-risk migrations, permission escalations, and dependency changes are blocked
separately with explicit block reasons. No scope creep.

Usage:
    from shared.runtime_intent import (
        RuntimeIntent, IntentKind, RiskLevel,
        RuntimePermission,
        RuntimeRecovery, RecoveryStrategy,
        check_intent_permission,
        check_high_risk_blockers,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

# ── Enums ──


class IntentKind(str, Enum):
    """High-level category of a runtime intent."""

    RESEARCH = "research"           # Research / investigation
    INGESTION = "ingestion"         # File/URL ingestion & conversion
    EVALUATION = "evaluation"       # Trace evaluation & redaction
    INDEXING = "indexing"           # Derived index rebuild (FTS, vector, graph)
    SYNCHRONIZATION = "sync"        # External sync (Obsidian, etc.)
    KNOWLEDGE_PROMOTION = "promotion"  # Knowledge promotion & review
    EXECUTION = "execution"         # Tool-based task execution
    MIGRATION = "migration"         # Schema / data migration
    PERMISSION_CHANGE = "permission_change"  # Permission / access changes
    DEPENDENCY_CHANGE = "dependency_change"  # Dependency / config changes
    RELEASE = "release"             # Build, package, release
    RECOVERY = "recovery"           # Recovery / retry / rollback
    MAINTENANCE = "maintenance"     # Cleanup, backup, integrity check
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Assessment of how risky an intent is to execute."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(str, Enum):
    """How to recover when an intent fails."""

    RETRY = "retry"                    # Retry with backoff (finite attempts)
    ROLLBACK = "rollback"              # Undo the intent's side effects
    FAIL_CLOSED = "fail_closed"        # Leave state unchanged, block further writes
    ESCALATE = "escalate"              # Escalate to human or supervisor
    CONTINUE = "continue"              # Log and continue (best-effort only)
    ABORT = "abort"                    # Immediate abort, no recovery


# ── Intent definition ──


@dataclass(frozen=True)
class RuntimeIntent:
    """Canonical description of what the runtime intends to do.

    Fields:
        intent_id: stable identifier for this intent instance.
        kind: high-level category (research, ingestion, evaluation, …).
        goal: human-readable description of the intent's purpose.
        risk: assessed risk level (default LOW).
        timeout_seconds: hard deadline in seconds (default 300 = 5 min).
        max_retries: how many times to retry before escalation (default 3).
        recovery_strategy: how to recover on failure (default FAIL_CLOSED).
        requires_human_review: true if human oversight is mandatory.
        requires_migration_lock: true if this intent needs exclusive DB migration lock.
        may_create_checkpoint: true if this intent may persist intermediate state.
        metadata: extra key-value bag for intent-specific context.
    """

    intent_id: str
    kind: IntentKind = IntentKind.UNKNOWN
    goal: str = ""
    risk: RiskLevel = RiskLevel.LOW
    timeout_seconds: int = 300
    max_retries: int = 3
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.FAIL_CLOSED
    requires_human_review: bool = False
    requires_migration_lock: bool = False
    may_create_checkpoint: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_blocked(self) -> bool:
        """Return True if this intent cannot execute without external review."""
        return self.risk in (RiskLevel.HIGH, RiskLevel.CRITICAL) or self.requires_human_review


# ── Permission decision ──


@dataclass(frozen=True)
class RuntimePermission:
    """Typed permission decision for one runtime intent.

    Fields:
        allowed: true if the intent may proceed.
        reason: human-readable justification.
        risk: assessed risk level (may be escalated from the original intent).
        effective_timeout_seconds: actual timeout (may differ from intent due to escalation).
        allowed_tools: tools the intent is permitted to use (empty = any non-blocked).
        blocked_tools: tools explicitly forbidden.
        requires_human_review: true if human review is still needed (deferred check).
        recovery_strategy: effective recovery strategy (may be escalated).
        block_reason: if allowed=False, explains why.
    """

    allowed: bool
    reason: str = ""
    risk: RiskLevel = RiskLevel.LOW
    effective_timeout_seconds: int = 300
    allowed_tools: tuple[str, ...] = ()
    blocked_tools: tuple[str, ...] = ()
    requires_human_review: bool = False
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.FAIL_CLOSED
    block_reason: str = ""


# ── Recovery / contract ──


@dataclass(frozen=True)
class RuntimeRecovery:
    """Contract that defines recovery behavior for one runtime intent.

    Fields:
        strategy: recovery strategy to apply.
        max_attempts: maximum total attempts (including initial).
        attempt: current attempt number (1-based).
        retry_delay_seconds: delay between retries.
        last_error: human-readable description of the last failure.
        created_at: when the recovery was defined.
        expires_at: after this time, the recovery is considered stale.
    """

    strategy: RecoveryStrategy = RecoveryStrategy.FAIL_CLOSED
    max_attempts: int = 3
    attempt: int = 1
    retry_delay_seconds: int = 5
    last_error: str = ""
    created_at: str = ""
    expires_at: str = ""

    def should_retry(self) -> bool:
        """Return True if the intent should be retried."""
        if self.strategy != RecoveryStrategy.RETRY:
            return False
        return self.attempt < self.max_attempts

    def next_attempt(self, error: str = "") -> RuntimeRecovery:
        """Advance the attempt counter and record the error."""
        return RuntimeRecovery(
            strategy=self.strategy,
            max_attempts=self.max_attempts,
            attempt=self.attempt + 1,
            retry_delay_seconds=self.retry_delay_seconds,
            last_error=error or self.last_error,
            created_at=self.created_at,
            expires_at=self.expires_at,
        )


# ── Permission checker ──


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_intent_permission(
    intent: RuntimeIntent,
    *,
    tool_risk_registry: dict[str, RiskLevel] | None = None,
    blocked_intent_kinds: set[IntentKind] | None = None,
    blocked_tools: set[str] | None = None,
    max_timeout_seconds: int = 3600,
) -> RuntimePermission:
    """Check whether a RuntimeIntent is permitted to execute.

    Args:
        intent: the intent to check.
        tool_risk_registry: mapping of tool names to their RiskLevel (optional).
        blocked_intent_kinds: intent kinds that are always blocked (optional).
        blocked_tools: tool names that are always blocked (optional).
        max_timeout_seconds: maximum allowed timeout (default 1 hour).

    Returns:
        RuntimePermission with allowed/reason/block_reason.
    """
    reasons: list[str] = []
    risk = intent.risk

    # --- Check blocked intent kinds ---
    if blocked_intent_kinds and intent.kind in blocked_intent_kinds:
        return RuntimePermission(
            allowed=False,
            reason=f"Intent kind '{intent.kind.value}' is blocked",
            risk=RiskLevel.CRITICAL,
            block_reason=f"intent_kind_blocked: {intent.kind.value}",
        )

    # --- Check high-risk blockers ---
    blocker = check_high_risk_blockers(intent)
    if blocker is not None:
        return blocker

    # --- Check tool risk ---
    tool_risk = tool_risk_registry or {}
    for tool, tool_level in tool_risk.items():
        if tool_level == RiskLevel.CRITICAL:
            return RuntimePermission(
                allowed=False,
                reason=f"Tool '{tool}' is critical risk — permanently blocked",
                risk=RiskLevel.CRITICAL,
                block_reason=f"critical_tool_blocked: {tool}",
            )

    # --- Check blocked tools ---
    if blocked_tools:
        intersected = blocked_tools & set(tool_risk.keys())
        if intersected:
            blocked_list = sorted(intersected)
            return RuntimePermission(
                allowed=False,
                reason=f"Blocked tools requested: {', '.join(blocked_list)}",
                risk=RiskLevel.CRITICAL,
                block_reason=f"blocked_tools: {', '.join(blocked_list)}",
            )

    # --- Enforce timeout bounds ---
    effective_timeout = min(intent.timeout_seconds, max_timeout_seconds)
    if effective_timeout < intent.timeout_seconds:
        reasons.append(f"timeout clamped from {intent.timeout_seconds}s to {effective_timeout}s")

    # --- Escalate risk for certain kinds ---
    if intent.kind in (IntentKind.MIGRATION, IntentKind.PERMISSION_CHANGE, IntentKind.DEPENDENCY_CHANGE):
        if risk == RiskLevel.LOW:
            risk = RiskLevel.MEDIUM
            reasons.append("migration/perm/dep change escalated from low→medium")
        elif risk == RiskLevel.MEDIUM:
            risk = RiskLevel.HIGH
            reasons.append("migration/perm/dep change escalated from medium→high")

    # --- Determine recovery strategy ---
    recovery = intent.recovery_strategy
    if (
        risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        and recovery not in (RecoveryStrategy.FAIL_CLOSED, RecoveryStrategy.ABORT)
    ):
        # High/Critical risk always uses fail-closed or escalate
        recovery = RecoveryStrategy.FAIL_CLOSED
        reasons.append("recovery escalated to fail_closed for high/critical risk")

    requires_review = intent.requires_human_review or risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    if not reasons:
        reasons.append("all checks passed")

    return RuntimePermission(
        allowed=not requires_review,
        reason="; ".join(reasons),
        risk=risk,
        effective_timeout_seconds=effective_timeout,
        recovery_strategy=recovery,
        requires_human_review=requires_review,
        block_reason="requires_human_review" if requires_review else "",
    )


# ── High-risk blockers ──


HIGH_RISK_KEYWORDS: tuple[str, ...] = (
    # Database / schema
    "drop table", "drop database", "truncate table", "alter schema",
    "delete from", "update set", "rebuild index all",
    # Permissions / auth
    "chmod 777", "chown", "sudo ", "su ",
    "change permission", "grant all", "revoke all",
    "disable auth", "disable authentication", "bypass auth",
    "create user", "drop user", "alter user",
    # Dependency / config
    "pip install --force", "npm install --force", "rm -rf node_modules",
    "replace requirements", "replace pyproject", "replace package.json",
    "override config", "overwrite config",
    # Destructive file operations
    "rm -rf /", "rm -rf .", "disk format", "mkfs",
    "delete database", "remove database",
    # Network / firewall
    "disable firewall", "open port", "expose endpoint",
    "allow all origins",
    # Secrets
    "set env API_KEY", "export SECRET", "write .env",
    "commit .env", "commit credentials",
)


def check_high_risk_blockers(intent: RuntimeIntent) -> RuntimePermission | None:
    """Check for high-risk patterns that always block execution.

    Returns a blocked RuntimePermission if a blocker is found, None otherwise.
    """
    goal_lower = intent.goal.lower()

    for keyword in HIGH_RISK_KEYWORDS:
        if keyword.lower() in goal_lower:
            return RuntimePermission(
                allowed=False,
                reason=f"High-risk keyword in intent goal: '{keyword}'",
                risk=RiskLevel.CRITICAL,
                recovery_strategy=RecoveryStrategy.ABORT,
                block_reason=f"high_risk_keyword: {keyword}",
            )

    # Kind-specific blockers
    if intent.kind == IntentKind.PERMISSION_CHANGE and intent.risk != RiskLevel.LOW:
        return RuntimePermission(
            allowed=False,
            reason="Non-low permission changes require independent human review",
            risk=RiskLevel.CRITICAL,
            recovery_strategy=RecoveryStrategy.ABORT,
            block_reason="permission_change_requires_review",
        )

    if intent.kind == IntentKind.DEPENDENCY_CHANGE and intent.risk != RiskLevel.LOW:
        return RuntimePermission(
            allowed=False,
            reason="Non-low dependency changes require independent human review",
            risk=RiskLevel.CRITICAL,
            recovery_strategy=RecoveryStrategy.ABORT,
            block_reason="dependency_change_requires_review",
        )

    if intent.kind == IntentKind.MIGRATION and intent.risk == RiskLevel.CRITICAL:
        return RuntimePermission(
            allowed=False,
            reason="Critical migrations require independent human review before any execution",
            risk=RiskLevel.CRITICAL,
            requires_human_review=True,
            recovery_strategy=RecoveryStrategy.FAIL_CLOSED,
            block_reason="critical_migration_blocked",
        )

    return None


# ── Recovery helpers ──


def make_recovery(
    intent: RuntimeIntent,
    *,
    error: str = "",
    permission: RuntimePermission | None = None,
) -> RuntimeRecovery:
    """Build a RuntimeRecovery from an intent and optional permission.

    Args:
        intent: the original intent.
        error: description of the current failure.
        permission: the permission decision (overrides intent's recovery).

    Returns:
        A RuntimeRecovery ready to be recorded.
    """
    strategy = (
        permission.recovery_strategy
        if permission is not None
        else intent.recovery_strategy
    )
    now = _now_iso()
    timeout = timedelta(
        seconds=(permission.effective_timeout_seconds if permission else intent.timeout_seconds)
    )
    expires = (datetime.now(timezone.utc) + timeout).isoformat()

    return RuntimeRecovery(
        strategy=strategy,
        max_attempts=intent.max_retries + 1,
        attempt=1,
        retry_delay_seconds=min(60, max(1, intent.timeout_seconds // 10)),
        last_error=error,
        created_at=now,
        expires_at=expires,
    )


# ── Safe defaults ──

SAFE_TOOL_REGISTRY: dict[str, RiskLevel] = {
    "read_file": RiskLevel.LOW,
    "search_files": RiskLevel.LOW,
    "read_terminal": RiskLevel.LOW,
    "terminal": RiskLevel.MEDIUM,
    "patch": RiskLevel.MEDIUM,
    "write_file": RiskLevel.MEDIUM,
    "web_search": RiskLevel.MEDIUM,
    "web_extract": RiskLevel.MEDIUM,
    "execute_code": RiskLevel.HIGH,
    "process": RiskLevel.HIGH,
}

BLOCKED_HIGH_RISK_INTENTS: set[IntentKind] = {
    IntentKind.MIGRATION,
    IntentKind.PERMISSION_CHANGE,
    IntentKind.DEPENDENCY_CHANGE,
    IntentKind.RELEASE,
}

SAFE_INTENT_KINDS: set[IntentKind] = {
    IntentKind.RESEARCH,
    IntentKind.INGESTION,
    IntentKind.EVALUATION,
    IntentKind.INDEXING,
    IntentKind.EXECUTION,
    IntentKind.MAINTENANCE,
    IntentKind.SYNCHRONIZATION,
    IntentKind.KNOWLEDGE_PROMOTION,
}
