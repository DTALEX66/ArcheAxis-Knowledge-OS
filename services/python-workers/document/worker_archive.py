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

Isolation boundary: never opens the vNext database and never executes file content. Members
are written out only when the caller supplies a destination, and the container itself is opened
for reading only, so its own bytes remain the source of record.

Usage:
    python worker_archive.py <input-file>
Output: {"engine","engine_version","text","structure","loss_receipt"}
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import tarfile
import zipfile
from pathlib import Path

ENGINE = "python-worker-archive"
ENGINE_VERSION = "0.3.1"
# R08: identity advertised in the sidecar handshake for this route.
WORKER_IDENTITY = "python-worker-archive-ndjson"
MEMBER_CAP = 5000
LISTED_CAP = 2000
NESTED_SUFFIXES = (
    ".apkg",
    ".colpkg",
    ".jex",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".zip",
    ".jar",
    ".war",
    ".odt",
    ".ods",
    ".odp",
    ".epub",
    ".docx",
    ".xlsx",
    ".pptx",
)
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
    # Core rejects consecutive dots in an offered flat file name.  Keep the
    # last dot so an original extension such as .csv remains available.
    while ".." in safe:
        safe = safe.replace("..", "_.")
    return f"{index:04d}-{safe or 'member'}"


def _long_path(path: Path) -> str:
    """A path string that still creates a file inside a deep workspace.

    Windows answers a create whose full path passes MAX_PATH with ERROR_FILE_NOT_FOUND, so
    the failure reads as "the directory vanished" instead of "the name is too long". The
    transfer area here is keyed by a 64-character container digest, so an ordinary worktree
    reaches that limit on its own; the extended-length prefix removes the limit.
    """
    text = str(path)
    if sys.platform == "win32" and not text.startswith("\\\\?\\") and Path(text).is_absolute():
        return "\\\\" + "?\\" + text
    return text


def _checked_directory_chain(path: Path) -> None:
    """Reject links or reparse points observed along the output directory path.

    These path checks are not an OS sandbox: a component can still be replaced
    between a check and a subsequent operation.
    """
    absolute = path.absolute()
    for component in reversed((absolute, *absolute.parents)):
        try:
            info = os.lstat(_long_path(component))
        except FileNotFoundError:
            continue
        if (
            stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & 0x400
            or not stat.S_ISDIR(info.st_mode)
        ):
            raise OSError("archive member directory contains a link or non-directory")


def _regular_member_identity(info) -> tuple[int, int, int, int, int]:
    if (
        not stat.S_ISREG(info.st_mode)
        or getattr(info, "st_file_attributes", 0) & 0x400
        or info.st_nlink != 1
        or not info.st_ino
    ):
        raise OSError("archive member target identity is not a single regular file")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)


def _compare_member_bytes(fd: int, payload: bytes) -> None:
    """Read no more than one byte past the expected content, including on growth."""
    total = 0
    while total <= len(payload):
        chunk = os.read(fd, min(65536, len(payload) + 1 - total))
        if not chunk:
            break
        if chunk != payload[total : total + len(chunk)]:
            raise FileExistsError("archive member target contains different bytes")
        total += len(chunk)
    if total != len(payload):
        raise OSError("archive member target changed during verification")


def _verify_existing_member(target: Path, payload: bytes) -> None:
    """Reuse only the same bounded bytes on the observed single regular file."""
    path = _long_path(target)
    before = _regular_member_identity(os.lstat(path))
    if before[2] != len(payload):
        raise FileExistsError("archive member target already contains different bytes")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        if _regular_member_identity(os.fstat(fd)) != before:
            raise OSError("archive member target changed before verification")
        _checked_directory_chain(target.parent)
        _compare_member_bytes(fd, payload)
        if _regular_member_identity(os.fstat(fd)) != before:
            raise OSError("archive member target changed during verification")
        if _regular_member_identity(os.lstat(path)) != before:
            raise OSError("archive member target path changed during verification")
        _checked_directory_chain(target.parent)
    finally:
        os.close(fd)


