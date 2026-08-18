"""Quiz generation & grading — absorbed from DeepTutor / OpenTutor patterns.

Turns machine knowledge (a concept, reference text and key terms) into
practice items, and grades learner answers with a deterministic local scorer
(LLM optional, never required):

    generate_quiz(concept, reference, key_terms, other_concepts)
        → recall items (fill-in) and MCQ items (distractors from other concepts)
    grade_answer(item, answer)
        → (correct, score, feedback) — recall uses bidirectional term overlap
          (CJK-safe), MCQ uses exact match

Governance: quiz items are derived from machine knowledge but a pass is only
M4 evidence after a human truth flag; model confidence is never the truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

QuizKind = Literal["recall", "mcq"]


class QuizError(ValueError):
    """Raised when a quiz operation is invalid."""


@dataclass(frozen=True)
class QuizItem:
    item_id: str
    concept: str
    kind: QuizKind
    prompt: str
    answer: str
    distractors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {"item_id": self.item_id, "concept": self.concept, "kind": self.kind,
                "prompt": self.prompt, "answer": self.answer,
                "distractors": list(self.distractors)}


@dataclass(frozen=True)
class GradingOutcome:
    item_id: str
    correct: bool
    score: float
    feedback: str


def _stable_id(concept: str, prompt: str) -> str:
    from hashlib import sha256

    return "quiz_" + sha256(f"{concept}:{prompt}".encode()).hexdigest()[:24]


def _terms(text: str) -> set[str]:
    words = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    return {w for w in words if w.strip() and len(w) > 1}


def _key_phrase_from_reference(reference: str, key_terms: list[str]) -> str:
    """Pick the most distinctive key term present in the reference as the answer."""
    for term in key_terms:
        if term.lower() in reference.lower():
            return term
    words = sorted(_terms(reference), key=len, reverse=True)
    return words[0] if words else "概念"


def generate_quiz(
    *,
    concept: str,
    reference: str,
    key_terms: list[str] | None = None,
    other_concepts: list[str] | None = None,
    kinds: list[QuizKind] | None = None,
) -> list[QuizItem]:
    """Generate recall + MCQ items from machine knowledge (deterministic)."""
    if not concept.strip() or not reference.strip():
        raise QuizError("quiz generation requires concept and reference")
    key_terms = [t.strip() for t in (key_terms or []) if t.strip()]
    kinds = kinds or ["recall", "mcq"]
    answer = _key_phrase_from_reference(reference, key_terms)
    items: list[QuizItem] = []

    if "recall" in kinds:
        prompt = f"{concept}：请补全 —— 「{reference}」"
        items.append(QuizItem(item_id=_stable_id(concept, "recall"), concept=concept,
                              kind="recall", prompt=prompt, answer=answer))

    if "mcq" in kinds:
        distractors = [c for c in (other_concepts or [])
                       if c.strip() and c.strip().lower() != answer.lower()]
        # ensure at least 2 distractors; pad with generic options
        while len(distractors) < 2:
            distractors.append(f"非{answer}")
        prompt = f"{concept} 最匹配的核心术语是？"
        items.append(QuizItem(item_id=_stable_id(concept, "mcq"), concept=concept,
                              kind="mcq", prompt=prompt, answer=answer,
                              distractors=tuple(distractors[:3])))

    return items


def grade_answer(item: QuizItem, answer: str) -> GradingOutcome:
    """Grade one answer (recall: term overlap; mcq: exact match)."""
    if not answer.strip():
        return GradingOutcome(item_id=item.item_id, correct=False, score=0.0,
                              feedback="未作答")
    if item.kind == "mcq":
        correct = answer.strip().lower() == item.answer.lower()
        return GradingOutcome(item_id=item.item_id, correct=correct, score=1.0 if correct else 0.0,
                              feedback="正确" if correct else f"正确答案：{item.answer}")
    # recall: bidirectional substring match (CJK has no spaces)
    answer_terms = _terms(answer)
    answer_norm = answer.lower()
    target = item.answer.lower()
    hit = target in answer_norm or any(t in target or target in t for t in answer_terms)
    if hit:
        return GradingOutcome(item_id=item.item_id, correct=True, score=1.0,
                              feedback="命中关键术语")
    overlap = len(answer_terms & _terms(item.answer))
    score = round(min(1.0, overlap / max(len(_terms(item.answer)), 1)), 3)
    return GradingOutcome(item_id=item.item_id, correct=score >= 0.8, score=score,
                          feedback=f"期望术语：{item.answer}")
