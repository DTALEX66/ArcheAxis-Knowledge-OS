"""R08: the OCR route answers in the same contract as the text and PDF routes
(engine / text / structure anchors / loss receipt), keeps region boxes for
review, never presents confidence as accuracy, and degrades explicitly when a
sample carries no recognisable text.

Samples are synthetic (PIL-rendered images); the OCR engine here is the real
Tesseract install, so a missing engine is reported as a skip rather than a
silent pass.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PIL_Image = pytest.importorskip("PIL.Image", reason="PIL required to build samples")
PIL_ImageDraw = pytest.importorskip("PIL.ImageDraw", reason="PIL required to build samples")

WORKER = Path(__file__).resolve().parents[1] / "services" / "python-workers" / "vision" / "worker_ocr.py"
# AGENTS.md: scanned input requires OCR with TESSDATA_PREFIX set. The repository
# ships the traineddata under tools/tesseract/tessdata, and the ambient
# TESSDATA_PREFIX in some shells points at a directory that does not exist, so the
# route is exercised with the repository tessdata explicitly.
TESSDATA = Path(__file__).resolve().parents[1] / "tools" / "tesseract" / "tessdata"


def _load():
    spec = importlib.util.spec_from_file_location("worker_ocr_under_test", WORKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


worker = _load()


def _engine_available() -> bool:
    try:
        worker._tesseract()
    except Exception:
        return False
    return (TESSDATA / "eng.traineddata").is_file()


pytestmark = pytest.mark.skipif(not _engine_available(), reason="tesseract binary or eng.traineddata missing")


def _render(path: Path, line: str) -> None:
    image = PIL_Image.new("RGB", (520, 120), "white")
    draw = PIL_ImageDraw.Draw(image)
    # Large, high-contrast text so a synthetic sample is reliable to recognise.
    draw.text((20, 40), line, fill="black")
    image.save(path)


def test_ocr_route_returns_the_shared_contract_with_line_anchors(tmp_path: Path) -> None:
    sample = tmp_path / "screenshot.png"
    _render(sample, "ArcheAxis 6371 km")
    result = worker.extract(sample, lang="eng", tessdata_dir=TESSDATA)

    assert result["engine"] == worker.ENGINE
    assert result["text"].strip(), "a non-empty synthetic sample must produce text"
    assert "6371" in result["text"] or "637" in result["text"], result["text"]

    # R08: the Core's projection contract is line-based for every route, so the
    # structure artifact is canonical line anchors in the recognised text.
    structure = result["structure"]
    assert structure, "recognised text must be anchored"
    anchor = structure[0]
    assert anchor["kind"] == "line"
    assert anchor["path"][0].startswith("line-")
    assert 0 <= anchor["char_start"] < anchor["char_end"] <= len(result["text"])
    # The recognised text is fully covered line by line.
    assert structure[-1]["char_end"] == len(result["text"])

    receipt = result["loss_receipt"]
    assert receipt["engine"] == worker.ENGINE
    # OCR's own word regions are review metadata, not the projection contract.
    regions = receipt["params"]["regions"]
    assert regions, "word boxes must still be retained for review"
    assert set(regions[0]["bbox"]) == {"x", "y", "w", "h"}, regions[0]["bbox"]
    assert isinstance(regions[0]["confidence"], (int, float))
    # Coverage is supplied with the anchors, in the same unit.
    assert receipt["covered"] == receipt["total"] == len(structure)
    assert receipt["coverage"] == 1.0
    assert "accuracy" not in str(receipt).lower(), "confidence must not be presented as accuracy"


def test_blank_sample_does_not_claim_recognition(tmp_path: Path) -> None:
    blank = tmp_path / "blank.png"
    PIL_Image.new("RGB", (400, 100), "white").save(blank)
    result = worker.extract(blank, lang="eng", tessdata_dir=TESSDATA)
    assert result["text"].strip() == "", "no text may be invented for a blank sample"
    assert result["structure"] == []
    assert result["anchor_summary"] == {"covered": 0, "total": 0}
    assert result["loss_receipt"]["loss_note"], "an empty result still carries an honest loss note"
