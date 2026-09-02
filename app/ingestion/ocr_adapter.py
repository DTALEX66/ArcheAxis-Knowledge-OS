"""AXW-023D: structured OCR adapter (page anchors + quality metrics).

Converts scanned PDF pages / images into per-page OCR blocks with stable
page/region anchors, engine + language metadata and a per-page quality
score (non-space char ratio). Detects language hints from a small keyword
set (zh/eng). Fails closed when pytesseract / tesseract binaries are
unavailable — no fake success, no automatic model downloads.
"""

from __future__ import annotations

import contextlib
import os
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from shared.adapter_contract import AdapterResult

def _is_usable_tesseract(candidate: str | Path) -> bool:
    """Check that a Tesseract candidate is runnable, not merely present."""
    try:
        completed = subprocess.run(
            [str(candidate), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and "tesseract" in completed.stdout.casefold()


def _external_roots() -> tuple[Path, ...]:
    """Read the configured shared-tool root at conversion time."""
    return tuple(
        Path(value)
        for value in (
            os.environ.get("OS_EXTERNAL_CONFIG", "").strip(),
            os.environ.get("ARCHEAXIS_EXTERNAL_ROOT", "").strip(),
        )
        if value
    )


def _resolve_tesseract() -> str:
    """Resolve a functioning binary, skipping stale PATH shims on Windows."""
    import shutil

    candidates = [os.environ.get("TESSERACT_CMD", "").strip(), shutil.which("tesseract") or ""]
    for root in _external_roots():
        candidates.extend(
            str(root / relative)
            for relative in (
                Path("10-toolchains") / "scoop" / "apps" / "tesseract" / "current" / "tesseract.exe",
                Path("toolchains") / "scoop" / "apps" / "tesseract" / "current" / "tesseract.exe",
            )
        )
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        normalized = os.path.normcase(os.path.abspath(candidate))
        if normalized in seen:
            continue
        seen.add(normalized)
        if Path(candidate).is_file() and _is_usable_tesseract(candidate):
            return candidate
    return ""


def configure_tesseract() -> tuple[str, str]:
    """Resolve tesseract binary + TESSDATA_PREFIX robustly (fixes broken env).

    The user/session env may carry a stale TESSDATA_PREFIX (e.g. missing the
    "10-" prefix) that makes every OCR call fail with "couldn't load any
    languages". This resolver:
      1. finds the binary via env -> shutil.which -> known scoop paths,
      2. finds a valid tessdata dir via env -> scoop tesseract-languages ->
         tesseract's own tessdata/,
      3. pins pytesseract.tesseract_cmd and os.environ["TESSDATA_PREFIX"].
    """
    binary = _resolve_tesseract()

    def valid_tessdata(candidate: Path) -> bool:
        return candidate.is_dir() and any(candidate.glob("*.traineddata"))

    tessdata = ""
    env_prefix = os.environ.get("TESSDATA_PREFIX", "")
    if env_prefix and valid_tessdata(Path(env_prefix)):
        tessdata = env_prefix
    if not tessdata:
        for root in _external_roots():
            for prefix in ("10-toolchains", "toolchains"):
                candidate = root / prefix / "scoop" / "apps" / "tesseract-languages" / "current"
                if valid_tessdata(candidate):
                    tessdata = str(candidate)
                    break
            if tessdata:
                break
    if not tessdata and binary:
        binary_path = Path(binary)
        toolchain_root = next(
            (parent for parent in binary_path.parents if parent.name in {"10-toolchains", "toolchains"}),
            None,
        )
        if toolchain_root is not None:
            candidate = toolchain_root / "scoop" / "apps" / "tesseract-languages" / "current"
            if valid_tessdata(candidate):
                tessdata = str(candidate)
    if not tessdata and binary:
        own = Path(binary).parent / "tessdata"
        if valid_tessdata(own):
            tessdata = str(own)

    try:
        import pytesseract
        if binary:
            pytesseract.pytesseract.tesseract_cmd = binary
        if tessdata:
            os.environ["TESSDATA_PREFIX"] = tessdata
    except ImportError:
        pass
    return binary, tessdata


configure_tesseract()

_LANG_HINTS = {
    "zh": re.compile(r"[\u4e00-\u9fff]"),
    "eng": re.compile(r"[A-Za-z]{3,}"),
}


def _sha256(file_path: str | Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _detect_language(text: str) -> list[str]:
    """Heuristic language hint from OCR text (zh/eng only)."""
    langs: list[str] = []
    for lang, pattern in _LANG_HINTS.items():
        if pattern.search(text):
            langs.append(lang)
    return langs or ["unknown"]


def _quality(text: str) -> float:
    """Non-space printable ratio as a simple per-page OCR quality signal."""
    if not text:
        return 0.0
    non_space = sum(1 for ch in text if not ch.isspace())
    return round(non_space / len(text), 3)


def _ocr_image(path: Path, lang: str) -> tuple[str, str]:
    """OCR one image; returns (text, engine_label)."""
    import pytesseract
    from PIL import Image

    text = pytesseract.image_to_string(Image.open(path), lang=lang)
    return text or "", f"pytesseract({lang})"


def _extract_pages(path: Path, lang: str) -> tuple[list[dict[str, Any]], list[str]]:
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    blocks: list[dict[str, Any]] = []
    loss: list[str] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        # Prefer the embedded text layer; fall back to OCR only when empty.
        text = page.get_text().strip()
        engine = "embedded-text"
        if not text:
            pix = page.get_pixmap(dpi=200)
            tmp = path.with_suffix(f".p{page_idx}.png")
            pix.save(str(tmp))
            try:
                text, engine = _ocr_image(tmp, lang)
            finally:
                with contextlib.suppress(OSError):
                    tmp.unlink()
            if not text:
                loss.append(f"page {page_idx + 1}: OCR returned no text")
                continue
        blocks.append(
            {
                "kind": "page",
                "text": text,
                "anchor": {"page_index": page_idx, "page_number": page_idx + 1},
                "metadata": {"engine": engine, "quality": _quality(text)},
            }
        )
    doc.close()
    return blocks, loss


def convert_ocr(file_path: str | Path, lang: str = "eng+chi_sim") -> AdapterResult:
    """OCR a scanned PDF or image into per-page/region blocks."""
    path = Path(file_path)
    if not path.is_file():
        return AdapterResult(success=False, content="", engine="ocr-adapter", error="file not found")

    try:
        import fitz  # noqa: F401
        import pytesseract  # noqa: F401
    except ImportError:
        return AdapterResult(
            success=False,
            content="",
            engine="ocr-adapter",
            error="OCR requires pytesseract + PyMuPDF; install pymupdf and pytesseract.",
        )

    try:
        blocks, loss = _extract_pages(path, lang)
    except Exception as exc:  # pragma: no cover - host-tooling dependent
        return AdapterResult(
            success=False,
            content="",
            engine="ocr-adapter",
            error=f"OCR conversion failed: {exc}",
        )

    if not blocks:
        return AdapterResult(
            success=False,
            content="",
            engine="ocr-adapter",
            error="OCR returned no content; treat as degraded.",
        )

    text = "\n\n".join(b["text"] for b in blocks)
    languages = _detect_language(text)
    return AdapterResult(
        success=True,
        content=text,
        engine="ocr-adapter",
        metadata={
            "char_count": len(text),
            "block_count": len(blocks),
            "blocks": blocks,
            "loss_notes": loss,
            "languages": languages,
        },
    )


def convert_ocr_to_run(
    file_path: str | Path,
    db: str | Path,
    source_name: str | None = None,
    version: int = 1,
    lang: str = "eng+chi_sim",
) -> dict[str, Any]:
    """OCR a file and persist a ConversionRun; returns run metadata."""
    result = convert_ocr(file_path, lang=lang)
    if not result.success:
        raise RuntimeError(result.error or "OCR conversion failed")

    from app.ingestion.conversion_run import create_conversion_run, store_conversion_run

    raw_sha = _sha256(file_path)
    blocks: list[dict[str, Any]] = result.metadata.get("blocks") or []
    loss = result.metadata.get("loss_notes") or []
    run = create_conversion_run(
        raw_sha256=raw_sha,
        source_name=source_name or Path(file_path).name,
        blocks=blocks,
        engine=result.engine,
        version=version,
    )
    store_conversion_run(db, run)
    return {
        "run_id": run.run_id,
        "document_id": run.document.document_id,
        "block_count": len(blocks),
        "loss_notes": loss,
        "languages": result.metadata.get("languages", []),
    }
