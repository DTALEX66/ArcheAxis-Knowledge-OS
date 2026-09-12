#!/usr/bin/env python3
"""Deterministic synthetic fixture factory for ArcheAxis worker tests (BULK-0907 P03).

Generates fixed-seed, byte-deterministic samples for the text-family document
formats (plain text / JSON / JSON Canvas / SRT / VTT / HTML) plus a deterministic
corruption helper that preserves the original sample hash. Independent expectations
(text lengths, anchor counts, cue counts, offsets) are written by the generator
itself into a manifest; tests and workers never copy parser output back as the
expected value.

Third-party/zip formats are intentionally out of this first slice: the factory
grows per need and documents any format whose byte determinism cannot be proven.

Usage:
    python bulk_fixture_factory.py --out-dir <run-root-relative> --seed <int> \\
        --format text|json|canvas|srt|vtt|html
    python bulk_fixture_factory.py --out-dir <run-root-relative> --seed <int> \\
        --format corrupt --input <file> --output <name>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMATS = {"text", "json", "canvas", "srt", "vtt", "html", "corrupt"}

_CHINESE = "核聚变研究目标与测量等离子体约束证据锚点中文文本列表表格段落关系时间窗口"
_ASCII_WORDS = ["alpha", "beta", "gamma", "delta", "anchor", "evidence", "line"]


def _usage_error(message: str) -> int:
    print(f"bulk_fixture_factory: {message}", file=sys.stderr)
    return 2


def _validate_out(base: Path, out_dir: Path) -> Path:
    raw = str(out_dir)
    if re.match(r"^[A-Za-z]:", raw) and raw[:2].upper() == "E:":
        raise ValueError("E: drive is not allowed")
    if raw.replace("\\", "/").startswith(("//", "/")):
        raise ValueError("UNC or absolute-root output is not allowed")
    resolved = Path(os.path.abspath(out_dir))
    base_abs = Path(os.path.abspath(base))
    try:
        common = os.path.commonpath([str(base_abs), str(resolved)])
    except ValueError as exc:
        raise ValueError("output dir escapes its run root") from exc
    if common != str(base_abs):
        raise ValueError(f"output dir escapes its run root: {resolved}")
    for part in (*reversed(resolved.parents), resolved):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError(f"output path crosses a link or reparse point: {part}")
    return resolved


def _run_root() -> Path:
    value = os.environ.get("ARCHEAXIS_RUN_ROOT")
    if not value:
        raise ValueError("ARCHEAXIS_RUN_ROOT is required (run through scripts/runtime/dev.py)")
    return Path(os.path.abspath(value))


def _seed_text(rng: random.Random) -> list[str]:
    return ["".join(rng.choice(_CHINESE) for _ in range(rng.randint(2, 6)))
            + " " + rng.choice(_ASCII_WORDS) for _ in range(rng.randint(3, 6))]


def generate_text(rng: random.Random) -> dict:
    lines = _seed_text(rng)
    body = "\n".join(lines)
    return {"name": f"text-{rng.randint(0, 0):02d}.txt", "data": (body + "\n").encode("utf-8"),
            "expectations": {"lines": len(lines), "chinese_count": sum(ch in _CHINESE for ch in body)}}


def generate_json(rng: random.Random) -> dict:
    doc = {
        "title": "synthetic-" + str(rng.randint(1000, 9999)),
        "language": "zh",
        "values": [rng.randint(0, 9) for _ in range(5)],
        "nested": {"anchor": rng.choice(_ASCII_WORDS), "note": "deterministic"},
    }
    data = json.dumps(doc, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"name": "json-sample.json", "data": data,
            "expectations": {"key_count": len(doc), "title": doc["title"]}}


def generate_canvas(rng: random.Random) -> dict:
    canvas = {
        "nodes": [
            {"id": "n1", "type": "text", "text": "核聚变研究", "x": 0, "y": 0, "width": 100, "height": 50},
            {"id": "n2", "type": "text", "text": "目标与测量 " + rng.choice(_ASCII_WORDS), "x": 10, "y": 10, "width": 120, "height": 50},
        ],
        "edges": [{"id": "e1", "fromNode": "n1", "toNode": "n2", "fromSide": "right", "toSide": "left"}],
    }
    data = json.dumps(canvas, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"name": "canvas-zh-synthetic.canvas", "data": data,
            "expectations": {"text_nodes": 2, "edges": 1, "projected_text": "核聚变研究\n目标与测量 " + canvas["nodes"][1]["text"].split()[-1]}}


def generate_srt(rng: random.Random) -> dict:
    lines = _seed_text(rng)
    cues = []
    offset = 1000
    for index, line in enumerate(lines, start=1):
        duration = 1500 + index * 10
        cues.append({"index": index, "start_ms": offset, "end_ms": offset + duration, "text": line})
        offset += duration + 500
    parts = []
    for cue in cues:
        start_s = f"{cue['start_ms'] // 3600000:02d}:{(cue['start_ms'] // 60000) % 60:02d}:{(cue['start_ms'] // 1000) % 60:02d},{cue['start_ms'] % 1000:03d}"
        end_s = f"{cue['end_ms'] // 3600000:02d}:{(cue['end_ms'] // 60000) % 60:02d}:{(cue['end_ms'] // 1000) % 60:02d},{cue['end_ms'] % 1000:03d}"
        parts.append(f"{cue['index']}\n{start_s} --> {end_s}\n{cue['text']}")
    body = "\n\n".join(parts) + "\n"
    return {"name": f"srt-seed-{rng.randint(0, 0):02d}.srt", "data": body.encode("utf-8"),
            "expectations": {"cues": len(cues), "offsets_ms": [c["start_ms"] for c in cues],
                             "joined_text": "\n".join(c["text"] for c in cues)}}


def generate_vtt(rng: random.Random) -> dict:
    srt = generate_srt(rng)
    text = srt["data"].decode("utf-8")
    body = "WEBVTT\n\nNOTE dropped note line\n\n" + text
    body = body.replace(",", ".")  # VTT uses dot milliseconds
    return {"name": "vtt-synthetic.vtt", "data": body.encode("utf-8"),
            "expectations": {"cues": srt["expectations"]["cues"], "note_stripped": "NOTE" in body}}


def generate_html(rng: random.Random) -> dict:
    title = "磁约束聚变简介"
    body = (
        "<!DOCTYPE html><html lang=\"zh\"><head><meta charset=\"utf-8\">"
        f"<title>{title}</title><style>p{{color:gray}}</style></head><body>"
        "<script>document.write('x')</script>"
        "<h1>磁约束聚变简介</h1><p>第一段正文用于验证&nbsp;数值 n = 1e20。</p>"
        "<ul><li>环形磁场</li><li>极向磁场</li></ul>"
        "<table><tr><th>名称</th><th>数值</th></tr><tr><td>密度</td><td>1e20</td></tr></table>"
        "</body></html>"
    )
    data = body.encode("utf-8")
    return {"name": "html-synthetic.html", "data": data,
            "expectations": {"title": title, "li_count": 2, "table_cells": 4}}


def corrupt_bytes(data: bytes, rng: random.Random) -> tuple[bytes, str]:
    mode = rng.choice(["flip", "truncate", "garbage"])
    if mode == "flip" and data:
        position = rng.randrange(len(data))
        changed = bytearray(data)
        changed[position] ^= 0xFF
        return bytes(changed), f"flip@{position}"
    if mode == "truncate" and len(data) > 2:
        cut = max(1, len(data) // 3)
        return data[:cut], f"truncate->{cut}"
    return b"\x00\xff\x81broken-encoding" + data[:64], "garbage-prefix"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True, help="run-root-relative target directory")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--format", choices=sorted(FORMATS), required=True)
    parser.add_argument("--input", help="file inside out-dir to corrupt (corrupt format)")
    parser.add_argument("--output", help="corrupted output filename (corrupt format)")
    args = parser.parse_args()
    try:
        base = _run_root()
        out = _validate_out(base, args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        rng = random.Random(args.seed)
        if args.format == "corrupt":
            if not args.input or not args.output:
                return _usage_error("corrupt requires --input and --output")
            source = _validate_out(out, out / args.input)
            if not source.is_file():
                return _usage_error(f"input file not found: {args.input}")
            original = source.read_bytes()
            original_sha = hashlib.sha256(original).hexdigest()
            mutated, note = corrupt_bytes(original, rng)
            (out / args.output).write_bytes(mutated)
            result = {"name": args.output, "format": "corrupt", "seed": args.seed,
                      "original_file": args.input, "original_sha256": original_sha,
                      "corrupt_sha256": hashlib.sha256(mutated).hexdigest(),
                      "corruption": note, "bytes": len(mutated)}
        else:
            entry = {"text": generate_text, "json": generate_json, "canvas": generate_canvas,
                     "srt": generate_srt, "vtt": generate_vtt, "html": generate_html}[args.format](rng)
            (out / entry["name"]).write_bytes(entry["data"])
            result = {"name": entry["name"], "format": args.format, "seed": args.seed,
                      "sha256": hashlib.sha256(entry["data"]).hexdigest(),
                      "bytes": len(entry["data"]), "expectations": entry["expectations"]}
        manifest = {"schema": "archeaxis.bulk-fixture-factory/v1", "out_dir": str(out),
                    "entries": [result]}
        manifest_path = out / f"{args.format}-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ValueError as exc:
        return _usage_error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
