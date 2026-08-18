"""RapidOCR adapter — Chinese OCR primary engine (包 C conclusion).

rapidocr-onnxruntime is installed: PaddleOCR models re-implemented in ONNX
(no Paddle dependency, ~15MB, CPU fast, fully offline). Use it for images and
scanned PDFs; tesseract stays as fallback/gate.

    ocr_image(path)          → (text, engine) via RapidOCR
    convert_image_rapid(p)   → dict {success, text, engine, chars}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class RapidOcrError(ValueError):
    """Raised when RapidOCR is unavailable or fails."""


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _engine = RapidOCR()
        except ImportError as exc:
            raise RapidOcrError("rapidocr-onnxruntime not installed") from exc
    return _engine


def ocr_image(path: str | Path) -> tuple[str, str]:
    """OCR one image; returns (text, engine_label)."""
    engine = _get_engine()
    result, _ = engine(str(path))
    if not result:
        return "", "rapidocr"
    lines = [item[1] for item in result if len(item) > 1 and item[1]]
    return "\n".join(lines), "rapidocr"


def convert_image_rapid(path: str | Path) -> dict[str, Any]:
    """Convert one image via RapidOCR (fail-closed dict result)."""
    p = Path(path)
    if not p.is_file():
        return {"success": False, "text": "", "engine": "rapidocr",
                "error": "file not found"}
    try:
        text, engine = ocr_image(p)
    except RapidOcrError as exc:
        return {"success": False, "text": "", "engine": "rapidocr",
                "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "text": "", "engine": "rapidocr",
                "error": f"rapidocr failed: {exc}"}
    return {"success": bool(text.strip()), "text": text, "engine": engine,
            "chars": len(text)}
