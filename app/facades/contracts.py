"""Identity-preserving exports of the existing runtime contracts."""

from app.adapters.claim import bind_legacy_evidence, verify_with_legacy_evidence
from app.adapters.evaluation import from_runtime_evaluation, to_runtime_evaluation
from app.adapters.evidence import from_match_result, to_legacy_verification_evidence
from app.adapters.execution_trace import (
    from_runtime_trace,
    from_trace_row,
    to_runtime_trace,
    to_trace_row,
)
from app.adapters.knowledge_graph import (
    from_graph_entity_row,
    from_graph_relation_row,
    to_graph_entity_row,
    to_graph_relation_row,
)
from app.adapters.lesson import (
    from_lesson_row,
    from_runtime_lesson,
    to_lesson_row,
    to_runtime_lesson,
)
from app.adapters.mastery_signal import from_learning_snapshots
from app.adapters.research_package import build_candidate_research_package
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
    EvidenceV1,
    ExecutionTraceV1,
    KnowledgeUnitV1,
    LessonV1,
    MasterySignalV1,
    RelationV1,
    ResearchPackageV1,
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
    "EvidenceV1",
    "ExecutionTrace",
    "ExecutionTraceV1",
    "KnowledgeUnitV1",
    "LessonV1",
    "MasterySignalV1",
    "MachineLesson",
    "PermissionDecision",
    "ResearchPackageV1",
    "RelationV1",
    "RuntimeTaskProjection",
    "SourceRecordV1",
    "TaskPack",
    "TaskPackV1",
    "TaskStepV1",
    "bind_legacy_evidence",
    "build_candidate_research_package",
    "from_graph_entity_row",
    "from_graph_relation_row",
    "from_learning_snapshots",
    "from_match_result",
    "from_knowledge_taskpack",
    "from_kb_document_row",
    "from_lesson_row",
    "from_runtime_evaluation",
    "from_runtime_lesson",
    "from_runtime_trace",
    "from_trace_row",
    "project_to_runtime",
    "to_graph_entity_row",
    "to_graph_relation_row",
    "to_knowledge_taskpack",
    "to_kb_document_row",
    "to_legacy_verification_evidence",
    "to_lesson_row",
    "to_runtime_evaluation",
    "to_runtime_lesson",
    "to_runtime_trace",
    "to_trace_row",
    "verify_with_legacy_evidence",
]
