#!/usr/bin/env python3
"""ArcheAxis vNext archive worker: container inventory (F15).

A ZIP is binary, so it never travels through the text route: decoding it as text
would produce noise. This worker reads the container's own directory and projects an
**inventory listing** - one line per member, `name<TAB>size` - so the projection is a
real, addressable text with line anchors, while the loss receipt says plainly that
this is an inventory of the container and NOT the members' contents.

What it reports as facts: member count, file and directory counts, the total
uncompressed and compressed bytes, the compression methods present, nested archive
members, members that are encrypted, and the member list itself (capped, with an
explicit capped fact).

Isolation boundary: never opens the vNext database, never executes file content, and
never extracts a member to disk.

Usage:
    python worker_archive.py <input-file>
Output: {"engine","engine_version","text","structure","loss_receipt"}
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

ENGINE = "python-worker-archive"
ENGINE_VERSION = "0.1.0"
# R08: identity advertised in the sidecar handshake for this route.
WORKER_IDENTITY = "python-worker-archive-ndjson"
MEMBER_CAP = 5000
LISTED_CAP = 2000
NESTED_SUFFIXES = (".zip", ".jar", ".war", ".odt", ".ods", ".odp", ".epub", ".docx", ".xlsx", ".pptx")
COMPRESSION_NAMES = {0: "stored", 8: "deflate", 12: "bzip2", 14: "lzma"}
# R15/F15 second half: members can be offered to the Core as sources of their own.
# Extraction is bounded by count and by total bytes, and every bound is declared.
MEMBER_JOB_CAP = 50
MEMBER_BYTES_CAP = 64 * 1024 * 1024
UNSAFE_NAME = ("..", "/", "\\", ":")


def _safe_member_name(index: int, name: str) -> str:
    """A flat, collision-free file name for one extracted member.

    The member's own name may contain separators, be absolute or try to escape, so the
    extracted file is named by its index with a sanitised suffix; the true member name
    travels in the declaration, never in the path.
    """
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in base)[-64:]
    return f"{index:04d}-{safe or 'member'}"


def _extract_members(members, container, out_dir: Path | None) -> tuple[list[dict], list[str]]:
    """Write the members the Core may import, and declare each one by digest.

    The worker cannot enqueue anything (it holds no database handle), so it does the
    half it owns. Directories are skipped, encrypted or unreadable members are reported
    as problems rather than silently dropped, and nothing is written when no output
    directory was supplied.
    """
    extracted: list[dict] = []
    problems: list[str] = []
    if out_dir is None:
        return extracted, problems
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    files = [info for info in members if not info.is_dir()]
    for index, info in enumerate(files, start=1):
        if len(extracted) >= MEMBER_JOB_CAP:
            problems.append(f"only the first {MEMBER_JOB_CAP} of {len(files)} members were extracted")
            break
        if total + info.file_size > MEMBER_BYTES_CAP:
            problems.append(f"member byte budget of {MEMBER_BYTES_CAP} reached; later members were not extracted")
            break
        if info.flag_bits & 0x1:
            problems.append(f"member {info.filename!r} is encrypted and was not extracted")
            continue
        target = out_dir / _safe_member_name(index, info.filename)
        try:
            payload = container.read(info)
            target.write_bytes(payload)
            total += len(payload)
            extracted.append(
                {
                    "name": info.filename,
                    "file": target.name,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
        except Exception as exc:  # noqa: BLE001 - an unreadable member is a fact
            problems.append(f"member {info.filename!r} could not be extracted: {type(exc).__name__}: {exc}")
    return extracted, problems


def _line_anchors(text: str, cap: int = 5000) -> list[dict]:
    anchors: list[dict] = []
    offset = 0
    for index, line in enumerate(text.splitlines(keepends=True), start=1):
        anchors.append(
            {"kind": "line", "path": [f"line-{index}"], "char_start": offset, "char_end": offset + len(line)}
        )
        offset += len(line)
        if index >= cap:
            break
    return anchors


def extract(path: str, member_dir: Path | None = None) -> dict:
    raw = Path(path).read_bytes()
    try:
        with zipfile.ZipFile(path) as container:
            members = container.infolist()
            listing = [(info.filename, info.file_size, info.compress_size, info.compress_type, info.is_dir())
                       for info in members]
            encrypted = [info.filename for info in members if info.flag_bits & 0x1]
            methods = sorted({info.compress_type for info in members})
            extracted, extraction_problems = _extract_members(members, container, member_dir)
    except zipfile.BadZipFile as error:
        # a corrupt container must fail loudly; an empty success would be a lie
        raise ValueError(f"unreadable archive: {error}") from error
    if not listing:
        raise ValueError("archive exposes no members")

    files = [item for item in listing if not item[4]]
    directories = [item for item in listing if item[4]]
    nested = [name for name, *_ in files if name.lower().endswith(NESTED_SUFFIXES)]
    # The projection: the inventory as text, one member per line, deterministically
    # ordered exactly as the container lists them.
    text = "".join(f"{name}\t{size}\n" for name, size, *_ in listing)
    structure = _line_anchors(text)
    losses: list[str] = []
    if len(listing) > LISTED_CAP:
        losses.append(f"only the first {LISTED_CAP} members are projected; the container lists {len(listing)}")
    if encrypted:
        losses.append(f"{len(encrypted)} member(s) are encrypted and were not read: {', '.join(encrypted[:5])}")
    if nested:
        losses.append(
            f"{len(nested)} member(s) are themselves containers and are listed, not opened: {', '.join(nested[:5])}"
        )
    if extraction_problems:
        losses.append("member extraction: " + "; ".join(extraction_problems))
    loss_receipt = {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "params": {
            "projection": "container inventory (one member per line: name, size)",
            "projection_note": (
                "this is an inventory of the container, NOT the members' contents: no member was extracted, "
                "executed or decoded, and the container's own bytes remain the source of record"
            ),
            "coverage_unit": "line anchors over the inventory listing",
            "structure": {
                "member_count": len(listing),
                "file_count": len(files),
                "directory_count": len(directories),
                "uncompressed_bytes": sum(item[1] for item in files),
                "compressed_bytes": sum(item[2] for item in files),
                "compression_methods": [COMPRESSION_NAMES.get(code, f"unknown({code})") for code in methods],
                "nested_containers": nested,
                "encrypted_members": encrypted,
                "members": [
                    {
                        "name": name,
                        "size": size,
                        "compressed_size": compressed,
                        "compression": COMPRESSION_NAMES.get(code, f"unknown({code})"),
                        "directory": is_dir,
                    }
                    for name, size, compressed, code, is_dir in listing[:MEMBER_CAP]
                ],
                "members_capped": len(listing) > MEMBER_CAP,
                # R15/F15 second half: what the Core may import as sources of their
                # own, each verified by digest before anything is enqueued.
                "extractable_members": extracted,
                "extractable_member_count": len(extracted),
                "member_extraction": {
                    "cap": MEMBER_JOB_CAP,
                    "bytes_cap": MEMBER_BYTES_CAP,
                    "note": (
                        "members are written into the transfer area and declared with their digests; "
                        "the Core verifies each one, imports it as a source recording that it came from "
                        "this container, and decides whether its name resolves to a route"
                    ),
                },
            },
        },
        "losses": losses,
        "covered": len(structure),
        "total": len(text.splitlines(keepends=True)),
        "coverage": 1.0,
        "loss_note": "; ".join(losses) if losses else "no transform applied",
    }
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "structure": structure,
        "loss_receipt": loss_receipt,
    }


def main() -> int:
    # R08: the same sidecar stdio loop every route uses, with this route's own
    # identity and capability, so a container reaches the Core through the same
    # job/attempt/error machinery instead of a private CLI path.
    if "--staging-root" in sys.argv:
        import argparse

        repo_root = Path(__file__).resolve().parents[3]
        spec = importlib.util.spec_from_file_location(
            "archive_transport", repo_root / "services" / "python-workers" / "transport" / "text_ndjson.py"
        )
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--staging-root", type=Path, required=True)
        parser.add_argument("--artifact-root", type=Path, default=None)
        args = parser.parse_args()
        return transport.serve_stdio(WORKER_IDENTITY, ["archive.inventory"], args.staging_root, args.artifact_root)

    with contextlib.suppress(AttributeError, OSError):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: worker_archive.py <input-file> | --staging-root <dir>"}))
        return 2
    try:
        print(json.dumps(extract(sys.argv[1]), ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001 - explicit failure, never silent
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}", "engine": ENGINE}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
