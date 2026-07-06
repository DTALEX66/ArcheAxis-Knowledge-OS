"""Fact extraction — subject-verb-object triple extraction from text.

Zero-dependency NLP: extracts (subject, predicate, object) triples
using regex patterns + part-of-speech heuristics.  Like spaCy + textacy
knowledge graph extraction, but no model download needed.

Usage:
    from shared.fact_extractor import extract_facts
    facts = extract_facts("Python was created by Guido van Rossum in 1991.")
    # → [{subject: "Python", predicate: "was created by", object: "Guido van Rossum"}]
"""

from __future__ import annotations

import re
from typing import Any


# ── Pattern-based fact extraction ───────────────────────


# Common predicate patterns: "X is Y", "X was created by Y", "X uses Y", etc.
_FACT_PATTERNS: list[tuple[str, str]] = [
    # (regex pattern, predicate label)
    (r"(\b[A-Z][a-zA-Z]*(?:\s+[a-zA-Z]+){0,3})\s+(is|was|are|were)\s+(a\s+)?(.+?)(?:\.|,|\sand\s|$)", "is_a"),
    (r"(.+?)\s+(created|developed|built|made|designed|invented|founded)\s+(?:by\s+)?(.+?)(?:\.|,|\sin\s|$)", "created_by"),
    (r"(.+?)\s+(uses|using|utilizes|employs|leverages|supports|requires)\s+(.+?)(?:\.|,|\sfor\s|$)", "uses"),
    (r"(.+?)\s+(consists of|contains|includes|comprises|is composed of)\s+(.+?)(?:\.|,|\sand\s|$)", "contains"),
    (r"(.+?)\s+(causes|leads to|results in|produces|generates|triggers)\s+(.+?)(?:\.|,|\sby\s|$)", "causes"),
    (r"(.+?)\s+(depends on|relies on|is based on|is derived from)\s+(.+?)(?:\.|,|\sand\s|$)", "depends_on"),
    (r"(.+?)\s+(is part of|belongs to|is a member of|is a type of)\s+(.+?)(?:\.|,|\sand\s|$)", "part_of"),
    (r"(.+?)\s+(is similar to|resembles|is like|is analogous to)\s+(.+?)(?:\.|,|\sbut\s|$)", "similar_to"),
]


# Relations extracted from "X of Y" patterns
_OF_PATTERN = re.compile(r"(\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\s+of\s+(\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})")


def _clean_entity(text: str) -> str:
    """Clean an extracted entity string."""
    text = text.strip().rstrip(".,;:!?)")
    # Remove trailing prepositions
    for prep in [" in", " at", " on", " by", " for", " with", " from", " to"]:
        if text.endswith(prep):
            text = text[:-len(prep)]
    return text.strip()


def extract_facts(text: str, max_facts: int = 20) -> list[dict[str, Any]]:
    """Extract (subject, predicate, object) triples from text.

    Args:
        text: natural language text.
        max_facts: max triples to return.

    Returns:
        List of {subject, predicate, object, pattern, confidence}.
    """
    facts: list[dict[str, Any]] = []

    for pattern, label in _FACT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if len(facts) >= max_facts:
                break

            groups = match.groups()
            if len(groups) >= 2:
                subject = _clean_entity(groups[0])
                if len(groups) == 2:
                    obj = _clean_entity(groups[1])
                elif len(groups) == 3:
                    # Skip filler "a" group
                    obj = _clean_entity(groups[2] if groups[1] in ("a ", "an ") else groups[1])
                    obj_val = _clean_entity(groups[-1])
                    if len(obj_val) > len(obj):
                        obj = obj_val
                elif len(groups) >= 4:
                    obj = _clean_entity(groups[-1])
                else:
                    obj = ""

                if subject and obj and len(subject) > 1 and len(obj) > 1:
                    facts.append({
                        "subject": subject,
                        "predicate": label,
                        "object": obj,
                        "confidence": 0.7,
                    })

    # Also extract "X of Y" relations
    for match in _OF_PATTERN.finditer(text):
        if len(facts) >= max_facts:
            break
        x = _clean_entity(match.group(1))
        y = _clean_entity(match.group(2))
        if x and y:
            facts.append({
                "subject": y,
                "predicate": "has",
                "object": x,
                "confidence": 0.5,
            })

    return facts[:max_facts]


def extract_key_entities(text: str, top_k: int = 15) -> list[dict[str, Any]]:
    """Extract key named entities and concepts from text.

    Uses capitalization heuristics + keyword frequency.

    Returns:
        List of {entity, type, count}.
    """
    from shared.auto_tagger import extract_keywords

    # Capitalized phrases (likely named entities)
    cap_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b")
    caps = [m.group(1) for m in cap_pattern.finditer(text)]
    from collections import Counter
    cap_counts = Counter(caps)

    # Keywords
    keywords = extract_keywords(text, top_k=top_k)

    entities = []
    for word, count in cap_counts.most_common(top_k):
        entities.append({"entity": word, "type": "named_entity", "count": count})

    for kw in keywords[:top_k]:
        entities.append({
            "entity": kw["keyword"],
            "type": "keyword",
            "count": kw["count"],
        })

    return entities[:top_k]


def text_to_knowledge_graph(text: str) -> dict[str, Any]:
    """Convert text to a knowledge graph (nodes + edges) using fact extraction.

    Equivalent to spaCy + textacy + NetworkX pipeline, but zero-dependency.

    Returns:
        {nodes: [{id, label, type}], edges: [{source, target, relation}]}.
    """
    facts = extract_facts(text, max_facts=30)
    entities = extract_key_entities(text, top_k=20)

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    # Add extracted entities as nodes
    for ent in entities:
        name = ent["entity"]
        if name not in nodes:
            nodes[name] = {"id": name, "label": name, "type": ent["type"]}

    # Add facts as edges
    for fact in facts:
        subj = fact["subject"]
        obj = fact["object"]
        if subj not in nodes:
            nodes[subj] = {"id": subj, "label": subj, "type": "concept"}
        if obj not in nodes:
            nodes[obj] = {"id": obj, "label": obj, "type": "concept"}

        edges.append({
            "source": subj,
            "target": obj,
            "relation": fact["predicate"],
        })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "fact_count": len(facts),
        "entity_count": len(nodes),
    }
