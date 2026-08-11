"""Tests for shared.file_detection (vendored Magika ONNX content detection).

The model is vendored (shared/models/magika/model.onnx ~3MB), so these
tests run real ONNX inference when the model is present and fall back
to pure unit tests otherwise.
"""

from __future__ import annotations

import numpy as np
import pytest

from shared.file_detection import (
    _classify_group,
    _extract_features,
    _softmax,
    detect,
    is_available,
)


def test_is_available_true_with_vendored_model() -> None:
    assert is_available() is True


def test_classify_group_text() -> None:
    assert _classify_group("markdown") == "text"
    assert _classify_group("python") == "text"
    assert _classify_group("csv") == "text"


def test_classify_group_binary_categories() -> None:
    assert _classify_group("pdf") == "office"
    assert _classify_group("png") == "image"
    assert _classify_group("wav") == "audio"
    assert _classify_group("zip") == "archive"
    assert _classify_group("elf") == "binary"
    assert _classify_group("totally-unknown-label") == "unknown"


def test_extract_features_shape() -> None:
    from shared.file_detection import _load_model

    _load_model()  # initializes _config for feature extraction
    features = _extract_features(b"hello world")
    # config: beg_size 1024 + end_size 1024 = 2048 input dim
    assert features.shape == (1, 2048)
    assert features.dtype == np.int32
    assert features[0][0] == ord("h")
    assert features[0][1023] == 256  # padding token after short content


def test_extract_features_padding() -> None:
    from shared.file_detection import _load_model

    _load_model()
    features = _extract_features(b"")
    assert features.shape == (1, 2048)
    # empty content → all padding token (256), never 0-fill
    assert (features[0] == 256).all()


def test_softmax_distribution() -> None:
    probs = _softmax(np.array([1.0, 2.0, 3.0]))
    assert abs(probs.sum() - 1.0) < 1e-6
    assert probs[2] > probs[1] > probs[0]
    assert (probs > 0).all()


@pytest.mark.skipif(not is_available(), reason="vendored Magika model missing")
def test_detect_markdown_content() -> None:
    content = b"# Heading\n\nSome **markdown** text with [[wikilinks]].\n"
    result = detect(content, path_hint="note.md")
    assert result["label"] == "markdown", result
    assert result["group"] == "text"
    assert result["path_hint"] == "note.md"
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.skipif(not is_available(), reason="vendored Magika model missing")
def test_detect_json_content() -> None:
    result = detect(b'{"key": "value", "n": 42}', path_hint="data.json")
    # Magika distinguishes json vs jsonl; both group as text
    assert result["label"] in {"json", "jsonl"}, result
    assert result["group"] == "text"


@pytest.mark.skipif(not is_available(), reason="vendored Magika model missing")
def test_detect_png_magic_bytes() -> None:
    # Minimal PNG header magic
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    result = detect(png_header, path_hint="image.png")
    assert result["group"] == "image", result
