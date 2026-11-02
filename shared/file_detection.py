"""File content-type detection via vendored Magika ONNX model.

Apache-2.0 licensed. Model source: google/magika (standard_v3_0).
Vendored 2026-08-11 — model.onnx + config.min.json + LICENSE at shared/models/magika/.

Feature extraction algorithm adapted from magika.py (Google LLC, Apache-2.0).
ONNX inference replaces the magika pip dependency entirely.
"""

from __future__ import annotations

import json
import logging
import os
from functools import wraps
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Any

import numpy as np
import onnxruntime as rt

_log = logging.getLogger(__name__)

_MODEL_DIR = Path(__file__).resolve().parent / "models" / "magika"
_MODEL_PATH = _MODEL_DIR / "model.onnx"
_CONFIG_PATH = _MODEL_DIR / "config.min.json"

# Lazy-loaded globals
_sess: rt.InferenceSession | None = None
_config: dict[str, Any] | None = None
_labels: list[str] = []
_thresholds: dict[str, float] = {}
_overwrites: dict[str, str] = {}
_loaded_paths: tuple[Path, Path] | None = None
_model_identity: dict[str, str] = {}
_model_lock = RLock()


def _with_model_lock(function):
    @wraps(function)
    def locked(*args, **kwargs):
        with _model_lock:
            return function(*args, **kwargs)

    return locked


def _model_paths() -> tuple[Path, Path]:
    """Return the configured Magika model/config paths.

    An explicit ``ARCHEAXIS_MAGIKA_MODEL_DIR`` directory is preferred when it
    contains both required files.  The repository copy remains an offline
    fallback so file detection stays usable when the shared model library is
    unavailable.
    """
    configured = os.environ.get("ARCHEAXIS_MAGIKA_MODEL_DIR", "").strip()
    if configured:
        external_dir = Path(configured).expanduser()
        external_model = external_dir / "model.onnx"
        external_config = external_dir / "config.min.json"
        if external_model.is_file() and external_config.is_file():
            return external_model, external_config
    return _MODEL_PATH, _CONFIG_PATH


@_with_model_lock
def _load_model(model_paths: tuple[Path, Path] | None = None) -> None:
    global _sess, _config, _labels, _thresholds, _overwrites, _loaded_paths, _model_identity
    paths = tuple(path.resolve() for path in (model_paths or _model_paths()))
    if _sess is not None and _loaded_paths == paths:
        return
    # Hash the same bytes that the parser and ONNX runtime actually consume.
    # A cached session retains this identity even if its files later change.
    model_bytes = paths[0].read_bytes()
    config_bytes = paths[1].read_bytes()
    config = json.loads(config_bytes)
    labels = [str(label) for label in config["target_labels_space"]]
    session = rt.InferenceSession(model_bytes, providers=["CPUExecutionProvider"])
    _config, _labels, _sess = config, labels, session
    _thresholds = config.get("thresholds", {})
    _overwrites = config.get("overwrite_map", {})
    _loaded_paths = paths
    _model_identity = {
        "model_sha256": sha256(model_bytes).hexdigest(),
        "config_sha256": sha256(config_bytes).hexdigest(),
    }


@_with_model_lock
def detect(
    content: bytes,
    *,
    path_hint: str | None = None,
    model_paths: tuple[Path, Path] | None = None,
) -> dict[str, object]:
    """Return content type prediction dict with label, group, mime."""
    _load_model(model_paths)
    features = _extract_features(content)
    ort_inputs = {_sess.get_inputs()[0].name: features}
    raw = _sess.run(None, ort_inputs)[0]
    # Magika's ONNX model already outputs softmax probabilities
    # (raw.sum() == 1.0); applying _softmax again flattens the
    # distribution and collapses every confident prediction to ~0.01.
    probs = raw[0]
    idx = int(np.argmax(probs))
    conf = float(probs[idx])
    label = _labels[idx] if idx < len(_labels) else "unknown"

    # Apply thresholds
    threshold = max(_thresholds.get(label, 0.0), 0.5)
    if conf < threshold:
        label = "unknown"

    # Apply overwrites
    label = _overwrites.get(label, label)

    return {
        "label": label,
        "group": _classify_group(label),
        "confidence": round(conf, 4),
        "path_hint": path_hint,
        "model_identity": dict(_model_identity),
    }


