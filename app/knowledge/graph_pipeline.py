"""Knowledge-graph pipeline — absorbed from Cognee (ECL) patterns.

ECL = Extract → Cognify → Load (report §3.7):
    extract(text, glossary, patterns)
        → entities (id → type) + relations (src, predicate, target) + provenance
    cognify(result)
        → dedupe/merge (case-normalise, drop duplicate edges)
    load(result, store)
        → write into a graph store (GraphDB-shaped: add_entity/add_relation)
          with a provenance receipt

Extraction is deterministic and local (rule-based); the pipeline never
asserts verified truth — provenance keeps every edge traceable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

Pattern = tuple[str, str, str]  # (regex with named groups, predicate, flags)


@dataclass(frozen=True)
class ExtractResult:
    entities: dict[str, str] = field(default_factory=dict)          # id → type
    relations: list[tuple[str, str, str]] = field(default_factory=list)  # (src, pred, tgt)
    provenance: list[dict[str, Any]] = field(default_factory=list)

    def entity_count(self) -> int:
        return len(self.entities)

    def relation_count(self) -> int:
        return len(self.relations)


class GraphStore(Protocol):
    def add_entity(self, entity_id: str, entity_type: str, props: dict[str, Any]) -> None: ...

    def add_relation(self, source: str, target: str, relation: str, weight: float) -> None: ...


DEFAULT_PATTERNS: tuple[Pattern, ...] = (
    (r"(?P<src>[\w\u4e00-\u9fff]{1,20})\s*(?:支持|supports)\s*(?P<tgt>[\w\u4e00-\u9fff]{1,20})", "supports", ""),
    (r"(?P<src>[\w\u4e00-\u9fff]{1,20})\s*(?:依赖|depends on|requires)\s*(?P<tgt>[\w\u4e00-\u9fff]{1,20})", "requires", ""),
    (r"(?P<src>[\w\u4e00-\u9fff]{1,20})\s*(?:属于|belongs to)\s*(?P<tgt>[\w\u4e00-\u9fff]{1,20})", "belongs_to", ""),
    (r"(?P<src>[\w\u4e00-\u9fff]{1,20})\s*(?:先修|prerequisite of)\s*(?P<tgt>[\w\u4e00-\u9fff]{1,20})", "prerequisite_of", ""),
)


class GraphPipelineError(ValueError):
    """Raised when the graph pipeline receives invalid input."""


def extract(
    text: str,
    *,
    glossary: dict[str, str] | None = None,
    patterns: tuple[Pattern, ...] = DEFAULT_PATTERNS,
    source: str = "unknown",
) -> ExtractResult:
    """Extract entities and relations from one text (deterministic)."""
    if not text.strip():
        raise GraphPipelineError("extract requires non-empty text")
    entities: dict[str, str] = {}
    relations: list[tuple[str, str, str]] = []
    provenance: list[dict[str, Any]] = []

    glossary = glossary or {}
    for term, entity_type in glossary.items():
        if term.lower() in text.lower():
            entities.setdefault(term, entity_type)
            provenance.append({"kind": "entity", "source": source, "term": term,
                               "type": entity_type})

    for pattern, predicate, flags in patterns:
        regex = re.compile(pattern, re.IGNORECASE if flags else 0)
        for match in regex.finditer(text):
            src = match.groupdict().get("src")
            tgt = match.groupdict().get("tgt")
            if not src or not tgt:
                continue
            entities.setdefault(src, "concept")
            entities.setdefault(tgt, "concept")
            relations.append((src, predicate, tgt))
            provenance.append({"kind": "relation", "source": source,
                               "src": src, "predicate": predicate, "tgt": tgt})

    return ExtractResult(entities=entities, relations=relations, provenance=provenance)


def cognify(result: ExtractResult) -> ExtractResult:
    """Dedupe/merge: normalise ids, drop duplicate edges, keep provenance."""
    def norm(value: str) -> str:
        return value.strip().lower()

    entities: dict[str, str] = {}
    id_map: dict[str, str] = {}
    for entity_id, entity_type in result.entities.items():
        key = norm(entity_id)
        if key not in id_map:
            id_map[key] = entity_id
        entities[id_map[key]] = entity_type

    seen: set[tuple[str, str, str]] = set()
    relations: list[tuple[str, str, str]] = []
    for src, pred, tgt in result.relations:
        s = id_map.get(norm(src), src)
        t = id_map.get(norm(tgt), tgt)
        key = (s, pred, t)
        if key not in seen:
            seen.add(key)
            relations.append(key)

    return ExtractResult(entities=entities, relations=relations,
                         provenance=list(result.provenance))


def load(result: ExtractResult, store: GraphStore) -> dict[str, Any]:
    """Load a cognified result into a graph store with a provenance receipt."""
    for entity_id, entity_type in result.entities.items():
        store.add_entity(entity_id, entity_type, {"provenance_count": len(result.provenance)})
    for src, pred, tgt in result.relations:
        store.add_relation(src, tgt, pred, 1.0)
    return {
        "entities": len(result.entities),
        "relations": len(result.relations),
        "provenance_entries": len(result.provenance),
    }


def run_pipeline(
    text: str,
    store: GraphStore,
    *,
    glossary: dict[str, str] | None = None,
    source: str = "unknown",
) -> dict[str, Any]:
    """Full ECL: extract → cognify → load (convenience)."""
    raw = extract(text, glossary=glossary, source=source)
    cleaned = cognify(raw)
    return {"receipt": load(cleaned, store),
            "provenance": cleaned.provenance}
