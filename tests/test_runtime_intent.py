"""Tests for shared/runtime_intent.py — typed intent, permission, recovery contracts.

Coverage:
  - Intent creation and defaults
  - is_blocked() for high/critical risk and human review
  - Permission checks: low/medium/high/critical
  - High-risk keyword blocking
  - Kind-specific high-risk blockers (migration, perm, dep)
  - Timeout clamping
  - Recovery escalation for high/critical
  - Recovery should_retry / next_attempt
  - make_recovery helper
  - Safe tool registry defaults
  - Intent kind blocking
  - Tool-level blocking
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from shared.runtime_intent import (
    BLOCKED_HIGH_RISK_INTENTS,
    HIGH_RISK_KEYWORDS,
    SAFE_INTENT_KINDS,
    SAFE_TOOL_REGISTRY,
    IntentKind,
    RecoveryStrategy,
    RiskLevel,
    RuntimeIntent,
    RuntimeRecovery,
    check_high_risk_blockers,
    check_intent_permission,
    make_recovery,
)

# ── Fixtures ──


@pytest.fixture
def low_intent() -> RuntimeIntent:
    return RuntimeIntent(
        intent_id="intent-001",
        kind=IntentKind.INGESTION,
        goal="Convert a PDF document to markdown",
        risk=RiskLevel.LOW,
        timeout_seconds=120,
        max_retries=2,
    )


@pytest.fixture
def high_intent() -> RuntimeIntent:
    return RuntimeIntent(
        intent_id="intent-002",
        kind=IntentKind.EXECUTION,
        goal="Run a shell command that modifies the file system",
        risk=RiskLevel.HIGH,
        timeout_seconds=600,
        recovery_strategy=RecoveryStrategy.RETRY,
    )


@pytest.fixture
def critical_intent() -> RuntimeIntent:
    return RuntimeIntent(
        intent_id="intent-003",
        kind=IntentKind.MIGRATION,
        goal="Execute a critical database migration",
        risk=RiskLevel.CRITICAL,
        timeout_seconds=300,
    )


@pytest.fixture
def tool_registry() -> dict[str, RiskLevel]:
    return {
        "read_file": RiskLevel.LOW,
        "write_file": RiskLevel.MEDIUM,
        "execute_code": RiskLevel.HIGH,
        "shell_exec": RiskLevel.CRITICAL,
    }


# ══════════════════════════════════════════════════════════════
# 1. RuntimeIntent basics
# ══════════════════════════════════════════════════════════════


class TestRuntimeIntent:
    def test_defaults(self) -> None:
        intent = RuntimeIntent(intent_id="test")
        assert intent.intent_id == "test"
        assert intent.kind == IntentKind.UNKNOWN
        assert intent.goal == ""
        assert intent.risk == RiskLevel.LOW
        assert intent.timeout_seconds == 300
        assert intent.max_retries == 3
        assert intent.recovery_strategy == RecoveryStrategy.FAIL_CLOSED
        assert intent.requires_human_review is False
        assert intent.requires_migration_lock is False
        assert intent.may_create_checkpoint is False
        assert intent.metadata == {}

    def test_is_blocked_low(self, low_intent: RuntimeIntent) -> None:
        assert low_intent.is_blocked() is False

    def test_is_blocked_medium(self) -> None:
        intent = RuntimeIntent(intent_id="med", kind=IntentKind.RESEARCH, risk=RiskLevel.MEDIUM)
        assert intent.is_blocked() is False

    def test_is_blocked_high(self, high_intent: RuntimeIntent) -> None:
        assert high_intent.is_blocked() is True

    def test_is_blocked_critical(self, critical_intent: RuntimeIntent) -> None:
        assert critical_intent.is_blocked() is True

    def test_is_blocked_human_review(self) -> None:
        intent = RuntimeIntent(
            intent_id="hr",
            kind=IntentKind.RESEARCH,
            risk=RiskLevel.LOW,
            requires_human_review=True,
        )
        assert intent.is_blocked() is True

    def test_frozen(self) -> None:
        intent = RuntimeIntent(intent_id="frozen")
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            intent.goal = "should fail"  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════
# 2. High-risk keyword blocking
# ══════════════════════════════════════════════════════════════


class TestHighRiskBlockers:
    @pytest.mark.parametrize("kw", HIGH_RISK_KEYWORDS)
    def test_all_keywords_blocked(self, kw: str) -> None:
        intent = RuntimeIntent(intent_id=f"block-{kw}", goal=f"I want to {kw} the database")
        result = check_high_risk_blockers(intent)
        assert result is not None
        assert result.allowed is False
        assert result.risk == RiskLevel.CRITICAL
        assert result.recovery_strategy == RecoveryStrategy.ABORT
        # The reported keyword may be a shorter prefix match
        # (e.g. "disable auth" matches before "disable authentication")
        assert result.block_reason.startswith("high_risk_keyword:")

    def test_innocent_goal_not_blocked(self) -> None:
        intent = RuntimeIntent(
            intent_id="ok",
            goal="Read a file and extract text from it",
            risk=RiskLevel.LOW,
        )
        assert check_high_risk_blockers(intent) is None

    def test_case_insensitive(self) -> None:
        intent = RuntimeIntent(intent_id="ci", goal="DROP TABLE users", risk=RiskLevel.MEDIUM)
        result = check_high_risk_blockers(intent)
        assert result is not None
        assert result.allowed is False
        assert "drop table" in result.block_reason

    def test_permission_change_nonlow_blocked(self) -> None:
        intent = RuntimeIntent(
            intent_id="perm-change",
            kind=IntentKind.PERMISSION_CHANGE,
            goal="Change file permissions for a directory",
            risk=RiskLevel.MEDIUM,
        )
        result = check_high_risk_blockers(intent)
        assert result is not None
        assert result.allowed is False
        assert "permission_change_requires_review" in result.block_reason

    def test_permission_change_low_allowed(self) -> None:
        intent = RuntimeIntent(
            intent_id="perm-low",
            kind=IntentKind.PERMISSION_CHANGE,
            goal="Add a read-only permission entry",
            risk=RiskLevel.LOW,
        )
        assert check_high_risk_blockers(intent) is None

    def test_dependency_change_nonlow_blocked(self) -> None:
        intent = RuntimeIntent(
            intent_id="dep-change",
            kind=IntentKind.DEPENDENCY_CHANGE,
            goal="Update dependency version",
            risk=RiskLevel.MEDIUM,
        )
        result = check_high_risk_blockers(intent)
        assert result is not None
        assert result.allowed is False
        assert "dependency_change_requires_review" in result.block_reason

    def test_critical_migration_blocked(self, critical_intent: RuntimeIntent) -> None:
        result = check_high_risk_blockers(critical_intent)
        assert result is not None
        assert result.allowed is False
        assert "critical_migration_blocked" in result.block_reason


# ══════════════════════════════════════════════════════════════
# 3. Permission checking
# ══════════════════════════════════════════════════════════════


class TestCheckIntentPermission:
    def test_low_intent_allowed(self, low_intent: RuntimeIntent) -> None:
        perm = check_intent_permission(low_intent)
        assert perm.allowed is True
        assert perm.risk == RiskLevel.LOW
        assert perm.requires_human_review is False
        assert perm.block_reason == ""

    def test_high_intent_blocked(self, high_intent: RuntimeIntent) -> None:
        perm = check_intent_permission(high_intent)
        assert perm.allowed is False
        assert perm.risk == RiskLevel.HIGH
        assert perm.requires_human_review is True
        assert "requires_human_review" in perm.block_reason

    def test_critical_intent_blocked(self, critical_intent: RuntimeIntent) -> None:
        perm = check_intent_permission(critical_intent)
        assert perm.allowed is False
        assert perm.risk == RiskLevel.CRITICAL
        assert perm.requires_human_review is True

    def test_blocked_intent_kind(self) -> None:
        intent = RuntimeIntent(
            intent_id="test",
            kind=IntentKind.RELEASE,
            goal="Build a release artifact",
            risk=RiskLevel.LOW,
        )
        perm = check_intent_permission(
            intent,
            blocked_intent_kinds={IntentKind.RELEASE},
        )
        assert perm.allowed is False
        assert "intent_kind_blocked" in perm.block_reason

    def test_critical_tool_blocks(self, tool_registry: dict[str, RiskLevel]) -> None:
        intent_with_critical_tool = RuntimeIntent(
            intent_id="critical-tool",
            kind=IntentKind.EXECUTION,
            goal="Execute a shell command",
            risk=RiskLevel.LOW,
        )
        perm = check_intent_permission(
            intent_with_critical_tool,
            tool_risk_registry=tool_registry,
            blocked_tools={"shell_exec"},
        )
        assert perm.allowed is False
        assert "critical_tool_blocked" in perm.block_reason
        assert perm.risk == RiskLevel.CRITICAL

    def test_timeout_clamping(self) -> None:
        intent = RuntimeIntent(
            intent_id="timeout",
            kind=IntentKind.RESEARCH,
            goal="Long research task",
            risk=RiskLevel.LOW,
            timeout_seconds=7200,
        )
        perm = check_intent_permission(intent, max_timeout_seconds=3600)
        assert perm.allowed is True
        assert perm.effective_timeout_seconds == 3600
        assert "timeout clamped" in perm.reason

    def test_migration_escalated_low_to_medium(self) -> None:
        intent = RuntimeIntent(
            intent_id="mig-escalate",
            kind=IntentKind.MIGRATION,
            goal="Apply a non-critical migration",
            risk=RiskLevel.LOW,
        )
        perm = check_intent_permission(intent)
        assert perm.risk == RiskLevel.MEDIUM
        assert "migration/perm/dep change escalated from low→medium" in perm.reason

    def test_permission_change_escalated_medium_to_high(self) -> None:
        intent = RuntimeIntent(
            intent_id="perm-escalate",
            kind=IntentKind.PERMISSION_CHANGE,
            goal="Modify access control list",
            risk=RiskLevel.MEDIUM,
        )
        perm = check_intent_permission(intent)
        # Medium-risk permission change is blocked by high-risk blocker (CRITICAL)
        assert perm.allowed is False
        assert perm.risk == RiskLevel.CRITICAL
        assert "permission_change_requires_review" in perm.block_reason

    def test_recovery_escalated_for_high_risk(self) -> None:
        intent = RuntimeIntent(
            intent_id="rec-escalate",
            kind=IntentKind.EXECUTION,
            goal="High-risk execution with retry",
            risk=RiskLevel.HIGH,
            recovery_strategy=RecoveryStrategy.RETRY,
        )
        perm = check_intent_permission(intent)
        assert perm.recovery_strategy == RecoveryStrategy.FAIL_CLOSED
        assert "recovery escalated to fail_closed" in perm.reason


# ══════════════════════════════════════════════════════════════
# 4. RuntimeRecovery
# ══════════════════════════════════════════════════════════════


class TestRuntimeRecovery:
    def test_should_retry_below_max(self) -> None:
        recovery = RuntimeRecovery(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=3,
            attempt=1,
        )
        assert recovery.should_retry() is True

    def test_should_not_retry_at_max(self) -> None:
        recovery = RuntimeRecovery(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=3,
            attempt=3,
        )
        assert recovery.should_retry() is False

    def test_should_not_retry_abort(self) -> None:
        recovery = RuntimeRecovery(
            strategy=RecoveryStrategy.ABORT,
            max_attempts=3,
            attempt=1,
        )
        assert recovery.should_retry() is False

    def test_should_not_retry_fail_closed(self) -> None:
        recovery = RuntimeRecovery(
            strategy=RecoveryStrategy.FAIL_CLOSED,
            max_attempts=3,
            attempt=1,
        )
        assert recovery.should_retry() is False

    def test_next_attempt(self) -> None:
        recovery = RuntimeRecovery(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=3,
            attempt=1,
            last_error="timeout",
        )
        next_rec = recovery.next_attempt(error="connection refused")
        assert next_rec.attempt == 2
        assert next_rec.last_error == "connection refused"
        assert next_rec.strategy == RecoveryStrategy.RETRY
        assert next_rec.max_attempts == 3

    def test_next_attempt_preserves_prev_error(self) -> None:
        recovery = RuntimeRecovery(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=3,
            attempt=1,
            last_error="timeout",
        )
        next_rec = recovery.next_attempt()
        assert next_rec.attempt == 2
        assert next_rec.last_error == "timeout"


# ══════════════════════════════════════════════════════════════
# 5. make_recovery
# ══════════════════════════════════════════════════════════════


class TestMakeRecovery:
    def test_from_intent(self, low_intent: RuntimeIntent) -> None:
        recovery = make_recovery(low_intent)
        assert recovery.strategy == RecoveryStrategy.FAIL_CLOSED
        assert recovery.max_attempts == 3  # max_retries=2 + 1
        assert recovery.attempt == 1
        assert recovery.created_at != ""
        assert recovery.expires_at != ""

    def test_from_permission(self, high_intent: RuntimeIntent) -> None:
        perm = check_intent_permission(high_intent)
        recovery = make_recovery(high_intent, error="permission denied", permission=perm)
        assert recovery.strategy == RecoveryStrategy.FAIL_CLOSED  # escalated
        assert recovery.last_error == "permission denied"
        assert recovery.retry_delay_seconds >= 1

    def test_retry_delay_reasonable(self) -> None:
        intent = RuntimeIntent(
            intent_id="fast",
            kind=IntentKind.EVALUATION,
            goal="Quick evaluation",
            risk=RiskLevel.LOW,
            timeout_seconds=30,
        )
        recovery = make_recovery(intent)
        # timeout/10 = 3, clamped [1, 60]
        assert 1 <= recovery.retry_delay_seconds <= 60

    def test_expires_at_after_timeout(self) -> None:
        intent = RuntimeIntent(
            intent_id="timed",
            kind=IntentKind.RESEARCH,
            risk=RiskLevel.LOW,
            timeout_seconds=1,
        )
        recovery = make_recovery(intent)
        # expires_at should be ~1 second in the future
        future = datetime.fromisoformat(recovery.expires_at)
        delta = (future - datetime.now(timezone.utc)).total_seconds()
        assert 0.5 <= delta <= 5.0


# ══════════════════════════════════════════════════════════════
# 6. Safe defaults
# ══════════════════════════════════════════════════════════════


class TestSafeDefaults:
    def test_safe_tool_registry(self) -> None:
        assert "read_file" in SAFE_TOOL_REGISTRY
        assert "write_file" in SAFE_TOOL_REGISTRY
        assert "terminal" in SAFE_TOOL_REGISTRY
        assert "execute_code" in SAFE_TOOL_REGISTRY
        assert SAFE_TOOL_REGISTRY["read_file"] == RiskLevel.LOW
        assert SAFE_TOOL_REGISTRY["execute_code"] == RiskLevel.HIGH

    def test_safe_intent_kinds(self) -> None:
        assert IntentKind.RESEARCH in SAFE_INTENT_KINDS
        assert IntentKind.INGESTION in SAFE_INTENT_KINDS
        assert IntentKind.MIGRATION not in SAFE_INTENT_KINDS
        assert IntentKind.PERMISSION_CHANGE not in SAFE_INTENT_KINDS
        assert IntentKind.RELEASE not in SAFE_INTENT_KINDS

    def test_blocked_high_risk_intents(self) -> None:
        assert IntentKind.MIGRATION in BLOCKED_HIGH_RISK_INTENTS
        assert IntentKind.PERMISSION_CHANGE in BLOCKED_HIGH_RISK_INTENTS
        assert IntentKind.DEPENDENCY_CHANGE in BLOCKED_HIGH_RISK_INTENTS
        assert IntentKind.RELEASE in BLOCKED_HIGH_RISK_INTENTS

    def test_intent_enums_exhaustive(self) -> None:
        """Every IntentKind belongs to either safe, blocked, or high-risk set."""
        all_kinds = set(IntentKind)
        classified = BLOCKED_HIGH_RISK_INTENTS | SAFE_INTENT_KINDS | {IntentKind.UNKNOWN, IntentKind.RECOVERY}
        # Each kind should appear at least in one set
        assert all_kinds == classified, f"Unclassified kinds: {all_kinds - classified}"


# ══════════════════════════════════════════════════════════════
# 7. Edge cases
# ══════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_empty_goal_not_blocked(self) -> None:
        intent = RuntimeIntent(intent_id="empty", goal="", risk=RiskLevel.LOW)
        perm = check_intent_permission(intent)
        assert perm.allowed is True

    def test_no_blocked_kinds_not_blocked(self) -> None:
        intent = RuntimeIntent(intent_id="no-block", kind=IntentKind.RESEARCH, risk=RiskLevel.LOW)
        perm = check_intent_permission(intent, blocked_intent_kinds=set())
        assert perm.allowed is True

    def test_no_tools_not_blocked(self, low_intent: RuntimeIntent) -> None:
        perm = check_intent_permission(low_intent, tool_risk_registry={})
        assert perm.allowed is True

    def test_recovery_frozen(self) -> None:
        recovery = RuntimeRecovery(strategy=RecoveryStrategy.RETRY, max_attempts=3)
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            recovery.strategy = RecoveryStrategy.ABORT  # type: ignore[misc]

    def test_high_risk_keywords_tuple(self) -> None:
        assert isinstance(HIGH_RISK_KEYWORDS, tuple)
        assert len(HIGH_RISK_KEYWORDS) > 20  # Substantial list

    def test_kind_run_allowed(self) -> None:
        """Low-risk EXECUTION with no blockers should be allowed."""
        intent = RuntimeIntent(
            intent_id="run",
            kind=IntentKind.EXECUTION,
            goal="Execute a safe file operation",
            risk=RiskLevel.LOW,
            timeout_seconds=60,
        )
        perm = check_intent_permission(intent)
        assert perm.allowed is True

    def test_sync_low_allowed(self) -> None:
        intent = RuntimeIntent(
            intent_id="sync",
            kind=IntentKind.SYNCHRONIZATION,
            goal="Sync knowledge base with local files",
            risk=RiskLevel.LOW,
        )
        perm = check_intent_permission(intent)
        assert perm.allowed is True

    def test_unknown_kind_allowed_low(self) -> None:
        intent = RuntimeIntent(intent_id="unknown", risk=RiskLevel.LOW)
        perm = check_intent_permission(intent)
        assert perm.allowed is True


# ══════════════════════════════════════════════════════════════
# 8. Integration — typed contract end-to-end
# ══════════════════════════════════════════════════════════════


class TestIntegration:
    def test_intent_to_permission_to_recovery(self) -> None:
        """Create a safe intent, check permission, build recovery — all pass."""
        intent = RuntimeIntent(
            intent_id="e2e-001",
            kind=IntentKind.INGESTION,
            goal="Convert a PDF document to text and ingest it",
            risk=RiskLevel.LOW,
            timeout_seconds=120,
            max_retries=2,
            recovery_strategy=RecoveryStrategy.RETRY,
        )
        perm = check_intent_permission(intent)
        assert perm.allowed is True
        assert perm.risk == RiskLevel.LOW

        recovery = make_recovery(intent, permission=perm)
        assert recovery.max_attempts == 3
        assert recovery.should_retry() is True

    def test_high_risk_intent_blocked_chain(self) -> None:
        """High-risk intent is blocked, recovery is fail-closed."""
        intent = RuntimeIntent(
            intent_id="e2e-002",
            kind=IntentKind.EXECUTION,
            goal="Execute a code that may delete important files",
            risk=RiskLevel.HIGH,
        )
        perm = check_intent_permission(intent)
        assert perm.allowed is False
        assert perm.risk == RiskLevel.HIGH
        assert perm.requires_human_review is True
        assert perm.recovery_strategy == RecoveryStrategy.FAIL_CLOSED

        recovery = make_recovery(intent, permission=perm)
        assert recovery.strategy == RecoveryStrategy.FAIL_CLOSED
        assert recovery.should_retry() is False

    def test_dangerous_keyword_aborts(self) -> None:
        """A 'drop table' keyword aborts immediately with no retry."""
        intent = RuntimeIntent(
            intent_id="e2e-003",
            kind=IntentKind.EXECUTION,
            goal="Execute DROP TABLE on the main database",
            risk=RiskLevel.LOW,  # Even low risk
        )
        perm = check_intent_permission(intent)
        assert perm.allowed is False
        assert perm.risk == RiskLevel.CRITICAL
        assert perm.recovery_strategy == RecoveryStrategy.ABORT

    def test_migration_escalation_and_permission(self) -> None:
        """A low-risk migration gets escalated to medium, still allowed."""
        intent = RuntimeIntent(
            intent_id="e2e-004",
            kind=IntentKind.MIGRATION,
            goal="Apply a safe index migration",
            risk=RiskLevel.LOW,
        )
        perm = check_intent_permission(intent)
        # Escalated low→medium
        assert perm.risk == RiskLevel.MEDIUM
        # Medium risk requires review? No — only high/critical block
        assert perm.allowed is True

    def test_serialize_to_json(self) -> None:
        """RuntimeIntent can be JSON-serialized."""
        intent = RuntimeIntent(
            intent_id="json-test",
            kind=IntentKind.INGESTION,
            goal="Ingest a file",
            risk=RiskLevel.LOW,
        )
        data = {
            "intent_id": intent.intent_id,
            "kind": intent.kind.value,
            "goal": intent.goal,
            "risk": intent.risk.value,
        }
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["intent_id"] == "json-test"
        assert deserialized["kind"] == "ingestion"
