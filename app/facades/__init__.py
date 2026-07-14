"""Stable public facades for Cognitive-Loop-OS domains."""

from app.facades.knowledge import KnowledgeHit, KnowledgeQueryResult, query_knowledge
from app.facades.research import ResearchIntakeResult, ingest_candidate
from app.facades.runtime import RuntimeExecution, execute_runtime

__all__ = [
    "KnowledgeHit",
    "KnowledgeQueryResult",
    "ResearchIntakeResult",
    "RuntimeExecution",
    "execute_runtime",
    "ingest_candidate",
    "query_knowledge",
]
