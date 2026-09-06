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
    python worker_ocr.py --probe [--profile public-profile.yaml] [--lang eng]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ENGINE = "python-worker-ocr"
ENGINE_VERSION = "0.1.0"

SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    # No visible Tesseract console when invoked from the desktop worker lane.
    return subprocess.run(command, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, **kwargs)


def _tesseract() -> str:
    binary = shutil.which("tesseract")
    if not binary:
        raise RuntimeError("tesseract binary not found on PATH (OCR engine unavailable)")
    return binary


def _public_path(value: str | Path) -> Path:
    text = str(value).replace("\\", "/")
    if text.lower().startswith(("e:", "//")):
        raise ValueError("protected drive or UNC path is not permitted")
    path = Path(value).absolute()
    if any(part.casefold() in {".env", ".codex", ".dsh", ".hermes", ".openhuman", ".claude", ".agents"}
           for part in path.parts):
        raise ValueError("private agent configuration is not a public OCR profile")
    return path


def load_tessdata_dir(profile: Path) -> Path:
    """Read only the explicitly selected public YAML; never infer a profile."""
    import yaml

    profile = _public_path(profile)
    if profile.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError("OCR profile must be a public YAML file")
    payload = yaml.safe_load(profile.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != "archeaxis.model-profile/v1":
        raise ValueError("invalid OCR model profile schema")
    config = payload.get("ocr")
    value = config.get("tessdata_dir") if isinstance(config, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("explicit OCR profile requires ocr.tessdata_dir")
    path = _public_path(value)
    if not Path(value).is_absolute():
        path = _public_path(profile.parent / value)
    if not path.is_dir():
        raise ValueError(f"OCR tessdata_dir does not exist: {path}")
    return path


def _tessdata_args(tessdata_dir: Path | None) -> list[str]:
    return ["--tessdata-dir", str(tessdata_dir)] if tessdata_dir is not None else []


def probe(lang: str = "eng", tessdata_dir: Path | None = None) -> dict:
    try:
        binary = _tesseract()
        version = _run(
            [binary, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20
        )
        if version.returncode != 0 or not version.stdout.strip():
            raise RuntimeError(f"tesseract version probe failed (exit {version.returncode})")
        listed = _run(
            [binary, "--list-langs", *_tessdata_args(tessdata_dir)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
        )
        if listed.returncode != 0:
            raise RuntimeError(f"tesseract language probe failed (exit {listed.returncode}): {listed.stderr[-400:]}")
        langs = [line.strip() for line in listed.stdout.splitlines()
                 if re.fullmatch(r"[A-Za-z0-9_./\\-]+", line.strip())]
        required = lang.split("+")
        if not langs or any(not token or token not in langs for token in required):
            raise RuntimeError(f"required OCR languages unavailable: {lang}")
        return {
            "capability": True,
            "engine": ENGINE,
            "tesseract": binary,
            "version": version.stdout.splitlines()[0],
            "languages": langs,
            "requested_languages": required,
            "tessdata_dir": str(tessdata_dir) if tessdata_dir is not None else None,
            "warnings": [message.strip() for message in (version.stderr, listed.stderr) if message.strip()],
            "formats": sorted(SUPPORTED),
            "note": "text+boxes only; diagram description is the local vision-model lane",
        }
    except Exception as exc:  # noqa: BLE001 - capability failures must remain JSON
        return {"capability": False, "reason": f"{type(exc).__name__}: {exc}", "engine": ENGINE}


def extract(path: Path, lang: str, tessdata_dir: Path | None = None) -> dict:
    binary = _tesseract()
    if not path.is_file():
        raise ValueError(f"input image not found: {path}")
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"unsupported image extension: {path.suffix}")

    plain = _run(
        [binary, str(path), "stdout", "-l", lang, "--psm", "6", *_tessdata_args(tessdata_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if plain.returncode != 0:
        raise RuntimeError(f"tesseract failed: {plain.stderr[-400:]}")

    tsv = _run(
        # Language-only tessdata packages may omit configs/tsv. Tesseract's
        # documented -c parameter selects the same renderer without that file.
        [binary, str(path), "stdout", "-l", lang, "--psm", "6", *_tessdata_args(tessdata_dir),
         "-c", "tessedit_create_tsv=1"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if tsv.returncode != 0:
        raise RuntimeError(f"tesseract TSV failed: {tsv.stderr[-400:]}")
    if not tsv.stdout.startswith("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"):
        raise RuntimeError("tesseract TSV output is missing or invalid")
    words: list[dict] = []
    if tsv.returncode == 0:
        lines = tsv.stdout.splitlines()
        if lines and lines[0].startswith("level"):
            for line in lines[1:]:
                fields = line.split("\t")
                if len(fields) < 12:
                    raise RuntimeError("truncated Tesseract TSV row")
                try:
                    word_text = fields[11]
                    conf = float(fields[10])
                except (ValueError, IndexError) as exc:
                    raise RuntimeError("invalid Tesseract TSV confidence") from exc
                if not math.isfinite(conf):
                    raise RuntimeError("non-finite Tesseract TSV confidence")
                if word_text.strip() and conf >= 0:
                    bounds = [int(fields[index]) for index in (6, 7, 8, 9)]
                    if any(value < 0 for value in bounds) or bounds[2] == 0 or bounds[3] == 0 or conf > 100:
                        raise RuntimeError("invalid Tesseract word bounds/confidence")
                    words.append(
                        {
                            "text": word_text,
                            "confidence": round(conf, 1),
                            "x": bounds[0],
                            "y": bounds[1],
                            "w": bounds[2],
                            "h": bounds[3],
                        }
                    )

    text = plain.stdout.strip()
    if text and not words:
        raise RuntimeError("tesseract returned text without word boxes; OCR output is incomplete")
    warnings = [{"stage": stage, "message": result.stderr.strip()}
                for stage, result in (("text", plain), ("tsv", tsv)) if result.stderr.strip()]
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "words": words,
        "loss_receipt": {
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "params": {"lang": lang, "psm": 6, "engine": "tesseract",
                       "tessdata_dir": str(tessdata_dir) if tessdata_dir is not None else None,
                       "tsv_renderer": "tessedit_create_tsv=1", "warnings": warnings},
            "loss_note": (
                "OCR text with per-word boxes/confidence; reading order follows "
                "Tesseract layout; diagram semantics, handwriting and low-quality "
                "region retries are separate lanes"
                + ("; subprocess warnings retained in params.warnings" if warnings else "")
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ArcheAxis OCR worker")
    parser.add_argument("input", nargs="?", help="image file")
    parser.add_argument("--lang", default="eng")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--profile", type=Path, help="explicit public OCR model-profile YAML")
    args = parser.parse_args()
    if not args.probe and not args.input:
        print(json.dumps({"error": "usage: worker_ocr.py <image-file> [--lang eng]"}))
        return 2
    try:
        tessdata_dir = load_tessdata_dir(args.profile) if args.profile is not None else None
        out = probe(args.lang, tessdata_dir) if args.probe else extract(Path(args.input), args.lang, tessdata_dir)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
