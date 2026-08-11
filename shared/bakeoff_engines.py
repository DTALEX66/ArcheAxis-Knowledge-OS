"""H2 bake-off engine registry.

Each engine is an EngineUnderTest with a callable that converts a file
to text. Engines may be unavailable (MissingDependency) — the bake-off
skips them honestly.

Only Tesseract is currently available (system binary via pytesseract).
PaddleOCR, RapidOCR, EasyOCR are registered as unavailable-honest stubs
— they will become available when the corresponding package is installed.
"""

from __future__ import annotations

from pathlib import Path

from shared.bakeoff import EngineUnderTest

__all__ = ["OCR_ENGINES", "get_available_engines"]


# ── Tesseract (always available if system binary exists) ──


def _tesseract(fp: Path) -> str:
    import pytesseract
    from PIL import Image

    img = Image.open(fp)
    return pytesseract.image_to_string(img, lang="eng+chi_sim")


TESSERACT = EngineUnderTest(
    name="tesseract",
    fn=_tesseract,
    available=True,
    version="5.5.0 (tesseract) + 1.85.0 (leptonica)",
    notes="System binary; eng+chi_sim language data required.",
)


# ── PaddleOCR (unavailable by default — requires paddlepaddle) ──


def _paddleocr_stub(fp: Path) -> str:
    try:
        from paddleocr import PaddleOCR  # noqa: F811
    except ImportError:
        raise RuntimeError("PaddleOCR not installed: pip install paddlepaddle paddleocr")
    ocr = PaddleOCR(lang="ch")
    result = ocr.ocr(str(fp))
    lines = []
    if result and result[0]:
        for line in result[0]:
            text = line[1][0] if len(line) > 1 and line[1] else ""
            if text:
                lines.append(text)
    return "\n".join(lines)


PADDLEOCR = EngineUnderTest(
    name="paddleocr",
    fn=_paddleocr_stub,
    available=False,
    version="unknown (not installed)",
    notes="Requires paddlepaddle + paddleocr packages. Strongest Chinese OCR candidate.",
)


# ── EasyOCR (unavailable by default — requires torch) ──


def _easyocr_stub(fp: Path) -> str:
    try:
        import easyocr  # noqa: F401
    except ImportError:
        raise RuntimeError("EasyOCR not installed: pip install easyocr")
    import easyocr as _eocr

    reader = _eocr.Reader(["en", "ch_sim"])
    result = reader.readtext(str(fp))
    return "\n".join(text for _, text, _ in result)


EASYOCR = EngineUnderTest(
    name="easyocr",
    fn=_easyocr_stub,
    available=False,
    version="unknown (not installed)",
    notes="Requires torch + easyocr. Bake-off candidate vs Tesseract/PaddleOCR.",
)


# ── RapidOCR (unavailable by default — ONNX-based) ──


def _rapidocr_stub(fp: Path) -> str:
    try:
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401
    except ImportError:
        raise RuntimeError("RapidOCR not installed: pip install rapidocr-onnxruntime")
    from rapidocr_onnxruntime import RapidOCR as _ROCR

    engine = _ROCR()
    result, _ = engine(str(fp))
    lines = []
    if result:
        for item in result:
            text = item[1] if len(item) > 1 else ""
            if text:
                lines.append(text)
    return "\n".join(lines)


RAPIDOCR = EngineUnderTest(
    name="rapidocr",
    fn=_rapidocr_stub,
    available=False,
    version="unknown (not installed)",
    notes="ONNX-based, no heavy framework dependency. Windows/CPU friendly.",
)


# ── Registry ──

OCR_ENGINES: list[EngineUnderTest] = [TESSERACT, PADDLEOCR, EASYOCR, RAPIDOCR]


def get_available_engines() -> list[EngineUnderTest]:
    return [e for e in OCR_ENGINES if e.available]
