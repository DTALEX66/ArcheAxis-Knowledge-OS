"""Real PDFium raster transport; SIMULATED retrieval/SDK, no provider call."""

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
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "pdf_fixture", ROOT / "tests/workers/test_document_check_cloud.py"
)
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
worker = f.worker


def pdf(count=1, width=240):
    import pypdfium2 as p

    with p.PdfDocument.new() as d:
        for _ in range(count):
            page = d.new_page(width, 180)
            page.close()
        out = io.BytesIO()
        d.save(out)
        return out.getvalue()


def prepared(worker):
    return worker


def request(raw):
    r = f.request()
    r["original"] = {
        "media_type": "application/pdf",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "content_base64": base64.b64encode(raw).decode(),
    }
    return r


@pytest.mark.parametrize("count", [1, 3])
def test_all_actual_pages_reach_sdk_and_receipt(worker, monkeypatch, count):
    p = prepared(worker)
    raw = pdf(count)
    calls = []

    def completion(**kw):
        calls.append(kw)
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"status": "uncertain", "basis": "SIMULATED transport only"}
                        )
                    },
                    "finish_reason": "stop",
                }
            ],
            "model": "SIMULATED-model",
            "usage": {"total_tokens": 3},
        }

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=completion))
    result = p.execute(request(raw))
    assert result["outcome"] == "succeeded", result["reason"]
    receipt = result["engine_receipt"]["original_pdf"]
    assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["renderer_version"] and receipt["pdfium_version"]
    assert (
        receipt["covered_pages"] == list(range(1, count + 1)) and receipt["coverage"] == "all_pages"
    )
    parts = calls[0]["messages"][0]["content"]
    assert len(parts) == count + 1
    for part, page in zip(parts[1:], receipt["pages"], strict=True):
        png = base64.b64decode(part["image_url"]["url"].split(",")[1])
        assert hashlib.sha256(png).hexdigest() == page["sha256"]
        with Image.open(io.BytesIO(png)) as image:
            assert image.size == (240, 180)
    assert (
        result["engine_receipt"]["prompt_sha256"]
        == hashlib.sha256(parts[0]["text"].encode()).hexdigest()
    )
    assert all(page["sha256"] in parts[0]["text"] for page in receipt["pages"])
    assert receipt["sha256"] in parts[0]["text"]
    assert "RECOGNITION" in parts[0]["text"] and "not web text" in parts[0]["text"]


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("four_pages", "original_pdf_page_budget"),
        ("oversize", "original_pdf_pixel_budget"),
        ("corrupt", "original_pdf_invalid"),
        ("hash", "original_digest_mismatch"),
    ],
)
def test_rejected_pdf_never_reaches_network_or_sdk(worker, monkeypatch, mode, reason):
    p = prepared(worker)
    raw = (
        b"not-pdf"
        if mode == "corrupt"
        else pdf(4 if mode == "four_pages" else 1, 4097 if mode == "oversize" else 240)
    )
    req = request(raw)
    if mode == "hash":
        req["original"]["sha256"] = "0" * 64

    def forbidden(*a, **k):
        pytest.fail("invalid original cannot call retrieval/provider")

    monkeypatch.setattr(p, "retrieve_context", forbidden)
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=forbidden))
    result = p.execute(req)
    assert (
        result["outcome"] == "failed"
        and result["reason"] == reason
        and result["engine_receipt"] is None
    )


@pytest.mark.parametrize("media", ["audio/wav", "video/mp4"])
def test_audio_video_remain_explicitly_unsupported(worker, monkeypatch, media):
    p = prepared(worker)
    req = request(b"opaque media")
    req["original"]["media_type"] = media

    def forbidden(*a, **k):
        pytest.fail("unsupported media cannot invoke network or provider")

    monkeypatch.setattr(p, "retrieve_context", forbidden)
    result = p.execute(req)
    assert result["outcome"] == "failed" and result["reason"] == "unsupported_original_media"
    assert result["engine_receipt"] is None


@pytest.mark.parametrize("dimension", ["recognition_fidelity", "professional_basis"])
@pytest.mark.parametrize(
    "reason,fields",
    [
        ("retrieval_failed", {"failure_code": "dns", "failure_stage": "dns"}),
        ("retrieval_failed", {"failure_code": "timeout", "failure_stage": "transport"}),
        ("no_search_results", {}),
    ],
)
def test_auxiliary_failure_is_not_professional_support(
    worker, monkeypatch, dimension, reason, fields
):
    p = prepared(worker)
    calls = []
    req = f.request()
    req["dimension"] = dimension

    def retrieval(*a, **k):
        raise p.CheckExecutionError(reason, fields)

    monkeypatch.setattr(p, "retrieve_context", retrieval)

    def complete(**kw):
        calls.append(kw)
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"status":"faithful","basis":"SIMULATED original comparison"}'
                    },
                    "finish_reason": "stop",
                }
            ],
            "model": "SIMULATED-model",
            "usage": {"total_tokens": 3},
        }

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=complete))
    result = p.execute(req)
    if dimension == "recognition_fidelity":
        assert result["outcome"] == "succeeded" and len(calls) == 1
        assert "Original" in calls[0]["messages"][0]["content"]
        aux = [r for r in result["retrieval_receipts"] if r["kind"] == "auxiliary_unavailable"]
        assert len(aux) == 1 and aux[0]["reason"] == reason
        for key, value in fields.items():
            assert aux[0][key] == value
    else:
        assert result["outcome"] == "failed" and not calls and result["engine_receipt"] is None
        assert result["reason"] == reason and result["status"] == (
            "uncertain" if reason == "no_search_results" else "failed"
        )


def test_model_failure_stays_failed_after_auxiliary_failure(worker, monkeypatch):
    p = prepared(worker)

    def retrieval(*a, **k):
        raise p.CheckExecutionError(
            "retrieval_failed", {"failure_code": "dns", "failure_stage": "dns"}
        )

    def complete(**kw):
        raise RuntimeError("SECRET-must-not-persist")

    monkeypatch.setattr(p, "retrieve_context", retrieval)
    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=complete))
    result = p.execute(f.request())
    assert result["outcome"] == "failed" and result["engine_receipt"] is None
    assert any(r["kind"] == "auxiliary_unavailable" for r in result["retrieval_receipts"])
    assert "SECRET" not in json.dumps(result)


@pytest.mark.parametrize("mode", ["four", "total", "both", "base64"])
def test_adapter_multi_image_bounds_before_sdk(worker, monkeypatch, mode):
    p = prepared(worker)
    adapter = p.donor("llm_adapter")

    def forbidden(**kw):
        pytest.fail("unsafe material must not reach SDK")

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=forbidden))
    def image(raw):
        return "data:image/png;base64," + base64.b64encode(raw).decode()
    kw = {"image_data_urls": [image(b"x")]}
    if mode == "four":
        kw["image_data_urls"] *= 4
    if mode == "total":
        kw["image_data_urls"] = [image(b"x" * 32001)] * 2
    if mode == "both":
        kw["image_data_url"] = image(b"x")
    if mode == "base64":
        kw["image_data_urls"] = ["data:image/png;base64,!!!"]
    with pytest.raises(ValueError):
        adapter.complete("SIMULATED bounded material", model="explicit/model", **kw)
