"""Evidence matching and conservative multi-source verification.

Adapted from Obsidian-Assistance's content-matched keyframe and V10 verification
workflows. A candidate is returned only when a requested term occurs in extracted
text; no random page or frame fallback exists.
"""

from __future__ import annotations

from typing import Any


def _normalized_terms(terms: list[str]) -> list[str]:
    return list(dict.fromkeys(term.strip() for term in terms if term and term.strip()))


def match_evidence(terms: list[str], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Find the strongest text-grounded evidence candidate for the given terms."""
    checked_terms = _normalized_terms(terms)
    matches: list[tuple[int, int, dict[str, Any]]] = []
    for index, candidate in enumerate(candidates):
        text = str(candidate.get("text", ""))
        for term in checked_terms:
            position = text.find(term)
            if position < 0:
                continue
            context = text[max(0, position - 80) : position + len(term) + 120].strip()
            grounded = {
                "term": term,
                "source": str(candidate.get("source", "")),
                "location": str(candidate.get("location", "")),
                "asset": str(candidate.get("asset", "")),
                "kind": str(candidate.get("kind", "unknown")),
                "context": context,
                "status": "matched",
            }
            matches.append((len(term), -index, grounded))
    if not matches:
        return {
            "status": "no_semantic_match",
            "terms_checked": len(checked_terms),
            "candidates_checked": len(candidates),
        }
    matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return {
        "status": "matched",
        "terms_checked": len(checked_terms),
        "candidates_checked": len(candidates),
        "match": matches[0][2],
        "match_count": len(matches),
    }


def verification_status(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify caller-supplied evidence as candidates, never as verified truth.

    Source strings, locations, kinds and claim IDs are ordinary caller-provided
    fields. Until provenance is issued by a server-owned registry or signed
    workflow, this helper can summarize independence but cannot auto-verify.
    """
    matched = [item for item in evidence if item.get("status") in {"matched", "verified"}]
    independent = {
        (str(item.get("kind", "unknown")), str(item.get("source", "")))
        for item in matched
        if item.get("source")
    }
    sources = sorted({source for _, source in independent})
    kinds = sorted({kind for kind, _ in independent})
    claim_ids = {str(item.get("claim_id")) for item in matched if item.get("claim_id")}
    records_bound = len(claim_ids) == 1 and bool(matched) and all(
        item.get("location") or item.get("context") for item in matched
    )
    status = "caller_supplied_candidate" if matched else "unverified"
    return {
        "status": status,
        "matched_evidence_count": len(matched),
        "independent_source_count": len(sources),
        "independent_sources": sources,
        "evidence_kinds": kinds,
        "claim_bound_by_caller": records_bound,
        "server_verified": False,
        "requires_human_review": True,
    }
