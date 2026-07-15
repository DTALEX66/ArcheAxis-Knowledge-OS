"""Identity-preserving exports of the existing runtime contracts."""

from app.adapters.claim import bind_legacy_evidence, verify_with_legacy_evidence
from app.adapters.evaluation import from_runtime_evaluation, to_runtime_evaluation
from app.adapters.execution_trace import (
    from_runtime_trace,
    from_trace_row,
    to_runtime_trace,
    to_trace_row,
)
from app.adapters.lesson import (
    from_lesson_row,
    from_runtime_lesson,
    to_lesson_row,
    to_runtime_lesson,
)
from app.adapters.source_record import from_kb_document_row, to_kb_document_row
from app.adapters.taskpack import (
    RuntimeTaskProjection,
    from_knowledge_taskpack,
    project_to_runtime,
    to_knowledge_taskpack,
)
from app.contracts.v1 import (
    CONTRACT_VERSION,
    ClaimV1,
    EvaluationV1,
    ExecutionTraceV1,
    LessonV1,
    SourceRecordV1,
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
    "ClaimV1",
    "ContextPack",
    "CoreObject",
    "EvalResult",
    "EvaluationV1",
    "ExecutionTrace",
    "ExecutionTraceV1",
    "LessonV1",
    "MachineLesson",
    "PermissionDecision",
    "RuntimeTaskProjection",
    "SourceRecordV1",
    "TaskPack",
    "TaskPackV1",
    "TaskStepV1",
    "bind_legacy_evidence",
    "from_knowledge_taskpack",
    "from_kb_document_row",
    "from_lesson_row",
    "from_runtime_evaluation",
    "from_runtime_lesson",
    "from_runtime_trace",
    "from_trace_row",
    "project_to_runtime",
    "to_knowledge_taskpack",
    "to_kb_document_row",
    "to_lesson_row",
    "to_runtime_evaluation",
    "to_runtime_lesson",
    "to_runtime_trace",
    "to_trace_row",
    "verify_with_legacy_evidence",
]
