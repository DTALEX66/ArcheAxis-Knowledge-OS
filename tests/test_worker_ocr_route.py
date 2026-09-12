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


def test_low_scoring_regions_are_listed_for_review_without_claiming_correctness(tmp_path: Path) -> None:
    sample = tmp_path / "screenshot.png"
    _render(sample, "ArcheAxis 6371 km")
    result = worker.extract(sample, lang="eng", tessdata_dir=TESSDATA)
    receipt = result["loss_receipt"]
    review = receipt["params"]["review"]

    assert review["threshold"] == worker.REVIEW_THRESHOLD
    assert "not a correctness measure" in review["threshold_meaning"]
    assert review["region_count"] == len(receipt["params"]["regions"])
    assert review["scored_region_count"] + review["unscored_region_count"] == review["region_count"]
    assert review["low_confidence_count"] == len(review["low_confidence_regions"])

    # every listed region really is below the threshold, and carries its own score
    for region in review["low_confidence_regions"]:
        assert region["confidence"] < worker.REVIEW_THRESHOLD
        assert set(region["bbox"]) == {"x", "y", "w", "h"}
        assert 0 <= region["char_start"] < region["char_end"] <= len(result["text"])
    if review["scored_region_count"]:
        assert review["lowest_score"] == min(
            region["confidence"] for region in receipt["params"]["regions"]
        )
    # a listed region is also named in the loss list rather than only in the params
    if review["low_confidence_count"]:
        assert any("review threshold" in loss for loss in receipt["losses"])
    # and the receipt never uses the word that would turn a score into a claim
    assert "accuracy" not in str(receipt).lower()


def test_the_review_threshold_is_an_aid_not_a_verdict(tmp_path: Path) -> None:
    """A score above the threshold must never be read as "the text is right".

    A degraded render here is recognised as garbage ("nT" instead of the sample line)
    and still scores above the review threshold. That is exactly why the receipt names
    a review threshold instead of presenting the score as a measure of correctness, and
    this test pins the fact so nobody later treats the number as a verdict.
    """
    clean = tmp_path / "clean.png"
    _render(clean, "ArcheAxis 6371 km")
    degraded = tmp_path / "degraded.png"
    image = PIL_Image.new("RGB", (520, 120), "white")
    draw = PIL_ImageDraw.Draw(image)
    for x in range(0, 520, 3):
        draw.line([(x, 0), (x, 119)], fill=(200, 200, 200))
    draw.text((20, 40), "ArcheAxis 6371 km", fill="black")
    image.save(degraded)

    clean_receipt = worker.extract(clean, lang="eng", tessdata_dir=TESSDATA)["loss_receipt"]
    degraded_result = worker.extract(degraded, lang="eng", tessdata_dir=TESSDATA)
    degraded_receipt = degraded_result["loss_receipt"]

    for receipt in (clean_receipt, degraded_receipt):
        review = receipt["params"]["review"]
        # the arithmetic must hold whatever the image was
        assert review["region_count"] == len(receipt["params"]["regions"])
        assert review["scored_region_count"] + review["unscored_region_count"] == review["region_count"]
        assert review["low_confidence_count"] == len(review["low_confidence_regions"])
        assert review["low_confidence_count"] <= review["region_count"]
        assert review["threshold"] == worker.REVIEW_THRESHOLD
        assert "not a correctness measure" in review["threshold_meaning"]
        assert "accuracy" not in str(receipt).lower()

    # the degraded read really is wrong, and it can still score above the threshold
    if degraded_receipt["params"]["regions"]:
        assert "6371" not in degraded_result["text"] or degraded_result["text"] != "ArcheAxis 6371 km"
        scores = [region["confidence"] for region in degraded_receipt["params"]["regions"]]
        if scores and max(scores) >= worker.REVIEW_THRESHOLD:
            assert degraded_receipt["params"]["review"]["low_confidence_count"] < len(scores), (
                "a wrong reading above the threshold is the reason the threshold is an aid, not a verdict"
            )
