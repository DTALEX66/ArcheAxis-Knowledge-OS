"""Public read-only facade for the existing knowledge search implementation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from knowledge_base.search import keyword_search


class KnowledgeHit(BaseModel):
    id: str
    type: Literal["document", "card"]
    title: str = ""
    snippet: str = ""
    vector_distance: float | None = None
    keyword_score: float | None = None


class KnowledgeQueryResult(BaseModel):
    query: str
    mode: Literal["keyword"] = "keyword"
    count: int = 0
    items: list[KnowledgeHit] = Field(default_factory=list)


def query_knowledge(
    query: str,
    *,
    top_k: int = 5,
    mode: Literal["keyword"] = "keyword",
) -> KnowledgeQueryResult:
    """Run the real keyword/FTS search without copying ranking logic."""
    hits = keyword_search(query, top_k=top_k)
    items = [
        KnowledgeHit(
            id=hit["id"],
            type=hit["type"],
            title=hit.get("title", ""),
            snippet=hit.get("snippet", ""),
            keyword_score=hit.get("score"),
        )
        for hit in hits
    ]
    return KnowledgeQueryResult(query=query, mode=mode, count=len(items), items=items)
