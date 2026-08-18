"""Personal capability profile — D3 recommendation R2 (AI Learning OS).

Tracks per-concept capability with confidence calibration: the gap between
the learner's self-assessed confidence and actual correctness (metacognitive
accuracy, report §3.5). Calibration error is computed ECE-style over
confidence bins.

    update(profile, concept, confidence, correct)  → updated profile
    profile_summary(profile)                       → per-concept rows
    calibration_error(profile, concept)            → mean |confidence - accuracy|

Pure dataclasses + functions; persistence lives in callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConceptProfile:
    concept: str
    attempts: int = 0
    correct: int = 0
    confidence_sum: float = 0.0
    mastery: float = 0.0  # EMA of correctness

    @property
    def accuracy(self) -> float:
        return self.correct / self.attempts if self.attempts else 0.0

    @property
    def mean_confidence(self) -> float:
        return self.confidence_sum / self.attempts if self.attempts else 0.0


@dataclass
class LearnerProfile:
    concepts: dict[str, ConceptProfile] = field(default_factory=dict)

    def update(self, concept: str, *, confidence: float, correct: bool) -> "LearnerProfile":
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        entry = self.concepts.setdefault(concept, ConceptProfile(concept=concept))
        entry.attempts += 1
        entry.correct += 1 if correct else 0
        entry.confidence_sum += confidence
        # EMA of correctness with alpha=0.2 (recent wins)
        outcome = 1.0 if correct else 0.0
        entry.mastery = round(0.8 * entry.mastery + 0.2 * outcome, 3)
        return self

    def calibration_error(self, concept: str) -> float:
        entry = self.concepts.get(concept)
        if entry is None or entry.attempts == 0:
            return 0.0
        return round(abs(entry.mean_confidence - entry.accuracy), 3)

    def summary(self) -> list[dict[str, Any]]:
        rows = []
        for concept, entry in sorted(self.concepts.items()):
            rows.append({
                "concept": concept,
                "attempts": entry.attempts,
                "accuracy": round(entry.accuracy, 3),
                "mean_confidence": round(entry.mean_confidence, 3),
                "calibration_error": self.calibration_error(concept),
                "mastery": entry.mastery,
            })
        return rows
