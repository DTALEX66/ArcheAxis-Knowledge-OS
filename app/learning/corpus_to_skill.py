"""Corpus → Skill directory — absorbed from Corpus2Skill (dukesun99).

"Don't retrieve, navigate": distill a document corpus into a navigable,
hierarchical skill directory so an agent browses skills instead of running a
retrieval system at serve time (report §3.8).

Pipeline (deterministic, local):
    corpus {doc_id: text} → chunks → procedures (imperative/step sentences)
        → topic grouping → skill directory tree → skill proposals

Skill proposals are compatible with app.knowledge.skill_assets registration
(allowed/forbidden tasks + contracts); activation still requires review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_STEP_MARKERS = ("步骤", "第一步", "首先", "其次", "然后", "最后", "先", "再",
                 "1.", "2.", "3.", "ensure", "verify", "check", "set", "open",
                 "create", "use", "configure", "确保", "设置", "使用", "打开", "创建",
                 "配置", "检查", "验证")
_TOPIC_SPLIT = re.compile(r"[\s/:：,，。]+")


class CorpusToSkillError(ValueError):
    """Raised when corpus-to-skill input is invalid."""


@dataclass(frozen=True)
class Procedure:
    doc_id: str
    text: str
    topic: str

    def as_dict(self) -> dict[str, str]:
        return {"doc_id": self.doc_id, "text": self.text, "topic": self.topic}


@dataclass(frozen=True)
class SkillDirectory:
    """Navigable hierarchy: topic -> list of procedures (skills)."""

    root: str
    topics: dict[str, list[Procedure]]

    def to_tree(self) -> dict[str, Any]:
        return {"root": self.root,
                "topics": {t: [p.as_dict() for p in procs]
                           for t, procs in sorted(self.topics.items())}}

    def topic_count(self) -> int:
        return len(self.topics)

    def procedure_count(self) -> int:
        return sum(len(procs) for procs in self.topics.values())


@dataclass(frozen=True)
class SkillProposal:
    name: str
    version: str
    allowed_tasks: list[str]
    forbidden_tasks: list[str]
    input_contract: dict[str, Any]
    output_contract: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version,
                "allowed_tasks": self.allowed_tasks,
                "forbidden_tasks": self.forbidden_tasks,
                "input_contract": self.input_contract,
                "output_contract": self.output_contract}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？.!?])\s*", text.strip())
    return [p.strip() for p in parts if len(p.strip()) >= 4]


def _is_step(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(marker in lowered for marker in _STEP_MARKERS)


def _topic_of(sentence: str, doc_id: str) -> str:
    """Coarse topic: first content token of the doc, else first noun-ish token."""
    tokens = [t for t in _TOPIC_SPLIT.split(sentence) if len(t) >= 2]
    if not tokens:
        return doc_id
    return tokens[0][:20]


def extract_procedures(corpus: dict[str, str]) -> list[Procedure]:
    """Extract procedural sentences (steps) from a document corpus."""
    if not corpus:
        raise CorpusToSkillError("corpus must be non-empty")
    procedures: list[Procedure] = []
    for doc_id, text in corpus.items():
        if not text.strip():
            continue
        for sentence in _sentences(text):
            if _is_step(sentence):
                procedures.append(Procedure(doc_id=doc_id, text=sentence,
                                            topic=_topic_of(sentence, doc_id)))
    return procedures


def build_skill_directory(corpus: dict[str, str], *, root: str = "skills") -> SkillDirectory:
    """Group extracted procedures by topic into a navigable directory."""
    procedures = extract_procedures(corpus)
    topics: dict[str, list[Procedure]] = {}
    for proc in procedures:
        topics.setdefault(proc.topic, []).append(proc)
    return SkillDirectory(root=root, topics=topics)


def propose_skills(directory: SkillDirectory, *, version: str = "1.0.0") -> list[SkillProposal]:
    """Turn each directory topic into a skill-asset proposal."""
    proposals: list[SkillProposal] = []
    for topic, procs in sorted(directory.topics.items()):
        if not procs:
            continue
        allowed = [f"execute-{topic}"]
        proposals.append(SkillProposal(
            name=f"skill-{topic}", version=version,
            allowed_tasks=allowed,
            forbidden_tasks=["auto-execute-high-risk"],
            input_contract={"topic": topic, "doc_ids": sorted({p.doc_id for p in procs})},
            output_contract={"procedures": [p.text for p in procs]},
        ))
    return proposals
