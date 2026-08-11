"""Text quality: CER, WER, alignment, difference localization (JiWER + RapidFuzz).

Guardrails enforced by callers:
- CER/WER only computed when truth and prediction both exist.
- OCR/ASR engine confidence is not a proxy for CER/WER.
- These metrics measure transcription fidelity, not factual accuracy.
"""

from __future__ import annotations

import jiwer
from rapidfuzz import fuzz as _fuzz

__all__ = ["cer", "wer", "alignment_similarity", "find_disagreement_spans"]


def cer(truth: str, prediction: str) -> float:
    """Character Error Rate. Returns 0.0 when both strings are identical."""
    if not truth and not prediction:
        return 0.0
    return float(jiwer.cer(truth, prediction))


def wer(truth: str, prediction: str) -> float:
    """Word Error Rate. Returns 0.0 when both strings are identical."""
    if not truth and not prediction:
        return 0.0
    return float(jiwer.wer(truth, prediction))


def alignment_similarity(a: str, b: str) -> float:
    """Normalized similarity 0-1 using RapidFuzz token_sort_ratio."""
    return _fuzz.token_sort_ratio(a, b) / 100.0


def find_disagreement_spans(
    truth: str, prediction: str, threshold: float = 0.85
) -> list[dict[str, object]]:
    """Return candidate disagreement spans where local similarity drops below threshold.

    Returns list of {"start": int, "end": int, "truth_slice": str, "pred_slice": str}.
    A simple sliding-window approach; for production use a proper diff algorithm.
    """
    if not truth or not prediction:
        return []
    window = min(20, max(len(truth), len(prediction)) // 4 or 10)
    step = max(1, window // 2)
    spans: list[dict[str, object]] = []
    i = 0
    while i < max(len(truth), len(prediction)):
        t_slice = truth[i : i + window] if i < len(truth) else ""
        p_slice = prediction[i : i + window] if i < len(prediction) else ""
        sim = alignment_similarity(t_slice, p_slice)
        if sim < threshold:
            spans.append(
                {"start": i, "end": i + window, "truth_slice": t_slice, "pred_slice": p_slice}
            )
        i += step
    return spans
