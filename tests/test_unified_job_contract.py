"""R08: one job contract serves every extraction route.

All three routes (text.extract, pdf.extract, image.ocr) go through the same
request envelope, the same rejection semantics and the same artifact triple
(text + document_structure + loss_report), so PDF and OCR input now enter the
same job/attempt/error machinery as text instead of being separate CLIs.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"
TESSDATA = REPO / "tools" / "tesseract" / "tessdata"


def _load():
    spec = importlib.util.spec_from_file_location("transport_under_test", TRANSPORT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


transport = _load()


def _staging(tmp_path: Path, data: bytes) -> tuple[Path, str]:
    staging = tmp_path / "staging"
    (staging / "input").mkdir(parents=True)
    digest = hashlib.sha256(data).hexdigest()
    (staging / "input" / digest).write_bytes(data)
    return staging, digest


def _request(capability: str, digest: str, media_type: str, version: str = "1") -> dict:
    return {
        "schema": "archeaxis.worker-request/v1",
        "type": "job_request",
        "request_id": "req-1",
        "job_id": "job-1",
        "attempt": 1,
        "protocol_minor": 0,
        "capability": capability,
        "capability_version": version,
        "deadline_ms": 60_000,
        "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": media_type}],
        "parameters": {},
    }


def _artifact(staging: Path, outputs: list[dict], kind: str) -> bytes:
    entry = next(o for o in outputs if o["kind"] == kind)
    digest = entry["uri"].rsplit("/", 1)[-1]
    return (staging / "output" / digest).read_bytes()


def _kinds(outputs: list[dict]) -> list[str]:
    return [o["kind"] for o in outputs]


def test_text_route_still_uses_the_shared_envelope(tmp_path: Path) -> None:
    staging, digest = _staging(tmp_path, "alpha 6371 km\n".encode("utf-8"))
    outputs, measurements, _warnings = transport.execute(
        _request("text.extract", digest, "text/plain"), staging
    )
    assert _kinds(outputs) == ["text", "document_structure", "loss_report"]
    assert b"6371" in _artifact(staging, outputs, "text")
    assert measurements["input_bytes"] > 0
    assert all(o["authority_effect"] == "candidate_or_measurement_only" for o in outputs)


def test_pdf_route_uses_the_same_contract(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz", reason="native PDF engine required")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "PDF route 6371 km")
    pdf_bytes = doc.tobytes()
    doc.close()

    staging, digest = _staging(tmp_path, pdf_bytes)
    outputs, _measurements, _warnings = transport.execute(
        _request("pdf.extract", digest, "application/pdf"), staging
    )
    assert _kinds(outputs) == ["text", "document_structure", "loss_report"]
    assert b"6371" in _artifact(staging, outputs, "text")
    structure = json.loads(_artifact(staging, outputs, "document_structure"))
    assert structure and structure[0]["path"][0].startswith("page-")


def test_ocr_route_uses_the_same_contract(tmp_path: Path) -> None:
    Image = pytest.importorskip("PIL.Image", reason="PIL required")
    Draw = pytest.importorskip("PIL.ImageDraw", reason="PIL required")
    if not (TESSDATA / "eng.traineddata").is_file() or shutil.which("tesseract") is None:
        pytest.skip("tesseract binary or repository eng.traineddata unavailable")

    image = Image.new("RGB", (420, 110), "white")
    Draw.Draw(image).text((20, 40), "ocr route 6371", fill="black")
    buf = tmp_path / "shot.png"
    image.save(buf)

    staging, digest = _staging(tmp_path, buf.read_bytes())
    outputs, _measurements, _warnings = transport.execute(
        _request("image.ocr", digest, "image/png"), staging
    )
    assert _kinds(outputs) == ["text", "document_structure", "loss_report"]
    structure = json.loads(_artifact(staging, outputs, "document_structure"))
    assert structure and structure[0]["kind"] == "region"


def test_unknown_capability_is_rejected(tmp_path: Path) -> None:
    staging, digest = _staging(tmp_path, b"data")
    with pytest.raises(transport.Rejected) as excinfo:
        transport.execute(_request("video.transcode", digest, "text/plain"), staging)
    assert "unsupported capability" in str(excinfo.value)


def test_media_type_is_checked_per_route(tmp_path: Path) -> None:
    staging, digest = _staging(tmp_path, b"%PDF-1.4 not really")
    with pytest.raises(transport.Rejected) as excinfo:
        transport.execute(_request("pdf.extract", digest, "text/plain"), staging)
    assert "unsupported media type" in str(excinfo.value)


def test_wrong_capability_version_is_rejected(tmp_path: Path) -> None:
    staging, digest = _staging(tmp_path, b"alpha")
    with pytest.raises(transport.Rejected) as excinfo:
        transport.execute(_request("text.extract", digest, "text/plain", version="2"), staging)
    assert "unsupported capability or protocol version" in str(excinfo.value)
