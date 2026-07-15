from app.schemas import EvalResult, ExecutionTrace
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
    return EvalResult(
        success=success,
        score=score,
        failure_reason=failure_reason,
        improvement=(
            "retain the trace-bound evidence path"
            if success
            else "require completed ok steps with attributable non-dry-run tool evidence"
        ),
    )
