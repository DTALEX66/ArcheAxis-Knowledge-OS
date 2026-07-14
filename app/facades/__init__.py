"""Stable public facades for Cognitive-Loop-OS domains."""

from app.facades import contracts
from app.facades.enhancement import EnhancementArtifact, enhance_artifact
from app.facades.knowledge import KnowledgeHit, KnowledgeQueryResult, query_knowledge
from app.facades.research import ResearchIntakeResult, ingest_candidate
from app.facades.runtime import RuntimeExecution, execute_runtime

__all__ = [
    "EnhancementArtifact",
    "KnowledgeHit",
    "KnowledgeQueryResult",
    "ResearchIntakeResult",
    "RuntimeExecution",
    "contracts",
    "enhance_artifact",
    "execute_runtime",
    "ingest_candidate",
    "query_knowledge",
]