def _offer_member(target: Path, payload: bytes) -> None:
    """Create without overwrite, or verify an unchanged identical existing file."""
    _checked_directory_chain(target.parent)
    path = _long_path(target)
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        _verify_existing_member(target, payload)
        return
    try:
        opened = _regular_member_identity(os.fstat(fd))
        if _regular_member_identity(os.lstat(path)) != opened:
            raise OSError("archive member target path changed before writing")
        _checked_directory_chain(target.parent)
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset : offset + 65536])
            if written <= 0:
                raise OSError("archive member write made no progress")
            offset += written
        after = _regular_member_identity(os.fstat(fd))
        if after[:2] != opened[:2] or after[2] != len(payload):
            raise OSError("archive member target changed during writing")
        os.lseek(fd, 0, os.SEEK_SET)
        _compare_member_bytes(fd, payload)
        if _regular_member_identity(os.fstat(fd)) != after:
            raise OSError("archive member target changed during verification")
        if _regular_member_identity(os.lstat(path)) != after:
            raise OSError("archive member target path changed during writing")
        _checked_directory_chain(target.parent)
    finally:
        os.close(fd)


def _read_declared_member(container, info) -> bytes:
    """Require EOF and exactly the declared size, with a one-byte excess probe."""
    payload = bytearray()
    declared = info.file_size
    with container.open(info) as member:
        while len(payload) <= declared:
            maximum = min(65536, declared + 1 - len(payload))
            chunk = member.read(maximum)
            if not isinstance(chunk, (bytes, bytearray)) or len(chunk) > maximum:
                raise OSError("archive member stream returned invalid bytes")
            if not chunk:
                break
            payload.extend(chunk)
    if len(payload) != declared:
        raise OSError("archive member bytes do not match the declared size")
    return bytes(payload)


def _finder_metadata(container, info, names):
    """Identify Finder records by name and header, paired to their file when applicable."""
    leaf = info.filename.rsplit("/", 1)[-1]
    if leaf == ".DS_Store":
        kind, header = "finder_store", b"\x00\x00\x00\x01Bud1"
    elif leaf.startswith("._") and len(leaf) > 2:
        relative = info.filename.removeprefix("__MACOSX/")
        folder, sep, _ = relative.rpartition("/")
        if folder + sep + leaf[2:] not in names:
            return None
        kind, header = "appledouble_v2", b"\x00\x05\x16\x07\x00\x02\x00\x00"
    else:
        return None
    try:
        with container.open(info) as member:
            if member.read(len(header)) == header:
                return kind
    except Exception:  # The ordinary reader records decompression and integrity errors.
        pass
    return None


