"""R15/F04: a model-backed route must fail by name when its model is absent.

The description itself is not pinned here - a model's wording is not a fact this
repository can fix - but the failure path is, because "no model installed" must never
become an empty description or a successful job with nothing in it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PIL_Image = pytest.importorskip("PIL.Image", reason="PIL required to build a sample")
PIL_ImageDraw = pytest.importorskip("PIL.ImageDraw", reason="PIL required to build a sample")

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "services" / "python-workers" / "vision" / "worker_caption.py"
TRANSPORT = REPO / "services" / "python-workers" / "transport" / "text_ndjson.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


caption = _load("worker_caption_under_test", WORKER)
transport = _load("caption_transport_under_test", TRANSPORT)


def _sample(path: Path) -> None:
    image = PIL_Image.new("RGB", (240, 90), "white")
    PIL_ImageDraw.Draw(image).text((10, 20), "6371", fill="black")
    image.save(path)


def test_a_missing_model_is_a_named_failure_not_an_empty_description(tmp_path, monkeypatch):
    sample = tmp_path / "figure.png"
    _sample(sample)
    monkeypatch.setattr(
        caption,
        "probe",
        lambda model: {
            "capability": False,
            "reason": f"model {model} not installed",
            "available": ["qwen2.5vl:7b", "qwen3:8b"],
        },
    )
    with pytest.raises(ValueError) as raised:
        caption.extract(str(sample))
    message = str(raised.value)
    assert "is not available" in message
    assert "not installed" in message
    # and the available models are named, so a reader knows what to install or pick
    assert "qwen3:8b" in message


def test_an_unreachable_endpoint_is_a_named_failure_too(tmp_path, monkeypatch):
    sample = tmp_path / "figure.png"
    _sample(sample)
    monkeypatch.setattr(
        caption,
        "probe",
        lambda model: {"capability": False, "reason": "ollama unreachable: connection refused"},
    )
    with pytest.raises(ValueError) as raised:
        caption.extract(str(sample))
    assert "ollama unreachable" in str(raised.value)


def test_an_unsupported_image_extension_is_refused(tmp_path, monkeypatch):
    sample = tmp_path / "figure.gif"
    _sample(sample)
    monkeypatch.setattr(caption, "probe", lambda model: {"capability": True, "model": model})
    with pytest.raises(ValueError) as raised:
        caption.extract(str(sample))
    assert "unsupported image extension" in str(raised.value)


def test_the_route_declares_the_caption_capability_with_the_image_media_types():
    route = transport.ROUTES["image.caption"]
    assert route["worker"] == "services/python-workers/vision/worker_caption.py"
    assert route["media_types"] == {"image/png", "image/jpeg", "image/tiff", "image/webp", "image/bmp"}
    # the worker validates the image suffix and staging has no extension, so the route
    # declares the suffix its media type implies
    assert route["suffix_by_media"]["image/png"] == ".png"
    assert route["suffix_by_media"]["image/webp"] == ".webp"


def test_a_description_is_labelled_as_model_output(tmp_path, monkeypatch):
    """The receipt fields are the promise: a reader must be able to tell a model
    description from extracted content without reading this worker."""
    sample = tmp_path / "figure.png"
    _sample(sample)
    monkeypatch.setattr(caption, "probe", lambda model: {"capability": True, "model": model})
    monkeypatch.setattr(
        caption,
        "describe",
        lambda image, model, timeout_s=300: {
            "engine": caption.ENGINE,
            "engine_version": caption.ENGINE_VERSION,
            "description": "a described figure",
            "model": model,
            "prompt_version": caption.PROMPT_VERSION,
            "elapsed_s": 0.1,
            "loss_receipt": {
                "engine": caption.ENGINE,
                "engine_version": caption.ENGINE_VERSION,
                "params": {"model": model},
                "loss_note": "description is model output, not OCR",
            },
        },
    )
    result = caption.extract(str(sample))
    assert result["text"] == "a described figure"
    assert result["engine"] == caption.ENGINE
    params = result["loss_receipt"]["params"]
    assert params["model"] == caption.DEFAULT_MODEL
    assert params["prompt_version"] == caption.PROMPT_VERSION
    assert "candidate" in params["authority"]
    assert "candidate" in result["loss_receipt"]["loss_note"]
    assert "accuracy" not in str(result["loss_receipt"]).lower()
