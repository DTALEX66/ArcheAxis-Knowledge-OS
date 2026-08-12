"""Stable public facades for archeaxis-workspace domains."""

from app.facades import contracts
from app.facades.enhancement import EnhancementArtifact, enhance_artifact
from app.facades.knowledge import KnowledgeHit, KnowledgeQueryResult, query_knowledge
from app.facades.research import (
    ResearchIntakeResult,
    get_research_package,
    ingest_candidate,
    research_github_repository,
)
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
    "get_research_package",
    "ingest_candidate",
    "query_knowledge",
    "research_github_repository",
]
