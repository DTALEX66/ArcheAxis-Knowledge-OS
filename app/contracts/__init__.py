"""Versioned canonical contracts."""

from app.contracts.knowledge_v3 import KnowledgeObjectV3, KnowledgeSourceV3
from app.contracts.v1 import (
    CONTRACT_VERSION,
    EvaluationV1,
    ExecutionTraceV1,
    LearningArtifactV1,
    LessonV1,
    MachineKnowledgeUnitV1,
    TaskPackV1,
    TaskStepV1,
)

__all__ = [
    "CONTRACT_VERSION",
    "EvaluationV1",
    "ExecutionTraceV1",
    "LearningArtifactV1",
    "LessonV1",
    "MachineKnowledgeUnitV1",
    "TaskPackV1",
    "TaskStepV1",
    "KnowledgeObjectV3",
    "KnowledgeSourceV3",
]


