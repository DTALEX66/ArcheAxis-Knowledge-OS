"""Model/provider-neutral evaluation/trace fallback with redaction gates.

Default behaviour: local, desensitised, project-artifact-bound. Never writes
secrets, auth/session tokens, or user data to disk. Designed to work without
the full app/ runtime (lightweight dataclasses, no Pydantic dependency).

Coverage:
    - success / failure / retry / replay evaluation
    - trace redaction (strip known secret patterns)
    - schema / contract failure detection
    - project-local artifact writing under .project-local/task-runtime/evaluation/

Usage:
    from shared.evaluation_fallback import (
        evaluate_trace,
        redact_trace,
        EvaluationResult,
        EvaluationDimension,
        TraceRedactionPolicy,
        write_evaluation_artifact,
    )
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

# ── Types ──────────────────────────────────────────────────────────────

DimensionStatus = Literal["passed", "failed", "unverified"]


@dataclass(frozen=True)
class EvaluationDimension:
    """One evaluation dimension with status and reason."""
    status: DimensionStatus
    reason: str


@dataclass(frozen=True)
class EvaluationEvent:
    """A single event in an evaluation trace.

    Fields:
        step: what was attempted (tool name, action, …).
        status: outcome of this step.
        risk_level: assessed risk of the step.
        duration_ms: how long the step took.
        detail: human-readable detail (already redacted).
    """
    step: str
    status: Literal["ok", "error", "blocked", "skipped"]
    risk_level: Literal["low", "medium", "high"] = "low"
    duration_ms: int = 0
    detail: str = ""


@dataclass(frozen=True)
class EvaluationResult:
    """Result of evaluating one execution trace.

    Fields:
        success: overall pass/fail.
        score: 0.0 – 1.0 summary score.
        failure_reason: why it failed (empty on success).
        improvement: suggested improvement (empty if not actionable).
        dimensions: named dimension results.
        events: flattened evaluation events (already redacted).
        schema_version: contract version string.
        trace_id: identifier for the evaluated trace.
        evaluated_at: ISO-8601 timestamp.
        artifact_path: path to the written artifact file (empty if not persisted).
    """
    success: bool
    score: float = 0.0
    failure_reason: str = ""
    improvement: str = ""
    dimensions: dict[str, EvaluationDimension] = field(default_factory=dict)
    events: list[EvaluationEvent] = field(default_factory=list)
    schema_version: str = "evaluation-fallback-v1"
    trace_id: str = ""
    evaluated_at: str = ""
    artifact_path: str = ""


@dataclass(frozen=True)
class RedactedTrace:
    """A runtime-safety-verified trace after redaction.

    Fields:
        trace_id: stable identifier.
        events: redacted event list.
        result: redacted result dict.
        success: original success value (bool or None).
        redacted_fields: count of fields that were redacted.
        original_hash: sha256 of the pre-redaction JSON dump (for audit).
        redacted_hash: sha256 of the post-redaction JSON dump.
        wrote_secrets: True if any secret-like value was detected and stripped.
    """
    trace_id: str
    events: list[dict[str, Any]]
    result: dict[str, Any]
    success: bool | None
    redacted_fields: int = 0
    original_hash: str = ""
    redacted_hash: str = ""
    wrote_secrets: bool = False


# ── Redaction patterns ─────────────────────────────────────────────────

_REDACT_PATTERNS: list[tuple[str, str]] = [
    # API keys / tokens
    (r'(?i)(api[_-]?key|apikey|token|secret|password|passwd|jwt|auth[_-]?token)["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]{16,}', r'\1 = "[REDACTED]"'),
    # Bearer tokens in headers / URLs
    (r'(?i)(bearer\s+)[A-Za-z0-9_\-\.]{8,}', r'\1[REDACTED]'),
    # Authorization headers
    (r'(?i)(authorization["\']?\s*[:=]\s*["\']?)[A-Za-z0-9_\-\.\+/=]{8,}', r'\1[REDACTED]'),
    # SSH keys (inline)
    (r'(-----BEGIN[ A-Z]+KEY-----[\s\S]+?-----END[ A-Z]+KEY-----)', '[REDACTED PRIVATE KEY]'),
    # Cookie / session values
    (r'(?i)(session|cookie|connect\.sid|_session_id)["\']?\s*[:=]\s*["\']?[A-Za-z0-9%\-\.]{8,}', r'\1 = "[REDACTED]"'),
    # Database connection strings with credentials
    (r'(?i)(postgres(?:ql)?|mysql|mongodb|sqlite|redis)://[^@]+@', r'\1://[REDACTED]@'),
    # AWS / cloud keys
    (r'(?i)(AKIA[0-9A-Z]{16})', '[REDACTED AWS KEY]'),
    (r'(?i)(ASIA[0-9A-Z]{16})', '[REDACTED AWS KEY]'),
    # Private / user-home paths
    (r'(?i)(/home/[^/"\'\\\s]+)', '[REDACTED HOME PATH]'),
    (r'(?i)(C:\\Users\\[^\\\\"\'\s]+)', '[REDACTED USER PATH]'),
    # /vault/ or /vaults/ paths
    (r'(?i)([^"\']*/vault[^"\'\s]*)', '[REDACTED VAULT PATH]'),
    # raw file content fields > 200 chars (likely contains user data)
    # Note: this pattern matches JSON-serialized "content":"longtext..." pairs.
    # For raw string values, the key-name-based redaction in _redact_dict handles length.
]
_HOME_PATH_MARKER = "/" + "home" + "/"


@dataclass(frozen=True)
class TraceRedactionPolicy:
    """Policy controlling what gets redacted from a trace.

    Fields:
        redact_api_keys: strip API keys, tokens, passwords (default True).
        redact_paths: strip user-home and vault paths (default True).
        redact_content_fields: strip large content/body/text fields (default True).
        max_content_length: truncate content fields to this many chars (0 = off).
    """
    redact_api_keys: bool = True
    redact_paths: bool = True
    redact_content_fields: bool = True
    max_content_length: int = 200  # default: truncate content fields > 200 chars


def redact_trace(
    trace: dict[str, Any],
    policy: TraceRedactionPolicy | None = None,
) -> RedactedTrace:
    """Redact sensitive values from a trace dict.

    Returns a RedactedTrace with all secrets stripped. The original and
    redacted sha256 hashes are computed for audit trail verification.
    """
    policy = policy or TraceRedactionPolicy()
    trace_id = trace.get("id", trace.get("trace_id", "unknown"))
    events = list(trace.get("events", []))
    result = dict(trace.get("result", {}))
    success = trace.get("success")

    original_json = json.dumps({"events": events, "result": result}, default=str, sort_keys=True)
    original_hash = hashlib.sha256(original_json.encode("utf-8")).hexdigest()

    redacted_fields = 0

    # Helper: apply redaction patterns to a string value
    def _redact_string(value: str) -> str:
        nonlocal redacted_fields
        original = value
        for pattern, replacement in _REDACT_PATTERNS:
            flags = 0
            # SSH keys and other multi-line patterns need DOTALL
            if "BEGIN" in pattern and "KEY-----" in pattern:
                flags = re.DOTALL
            if (policy.redact_api_keys and pattern.startswith("(?i)")) or (
                policy.redact_paths
                and (_HOME_PATH_MARKER in pattern or "Users" in pattern or "vault" in pattern.lower())
            ):
                value = re.sub(pattern, replacement, value, flags=flags)
            elif (
                not pattern.startswith("(?i)")
                and _HOME_PATH_MARKER not in pattern
                and "Users" not in pattern
                and "vault" not in pattern.lower()
                and any(marker in replacement for marker in ("SECRET", "AWS", "PRIVATE"))
            ):
                # Apply generic patterns
                value = re.sub(pattern, replacement, value, flags=flags)
        if value != original:
            # Count how many bytes differ
            diff = abs(len(value) - len(original)) or 1
            redacted_fields += max(diff // 8, 1)
        return value

    def _redact_dict(d: dict[str, Any], depth: int = 0) -> dict[str, Any]:
        nonlocal redacted_fields
        if depth > 10:
            return d
        result_dict: dict[str, Any] = {}
        for key, value in d.items():
            # Key-based redaction: check if key name matches a secret pattern
            lower_key = key.lower()
            if policy.redact_api_keys and any(
                pat in lower_key for pat in [
                    "api_key", "apikey", "token", "secret", "password",
                    "passwd", "jwt_secret", "auth", "credential",
                ]
            ) and isinstance(value, str) and len(value) > 3 and value.strip():
                result_dict[key] = "[REDACTED]"
                redacted_fields += 1
                continue

            # Content/body/text fields: truncate or redact if too long
            if (
                policy.redact_content_fields
                and isinstance(value, str)
                and len(value) > policy.max_content_length
                and lower_key in ("content", "body", "text", "raw")
            ):
                if policy.max_content_length > 0:
                    value = value[:policy.max_content_length] + "... [TRUNCATED]"
                else:
                    value = "[REDACTED CONTENT]"
                redacted_fields += 1

            if isinstance(value, str):
                if policy.max_content_length > 0 and len(value) > policy.max_content_length:
                    value = value[:policy.max_content_length] + "... [TRUNCATED]"
                    redacted_fields += 1
                result_dict[key] = _redact_string(value)
            elif isinstance(value, dict):
                result_dict[key] = _redact_dict(value, depth + 1)
            elif isinstance(value, list):
                result_dict[key] = _redact_list(value, depth + 1)
            else:
                result_dict[key] = value
        return result_dict

    def _redact_list(items: list[Any], depth: int = 0) -> list[Any]:
        if depth > 10:
            return items
        result_list: list[Any] = []
        for item in items:
            if isinstance(item, dict):
                result_list.append(_redact_dict(item, depth + 1))
            elif isinstance(item, list):
                result_list.append(_redact_list(item, depth + 1))
            elif isinstance(item, str):
                result_list.append(_redact_string(item))
            else:
                result_list.append(item)
        return result_list

    redacted_events = _redact_list(events)
    redacted_result = _redact_dict(result)

    redacted_json = json.dumps(
        {"events": redacted_events, "result": redacted_result},
        default=str, sort_keys=True,
    )
    redacted_hash = hashlib.sha256(redacted_json.encode("utf-8")).hexdigest()
    wrote_secrets = redacted_fields > 0

    return RedactedTrace(
        trace_id=trace_id,
        events=redacted_events,
        result=redacted_result,
        success=success,
        redacted_fields=redacted_fields,
        original_hash=original_hash,
        redacted_hash=redacted_hash,
        wrote_secrets=wrote_secrets,
    )


# ── Evaluation ─────────────────────────────────────────────────────────

_DEFAULT_DIMENSIONS: list[tuple[str, str, str]] = [
    ("correctness", "unverified", "no human truth/prediction pair for automated correctness"),
    ("completeness", "unverified", "no ground-truth coverage baseline"),
    ("evidence", "unverified", "no execution trace evidence verified"),
    ("safety", "unverified", "no risk assessment performed"),
    ("efficiency", "unverified", "no performance baseline"),
    ("maintainability", "unverified", "no code review performed"),
    ("knowledge_contribution", "unverified", "no lesson extracted"),
]


def _infer_dimension_status(events: list[EvaluationEvent], result: dict[str, Any]) -> dict[str, EvaluationDimension]:
    """Infer dimension statuses from evaluation events and result data.

    This is a local fallback — it does not call any model or external API.
    """
    dims: dict[str, EvaluationDimension] = {}

    # Evidence: check if any events have ok status
    ok_events = [e for e in events if e.status == "ok"]
    error_events = [e for e in events if e.status == "error"]
    blocked_events = [e for e in events if e.status == "blocked"]

    if error_events or blocked_events:
        dims["evidence"] = EvaluationDimension(
            status="failed",
            reason=f"{len(error_events)} error(s) and {len(blocked_events)} blocked step(s) found",
        )
    elif ok_events:
        dims["evidence"] = EvaluationDimension(
            status="passed",
            reason=f"{len(ok_events)} step(s) completed successfully",
        )
    else:
        dims["evidence"] = EvaluationDimension(
            status="unverified",
            reason="no events recorded",
        )

    # Completeness: check result for known keys
    result_keys = set(result.keys())
    expected_keys = {"status", "outputs"}
    present = result_keys & expected_keys
    if present == expected_keys:
        dims["completeness"] = EvaluationDimension(
            status="passed",
            reason=f"result contains all expected keys: {sorted(present)}",
        )
    elif present:
        dims["completeness"] = EvaluationDimension(
            status="unverified",
            reason=f"result contains partial keys: {sorted(present)}",
        )
    else:
        dims["completeness"] = EvaluationDimension(
            status="failed",
            reason=f"result is missing expected keys: {expected_keys}",
        )

    # Safety: check for high-risk events
    high_risk = [e for e in events if e.risk_level == "high"]
    if high_risk:
        dims["safety"] = EvaluationDimension(
            status="failed",
            reason=f"{len(high_risk)} high-risk step(s) detected",
        )
    else:
        dims["safety"] = EvaluationDimension(
            status="passed",
            reason="no high-risk steps detected",
        )

    # Correctness: check overall success
    overall_success = result.get("success", result.get("status")) if isinstance(result, dict) else None
    if overall_success in (True, "done", "completed", "success"):
        dims["correctness"] = EvaluationDimension(
            status="passed",
            reason="task completed successfully",
        )
    elif overall_success in (False, "failed", "error", "blocked"):
        dims["correctness"] = EvaluationDimension(
            status="failed",
            reason=f"task ended with status: {overall_success}",
        )

    # Efficiency: check if there are events with duration
    if events:
        total_ms = sum(e.duration_ms for e in events)
        if total_ms > 60_000:
            dims["efficiency"] = EvaluationDimension(
                status="failed",
                reason=f"total duration {total_ms}ms exceeds 60s threshold",
            )
        elif total_ms > 10_000:
            dims["efficiency"] = EvaluationDimension(
                status="unverified",
                reason=f"total duration {total_ms}ms exceeds 10s caution threshold",
            )
        else:
            dims["efficiency"] = EvaluationDimension(
                status="passed",
                reason=f"total duration {total_ms}ms within limits",
            )

    # Fill in any remaining defaults
    for name, status, reason in _DEFAULT_DIMENSIONS:
        if name not in dims:
            dims[name] = EvaluationDimension(status=status, reason=reason)

    return dims


def evaluate_trace(
    trace: dict[str, Any] | RedactedTrace,
    artifact_dir: str | Path | None = None,
    redaction_policy: TraceRedactionPolicy | None = None,
) -> EvaluationResult:
    """Evaluate an execution trace using local fallback (no model/API call).

    Steps:
        1. Redact the trace if not already redacted.
        2. Flatten events into EvaluationEvent list.
        3. Infer dimension statuses from event data.
        4. Compute overall score.
        5. Optionally write artifact to project-local dir.

    Args:
        trace: Raw trace dict or pre-redacted RedactedTrace.
        artifact_dir: If set, writes evaluation JSON artifact here.
        redaction_policy: Controls what gets redacted.

    Returns:
        EvaluationResult with local-only dimension inferences.
    """
    # Step 1: Redact if needed
    if isinstance(trace, RedactedTrace):
        redacted = trace
        trace_id = redacted.trace_id
        events_raw = redacted.events
        result = redacted.result
    else:
        redacted = redact_trace(trace, redaction_policy)
        trace_id = redacted.trace_id
        events_raw = redacted.events
        result = redacted.result
        trace_id = trace.get("id", trace.get("trace_id", trace_id))

    # Step 2: Flatten events
    eval_events: list[EvaluationEvent] = []
    for raw_event in events_raw:
        if not isinstance(raw_event, dict):
            continue
        step = raw_event.get("step", {})
        step_name = ""
        if isinstance(step, dict):
            step_name = step.get("tool", step.get("action", str(step)))
        elif isinstance(step, str):
            step_name = step
        else:
            step_name = str(step)

        event_result = raw_event.get("result", {})
        if isinstance(event_result, dict):
            evt_status = event_result.get("status", "ok")
            evt_risk = event_result.get("risk_level", "low")
        else:
            evt_status = "ok"
            evt_risk = "low"

        # Normalise status
        if evt_status in ("ok", "passed", "success", "done", True):
            norm_status: Literal["ok", "error", "blocked", "skipped"] = "ok"
        elif evt_status in ("error", "failed", False):
            norm_status = "error"
        elif evt_status in ("blocked",):
            norm_status = "blocked"
        else:
            norm_status = "skipped"

        eval_events.append(EvaluationEvent(
            step=step_name,
            status=norm_status,
            risk_level=evt_risk if evt_risk in ("low", "medium", "high") else "low",
            detail=str(event_result.get("error", event_result.get("detail", "")))[:200],
        ))

    # Step 3: Infer dimensions
    dimensions = _infer_dimension_status(eval_events, result)

    # Step 4: Compute overall score
    all_passed = [d for d in dimensions.values() if d.status == "passed"]
    all_failed = [d for d in dimensions.values() if d.status == "failed"]
    all_total = len(dimensions)
    if all_total == 0:
        score = 0.0
    else:
        score = max(0.0, min(1.0, len(all_passed) / all_total)) if not all_failed else 0.0

    overall_success = len(all_failed) == 0 and len(all_passed) >= 1

    failure_reason = ""
    improvement = ""
    if all_failed:
        failed_names = [n for n, d in dimensions.items() if d.status == "failed"]
        failure_reason = f"dimensions failed: {', '.join(failed_names)}"
        improvement = f"address failures in: {', '.join(failed_names)}"
    elif not all_passed:
        failure_reason = "no dimensions passed"
        improvement = "ensure at least one evaluation dimension can be verified"

    evaluated_at = datetime.now(timezone.utc).isoformat()

    # Step 5: Write artifact
    artifact_path = ""
    if artifact_dir:
        artifact_path = _write_evaluation_artifact(
            trace_id=trace_id,
            success=overall_success,
            score=score,
            failure_reason=failure_reason,
            improvement=improvement,
            dimensions={k: asdict(v) for k, v in dimensions.items()},
            events=[asdict(e) for e in eval_events],
            redacted=redacted,
            artifact_dir=artifact_dir,
        )

    return EvaluationResult(
        success=overall_success,
        score=score,
        failure_reason=failure_reason,
        improvement=improvement,
        dimensions=dimensions,
        events=eval_events,
        trace_id=trace_id,
        evaluated_at=evaluated_at,
        artifact_path=artifact_path,
    )


# ── Artifact writer ────────────────────────────────────────────────────

def _write_evaluation_artifact(
    trace_id: str,
    success: bool,
    score: float,
    failure_reason: str,
    improvement: str,
    dimensions: dict[str, dict[str, str]],
    events: list[dict[str, Any]],
    redacted: RedactedTrace,
    artifact_dir: str | Path,
) -> str:
    """Write an evaluation artifact to a project-local directory.

    Produces a JSON file with redaction metadata alongside the evaluation
    result. Never writes raw secrets — only the redaction stats hash.
    """
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", trace_id)[:64]
    artifact_path = artifact_dir / f"eval_{safe_id}_{int(time.time())}.json"

    artifact = {
        "schema_version": "evaluation-fallback-v1",
        "trace_id": trace_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "score": score,
        "failure_reason": failure_reason,
        "improvement": improvement,
        "dimensions": dimensions,
        "events": events,
        "redaction": {
            "redacted_fields": redacted.redacted_fields,
            "wrote_secrets": redacted.wrote_secrets,
            "original_hash": redacted.original_hash,
            "redacted_hash": redacted.redacted_hash,
            "hashes_match_after_redaction": redacted.original_hash != redacted.redacted_hash,
        },
    }

    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return str(artifact_path)


# ── Replay / retry helpers ────────────────────────────────────────────

def replay_evaluation(
    artifact_path: str | Path,
) -> EvaluationResult | None:
    """Replay a previously persisted evaluation from its artifact file.

    Returns the EvaluationResult (reconstructed from JSON) if the file
    exists and parses correctly, or None on failure.
    """
    path = Path(artifact_path)
    if not path.is_file():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Validate schema
    if data.get("schema_version") != "evaluation-fallback-v1":
        return None

    dims = {}
    for name, d in data.get("dimensions", {}).items():
        dims[name] = EvaluationDimension(
            status=d.get("status", "unverified"),
            reason=d.get("reason", ""),
        )

    evts = []
    for e in data.get("events", []):
        evts.append(EvaluationEvent(
            step=e.get("step", ""),
            status=e.get("status", "skipped"),
            risk_level=e.get("risk_level", "low"),
            duration_ms=e.get("duration_ms", 0),
            detail=e.get("detail", ""),
        ))

    return EvaluationResult(
        success=data.get("success", False),
        score=data.get("score", 0.0),
        failure_reason=data.get("failure_reason", ""),
        improvement=data.get("improvement", ""),
        dimensions=dims,
        events=evts,
        schema_version=data.get("schema_version", "evaluation-fallback-v1"),
        trace_id=data.get("trace_id", ""),
        evaluated_at=data.get("evaluated_at", ""),
        artifact_path=str(path),
    )


# ── Schema / contract validation ──────────────────────────────────────

@dataclass(frozen=True)
class ContractFailure:
    """A single contract/schema violation found during evaluation."""
    field: str
    expected: str
    actual: str
    severity: Literal["error", "warning"] = "error"


def validate_evaluation_schema(data: dict[str, Any]) -> list[ContractFailure]:
    """Validate that a dict conforms to the evaluation schema.

    Returns a list of ContractFailures; empty list means valid.
    """
    failures: list[ContractFailure] = []

    # Check required top-level keys
    required_keys = ["success", "score", "failure_reason", "improvement"]
    for key in required_keys:
        if key not in data:
            failures.append(ContractFailure(
                field=key,
                expected="present",
                actual="missing",
                severity="error",
            ))

    # Type checks
    if "success" in data and not isinstance(data["success"], bool):
        failures.append(ContractFailure(
            field="success",
            expected="bool",
            actual=str(type(data["success"]).__name__),
            severity="error",
        ))

    if "score" in data:
        if isinstance(data["score"], bool):
            failures.append(ContractFailure(
                field="score",
                expected="float or int",
                actual="bool",
                severity="error",
            ))
        elif not isinstance(data["score"], (int, float)):
            failures.append(ContractFailure(
                field="score",
                expected="float or int",
                actual=str(type(data["score"]).__name__),
                severity="error",
            ))

    # Dimensions should be a dict
    dims = data.get("dimensions", {})
    if not isinstance(dims, dict):
        failures.append(ContractFailure(
            field="dimensions",
            expected="dict",
            actual=str(type(dims).__name__),
            severity="error",
        ))
    else:
        for dim_name, dim_data in dims.items():
            if isinstance(dim_data, dict):
                if "status" not in dim_data:
                    failures.append(ContractFailure(
                        field=f"dimensions.{dim_name}.status",
                        expected="present",
                        actual="missing",
                        severity="error",
                    ))
                elif dim_data.get("status") not in ("passed", "failed", "unverified"):
                    failures.append(ContractFailure(
                        field=f"dimensions.{dim_name}.status",
                        expected="passed | failed | unverified",
                        actual=str(dim_data.get("status", "")),
                        severity="error",
                    ))

    # Events should be a list
    events = data.get("events", [])
    if not isinstance(events, list):
        failures.append(ContractFailure(
            field="events",
            expected="list",
            actual=str(type(events).__name__),
            severity="error",
        ))

    return failures


# ── Default artifact root resolver ────────────────────────────────────

def default_artifact_dir() -> Path:
    """Return the default project-local evaluation artifact directory.

    Resolves relative to ARCHEAXIS_DATA_DIR (fallback COGNITIVE_DATA_DIR), then project root, then
    .project-local/task-runtime/evaluation/. Creates if needed.
    """
    env_dir = os.environ.get("ARCHEAXIS_DATA_DIR", "") or os.environ.get("COGNITIVE_DATA_DIR", "")
    if env_dir:
        base = Path(env_dir)
    else:
        # Walk up to find project root
        cwd = Path.cwd()
        base = cwd

    artifact_dir = base / ".project-local" / "task-runtime" / "evaluation"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir
