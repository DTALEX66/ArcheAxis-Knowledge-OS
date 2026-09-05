#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ArcheAxis vNext vision worker: OCR text + boxes (F04 partial).

Runs the system Tesseract binary over a still image and returns:
- the OCR text (character-level order, no assumptions about reading order
  beyond Tesseract's own layout),
- per-word boxes with confidence from the TSV stream,
- a loss receipt noting engine/psm/language.

Text recognition and visual/diagram description are layered separately:
this worker only performs OCR; describing diagram semantics is the local
vision-model lane. Screenshots are never reduced to metadata only.

Usage:
    python worker_ocr.py <image.png|jpg|jpeg|webp|bmp|tiff> [--lang eng]
    python worker_ocr.py --probe
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ENGINE = "python-worker-ocr"
ENGINE_VERSION = "0.1.0"

SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def _tesseract() -> str:
    binary = shutil.which("tesseract")
    if not binary:
        raise RuntimeError("tesseract binary not found on PATH (OCR engine unavailable)")
    return binary


def probe() -> dict:
    binary = shutil.which("tesseract")
    if not binary:
        return {"capability": False, "reason": "tesseract not found", "engine": ENGINE}
    version_out = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, errors="replace", timeout=20
    ).stdout.splitlines()[0] if subprocess.run(
        [binary, "--version"], capture_output=True, text=True, errors="replace", timeout=20
    ).stdout else "unknown"
    langs_out = subprocess.run(
        [binary, "--list-langs"], capture_output=True, text=True, errors="replace", timeout=30
    ).stdout.splitlines()
    langs = [line.strip() for line in langs_out if line.strip() and not line.startswith("List")]
    return {
        "capability": True,
        "engine": ENGINE,
        "tesseract": binary,
        "version": version_out,
        "languages": langs,
        "formats": sorted(SUPPORTED),
        "note": "text+boxes only; diagram description is the local vision-model lane",
    }


def extract(path: Path, lang: str) -> dict:
    binary = _tesseract()
    if not path.is_file():
        raise ValueError(f"input image not found: {path}")
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"unsupported image extension: {path.suffix}")

    plain = subprocess.run(
        [binary, str(path), "stdout", "-l", lang, "--psm", "6"],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
    )
    if plain.returncode != 0:
        raise RuntimeError(f"tesseract failed: {plain.stderr[-400:]}")

    tsv = subprocess.run(
        [binary, str(path), "stdout", "-l", lang, "--psm", "6", "tsv"],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
    )
    words: list[dict] = []
    if tsv.returncode == 0:
        lines = tsv.stdout.splitlines()
        if lines and lines[0].startswith("level"):
            for line in lines[1:]:
                fields = line.split("\t")
                if len(fields) < 12:
                    continue
                try:
                    word_text = fields[11]
                    conf = float(fields[10])
                except (ValueError, IndexError):
                    continue
                if word_text.strip() and conf >= 0:
                    words.append(
                        {
                            "text": word_text,
                            "confidence": round(conf, 1),
                            "x": int(fields[6]),
                            "y": int(fields[7]),
                            "w": int(fields[8]),
                            "h": int(fields[9]),
                        }
                    )

    text = plain.stdout.strip()
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "words": words,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"lang": lang, "psm": 6, "engine": "tesseract"},
            "loss_note": (
                "OCR text with per-word boxes/confidence; reading order follows "
                "Tesseract layout; diagram semantics, handwriting and low-quality "
                "region retries are separate lanes"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ArcheAxis OCR worker")
    parser.add_argument("input", nargs="?", help="image file")
    parser.add_argument("--lang", default="eng")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe(), ensure_ascii=False))
        return 0
    if not args.input:
        print(json.dumps({"error": "usage: worker_ocr.py <image-file> [--lang eng]"}))
        return 2
    try:
        out = extract(Path(args.input), args.lang)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
