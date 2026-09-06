#!/usr/bin/env python3
"""Offline Markdown link auditor for tracked documents (BULK-0907 P04).

Parses inline links and reference definitions in an explicit list of Markdown
documents under one root, classifies each target, and reports a machine-readable
audit. It never scans the disk recursively, never follows external URLs, and never
edits files. Missing path targets and missing fragment targets are reported as
separate categories. Link syntax this parser cannot handle is labelled
UNSUPPORTED_SYNTAX instead of being miscounted as correct.

Usage:
    python bulk_link_audit.py --root <repo-or-test-root> <relative/doc.md> [...]
    python bulk_link_audit.py --root <root> --list <paths.txt>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
REF_DEF = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)")
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})")
CODE_SPAN = re.compile(r"`[^`]*`")


def _usage_error(message: str) -> int:
    print(f"bulk_link_audit: {message}", file=sys.stderr)
    return 2


def _plain(text: str) -> str:
    return text.replace("`", "").strip()


def iter_inline_targets(line: str):
    """Yield (target, label) for inline links outside code spans on one line."""
    stripped = CODE_SPAN.sub("", line)
    for match in INLINE_LINK.finditer(stripped):
        target = match.group(1)
        if target.endswith((")", "]")):
            target = target[:-1]
        yield target, _plain(match.group(0)[:60])


def strip_headings(text: str):
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            fragment = line.lstrip("#").strip().lower()
            fragment = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", fragment)
            yield fragment


def _resolve_target(root: Path, base_dir: Path, target: str):
    """Return a (path, fragment) pair, decoding percent-escapes; never leaves root."""
    if target.startswith(("#", "http://", "https://", "mailto:")):
        return None, None
    raw_path, _, fragment = target.partition("#")
    decoded = urllib.parse.unquote(raw_path)
    if not decoded:
        return None, None
    candidate = Path(os.path.abspath(base_dir / decoded))
    root_abs = Path(os.path.abspath(root))
    try:
        common = os.path.commonpath([str(root_abs), str(candidate)])
    except ValueError:
        return candidate, fragment
    if common != str(root_abs):
        return candidate, fragment
    return candidate, fragment


def _has_reparse(path: Path) -> bool:
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            return True
    return False


def classify(root: Path, doc_rel: Path, target: str):
    if target.startswith(("http://", "https://", "mailto:")):
        return {"kind": "EXTERNAL_NOT_CHECKED", "target": target}
    doc_path = root / doc_rel
    base_dir = doc_path.parent
    if target.startswith("#"):
        headings = set(strip_headings(doc_path.read_text(encoding="utf-8", errors="replace")))
        wanted = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", urllib.parse.unquote(target[1:]).lower())
        if wanted and wanted not in headings:
            return {"kind": "MISSING_FRAGMENT", "target": target}
        return {"kind": "ANCHOR_LOCAL", "target": target}
    candidate, fragment = _resolve_target(root, base_dir, target)
    if candidate is None:
        return {"kind": "FRAGMENT_ONLY", "target": target}
    root_abs = Path(os.path.abspath(root)).resolve()
    if not str(candidate.resolve()).startswith(str(root_abs)):
        return {"kind": "OUTSIDE_REPO", "target": target}
    if _has_reparse(candidate):
        return {"kind": "REPARSE_REJECTED", "target": target}
    if candidate.is_dir():
        return {"kind": "PRESENT_DIRECTORY", "target": target,
                "file": str(candidate.relative_to(root)).replace("\\", "/")}
    if not candidate.is_file():
        if fragment:
            return {"kind": "MISSING_PATH_AND_FRAGMENT", "target": target}
        return {"kind": "MISSING_PATH", "target": target}
    if fragment:
        headings = set(strip_headings(candidate.read_text(encoding="utf-8", errors="replace")))
        wanted = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", urllib.parse.unquote(fragment).lower())
        if wanted and wanted not in headings:
            return {"kind": "MISSING_FRAGMENT", "target": target, "file": str(candidate.relative_to(root)).replace("\\", "/")}
    return {"kind": "PRESENT", "target": target, "file": str(candidate.relative_to(root)).replace("\\", "/")}


def audit(root: Path, doc_paths: list[Path]) -> dict:
    rows: list[dict] = []
    unsupported = 0
    for doc_rel in doc_paths:
        doc = root / doc_rel
        if not doc.is_file():
            rows.append({"source": str(doc_rel).replace("\\", "/"), "line": None,
                         "kind": "MISSING_DOCUMENT", "target": None})
            continue
        text = doc.read_text(encoding="utf-8", errors="replace")
        in_fence = False
        for number, line in enumerate(text.splitlines(), start=1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            stripped = CODE_SPAN.sub("", line)
            definition = REF_DEF.match(stripped)
            if definition:
                target = definition.group(2)
                result = classify(root, doc_rel, target)
                rows.append({"source": str(doc_rel).replace("\\", "/"), "line": number,
                             "kind": result["kind"], "target": target,
                             **({"file": result.get("file")} if "file" in result else {})})
                continue
            inline = list(iter_inline_targets(stripped))
            if inline:
                for target, label in inline:
                    result = classify(root, doc_rel, target)
                    rows.append({"source": str(doc_rel).replace("\\", "/"), "line": number,
                                 "kind": result["kind"], "target": target, "label": label,
                                 **({"file": result.get("file")} if "file" in result else {})})
                continue
            if re.search(r"\]\s*\[", stripped) or ("(" in stripped and "]" in stripped
                                                    and re.search(r"\]\(", stripped)):
                unsupported += 1
    report = {"schema": "archeaxis.bulk-link-audit/v1", "root": str(root),
              "documents": [str(p).replace("\\", "/") for p in doc_paths],
              "rows": rows, "unsupported_syntax_lines": unsupported}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="base directory for documents")
    parser.add_argument("--list", type=Path, help="file with one document-relative path per line")
    parser.add_argument("--output-json", type=Path, help="write report to a run-root-relative path")
    parser.add_argument("docs", nargs="*", help="document paths relative to root")
    args = parser.parse_args()
    root = Path(os.path.abspath(args.root))
    if not root.is_dir():
        return _usage_error(f"root is not a directory: {root}")
    docs: list[Path] = [Path(d) for d in args.docs]
    if args.list:
        try:
            listed = [line.strip() for line in args.list.read_text(encoding="utf-8").splitlines()
                      if line.strip() and not line.strip().startswith("#")]
            docs = [Path(d) for d in listed]
        except OSError as exc:
            return _usage_error(f"cannot read list: {exc}")
    if not docs:
        return _usage_error("no documents supplied")
    report = audit(root, docs)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output_json:
        try:
            run = Path(os.path.abspath(os.environ.get("ARCHEAXIS_RUN_ROOT", "")))
            if not run.is_dir():
                return _usage_error("--output-json requires ARCHEAXIS_RUN_ROOT (run through dev.py)")
            out = Path(os.path.abspath(args.output_json)) if args.output_json.is_absolute() else run / args.output_json
            if os.path.commonpath([str(run), str(out)]) != str(run):
                return _usage_error("--output-json must be inside ARCHEAXIS_RUN_ROOT")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload + "\n", encoding="utf-8")
            print(f"bulk_link_audit report: {out}")
        except (OSError, ValueError) as exc:
            return _usage_error(str(exc))
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
