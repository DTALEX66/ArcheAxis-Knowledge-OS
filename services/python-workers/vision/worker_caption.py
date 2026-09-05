#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext vision worker: diagram/scene description (F04 layer 2).

Sends the image to a local vision model over HTTP (ollama) and returns a
structured description separate from OCR text. This lane NEVER claims OCR
accuracy: text is handled by worker_ocr; descriptions are model output
labeled with model + prompt version for reproducibility.

Only models that pass the capability probe are reported as usable.

Usage:
    python worker_caption.py <image-file> [--model qwen2.5vl:7b]
    python worker_caption.py --probe [--model qwen2.5vl:7b]
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ENGINE = "python-worker-caption"
ENGINE_VERSION = "0.1.0"
DEFAULT_MODEL = "qwen2.5vl:7b"
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"

PROMPT_TEMPLATE = (
    "Describe this image for a knowledge workspace. "
    "State the dominant text layer briefly, then the structure/entities/diagram "
    "elements, then anything notable. Answer in the language of the dominant "
    "text when detectable, otherwise English. Keep under 200 words. "
    "Do not invent facts; mark uncertainty explicitly."
)
PROMPT_VERSION = "archeaxis.vnext/v1 2026-09-05"


def _ollama_base() -> str:
    return OLLAMA_ENDPOINT


def probe(model: str) -> dict:
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"capability": False, "reason": f"ollama unreachable: {exc}", "engine": ENGINE}
    models = {item.get("name", "") for item in payload.get("models", [])}
    if model not in models:
        return {"capability": False, "reason": f"model {model} not installed", "engine": ENGINE, "available": sorted(models)}
    return {
        "capability": True,
        "engine": ENGINE,
        "model": model,
        "endpoint": "http://127.0.0.1:11434",
        "prompt_version": PROMPT_VERSION,
        "note": "model availability only; description quality is measured separately",
    }


def describe(image: Path, model: str, timeout_s: int = 300) -> dict:
    import urllib.request

    if not image.is_file():
        raise ValueError(f"input image not found: {image}")
    supported = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
    if image.suffix.lower() not in supported:
        raise ValueError(f"unsupported image extension: {image.suffix}")

    encoded = base64.b64encode(image.read_bytes()).decode("ascii")
    request_body = json.dumps(
        {
            "model": model,
            "prompt": PROMPT_TEMPLATE,
            "images": [encoded],
            "stream": False,
            "options": {"num_predict": 400},
        }
    ).encode("utf-8")
    started = time.monotonic()
    request = urllib.request.Request(
        _ollama_base(),
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"vision model call failed: {exc}") from exc
    elapsed_s = round(time.monotonic() - started, 2)
    description = str(payload.get("response", "")).strip()
    if not description:
        raise RuntimeError("vision model returned an empty description")
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "description": description,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "elapsed_s": elapsed_s,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"model": model, "prompt_version": PROMPT_VERSION},
            "loss_note": (
                "description is model output, not OCR; text fidelity is owned by "
                "worker_ocr; uncertainty marked by the model is preserved verbatim"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ArcheAxis vision description worker")
    parser.add_argument("input", nargs="?", help="image file")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe(args.model), ensure_ascii=False))
        return 0
    if not args.input:
        print(json.dumps({"error": "usage: worker_caption.py <image-file> [--model NAME]"}))
        return 2
    try:
        out = describe(Path(args.input), args.model)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
