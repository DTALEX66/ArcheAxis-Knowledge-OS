"""Static open-source discovery suggestions (legacy module name).

This does not retrieve content, inspect licensing, create a claim-level crosswalk,
or verify any recommendation. Entries are discovery candidates only.
"""

from __future__ import annotations

from typing import Any

_PROFILE_SIGNALS = {
    "technical": {"rag", "embedding", "prompt", "agent", "transformer", "rerank", "向量", "大模型", "知识图谱", "编程"},
    "learning": {"主动回想", "间隔重复", "复习", "记忆", "费曼", "学习"},
    "design": {"ui", "ux", "设计", "版式", "视觉", "组件", "色彩", "排版"},
}

_PROFILE_SOURCES: dict[str, list[dict[str, str]]] = {
    "technical": [
        {"dimension": "technical_docs", "source": "MDN Web Docs", "url": "https://developer.mozilla.org/", "use": "concepts, procedures, examples and failure modes"},
        {"dimension": "qa", "source": "Stack Exchange", "url": "https://stackexchange.com/", "use": "questions, context, answers and acceptance signals"},
        {"dimension": "knowledge_graph", "source": "Wikidata", "url": "https://www.wikidata.org/", "use": "entities, aliases, relations and provenance"},
        {"dimension": "coursework", "source": "MIT OpenCourseWare", "url": "https://ocw.mit.edu/", "use": "assignments, projects and rubrics"},
    ],
    "learning": [
        {"dimension": "textbook", "source": "OpenStax", "url": "https://openstax.org/", "use": "objectives, chapters, exercises and glossary"},
        {"dimension": "coursework", "source": "MIT OpenCourseWare", "url": "https://ocw.mit.edu/", "use": "syllabus, assignments and exams"},
        {"dimension": "knowledge_graph", "source": "Wikidata", "url": "https://www.wikidata.org/", "use": "entities and relations"},
    ],
    "design": [
        {"dimension": "design_guidance", "source": "Apple HIG", "url": "https://developer.apple.com/design/human-interface-guidelines/", "use": "interaction and platform guidance"},
        {"dimension": "design_system", "source": "Material Design", "url": "https://m3.material.io/", "use": "components, tokens and accessibility"},
        {"dimension": "open_media", "source": "Openverse", "url": "https://openverse.org/", "use": "licensed media metadata"},
    ],
    "general": [
        {"dimension": "encyclopedia", "source": "Wikipedia", "url": "https://www.wikipedia.org/", "use": "topic structure and citations"},
        {"dimension": "textbook", "source": "Wikibooks", "url": "https://www.wikibooks.org/", "use": "chapters, objectives and exercises"},
        {"dimension": "knowledge_graph", "source": "Wikidata", "url": "https://www.wikidata.org/", "use": "entities, properties and provenance"},
    ],
}


def classify_profile(text: str, terms: list[str] | None = None) -> str:
    corpus = f"{text} {' '.join(terms or [])}".lower()
    scores = {
        profile: sum(signal.lower() in corpus for signal in signals)
        for profile, signals in _PROFILE_SIGNALS.items()
    }
    best = max(scores, key=lambda profile: scores[profile])
    return best if scores[best] else "general"


def build_crosswalk(text: str, terms: list[str] | None = None) -> dict[str, Any]:
    """Return static source-discovery suggestions without license or claim verification."""
    profile = classify_profile(text, terms)
    return {
        "profile": profile,
        "terms": list(dict.fromkeys(terms or [])),
        "recommendations": _PROFILE_SOURCES[profile],
        "verification_status": "recommended_sources_only_not_verified",
        "required_next_step": (
            "retrieve claim-level excerpts, record URL and retrieval time, compare agreement, "
            "then obtain human review"
        ),
    }
