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


# ── H2: Conversion quality gate ──


def assess_conversion(
    source_path: str | None = None,
    output_text: str = "",
    truth_text: str | None = None,
    *,
    min_char_ratio: float = 0.01,
) -> dict[str, object]:
    """Post-conversion quality assessment (routing → quality gate).

    Returns a dict with:
      - status: "PASS" | "WARN" | "FAIL"
      - cer/wer: if truth provided
      - char_count, empty, issues list
    """
    issues: list[str] = []
    char_count = len(output_text)

    if char_count == 0:
        return {"status": "FAIL", "reason": "empty output", "char_count": 0, "issues": ["empty"]}

    # Structural heuristics
    control_char_ratio = sum(1 for c in output_text if ord(c) < 32 and c not in "\n\r\t") / max(char_count, 1)
    if control_char_ratio > 0.05:
        issues.append(f"high control chars ({control_char_ratio:.2%})")

    # Source-to-output ratio
    if source_path:
        try:
            from pathlib import Path

            src_size = Path(source_path).stat().st_size
            if src_size > 0 and char_count / src_size < min_char_ratio:
                issues.append(f"low output ratio ({char_count}/{src_size})")
        except OSError:
            pass

    # CER/WER if truth available
    result: dict[str, object] = {
        "char_count": char_count,
        "issues": issues,
        "status": "WARN" if issues else "PASS",
    }
    if truth_text:
        result["cer"] = round(cer(truth_text, output_text), 4)
        result["wer"] = round(wer(truth_text, output_text), 4)
        if float(result["cer"]) > 0.3:
            result["status"] = "FAIL"
            issues.append("high CER")
        elif float(result["cer"]) > 0.1:
            if result["status"] != "FAIL":
                result["status"] = "WARN"
            issues.append("elevated CER")

    result["issues"] = issues
    if result.get("status") != "FAIL":
        result["status"] = "WARN" if issues else "PASS"
    return result
