from app.schemas import EvalResult, ExecutionTrace


def evaluate(trace: ExecutionTrace) -> EvalResult:
    success = bool(trace.success)
    score = 1.0 if success else 0.0
    return EvalResult(
        success=success,
        score=score,
        failure_reason="" if success else "execution failed",
        improvement="replace stubs with real tools and add stronger checks"
        if success
        else "inspect trace events",
    )
