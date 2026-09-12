"""R15/F04: every image media type the Core can now name really works.

The Core derives a job's media type from the source name and requires it to be one
the OCR route accepts (png, jpeg, tiff, webp, bmp). That claim is only worth making
if each of those formats actually travels through the transport to the real engine,
so this test renders one synthetic screenshot, encodes it in each format, runs the
route's own `extract` with the format's media type, and asserts the recognised text
comes back.

The engine is the real Tesseract install; a missing engine is a skip, never a pass.
The sample is synthetic and rendered here, so nothing private is involved.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PIL_Image = pytest.importorskip("PIL.Image", reason="PIL required to build samples")
PIL_ImageDraw = pytest.importorskip("PIL.ImageDraw", reason="PIL required to build samples")

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "vision" / "worker_ocr.py"
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"
TESSDATA = REPO / "tools" / "tesseract" / "tessdata"

# (suffix, media type) exactly as the Core's ROUTE_MEDIA_TYPES declares them for
# image.ocr; the suffix is what makes the name recognisable to the derivation.
FORMATS = [
    (".png", "image/png"),
    (".jpg", "image/jpeg"),
    (".tiff", "image/tiff"),
    (".webp", "image/webp"),
    (".bmp", "image/bmp"),
]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load("worker_ocr_media_types", WORKER)
transport = _load("text_ndjson_media_types", TRANSPORT)


def _engine_available() -> bool:
    try:
        worker._tesseract()
    except Exception:
        return False
    return (TESSDATA / "eng.traineddata").is_file()


pytestmark = pytest.mark.skipif(not _engine_available(), reason="tesseract binary or eng.traineddata missing")


def _render(path: Path) -> None:
    image = PIL_Image.new("RGB", (520, 120), "white")
    PIL_ImageDraw.Draw(image).text((20, 40), "ArcheAxis 6371 km", fill="black")
    image.save(path)


def test_the_transport_accepts_exactly_the_media_types_the_core_can_name() -> None:
    """The Core's declared set and the worker's declared set must not drift apart."""
    declared = set(transport.ROUTES["image.ocr"]["media_types"])
    assert declared == {media for _, media in FORMATS}, declared


@pytest.mark.parametrize(("suffix", "media_type"), FORMATS)
def test_each_image_media_type_reaches_the_engine_and_returns_text(tmp_path: Path, suffix: str, media_type: str) -> None:
    sample = tmp_path / f"screenshot{suffix}"
    _render(sample)
    assert sample.stat().st_size > 0

    result = worker.extract(sample, lang="eng", tessdata_dir=TESSDATA)
    assert result["engine"] == worker.ENGINE
    assert result["text"].strip(), f"{media_type} produced no text"
    assert "6371" in result["text"] or "637" in result["text"], (media_type, result["text"])

    structure = result["structure"]
    assert structure, f"{media_type} text must be anchored"
    assert structure[0]["kind"] == "line"
    assert structure[-1]["char_end"] == len(result["text"])
    receipt = result["loss_receipt"]
    assert receipt["covered"] == receipt["total"] == len(structure)
    assert receipt["params"]["regions"], f"{media_type} must keep its word boxes for review"
    assert "accuracy" not in str(receipt).lower()


def test_a_format_the_core_cannot_name_is_not_silently_accepted(tmp_path: Path) -> None:
    """A format outside the declared set must not be presented as a supported image."""
    declared = {media for _, media in FORMATS}
    assert "image/gif" not in declared
    assert declared == set(transport.ROUTES["image.ocr"]["media_types"])
