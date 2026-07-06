"""Cross-reference engine — multi-source validation + credibility scoring.

Absorbs: OER crosswalk patterns, source trust evaluation, multi-source fusion.

Capabilities:
1. cross_reference(sources) → compare facts across sources
2. score_credibility(source) → rate source trustworthiness
3. detect_contradictions(facts) → find conflicting claims
4. fuse_sources(sources) → merge overlapping knowledge

Usage:
    from shared.cross_reference import cross_reference, score_credibility
    cr = cross_reference([doc1, doc2])
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))


# ── Credibility scoring ─────────────────────────────────


# Trusted domains (verified educational/research sources)
_TRUSTED_DOMAINS: set[str] = {
    "arxiv.org", "github.com", "wikipedia.org", "stackoverflow.com",
    "docs.python.org", "developer.mozilla.org", "pypi.org",
    "nature.com", "science.org", "ieee.org", "acm.org",
    "mit.edu", "stanford.edu", "berkeley.edu", "cmu.edu",
    "openai.com", "anthropic.com", "huggingface.co",
}

# Credibility signals
_CRED_SIGNALS: dict[str, float] = {
    "peer-reviewed": 0.3,
    "citation": 0.15,
    "reference": 0.1,
    "bibliography": 0.1,
    "doi": 0.2,
    "arxiv": 0.15,
    "github stars": 0.1,
    "license": 0.05,
    "version": 0.05,
    "last updated": 0.1,
    "author": 0.1,
    "affiliation": 0.1,
}


def _domain_trust(domain: str) -> float:
    """Score domain trustworthiness."""
    domain = domain.lower().replace("www.", "")
    if domain in _TRUSTED_DOMAINS:
        return 0.8
    if domain.endswith(".edu"):
        return 0.7
    if domain.endswith(".gov"):
        return 0.9
    if domain.endswith(".org"):
        return 0.5
    if "blog" in domain or "medium" in domain:
        return 0.3
    return 0.3


def score_credibility(source: dict[str, Any]) -> dict[str, Any]:
    """Score a knowledge source's credibility.

    Args:
        source: dict with {title, content, source, url, ...}.

    Returns:
        {score: 0-1, factors: {signal: contribution}, level: 'high'|'medium'|'low'}.
    """
    content = source.get("content", "") or ""
    url = source.get("url", "") or source.get("source", "") or ""
    title = source.get("title", "") or ""

    # Extract domain from URL
    domain = ""
    if "://" in url:
        domain = url.split("://")[1].split("/")[0]

    # Base score from domain trust
    score = _domain_trust(domain)
    factors: dict[str, float] = {"domain": round(score, 2)}

    # Content signals
    lower = (title + " " + content).lower()
    for signal, weight in _CRED_SIGNALS.items():
        if signal in lower:
            contribution = min(weight, 1.0 - score)
            score += contribution
            factors[signal] = round(contribution, 2)

    score = min(1.0, round(score, 2))

    if score >= 0.7:
        level = "high"
    elif score >= 0.4:
        level = "medium"
    else:
        level = "low"

    return {
        "score": score,
        "level": level,
        "domain": domain,
        "factors": factors,
    }


# ── Cross-reference ─────────────────────────────────────


def cross_reference(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Cross-reference multiple sources to find agreements and contradictions.

    Args:
        sources: list of source dicts with {title, content, source}.

    Returns:
        {agreements, contradictions, unique_to_each, credibility_map}.
    """
    from shared.fact_extractor import extract_facts
    from shared.auto_tagger import extract_keywords

    if len(sources) < 2:
        return {"error": "need at least 2 sources to cross-reference"}

    # Extract facts from each source
    source_facts: dict[int, list[dict]] = {}
    source_kw: dict[int, set[str]] = {}

    for i, src in enumerate(sources):
        text = src.get("title", "") + " " + src.get("content", "")
        source_facts[i] = extract_facts(text, max_facts=10)
        source_kw[i] = {k["keyword"] for k in extract_keywords(text, top_k=15)}

    # Compare pairwise
    agreements: list[dict] = []
    contradictions: list[dict] = []
    unique_to_each: dict[int, list[str]] = {i: [] for i in range(len(sources))}

    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            fi = source_facts[i]
            fj = source_facts[j]

            # Find similar facts
            for fa in fi:
                for fb in fj:
                    # Simple: same subject or same object
                    if fa["subject"].lower() == fb["subject"].lower():
                        if fa["predicate"] == fb["predicate"]:
                            if fa["object"].lower() == fb["object"].lower():
                                agreements.append({
                                    "fact": fa,
                                    "source_a": i,
                                    "source_b": j,
                                    "type": "exact_match",
                                })
                            else:
                                contradictions.append({
                                    "fact_a": fa, "fact_b": fb,
                                    "source_a": i, "source_b": j,
                                    "type": "object_differs",
                                })

            # Find unique keywords per source
            shared = source_kw[i] & source_kw[j]
            for s, kws in [(i, source_kw[i]), (j, source_kw[j])]:
                unique = kws - shared
                if unique:
                    unique_to_each[s].extend(list(unique)[:5])

    # Credibility per source
    cred_map = {i: score_credibility(src) for i, src in enumerate(sources)}

    return {
        "source_count": len(sources),
        "agreement_count": len(agreements),
        "contradiction_count": len(contradictions),
        "agreements": agreements[:10],
        "contradictions": contradictions[:10],
        "unique_keywords": {str(k): list(set(v))[:5] for k, v in unique_to_each.items()},
        "credibility": cred_map,
    }


def detect_contradictions(fact_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect contradictions within a single set of facts.

    Looks for subject-predicate pairs with different objects.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for fact in fact_list:
        key = (fact["subject"].lower(), fact["predicate"])
        if key not in groups:
            groups[key] = []
        groups[key].append(fact)

    contradictions = []
    for key, facts in groups.items():
        objects = {f["object"].lower() for f in facts}
        if len(objects) > 1:
            contradictions.append({
                "subject": key[0],
                "predicate": key[1],
                "conflicting_objects": list(objects),
                "sources": [f.get("source", "") for f in facts],
            })

    return contradictions


def fuse_sources(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Fuse multiple sources into a unified knowledge summary.

    Merges overlapping keywords, extracts consensus facts, and flags
    contradictions.
    """
    if not sources:
        return {"error": "no sources provided"}

    from shared.auto_tagger import extract_keywords, progressive_summarize

    # Combine all text
    combined = "\n\n".join(
        s.get("title", "") + "\n" + s.get("content", "")
        for s in sources
    )

    # Unified keywords
    all_kw: dict[str, int] = {}
    for src in sources:
        text = src.get("title", "") + " " + src.get("content", "")
        for kw in extract_keywords(text, top_k=10):
            all_kw[kw["keyword"]] = all_kw.get(kw["keyword"], 0) + 1

    # Consensus keywords (appear in multiple sources)
    consensus = [k for k, v in all_kw.items() if v >= 2][:10]

    # Cross-reference
    cr = cross_reference(sources) if len(sources) >= 2 else {}

    # Progressive summary of combined text
    summary = progressive_summarize(combined)

    return {
        "source_count": len(sources),
        "consensus_keywords": consensus,
        "all_keywords": sorted(all_kw.items(), key=lambda x: x[1], reverse=True)[:15],
        "cross_reference": cr,
        "summary": summary["layer_4_executive"],
        "credibility": {
            "average": round(
                sum(score_credibility(s)["score"] for s in sources) / len(sources), 2
            ),
            "by_source": [score_credibility(s) for s in sources],
        },
    }
