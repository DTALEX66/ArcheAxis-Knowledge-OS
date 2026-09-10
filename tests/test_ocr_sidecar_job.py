"""R08 step (b), OCR half: the image route reaches the Core through the same
sidecar stdio job loop as the text and PDF routes, declaring its own identity
and capability, and refuses capabilities it never advertised.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "vision" / "worker_ocr.py"
TESSDATA = REPO / "tools" / "tesseract" / "tessdata"

Image = pytest.importorskip("PIL.Image", reason="PIL required to build a sample")
Draw = pytest.importorskip("PIL.ImageDraw", reason="PIL required to build a sample")

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None or not (TESSDATA / "eng.traineddata").is_file(),
    reason="tesseract binary or repository eng.traineddata unavailable",
)


def _staging_with(tmp_path: Path, data: bytes) -> tuple[Path, str]:
    staging = tmp_path / "staging"
    (staging / "input").mkdir(parents=True)
    digest = hashlib.sha256(data).hexdigest()
    (staging / "input" / digest).write_bytes(data)
    return staging, digest


def _request(capability: str, digest: str, media_type: str) -> dict:
    return {
        "schema": "archeaxis.worker-request/v1",
        "type": "job_request",
        "request_id": "req-ocr-1",
        "job_id": "job-ocr-1",
        "attempt": 1,
        "protocol_minor": 0,
        "capability": capability,
        "capability_version": "1",
        "deadline_ms": 120_000,
        "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": media_type}],
        "parameters": {},
    }


def _run_sidecar(staging: Path, request: dict) -> tuple[dict, dict]:
    proc = subprocess.Popen(
        [sys.executable, str(WORKER), "--staging-root", str(staging)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    hello = json.loads(proc.stdout.readline())
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    response = json.loads(proc.stdout.readline())
    proc.stdin.close()
    proc.wait(timeout=120)
    return hello, response


def _sample(tmp_path: Path) -> bytes:
    image = Image.new("RGB", (460, 110), "white")
    Draw.Draw(image).text((20, 40), "ocr sidecar 6371", fill="black")
    path = tmp_path / "sample.png"
    image.save(path)
    return path.read_bytes()


def test_ocr_worker_speaks_the_sidecar_job_loop(tmp_path: Path) -> None:
    staging, digest = _staging_with(tmp_path, _sample(tmp_path))
    hello, response = _run_sidecar(staging, _request("image.ocr", digest, "image/png"))

    assert hello["type"] == "hello"
    assert hello["worker"]["name"] == "python-worker-ocr-ndjson", hello["worker"]
    assert hello["capabilities"] == ["image.ocr"]

    assert response["status"] == "succeeded", response
    assert response["job_id"] == "job-ocr-1"
    assert [o["kind"] for o in response["outputs"]] == ["text", "document_structure", "loss_report"]
    # Recognition is real, and the region anchors travel as the structure artifact.
    text_entry = next(o for o in response["outputs"] if o["kind"] == "text")
    text_digest = text_entry["uri"].rsplit("/", 1)[-1]
    recognized = (staging / "output" / text_digest).read_bytes().decode("utf-8")
    assert recognized.strip(), "a non-empty sample must produce recognised text"
    structure_entry = next(o for o in response["outputs"] if o["kind"] == "document_structure")
    structure_digest = structure_entry["uri"].rsplit("/", 1)[-1]
    structure = json.loads((staging / "output" / structure_digest).read_bytes())
    assert structure and structure[0]["kind"] == "region"


def test_ocr_worker_refuses_a_capability_it_did_not_advertise(tmp_path: Path) -> None:
    staging, digest = _staging_with(tmp_path, _sample(tmp_path))
    _hello, response = _run_sidecar(staging, _request("pdf.extract", digest, "application/pdf"))
    assert response["status"] == "rejected", response
    assert response["outputs"] == []
    assert "unsupported capability" in response["error"]["message"]
    assert response["error"]["retryable"] is False