def _extract_members(members, container, out_dir: Path | None, *, finder_records=None) -> tuple[list[dict], list[str]]:
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
    _checked_directory_chain(out_dir)
    Path(_long_path(out_dir)).mkdir(parents=True, exist_ok=True)
    _checked_directory_chain(out_dir)
    reserved_bytes = 0
    attempts = 0
    files = [info for info in members if not info.is_dir()]
    names = {info.filename.rstrip("/") for info in members} if finder_records is not None else set()
    for index, info in enumerate(files, start=1):
        if attempts >= MEMBER_JOB_CAP:
            problems.append(
                f"member attempt limit of {MEMBER_JOB_CAP} reached; later members were not attempted"
            )
            break
        if isinstance(info.file_size, bool) or not isinstance(info.file_size, int) or info.file_size < 0:
            problems.append(f"member {info.filename!r} has an invalid declared size")
            continue
        if finder_records is not None and index <= MEMBER_CAP and not (info.flag_bits & 0x1):
            kind = _finder_metadata(container, info, names)
            if kind:
                finder_records.append({"name": info.filename, "kind": kind})
                continue
        if reserved_bytes + info.file_size > MEMBER_BYTES_CAP:
            problems.append(
                f"member byte budget of {MEMBER_BYTES_CAP} reached; later members were not attempted"
            )
            break
        if info.flag_bits & 0x1:
            problems.append(f"member {info.filename!r} is encrypted and was not extracted")
            continue
        target = out_dir / _safe_member_name(index, info.filename)
        # A failed or conflicting attempt may leave bytes on disk.  Reserve
        # before opening the source or target and do not refund on failure;
        # this is an accounting bound, not a filesystem quota.
        attempts += 1
        reserved_bytes += info.file_size
        try:
            payload = _read_declared_member(container, info)
            _offer_member(target, payload)
            extracted.append(
                {
                    "name": info.filename,
                    "file": target.name,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
        except Exception as exc:  # noqa: BLE001 - an unreadable member is a fact
            problems.append(
                f"member {info.filename!r} could not be extracted: {type(exc).__name__}: {exc}"
            )
    return extracted, problems


def _line_anchors(text: str, cap: int = 5000) -> list[dict]:
    anchors: list[dict] = []
    offset = 0
    for index, line in enumerate(text.splitlines(keepends=True), start=1):
        anchors.append(
            {
                "kind": "line",
                "path": [f"line-{index}"],
                "char_start": offset,
                "char_end": offset + len(line),
            }
        )
        offset += len(line)
        if index >= cap:
            break
    return anchors


class _TarContainer:
    """Uncompressed, single-level TAR adapter; never call extract/extractall.

    Validate the complete bounded directory before creating any member output.
    Links, devices, sparse entries and unsafe original names are refused rather
    than made into apparent readable sources. Compressed TAR is not this profile.
    """

    def __init__(self, path):
        if Path(path).stat().st_size > MEMBER_BYTES_CAP + 16 * 1024 * 1024:
            raise ValueError("TAR input exceeds the byte budget")
        # This adapter owns the handle: validation exceptions and __exit__ close it.
        self.archive = tarfile.open(path, mode="r:")  # noqa: SIM115
        self.members = []
        self.by_name = {}
        total = 0
        try:
            for item in self.archive:
                if len(self.members) >= MEMBER_CAP:
                    raise ValueError("TAR member count exceeds the budget")
                parts = item.name.replace("\\", "/").split("/")
                if (
                    not item.name
                    or item.name in (".", "./")
                    or item.name.startswith(("/", "\\"))
                    or ":" in item.name
                    or ".." in parts
                    or "\\" in item.name
                ):
                    raise ValueError("unsafe TAR member name")
                if not (item.isfile() or item.isdir()) or item.sparse is not None:
                    raise ValueError("TAR links, special and sparse members are unsupported")
                key = item.name + ("/" if item.isdir() and not item.name.endswith("/") else "")
                if item.isfile() and item.name.endswith("/"):
                    raise ValueError("regular TAR member has directory name")
                if key in self.by_name:
                    raise ValueError("duplicate TAR member name")
                if item.size < 0:
                    raise ValueError("negative TAR member size")
                total += item.size
                if total > MEMBER_BYTES_CAP:
                    raise ValueError("TAR member bytes exceed the budget")
                info = zipfile.ZipInfo(
                    item.name + ("/" if item.isdir() and not item.name.endswith("/") else "")
                )
                info.file_size = item.size
                info.compress_size = item.size
                info.compress_type = zipfile.ZIP_STORED
                self.by_name[info.filename] = item
                self.members.append(info)
        except BaseException:
            self.archive.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.archive.close()

    def infolist(self):
        return self.members

    def open(self, info):
        stream = self.archive.extractfile(self.by_name[info.filename])
        if stream is None:
            raise ValueError("TAR regular member exposes no bytes")
        return stream


def _open_container(path):
    if zipfile.is_zipfile(path):
        return zipfile.ZipFile(path)
    try:
        return _TarContainer(path)
    except (tarfile.TarError, OSError) as error:
        raise ValueError(f"unreadable archive: {type(error).__name__}") from error


_JOPLIN_ID = r"[0-9a-f]{32}"
_JOPLIN_ITEM = re.compile(rf"({_JOPLIN_ID})\.md")
_JOPLIN_RESOURCE = re.compile(rf"resources/({_JOPLIN_ID})(?:\.[^/]+)?")
_JOPLIN_REFERENCE = re.compile(rf":/({_JOPLIN_ID})(?![0-9a-fA-F])")
_JOPLIN_KINDS = {"1": "notes", "2": "notebooks", "4": "resources", "5": "tags", "6": "note_tags"}


def _joplin_record(raw: bytes, expected_id: str) -> tuple[dict, str]:
    # Joplin BaseItem.serialize places the properties after the last blank line.
    # Scanning backwards keeps colon-containing lines and blank paragraphs in the actual note.
    lines = raw.decode("utf-8-sig").replace("\r\n", "\n").rstrip("\n").split("\n")
    start = len(lines)
    fields = {}
    while start and lines[start - 1].strip():
        start -= 1
        key, colon, value = lines[start].partition(":")
        if not colon or not key.strip() or key.strip() in fields:
            raise ValueError("invalid terminal item properties")
        fields[key.strip()] = value.strip()
    if fields.get("id") != expected_id or not fields.get("type_"):
        raise ValueError("missing item type or ID does not match the member name")
    header = lines[:start - 1] if start else []
    fields["title"] = header[0] if header else ""
    return fields, "\n".join(header[2:])


def _joplin_projection(container, members, extracted):
    """Resolve the exchange graph by Joplin IDs, independently of archive order and display names."""
    graph = {kind: [] for kind in _JOPLIN_KINDS.values()}
    records = {}
    bodies = {}
    payloads = {}
    offered = {entry["name"]: entry for entry in extracted}
    losses = []
    for info in members:
        if info.is_dir():
            continue
        name = info.filename.removeprefix("./")
        payload_id = _JOPLIN_RESOURCE.fullmatch(name)
        if payload_id:
            rid = payload_id.group(1)
            if rid in payloads:
                payloads[rid] = None
                losses.append(f"multiple resource payloads for {rid}")
                continue
            entry = offered.get(info.filename)
            digest = entry["sha256"] if entry else hashlib.sha256(_read_declared_member(container, info)).hexdigest()
            payloads[rid] = {"payload_member": info.filename, "payload_sha256": digest, "payload_bytes": info.file_size}
            continue
        item_id = _JOPLIN_ITEM.fullmatch(name)
        if not item_id:
            losses.append(f"unmapped JEX member: {info.filename}")
            continue
        rid = item_id.group(1)
        if rid in records:
            raise ValueError(f"duplicate Joplin item ID: {rid}")
        try:
            fields, body = _joplin_record(_read_declared_member(container, info), rid)
        except ValueError as exc:
            losses.append(f"{info.filename}: {exc}")
            continue
        kind = _JOPLIN_KINDS.get(fields["type_"])
        if not kind or fields.get("encryption_applied", "0") != "0":
            losses.append(f"{info.filename}: unsupported type {fields['type_']} or encrypted metadata; original retained")
            continue
        # Other native properties remain in the byte-preserved member. Only these fields
        # participate in this projection; never put an entire body or ciphertext in a loss receipt.
        item = {key: fields[key] for key in (
            "id", "title", "parent_id", "created_time", "updated_time", "user_created_time", "user_updated_time",
            "note_id", "tag_id", "mime", "filename", "file_extension", "size", "markup_language",
            "is_todo", "todo_due", "todo_completed", "source_url", "encryption_blob_encrypted",
        ) if key in fields}
        item["member"] = info.filename
        graph[kind].append(item)
        records[rid] = kind
        if kind == "notes":
            bodies[rid] = body
    if not records:
        raise ValueError("JEX contains no readable Joplin item records")

    notebooks = {item["id"]: item for item in graph["notebooks"]}
    tags = {item["id"]: item["title"] for item in graph["tags"]}
    note_tags = {}
    for edge in graph["note_tags"]:
        note, tag = edge.get("note_id"), edge.get("tag_id")
        if note in bodies and tag in tags:
            note_tags.setdefault(note, set()).add(tag)
        else:
            losses.append(f"unresolved note/tag relation {edge['id']}: {note}, {tag}")
    for item in graph["resources"]:
        rid = item["id"]
        payload = payloads.pop(rid, None)
        if not payload:
            losses.append(f"resource {rid} has no unique payload")
            continue
        item.update(payload)
        if item.get("encryption_blob_encrypted", "0") != "0":
            losses.append(f"resource {rid} retains encrypted bytes")
        if item.get("size") and item["size"] != str(item["payload_bytes"]):
            losses.append(f"resource {rid} metadata size differs from archived bytes")
    losses.extend(f"payload {rid} has no readable resource metadata" for rid in payloads)

    chunks = []
    offset = 0
    for item in graph["notes"]:
        rid = item["id"]
        names = []
        seen = set()
        parent = item.get("parent_id")
        while parent:
            if parent not in notebooks or parent in seen:
                losses.append(f"note {rid} has an incomplete notebook path at {parent}")
                break
            seen.add(parent)
            names.append(notebooks[parent]["title"])
            parent = notebooks[parent].get("parent_id")
        item["notebook_path"] = names[::-1]
        item["tag_ids"] = sorted(note_tags.get(rid, ()))
        body = bodies[rid]
        item["reference_ids"] = list(dict.fromkeys(_JOPLIN_REFERENCE.findall(body)))
        for target in item["reference_ids"]:
            if records.get(target) not in {"notes", "resources"}:
                losses.append(f"note {rid} references unavailable item {target}")
        heading = " / ".join([*item["notebook_path"], item["title"]])
        labels = ", ".join(tags[tag] for tag in item["tag_ids"])
        prefix = f"# {heading}\n" + (f"Tags: {labels}\n" if labels else "") + "\n"
        chunks.extend([prefix, body, "\n\n"])
        item["body_start"] = offset + len(prefix)
        item["body_end"] = item["body_start"] + len(body)
        offset = item["body_end"] + 2
    return "".join(chunks), graph, losses


def _anki_kernel():
    package_name = "_aaos_archive_compat"
    if package_name not in sys.modules:
        location = Path(__file__).resolve()
        for root in (location.parents[2], location.parents[3]):
            folder = root / "shared/compat"
            if (folder / "import_session.py").is_file():
                spec = importlib.util.spec_from_file_location(
                    package_name, folder / "__init__.py", submodule_search_locations=[str(folder)])
                module = importlib.util.module_from_spec(spec)
                sys.modules[package_name] = module
                spec.loader.exec_module(module)
                break
        else:
            raise ValueError("Anki collection reader missing from the worker runtime")
    return importlib.import_module(package_name + ".import_session")


def _anki_projection(container, member_dir, collection_backup):
    kernel = _anki_kernel()
    package = kernel.anki_package
    version, collection, data = package.collection_bytes(container, MEMBER_BYTES_CAP)
    graph = kernel.read_anki_collection(data, review_limit=MEMBER_CAP)
    entries = package.media_entries(container, version, MEMBER_BYTES_CAP)
    indexed = {}
    for entry in entries:
        _, name, size, _ = entry
        info = zipfile.ZipInfo(name)
        info.file_size = size
        indexed[info] = entry
    media = package.MediaSource(container, version, indexed, MEMBER_BYTES_CAP)
    extracted, problems = _extract_members(list(indexed), media, member_dir)
    graph.update(package_version=version, collection_member=collection, aaos_operation="read_only_projection",
                 native_import_semantics="replace_collection" if collection_backup else "merge_deck",
                 media=[{"slot": slot, "name": name, "bytes": size} for slot, name, size, _ in entries],
                 scheduling_origin="imported_from_source")
    chunks = []
    offset = 0
    for note in graph["notes"]:
        labels = graph["note_types"].get(note["note_type_id"], {}).get("fields", {})
        lines = [f"{note['note_type']} · {note['guid']}"]
        for index, field in enumerate(note["fields"]):
            lines.extend((labels.get(index, f"Field {index + 1}"), field))
        body = "\n".join(lines) + "\n\n"
        note["text_start"], note["text_end"] = offset, offset + len(body)
        offset += len(body)
        chunks.append(body)
    return "".join(chunks), graph, extracted, problems


def extract(path: str, member_dir: Path | None = None, *, media_type: str | None = None) -> dict:
    finder_records = []
    jex = media_type == "application/x-joplin-jex" if media_type else Path(path).suffix.lower() == ".jex"
    name = Path(path).name.lower()
    collection_backup = (media_type == "application/x-anki-collection" if media_type else
                         name.endswith(".colpkg") or name == "collection.apkg")
    anki = collection_backup or (media_type == "application/x-anki-package" if media_type else name.endswith(".apkg"))
    try:
        with (_TarContainer(path) if jex else _open_container(path)) as container:
            members = container.infolist()
            listing = [
                (
                    info.filename,
                    info.file_size,
                    info.compress_size,
                    info.compress_type,
                    info.is_dir(),
                )
                for info in members
            ]
            encrypted = [info.filename for info in members if info.flag_bits & 0x1]
            methods = sorted({info.compress_type for info in members})
            if anki:
                note_text, graph, extracted, extraction_problems = _anki_projection(container, member_dir, collection_backup)
            else:
                extracted, extraction_problems = _extract_members(
                    members, container, member_dir,
                    finder_records=finder_records if isinstance(container, zipfile.ZipFile) else None,
                )
            if jex:
                note_text, graph, jex_losses = _joplin_projection(container, members, extracted)
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
    text = "".join(f"{name}\t{size}\n" for name, size, *_ in listing[:LISTED_CAP])
    if (jex or anki) and note_text:
        text = note_text
    structure = _line_anchors(text)
    losses: list[str] = []
    if not ((jex or anki) and note_text) and len(listing) > LISTED_CAP:
        losses.append(
            f"only the first {LISTED_CAP} members are projected; the container lists {len(listing)}"
        )
    if encrypted:
        losses.append(
            f"{len(encrypted)} member(s) are encrypted and were not read: {', '.join(encrypted[:5])}"
        )
    if nested:
        losses.append(
            f"{len(nested)} member(s) are themselves containers and are listed, not opened by "
            f"this worker; any opening is the Core's own member expansion: {', '.join(nested[:5])}"
        )
    if extraction_problems:
        losses.append("member extraction: " + "; ".join(extraction_problems))
    if jex:
        losses.extend(jex_losses)
    if anki:
        losses.append("Deck options, card styling and template bodies are retained in the original package only.")
        history = graph["source_review_history"]
        if not history["available"]:
            losses.append("The source collection has no review history table.")
        elif history["total"] > len(history["events"]):
            losses.append(f"Only the latest {len(history['events'])} of {history['total']} native reviews are projected.")
    if (jex or anki) and len(text.splitlines(keepends=True)) > len(structure):
        losses.append("note text is complete; line anchors capped at 5000")
    loss_receipt = {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "params": {
            "container_profile": "zip-or-uncompressed-tar-single-level",
            "projection": "container inventory (one member per line: name, size)",
            # The note has to describe what THIS run did. Claiming nothing was extracted while
            # members sit in the destination would make the receipt itself untrue, which is the
            # one thing a loss receipt may never be.
            "projection_note": (
                "this is an inventory of the container, NOT the members' contents: no member was extracted, "
                "executed or decoded, and the container's own bytes remain the source of record"
                if not extracted and not extraction_problems
                else (
                    "this is an inventory of the container, NOT the members' contents: "
                    "no complete member was declared; failed attempts may leave partial or complete files; "
                    "nothing was executed or decoded, and the container's own bytes remain the source of record"
                )
                if not extracted
                else (
                    "this is an inventory of the container, NOT the members' contents: "
                    f"{len(extracted)} of {len(files)} member(s) were also written out or verified as candidate "
                    "sources, bounded by count and total bytes and declared by digest; "
                    + ("failed attempts may leave partial or complete files; " if extraction_problems else "")
                    + "nothing was executed or decoded, and the container's own bytes remain the source of record"
                )
            ),
            "coverage_unit": "line anchors over the inventory listing",
            "structure": {
                "member_count": len(listing),
                "file_count": len(files),
                "directory_count": len(directories),
                "uncompressed_bytes": sum(item[1] for item in files),
                "compressed_bytes": sum(item[2] for item in files),
                "compression_methods": [
                    COMPRESSION_NAMES.get(code, f"unknown({code})") for code in methods
                ],
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
    if finder_records:
        params = loss_receipt["params"]
        params["structure"]["member_extraction"]["container_metadata"] = {
            "total": len(finder_records), "members": finder_records, "disposition": "preserved_in_original_zip",
        }
        params["projection_note"] += f". {len(finder_records)} Finder metadata member(s) were retained in the original ZIP."
    if jex:
        params = loss_receipt["params"]
        params.update(container_profile="joplin-jex", projection="Joplin notes" if note_text else "Joplin item inventory",
                      projection_note="Note text offsets refer to the projection; original item files and resources retain their native bytes.",
                      coverage_unit="line anchors over projected text")
        params["structure"]["joplin"] = graph
        loss_receipt["coverage"] = len(structure) / loss_receipt["total"] if loss_receipt["total"] else 1.0
        if not losses:
            loss_receipt["loss_note"] = "Joplin item projection; original metadata is retained in member sources"
    if anki:
        params = loss_receipt["params"]
        params.update(container_profile="anki-package", projection="Anki note fields" if note_text else "Anki package inventory",
                      projection_note="Field HTML and source scheduling are preserved. Media sources use native names and decoded bytes.",
                      coverage_unit="line anchors over projected text")
        params["structure"]["anki"] = graph
        loss_receipt["coverage"] = len(structure) / loss_receipt["total"] if loss_receipt["total"] else 1.0
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "text": text,
        "structure": structure,
        "loss_receipt": loss_receipt,
    }


def main() -> int:
    if sys.argv[1:] == ["--check-anki-runtime"]:
        _anki_kernel().anki_package.zstd_module()
        print("Anki reader ready")
        return 0
    # R08: the same sidecar stdio loop every route uses, with this route's own
    # identity and capability, so a container reaches the Core through the same
    # job/attempt/error machinery instead of a private CLI path.
    if "--staging-root" in sys.argv:
        import argparse

        # The shared transport sits beside this worker's own category directory, in a
        # source checkout (`services/python-workers/transport/`) and in a staged runtime
        # (`workers/transport/`) alike, so both are tried from this file's location. A
        # fixed parents[3] plus a `services/python-workers/` suffix was correct only for
        # the source layout and left a staged worker unable to start.
        _transport_candidates = (
            Path(__file__).resolve().parent.parent / "transport" / "text_ndjson.py",
            Path(__file__).resolve().parents[2]
            / "services"
            / "python-workers"
            / "transport"
            / "text_ndjson.py",
        )
        _transport = next(
            (p for p in _transport_candidates if p.is_file()), _transport_candidates[0]
        )
        spec = importlib.util.spec_from_file_location("archive_transport", _transport)
        if spec is None or spec.loader is None:
            print(json.dumps({"error": "transport module is missing", "engine": ENGINE}))
            return 1
        transport = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transport)
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--staging-root", type=Path, required=True)
        parser.add_argument("--artifact-root", type=Path, default=None)
        args = parser.parse_args()
        return transport.serve_stdio(
            WORKER_IDENTITY, ["archive.inventory"], args.staging_root, args.artifact_root
        )

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
