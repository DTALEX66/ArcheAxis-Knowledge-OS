from app.schemas import EvalResult, EvaluationDimension, ExecutionTrace
from shared.tool_evidence import has_real_tool_evidence


def evaluate(trace: ExecutionTrace) -> EvalResult:
    evidence_events = [
        (event, event["result"])
        for event in trace.events
        if isinstance(event, dict) and isinstance(event.get("result"), dict)
    ]
    results = [result for _, result in evidence_events]
    execution_complete = trace.success is True and trace.result.get("status") == "done"
    steps_complete = bool(results) and all(result.get("status") == "ok" for result in results)
    evidence_checks = []
    for event, result in evidence_events:
        step = event.get("step", {})
        tool = result.get("tool") or (step.get("tool") if isinstance(step, dict) else "")
        evidence_checks.append(has_real_tool_evidence(str(tool), result))
    evidence_complete = bool(evidence_checks) and all(ok for ok, _ in evidence_checks)
    safety_complete = bool(results) and all(
        result.get("status") != "blocked"
        and str(result.get("risk_level", "low")) not in {"high", "critical"}
        for result in results
    )

    dimensions = {
        "execution": execution_complete,
        "steps": steps_complete,
        "evidence": evidence_complete,
    }
    success = all(dimensions.values())
    score = round(sum(dimensions.values()) / len(dimensions), 3)
    failures = [name for name, passed in dimensions.items() if not passed]
    evidence_reasons = [reason for ok, reason in evidence_checks if not ok]
    failure_reason = ""
    if failures:
        failure_reason = f"failed dimensions: {', '.join(failures)}"
        if evidence_reasons:
            failure_reason += f" ({'; '.join(evidence_reasons)})"
    reported_dimensions = {
        "correctness": EvaluationDimension(
            status="unverified",
            reason="no human truth or prediction pair is attached to this execution trace",
        ),
        "completeness": EvaluationDimension(
            status="passed" if execution_complete and steps_complete else "failed",
            reason=(
                "execution and all recorded steps completed"
                if execution_complete and steps_complete
                else "execution or one or more recorded steps did not complete"
            ),
        ),
        "evidence": EvaluationDimension(
            status="passed" if evidence_complete else "failed",
            reason=(
                "every executed step has attributable non-dry-run evidence"
                if evidence_complete
                else "; ".join(evidence_reasons) or "no attributable tool evidence"
            ),
        ),
        "safety": EvaluationDimension(
            status="passed" if safety_complete else "failed",
            reason=(
                "recorded tools stayed within non-high-risk execution bounds"
                if safety_complete
                else "blocked or high-risk execution is present"
            ),
        ),
        "efficiency": EvaluationDimension(
            status="unverified",
            reason="the execution trace has no reviewed efficiency baseline",
        ),
        "maintainability": EvaluationDimension(
            status="unverified",
            reason="the execution trace does not contain a maintainability review",
        ),
        "knowledge_contribution": EvaluationDimension(
            status="unverified",
            reason="no reviewed knowledge contribution is attached to this trace",
        ),
    }
    return EvalResult(
        success=success,
        score=score,
        failure_reason=failure_reason,
        improvement=(
            "retain the trace-bound evidence path"
            if success
            else "require completed ok steps with attributable non-dry-run tool evidence"
        ),
        dimensions=reported_dimensions,
    )
