"""Explicit adapters between canonical and legacy contracts."""

from app.adapters.evaluation import from_runtime_evaluation, to_runtime_evaluation
from app.adapters.execution_trace import (
    from_runtime_trace,
    from_trace_row,
    to_runtime_trace,
    to_trace_row,
)
from app.adapters.taskpack import (
    ContractMappingError,
    RuntimeTaskProjection,
    from_knowledge_taskpack,
    project_to_runtime,
    to_knowledge_taskpack,
)

__all__ = [
    "ContractMappingError",
    "RuntimeTaskProjection",
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
