"""Explicit adapters between canonical and legacy contracts."""

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
    "project_to_runtime",
    "to_knowledge_taskpack",
]
