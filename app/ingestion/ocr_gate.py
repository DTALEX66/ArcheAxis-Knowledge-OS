"""OCR quality gate — H2 quality gate (loop gap: OCR/ASR/quality).

Raw OCR output is not truth: garbage pages, blank scans and language mismatch
must be caught before content enters the evidence chain. This gate scores OCR
text deterministically and returns a fail-closed verdict:

    score_ocr(text)  → quality metrics (chars, printable ratio, script ratio)
    assess(text)     → verdict pass | review | fail + reasons

Pipeline callers route fail → REVIEW, pass → normal ingest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

MIN_VALID_CHARS = 20
MIN_PRINTABLE_RATIO = 0.5
MIN_SCRIPT_RATIO = 0.4


class OcrGateError(ValueError):
    """Raised when OCR gate input is invalid."""


@dataclass(frozen=True)
class OcrQuality:
    char_count: int
    printable_ratio: float
    script_ratio: float
    blank: bool

    def as_dict(self) -> dict[str, object]:
        return {"char_count": self.char_count, "printable_ratio": round(self.printable_ratio, 3),
                "script_ratio": round(self.script_ratio, 3), "blank": self.blank}


@dataclass(frozen=True)
class OcrVerdict:
    verdict: Literal["pass", "review", "fail"]
    quality: OcrQuality
    reasons: list[str]

    def as_dict(self) -> dict[str, object]:
        return {"verdict": self.verdict, "quality": self.quality.as_dict(),
                "reasons": self.reasons}


_SCRIPT_RE = re.compile(r"[\w\u4e00-\u9fff]")
_PRINTABLE_RE = re.compile(r"[^\x00-\x08\x0b-\x1f\x7f]")


def _char_count(text: str) -> int:
    return len(text.strip())


def score_ocr(text: str) -> OcrQuality:
    """Deterministic quality metrics for OCR output."""
    if not isinstance(text, str):
        raise OcrGateError("OCR text must be a string")
    stripped = text.strip()
    char_count = len(stripped)
    if char_count == 0:
        return OcrQuality(char_count=0, printable_ratio=0.0, script_ratio=0.0, blank=True)
    printable = len(_PRINTABLE_RE.findall(stripped))
    script = len(_SCRIPT_RE.findall(stripped))
    return OcrQuality(
        char_count=char_count,
        printable_ratio=printable / char_count,
        script_ratio=script / char_count,
        blank=False,
    )


def assess(text: str) -> OcrVerdict:
    """Fail-closed verdict: fail (blank/garbage) → review (low signal) → pass."""
    quality = score_ocr(text)
    reasons: list[str] = []
    if quality.blank:
        return OcrVerdict("fail", quality, ["blank OCR output"])
    if quality.char_count < MIN_VALID_CHARS:
        reasons.append(f"too few characters ({quality.char_count} < {MIN_VALID_CHARS})")
    if quality.printable_ratio < MIN_PRINTABLE_RATIO:
        reasons.append(f"low printable ratio ({quality.printable_ratio:.2f} < {MIN_PRINTABLE_RATIO})")
    if quality.script_ratio < MIN_SCRIPT_RATIO:
        reasons.append(f"low script ratio ({quality.script_ratio:.2f} < {MIN_SCRIPT_RATIO})")
    if not reasons:
        return OcrVerdict("pass", quality, ["OCR quality acceptable"])
    if quality.char_count >= MIN_VALID_CHARS and quality.printable_ratio >= MIN_PRINTABLE_RATIO:
        return OcrVerdict("review", quality, reasons)
    return OcrVerdict("fail", quality, reasons)
