"""SIMULATED SDK/network transport; real immutable image bytes, no paid call."""

import base64
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "image_fidelity_fixture", ROOT / "tests/workers/test_document_check_cloud.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
worker = fixture.worker


@pytest.mark.parametrize("format,media", [("PNG", "image/png"), ("JPEG", "image/jpeg")])
def test_original_pixels_reach_actual_sdk_message_without_ocr_substitution(
    worker, monkeypatch, format, media
):
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), "white").save(buffer, format=format)
    raw = buffer.getvalue()
    request = fixture.request()
    request["original"] = {
        "media_type": media,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "content_base64": base64.b64encode(raw).decode(),
    }
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"status": "uncertain", "basis": "SIMULATED image transport"}
                        )
                    },
                    "finish_reason": "stop",
                }
            ],
            "model": "SIMULATED-SDK-model",
            "usage": {"total_tokens": 9},
        }

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=completion))
    result = worker.execute(request)
    assert result["outcome"] == "succeeded" and result["status"] == "uncertain"
    parts = calls[0]["messages"][0]["content"]
    image = parts[1]["image_url"]["url"]
    assert image.startswith("data:" + media + ";base64,")
    assert base64.b64decode(image.split(",", 1)[1]) == raw
    assert "RECOGNITION" in parts[0]["text"] and "not web text" in parts[0]["text"]
    assert result["engine_receipt"]["original_image"]["sha256"] == request["original"]["sha256"]
    assert result["engine_receipt"]["original_image"]["width"] == 32


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("hash", "original_digest_mismatch"),
        ("fake", "original_image_invalid"),
        ("wide", "original_image_budget_or_format"),
        ("mime", "original_image_budget_or_format"),
    ],
)
def test_image_validation_refuses_before_network_or_sdk(worker, monkeypatch, mode, reason):
    buffer = io.BytesIO()
    Image.new("RGB", (4097 if mode == "wide" else 32, 1), "white").save(buffer, format="PNG")
    raw = b"not an image" if mode == "fake" else buffer.getvalue()
    request = fixture.request()
    request["original"] = {
        "media_type": "image/jpeg" if mode == "mime" else "image/png",
        "sha256": "0" * 64 if mode == "hash" else hashlib.sha256(raw).hexdigest(),
        "content_base64": base64.b64encode(raw).decode(),
    }

    def forbidden(*args, **kwargs):
        pytest.fail("invalid image must not reach retrieval or provider")

    monkeypatch.setattr(worker, "retrieve_context", forbidden)
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=forbidden))
    result = worker.execute(request)
    assert result["outcome"] == "failed" and result["reason"] == reason
    assert result["engine_receipt"] is None
