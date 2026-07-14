"""Identity-preserving exports of the existing runtime contracts."""

from app.adapters.evaluation import from_runtime_evaluation, to_runtime_evaluation
from app.adapters.execution_trace import (
    from_runtime_trace,
    from_trace_row,
    to_runtime_trace,
    to_trace_row,
)
from app.adapters.taskpack import (
    RuntimeTaskProjection,
    from_knowledge_taskpack,
    project_to_runtime,
    to_knowledge_taskpack,
)
from app.contracts.v1 import (
    CONTRACT_VERSION,
    EvaluationV1,
    ExecutionTraceV1,
    TaskPackV1,
    TaskStepV1,
)
from app.schemas import (
    AttentionDecision,
    ContextPack,
    CoreObject,
    EvalResult,
    ExecutionTrace,
    MachineLesson,
    PermissionDecision,
    TaskPack,
)

__all__ = [
    "AttentionDecision",
    "CONTRACT_VERSION",
    "ContextPack",
    "CoreObject",
    "EvalResult",
    "EvaluationV1",
    "ExecutionTrace",
    "ExecutionTraceV1",
    "MachineLesson",
    "PermissionDecision",
    "RuntimeTaskProjection",
    "TaskPack",
    "TaskPackV1",
    "TaskStepV1",
    "from_knowledge_taskpack",
    "from_runtime_evaluation",
    "from_runtime_trace",
    "from_trace_row",
    "project_to_runtime",
    "to_runtime_evaluation",
    "to_runtime_trace",
    "to_trace_row",
    "to_knowledge_taskpack",
]
