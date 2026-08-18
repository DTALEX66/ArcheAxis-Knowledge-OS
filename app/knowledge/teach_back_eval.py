"""Teach-Back evaluation — absorbed from Studyield / OpenCognition patterns.

Teach-Back is NOT the AI explaining to the learner: the learner restates a
concept in their own words and the system judges how well they actually
understand it (report §3.5, M3-Explain).

Scoring is rubric-based and fully local (deterministic, no provider call):
    accuracy      — how much of the restatement is grounded in the reference
    coverage      — how many key terms/claims of the reference were covered
    paraphrase    — own-words ratio (not copying the reference verbatim)
    organization  — presence of structure markers (first/next/because/…)

Misconception extraction flags missing key terms and extra claims. An optional
LLM grader (LiteLLM, provider-agnostic) can refine the rubric score, but the
human truth flag always outranks it (governance: model confidence is not truth).

Design rules: pure calculation; persistence and review live in callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.knowledge.dual_mastery import HumanMasteryLevel

__all__ = ["TeachBackEvaluation", "score_teach_back", "extract_misconceptions",
           "map_to_level", "grade_with_llm"]

_STRUCTURE_MARKERS = (
    "first", "next", "then", "because", "therefore", "however", "in short",
    "finally", "for example", "that is", "means", "in other words", "步骤", "首先",
    "其次", "然后", "因为", "所以", "例如", "总之", "换句话说",
)

_STOPWORDS = frozenset({
    "the", "a", "an", "of", "and", "or", "is", "are", "was", "were", "be", "been",
    "to", "in", "on", "at", "by", "for", "with", "it", "its", "that", "this",
    "these", "those", "as", "but", "not", "no", "so", "if", "then", "than",
    "from", "into", "over", "under", "about", "which", "who", "whom", "whose",
    "can", "could", "will", "would", "should", "may", "might", "must", "has",
    "have", "had", "do", "does", "did", "being", "having", "there", "here",
    "their", "they", "we", "you", "he", "she", "them", "his", "her", "ours",
    "yours", "ourselves", "themselves", "i", "me", "my", "us", "such", "own",
    "same", "very", "just", "also", "both", "each", "few", "more", "most",
    "other", "some", "any", "all", "one", "two", "three", "often", "always",
    "usually", "really", "actually", "thing", "things", "way", "ways", "kind",
    "sort", "basically", "generally", "basically", "的", "了", "是", "在", "和",
    "与", "也", "就", "都", "而", "及", "或", "之", "其", "这", "那", "个",
    "种", "有", "用", "把", "被", "让", "对", "从", "向", "为", "等", "中",
})


@dataclass(frozen=True)
class TeachBackEvaluation:
    """Rubric outcome for one teach-back restatement."""

    record_id: str
    concept: str
    accuracy: float
    coverage: float
    paraphrase: float
    organization: float
    overall: float
    missing_terms: list[str]
    extra_claims: list[str]

    def passes(self, threshold: float = 0.7) -> bool:
        """Whether the restatement demonstrates M3-Explain level understanding."""
        return self.overall >= threshold


def _terms(text: str) -> set[str]:
    words = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
    return {w for w in words if w.strip() and len(w) > 1 and w not in _STOPWORDS}


def _score_accuracy(restatement: str, reference: str) -> float:
    """Fraction of restatement content terms that also appear in the reference.

    High accuracy = restatement is grounded; low = hallucinated additions.
    """
    rest_terms = _terms(restatement)
    if not rest_terms:
        return 0.0
    grounded = sum(1 for t in rest_terms if t in reference.lower())
    return grounded / len(rest_terms)


def _score_coverage(restatement: str, key_terms: list[str]) -> float:
    if not key_terms:
        return 1.0
    text = restatement.lower()
    covered = sum(1 for t in key_terms if t.lower() in text)
    return covered / len(key_terms)


def _score_paraphrase(restatement: str, reference: str) -> float:
    """Own-words ratio: restatement terms NOT copied verbatim from reference."""
    rest_terms = _terms(restatement)
    if not rest_terms:
        return 0.0
    ref_terms = _terms(reference)
    overlap = rest_terms & ref_terms
    return 1.0 - (len(overlap) / len(rest_terms))


def _score_organization(restatement: str) -> float:
    text = restatement.lower()
    hits = sum(1 for m in _STRUCTURE_MARKERS if m in text)
    return min(1.0, hits / 3.0)


def extract_misconceptions(restatement: str, reference: str,
                           key_terms: list[str]) -> tuple[list[str], list[str]]:
    """Return (missing_terms, extra_claims).

    missing_terms: key terms of the reference absent from the restatement.
    extra_claims: restatement terms that appear in neither the reference nor
                  the key-term list (possible hallucinations).
    """
    text = restatement.lower()
    missing = [t for t in key_terms if t.lower() not in text]
    extra = sorted(t for t in _terms(restatement)
                   if t not in reference.lower() and t not in {k.lower() for k in key_terms})
    return missing, extra


def score_teach_back(*, record_id: str, concept: str, restatement: str,
                     reference: str, key_terms: list[str] | None = None) -> TeachBackEvaluation:
    """Score one teach-back restatement against a reference (pure, local)."""
    key_terms = key_terms or []
    if not restatement.strip() or not reference.strip():
        raise ValueError("teach-back scoring requires restatement and reference")
    accuracy = round(_score_accuracy(restatement, reference), 3)
    coverage = round(_score_coverage(restatement, key_terms), 3)
    paraphrase = round(_score_paraphrase(restatement, reference), 3)
    organization = round(_score_organization(restatement), 3)
    # weights: key-term coverage is the primary understanding signal; accuracy
    # (groundedness) second; structure third; paraphrase last.
    overall = round(0.50 * coverage + 0.25 * accuracy + 0.15 * organization + 0.10 * paraphrase, 3)
    # verbatim copying is rote memory, not understanding: cap the score
    if paraphrase < 0.10:
        overall = round(min(overall, 0.60), 3)
    missing, extra = extract_misconceptions(restatement, reference, key_terms)
    return TeachBackEvaluation(record_id=record_id, concept=concept, accuracy=accuracy,
                               coverage=coverage, paraphrase=paraphrase,
                               organization=organization, overall=overall,
                               missing_terms=missing, extra_claims=extra)


def map_to_level(evaluation: TeachBackEvaluation) -> HumanMasteryLevel:
    """Map a teach-back outcome onto the M scale (M2 recall / M3 explain)."""
    if evaluation.passes():
        return HumanMasteryLevel.M3_EXPLAIN
    if evaluation.coverage >= 0.4:
        return HumanMasteryLevel.M2_RECALL
    return HumanMasteryLevel.M1_RECOGNIZE


def grade_with_llm(restatement: str, reference: str, *,
                   model: str | None = None) -> dict[str, Any] | None:
    """Optional LLM-assisted grader (provider-agnostic via LiteLLM).

    Returns a dict {accuracy, coverage, paraphrase, organization, rationale} or
    None when no provider is configured — callers MUST fall back to the rubric.
    Model confidence is a hint only; the human truth flag stays authoritative.
    """
    try:
        import litellm  # type: ignore
    except ImportError:
        return None
    if not model:
        model = "ollama/llama3.1"
    system = (
        "You grade a learner's teach-back restatement of a concept. "
        "Return JSON only: {accuracy:0..1, coverage:0..1, paraphrase:0..1, organization:0..1, rationale:str}."
    )
    user = f"REFERENCE:\n{reference}\n\nRESTATEMENT:\n{restatement}"
    try:
        response = litellm.completion(
            model=model, messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ], response_format={"type": "json_object"}, temperature=0.0,
        )
        content = response["choices"][0]["message"]["content"]
        import json
        parsed = json.loads(content)
        return {k: parsed.get(k) for k in ("accuracy", "coverage", "paraphrase", "organization", "rationale")}
    except Exception:
        return None