def _extract_features(content: bytes) -> np.ndarray:
    cfg = _config
    assert cfg is not None
    beg_size = cfg.get("beg_size", 512)
    end_size = cfg.get("end_size", 512)
    padding = cfg.get("padding_token", 256)
    block = cfg.get("block_size", 4096)

    buf = content[:block]
    beg_raw = buf.lstrip(b"\r\n\t ")
    beg_ints = list(beg_raw[:beg_size])
    if len(beg_ints) < beg_size:
        beg_ints += [padding] * (beg_size - len(beg_ints))

    if len(content) > block:
        tail = content[-block:]
    else:
        tail = content
    end_raw = tail.rstrip(b"\r\n\t ")
    end_ints = list(end_raw[-end_size:] if len(end_raw) >= end_size else end_raw)
    if len(end_ints) < end_size:
        end_ints = [padding] * (end_size - len(end_ints)) + end_ints

    features = np.array([beg_ints + end_ints], dtype=np.int32)
    return features


def _softmax(x: np.ndarray) -> np.ndarray:
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


def _classify_group(label: str) -> str:
    """Map content label to a high-level ingestion group."""
    text_labels = {
        "txt", "markdown", "json", "jsonl", "csv", "tsv", "xml", "html",
        "css", "javascript", "typescript", "python", "ruby", "rust", "go",
        "java", "cpp", "c", "shell", "batch", "powershell", "yaml", "toml",
        "ini", "diff", "rst", "latex", "bib", "makefile", "cmake", "sql",
        "php", "perl", "lua", "r", "scala", "kotlin", "swift", "dart",
        "haskell", "elixir", "erlang", "clojure", "lisp", "julia", "tcl",
        "proto", "handlebars", "jinja", "twig", "vue", "scss", "svg",
        "htaccess", "gitattributes", "gitmodules", "ignorefile", "po",
    }
    office_labels = {
        "doc", "docx", "xls", "xlsx", "xlsb", "ppt", "pptx",
        "odt", "ods", "odp", "rtf", "pdf", "epub",
    }
    image_labels = {
        "png", "jpeg", "gif", "bmp", "webp", "tiff", "ico",
        "icns", "psd", "tga", "emf", "wmf", "jp2", "svg",
    }
    audio_labels = {"mp3", "wav", "flac", "ogg", "midi", "m4a"}
    video_labels = {"mp4", "mkv", "webm", "flv", "avi"}
    archive_labels = {
        "zip", "tar", "gzip", "bzip", "xz", "sevenzip", "rar",
        "cab", "deb", "rpm", "iso", "dmg", "lha", "mscompress",
        "squashfs", "xar", "xpi", "snap", "zlibstream",
    }
    binary_labels = {
        "elf", "macho", "pebin", "coff", "wasm", "dex", "apk",
        "jar", "pythonbytecode", "javabytecode", "pickle",
        "pytorch", "onnx", "npy", "npz", "h5", "parquet",
        "sqlite", "pcap", "pdb", "lnk", "msi", "crx",
        "ttf", "otf", "woff", "woff2",
    }

    if label in text_labels:
        return "text"
    if label in office_labels:
        return "office"
    if label in image_labels:
        return "image"
    if label in audio_labels:
        return "audio"
    if label in video_labels:
        return "video"
    if label in archive_labels:
        return "archive"
    if label in binary_labels:
        return "binary"
    return "unknown"


def is_available() -> bool:
    """Check if the model is present and usable."""
    model_path, config_path = _model_paths()
    return model_path.is_file() and config_path.is_file()
