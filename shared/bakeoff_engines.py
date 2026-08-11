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


def _tesseract(fp: Path, *, lang: str = "eng") -> str:
    import pytesseract
    from PIL import Image

    img = Image.open(fp)
    return pytesseract.image_to_string(img, lang=lang)


def _tesseract_eng(fp: Path) -> str:
    return _tesseract(fp, lang="eng")


def _tesseract_chi_sim(fp: Path) -> str:
    return _tesseract(fp, lang="chi_sim")


TESSERACT = EngineUnderTest(
    name="tesseract",
    fn=_tesseract_eng,
    available=True,
    version="5.5.0 (tesseract) + 1.85.0 (leptonica)",
    notes="System binary; English model. For Chinese use tesseract-chi-sim.",
)

# chi_sim model handles Chinese text without inserting spaces between
# characters (eng+chi_sim does, which inflates CER); English fixtures are
# still legible at slightly higher CER than the dedicated eng model.
TESSERACT_CHI_SIM = EngineUnderTest(
    name="tesseract-chi-sim",
    fn=_tesseract_chi_sim,
    available=True,
    version="5.5.0 (tesseract) + 1.85.0 (leptonica)",
    notes="System binary; Simplified-Chinese model. Recommended for CJK-first corpora.",
)


# ── PaddleOCR (unavailable by default — requires paddlepaddle) ──


def _paddleocr_stub(fp: Path) -> str:
    try:
        from paddleocr import PaddleOCR  # noqa: F811
    except ImportError:
        raise RuntimeError("PaddleOCR not installed: pip install paddlepaddle paddleocr") from None
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
        raise RuntimeError("EasyOCR not installed: pip install easyocr") from None
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
        raise RuntimeError("RapidOCR not installed: pip install rapidocr-onnxruntime") from None
    from rapidocr_onnxruntime import RapidOCR as RapidOCREngine

    engine = RapidOCREngine()
    result, _ = engine(str(fp))
    lines = []
    if result:
        for item in result:
            text = item[1] if len(item) > 1 else ""
            if text:
                lines.append(text)
    return "\n".join(lines)


def _rapidocr_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("rapidocr_onnxruntime") is not None
    except Exception:
        return False


RAPIDOCR = EngineUnderTest(
    name="rapidocr",
    fn=_rapidocr_stub,
    available=_rapidocr_available(),
    version="1.4.4 (rapidocr-onnxruntime)" if _rapidocr_available() else "unknown (not installed)",
    notes="ONNX-based, no heavy framework dependency. Windows/CPU friendly.",
)


# ── Registry ──

OCR_ENGINES: list[EngineUnderTest] = [TESSERACT, TESSERACT_CHI_SIM, PADDLEOCR, EASYOCR, RAPIDOCR]


# ── ASR engines (all unavailable — need model download) ──


def _faster_whisper_stub(fp: Path) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper not installed: pip install faster-whisper") from None
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(fp))
    return " ".join(s.text for s in segments)


FASTER_WHISPER = EngineUnderTest(
    name="faster-whisper", fn=_faster_whisper_stub, available=False,
    version="unknown", notes="MIT. CTranslate2-based. Best batch ASR candidate.",
)


def _whisper_cpp_stub(fp: Path) -> str:
    try:
        from whisper_cpp import Whisper
    except ImportError:
        raise RuntimeError("whisper.cpp not installed") from None
    return Whisper(model_path="ggml-base.bin").transcribe(str(fp))


WHISPER_CPP = EngineUnderTest(
    name="whisper.cpp", fn=_whisper_cpp_stub, available=False,
    version="unknown", notes="MIT. CPU/quantized. Independent from faster-whisper.",
)

ASR_ENGINES: list[EngineUnderTest] = [FASTER_WHISPER, WHISPER_CPP]


def get_available_engines() -> list[EngineUnderTest]:
    return [e for e in OCR_ENGINES if e.available]
