from app.memory.store import search_memory
from app.schemas import ContextPack


def _terms(text: str) -> set[str]:
    return {term for term in text.lower().split() if term.strip()}


def _score_context(query: str, items: list, top_k: int) -> tuple[float, list[str]]:
    if not items:
        return 0.0, ["no matching memory found"]

    query_terms = _terms(query)
    combined_terms = set()
    for item in items:
        combined_terms.update(_terms(item.content))

    item_count_signal = min(len(items) / max(top_k, 1), 1.0)
    overlap_signal = 0.0
    if query_terms:
        overlap_signal = len(query_terms & combined_terms) / len(query_terms)
    source_signal = 1.0 if any((item.source or "unknown") != "unknown" for item in items) else 0.0

    score = (
        item_count_signal * 0.35
        + overlap_signal * 0.50
        + source_signal * 0.15
    )
    score = round(min(score, 1.0), 3)

    reasons = [
        f"item_count={len(items)}/{top_k}",
        f"query_term_overlap={overlap_signal:.2f}",
        f"source_presence={source_signal:.2f}",
    ]
    return score, reasons


def retrieve(query: str, top_k: int = 5) -> ContextPack:
    items = search_memory(query, top_k=top_k)
    summary = "\n".join([item.content[:200] for item in items]) if items else "No prior memory found."
    score, reasons = _score_context(query, items, top_k)
    return ContextPack(query=query, items=items, summary=summary, score=score, score_reasons=reasons)
