"""R08 step (b): the PDF route reaches the Core through the same sidecar stdio
job loop as the text worker - same handshake, same request validation, same
response envelope and error vocabulary - declaring its own identity and
capability instead of a private CLI path.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "document" / "worker_pdf.py"

fitz = pytest.importorskip("fitz", reason="native PDF engine required")


def _pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 100), text)
    data = doc.tobytes()
    doc.close()
    return data


def _run_sidecar(staging: Path, request: dict) -> tuple[dict, dict]:
    proc = subprocess.Popen(
        [sys.executable, str(WORKER), "--staging-root", str(staging)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    hello_line = proc.stdout.readline()
    hello = json.loads(hello_line)
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    response_line = proc.stdout.readline()
    proc.stdin.close()
    proc.wait(timeout=60)
    return hello, json.loads(response_line)


def test_pdf_worker_speaks_the_sidecar_job_loop(tmp_path: Path) -> None:
    data = _pdf_bytes("sidecar 6371 km")
    staging = tmp_path / "staging"
    (staging / "input").mkdir(parents=True)
    digest = hashlib.sha256(data).hexdigest()
    (staging / "input" / digest).write_bytes(data)

    request = {
        "schema": "archeaxis.worker-request/v1",
        "type": "job_request",
        "request_id": "req-pdf-1",
        "job_id": "job-pdf-1",
        "attempt": 1,
        "protocol_minor": 0,
        "capability": "pdf.extract",
        "capability_version": "1",
        "deadline_ms": 60_000,
        "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": "application/pdf"}],
        "parameters": {},
    }
    hello, response = _run_sidecar(staging, request)

    assert hello["type"] == "hello"
    assert hello["worker"]["name"] == "python-worker-pdf-ndjson", hello["worker"]
    assert hello["capabilities"] == ["pdf.extract"]
    assert hello["protocol"]["major"] == 1

    assert response["schema"] == "archeaxis.worker-response/v1"
    assert response["type"] == "job_result"
    assert response["status"] == "succeeded", response
    assert response["job_id"] == "job-pdf-1" and response["attempt"] == 1
    assert [o["kind"] for o in response["outputs"]] == ["text", "document_structure", "loss_report"]
    assert all(o["authority_effect"] == "candidate_or_measurement_only" for o in response["outputs"])

    text_entry = next(o for o in response["outputs"] if o["kind"] == "text")
    text_digest = text_entry["uri"].rsplit("/", 1)[-1]
    assert b"6371" in (staging / "output" / text_digest).read_bytes()


def test_pdf_worker_rejects_a_text_capability(tmp_path: Path) -> None:
    data = b"plain text, not a pdf"
    staging = tmp_path / "staging"
    (staging / "input").mkdir(parents=True)
    digest = hashlib.sha256(data).hexdigest()
    (staging / "input" / digest).write_bytes(data)

    request = {
        "schema": "archeaxis.worker-request/v1",
        "type": "job_request",
        "request_id": "req-pdf-2",
        "job_id": "job-pdf-2",
        "attempt": 1,
        "protocol_minor": 0,
        "capability": "text.extract",  # a capability this worker does not offer
        "capability_version": "1",
        "deadline_ms": 60_000,
        "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": "text/plain"}],
        "parameters": {},
    }
    _hello, response = _run_sidecar(staging, request)
    assert response["status"] == "rejected", response
    assert response["outputs"] == []
    assert "unsupported capability" in response["error"]["message"]
    assert response["error"]["retryable"] is False
