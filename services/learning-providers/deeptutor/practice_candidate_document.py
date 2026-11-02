"""Offline, private preparation of one imported DeepTutor question document.

This module neither imports into Core nor runs a provider, model or grade.
The source, selected row and private receipt can contain answers or other
personal content; a private getter is an API convention, not access control.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import threading
import types


_ROOT = Path(__file__).absolute().parent
_PINS = {
    "candidate": ("candidate_document.py", 23_478,
                  "96ad414a1d35e842ad42362ea6ba1327ab7dfd8b3bb06d6e5bab39073a25953c"),
    "practice": ("practice_import.py", 47_396,
                 "fd8e8bbdf0700b84995f8b83fcd22b40770112e9414d2ea1c29cf65cf364a477"),
}
_MAX_SOURCE = 5 * 1024 * 1024
_MAX_PRIVATE_RECEIPT = 16 * 1024 * 1024
_TOKEN = re.compile(r"[A-Za-z0-9_-]+\Z")
_UPSTREAM_ID = re.compile(r"import:[0-9a-f]{64}\Z")
_SCOPES = {"json": "json_array_index_one_based",
           "csv": "tabular_record_index_one_based_including_header",
           "tsv": "tabular_record_index_one_based_including_header",
           "xlsx": "xlsx_worksheet_row_one_based_including_header"}
_LOCK = threading.Lock()
_candidate_module = None
_practice_module = None
_xlsx_source_uncertain = False
_ISSUED = object()


class PracticeCandidateError(ValueError):
    """A fixed reason code that never contains source or candidate values."""


def _read_pinned(which):
    """Read a fixed source with bounded, observed file-identity checks.

    These checks do not eliminate concurrent filesystem replacement races or
    authenticate the interpreter and installed dependencies.
    """
    if which not in _PINS:
        raise PracticeCandidateError("SOURCE_UNAVAILABLE")
    name, size, digest = _PINS[which]
    path = _ROOT / name
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise PracticeCandidateError("SOURCE_UNAVAILABLE")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise PracticeCandidateError("SOURCE_UNAVAILABLE")
            before.append(info)
        expected = before[-1]
        if (not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1
                or expected.st_size != size or not expected.st_ino):
            raise PracticeCandidateError("SOURCE_UNAVAILABLE")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != size):
                raise PracticeCandidateError("SOURCE_UNAVAILABLE")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise PracticeCandidateError("SOURCE_UNAVAILABLE")
            parts = []
            remaining = size + 1
            while remaining:
                chunk = os.read(fd, remaining)
                if not chunk:
                    break
                parts.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(parts)
            after = os.fstat(fd)
            if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink)
                    != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, 1)):
                raise PracticeCandidateError("SOURCE_UNAVAILABLE")
        finally:
            os.close(fd)
    except OSError:
        raise PracticeCandidateError("SOURCE_UNAVAILABLE") from None
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
        raise PracticeCandidateError("SOURCE_UNAVAILABLE")
    return raw


def _load_pinned(which, source):
    """Temporarily register a unique module for dataclass initialization."""
    name = "_deeptutor_practice_candidate_" + secrets.token_hex(16)
    if name in sys.modules:
        raise PracticeCandidateError("SOURCE_UNAVAILABLE")
    path = _ROOT / _PINS[which][0]
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    owned = True
    try:
        exec(compile(source, str(path), "exec"), module.__dict__)  # noqa: S102 -- fixed source pin
    except Exception:
        raise PracticeCandidateError("SOURCE_UNAVAILABLE") from None
    finally:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        else:
            owned = False
    if not owned:
        raise PracticeCandidateError("SOURCE_UNAVAILABLE")
    return module


def _modules():
    """Cache exactly one of each module within this adapter instance."""
    global _candidate_module, _practice_module
    candidate_source = _read_pinned("candidate")
    practice_source = _read_pinned("practice")
    if _candidate_module is None:
        _candidate_module = _load_pinned("candidate", candidate_source)
    if _practice_module is None:
        _practice_module = _load_pinned("practice", practice_source)
    return _candidate_module, _practice_module


def _text(value, max_bytes, *, nonblank=False):
    if type(value) is not str or "\x00" in value or (nonblank and not value.strip()):
        raise PracticeCandidateError("QUESTION_OUTSIDE_CORE_BOUNDS")
    try:
        length = len(value.encode("utf-8", "strict"))
    except UnicodeError:
        raise PracticeCandidateError("QUESTION_OUTSIDE_CORE_BOUNDS") from None
    if length > max_bytes:
        raise PracticeCandidateError("QUESTION_OUTSIDE_CORE_BOUNDS")
    return length


def _token(value, max_bytes):
    return type(value) is str and 1 <= len(value) <= max_bytes and bool(_TOKEN.fullmatch(value))


def _fold(value):
    # This matches the original practice grader's alias folding. It does not
    # judge whether the answer is factually correct.
    return " ".join(value.strip().upper().split())


def _reject_ambiguous_aliases(options, question_type):
    aliases = {}
    for key, value in options.items():
        for alias in (key, value, f"{key}. {value}", f"{key}) {value}"):
            folded = _fold(alias)
            if folded in aliases and aliases[folded] != key:
                raise PracticeCandidateError("AMBIGUOUS_OPTIONS")
            aliases[folded] = key
    # The original grader first tries a whole-string alias, then treats a
    # multi-select answer as separated keys. A visible option alias must not
    # also denote a different multi-key selection, including its continuous
    # key fallback (e.g. AB -> {A, B}, AA -> {A}).
    if question_type == "multi_choice":
        for alias, owner in aliases.items():
            parts = {part.strip().upper() for part in re.split(r"[,;，；\s]+", alias) if part.strip()}
            if len(parts) == 1 and not parts <= options.keys():
                parts = set(alias.strip().upper())
            if parts and parts <= options.keys() and parts != {owner}:
                raise PracticeCandidateError("AMBIGUOUS_OPTIONS")
            # A multi-character option key can itself take precedence over a
            # continuous multi-selection in the original grader. Reject that
            # additional representational ambiguity even if its fallback would
            # not run because the whole key exists.
            continuous = set(alias.strip().upper())
            if len(alias) > 1 and continuous <= options.keys() and continuous != {owner}:
                raise PracticeCandidateError("AMBIGUOUS_OPTIONS")


def _question(candidate, question_id, material):
    fields = {"question_id", "question", "question_type", "options", "correct_answer", "explanation",
              "difficulty", "user_answer", "tags"}
    if (type(candidate) is not dict or set(candidate) != fields
            or type(candidate["question_id"]) is not str or not _UPSTREAM_ID.fullmatch(candidate["question_id"])):
        raise PracticeCandidateError("IMPORTED_ROW_UNAVAILABLE")
    question_bytes = _text(candidate["question"], 128_000, nonblank=True)
    type_bytes = _text(candidate["question_type"], 128)
    answer_bytes = _text(candidate["correct_answer"], 20_000)
    explanation_bytes = _text(candidate["explanation"], 128_000)
    options = candidate["options"]
    if type(options) is not dict or len(options) > 64:
        raise PracticeCandidateError("QUESTION_OUTSIDE_CORE_BOUNDS")
    option_bytes = 0
    for key, value in options.items():
        option_bytes += _text(key, 256, nonblank=True) + _text(value, 20_000)
    _reject_ambiguous_aliases(options, candidate["question_type"])
    # The existing builder repeats visible strings in paragraphs and attrs.
    # Each UTF-8 byte can conservatively expand to six JSON bytes; fixed syntax
    # and a 64-option structural margin are covered by 8192 bytes. Core still
    # performs its own exact 1 MiB serialized-editor check.
    material_bytes = len(material["document_id"].encode("ascii")) + len(material["content_sha256"])
    upper = 8192 + 12 * (question_bytes + option_bytes) + 6 * (
        type_bytes + answer_bytes + explanation_bytes + len(question_id) + material_bytes)
    if upper > 1024 * 1024:
        raise PracticeCandidateError("QUESTION_OUTSIDE_CORE_BOUNDS")
    return {"question_id": question_id, "question": candidate["question"],
            "question_type": candidate["question_type"], "options": dict(options),
            "correct_answer": candidate["correct_answer"], "explanation": candidate["explanation"]}


class PrivatePracticeCandidate:
    """Private handoff; getters can reveal answers and other source content."""

    __slots__ = ("_candidate", "_receipt_json")

    def __init__(self, candidate, receipt_json, *, _issued=None):
        if _issued is not _ISSUED:
            raise PracticeCandidateError("CANDIDATE_NOT_PREPARED")
        object.__setattr__(self, "_candidate", candidate)
        object.__setattr__(self, "_receipt_json", receipt_json)

    def __setattr__(self, _name, _value):
        raise AttributeError("prepared candidate is immutable")

    def __repr__(self):
        return "<PrivatePracticeCandidate: contents withheld>"

    def report(self):
        return self._candidate.report()

    def original_source_bytes(self):
        return self._candidate.original_response_bytes()

    def raw_import_request(self):
        return self._candidate.raw_import_request()

    def document_create_request(self, claimed_import_receipt):
        """Use only the caller-supplied Core-shaped receipt; do not invent one."""
        try:
            return self._candidate.document_create_request(claimed_import_receipt)
        except Exception:
            raise PracticeCandidateError("INVALID_IMPORT_RECEIPT") from None

    def private_import_receipt(self):
        """Fresh private row/loss data; this adapter does not persist it."""
        return json.loads(self._receipt_json)


def prepare_practice_row(data, format, row, material_snapshot, question_id, create_request_id, title):
    """Reparse caller bytes and prepare one unverified question document.

    Calls through this module instance are non-blocking and serialized. XLSX
    uses the one cached practice module and its own cleanup-unknown slot.
    The host must coordinate other module instances, processes and restarts.
    """
    global _xlsx_source_uncertain
    if not _LOCK.acquire(blocking=False):
        raise PracticeCandidateError("BUSY")
    try:
        if (type(data) is not bytes or not data or len(data) > _MAX_SOURCE
                or type(format) is not str or format not in _SCOPES
                or type(row) is not int or row < 1
                or not _token(question_id, 256) or not _token(create_request_id, 128)
                or type(title) is not str):
            raise PracticeCandidateError("INVALID_INPUT")
        try:
            if len(title.encode("utf-8", "strict")) > 1024 or "\x00" in title:
                raise PracticeCandidateError("INVALID_INPUT")
        except UnicodeError:
            raise PracticeCandidateError("INVALID_INPUT") from None
        if format == "xlsx" and _xlsx_source_uncertain:
            raise PracticeCandidateError("XLSX_SOURCE_UNKNOWN")
        candidate_module, practice = _modules()
        try:
            material = candidate_module._snapshot(material_snapshot)
        except Exception:
            raise PracticeCandidateError("INVALID_MATERIAL_SNAPSHOT") from None
        future_id = "doc_req_" + hashlib.sha256(create_request_id.encode("ascii")).hexdigest()
        if material["document_id"] == future_id:
            raise PracticeCandidateError("INVALID_MATERIAL_SNAPSHOT")
        try:
            batch = practice._private_preview(data, format)
        except Exception:
            raise PracticeCandidateError("IMPORT_UNAVAILABLE_OR_REJECTED") from None
        finally:
            if format == "xlsx":
                try:
                    _read_pinned("practice")
                except PracticeCandidateError:
                    # The child loads this path itself. A changed/unavailable
                    # source after invocation leaves its identity unknown.
                    _xlsx_source_uncertain = True
        if format == "xlsx" and _xlsx_source_uncertain:
            raise PracticeCandidateError("XLSX_SOURCE_UNKNOWN")
        if (batch.source != data or batch.source_sha256 != hashlib.sha256(data).hexdigest()
                or batch.format != format or type(batch.rows) is not list or len(batch.rows) > 500):
            raise PracticeCandidateError("IMPORTED_ROW_UNAVAILABLE")
        numbers = [item.get("row") for item in batch.rows if type(item) is dict]
        if (len(numbers) != len(batch.rows) or any(type(n) is not int or n < 1 for n in numbers)
                or len(set(numbers)) != len(numbers)):
            raise PracticeCandidateError("IMPORTED_ROW_UNAVAILABLE")
        selected = [item for item in batch.rows if item["row"] == row]
        if len(selected) != 1 or selected[0].get("candidate") is None:
            raise PracticeCandidateError("IMPORTED_ROW_UNAVAILABLE")
        item = selected[0]
        if (set(item) != {"row", "raw", "unmapped", "candidate", "option_changes"}
                or type(item["raw"]) is not dict or type(item["unmapped"]) is not list
                or (item["option_changes"] is not None and type(item["option_changes"]) is not list)):
            raise PracticeCandidateError("IMPORTED_ROW_UNAVAILABLE")
        question = _question(item["candidate"], question_id, material)
        report = {"schema": "archeaxis.deeptutor-practice-candidate/v1", "status": "PRIVATE_CANDIDATE_PREPARED",
                  "origin": "CALLER_SUPPLIED_UNVERIFIED", "material_snapshot": "CALLER_DECLARED_UNVERIFIED",
                  "source_link": "XLSX_CHILD_SOURCE_LINK_UNVERIFIED" if format == "xlsx"
                                 else "PINNED_PARSER_OF_CALLER_BYTES_NOT_AUTHENTICATED",
                  "source_import": "NOT_EXECUTED", "core_document_write": "NOT_EXECUTED",
                  "core_authorization": "NOT_ESTABLISHED", "provider_generation": "NOT_ESTABLISHED",
                  "question_replay": "NOT_INVOKED", "provider_execution": "NOT_INVOKED",
                  "model_call": "NOT_INVOKED", "grading": "NOT_INVOKED", "independent_mastery": "NOT_ESTABLISHED",
                  "loss_scope": "KNOWN_OPTION_CHANGES_ONLY_OTHER_SELECTED_VALUES_NOT_COMPARED",
                  "private_row_receipt_persistence": "NOT_ESTABLISHED",
                  "source_and_document_calls": "SEPARATE_DOCUMENT_FAILURE_MAY_LEAVE_SOURCE",
                  "request_binding": "AT_CONSTRUCTION_ONLY_MUTABLE_AFTER_RETURN_NOT_VERIFIED_BY_CORE",
                  "privacy_filter": "NOT_APPLIED", "logging_safety": "NOT_ESTABLISHED"}
        receipt = {"schema": "archeaxis.deeptutor-practice-private-row/v1",
                   "source_format": format, "source_sha256": batch.source_sha256,
                   "source_row_scope": _SCOPES[format], "source_row": row,
                   "raw_row": item["raw"], "unmapped": item["unmapped"],
                   "option_changes": item["option_changes"], "normalized_candidate": item["candidate"],
                   "skipped_source_rows": batch.skipped_rows,
                   "other_selected_values_compared": False,
                   "source_link": report["source_link"], "persistence": "NOT_ESTABLISHED"}
        try:
            receipt_json = json.dumps(receipt, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            if len(receipt_json.encode("utf-8", "strict")) > _MAX_PRIVATE_RECEIPT:
                raise PracticeCandidateError("PRIVATE_RECEIPT_LIMIT")
            prepared = candidate_module.PrivateCandidate(data, question, material, create_request_id, title, report,
                source_name="deeptutor-practice-import." + format, _issued=candidate_module._ISSUED)
        except PracticeCandidateError:
            raise
        except Exception:
            raise PracticeCandidateError("CANDIDATE_UNAVAILABLE") from None
        return PrivatePracticeCandidate(prepared, receipt_json, _issued=_ISSUED)
    finally:
        _LOCK.release()
