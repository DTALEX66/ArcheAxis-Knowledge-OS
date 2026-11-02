"""Private offline comparison of one prepared practice candidate and readbacks.

All input and HTTP-shaped responses are caller-supplied and unauthenticated.
The selected source and prepared object can contain answers and private data.
No network, Core, database, model, or grade is invoked by this module.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import secrets
import stat
import sys
import threading
import types


_ROOT = Path(__file__).absolute().parent
_PINS = {
    "practice": ("practice_candidate_document.py", 17_679,
                 "219e04721d662198b1fa1169c4be8e3acc63be24e3c7595d3e01847d1c2ead17"),
    "comparison": ("candidate_readback.py", 18_952,
                    "04936dbd2f8a2b7c1dbb5b75c5b7b7995f9624613b17ccc817390de603105072"),
}
_MAX_SOURCE = 5 * 1024 * 1024
_MAX_SOURCE_JSON = ((_MAX_SOURCE + 2) // 3) * 4 + 65_536
_MAX_DOCUMENT_JSON = 4 * 1024 * 1024
_MAX_VIEW_JSON = 512 * 1024
_MAX_PRIVATE_RECEIPT = 16 * 1024 * 1024
_SCOPES = {"json": "json_array_index_one_based",
           "csv": "tabular_record_index_one_based_including_header",
           "tsv": "tabular_record_index_one_based_including_header",
           "xlsx": "xlsx_worksheet_row_one_based_including_header"}
_LOCK = threading.Lock()
_practice = None
_comparison = None
_latest = None
_latest_fingerprint = None
_ALLOWED_ERRORS = {"INVALID_RESPONSE_ENVELOPE", "INVALID_RESPONSE_JSON", "IMPORT_UNAVAILABLE",
                   "SOURCE_UNAVAILABLE", "DOCUMENT_CREATE_UNAVAILABLE", "DOCUMENT_READ_UNAVAILABLE",
                   "VIEW_UNAVAILABLE", "SOURCE_MISMATCH", "DOCUMENT_MISMATCH", "VIEW_MISMATCH"}


class PracticeReadbackError(ValueError):
    """A fixed code without caller-provided material."""


def _read_pinned(which):
    """Read one fixed source; observed identity checks do not eliminate TOCTOU."""
    if which not in _PINS:
        raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
    name, size, digest = _PINS[which]
    path = _ROOT / name
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
            before.append(info)
        expected = before[-1]
        if (not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1
                or expected.st_size != size or not expected.st_ino):
            raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != size):
                raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
            chunks = []
            remaining = size + 1
            while remaining:
                part = os.read(fd, remaining)
                if not part:
                    break
                chunks.append(part)
                remaining -= len(part)
            raw = b"".join(chunks)
            after = os.fstat(fd)
            if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink)
                    != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, 1)):
                raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
        finally:
            os.close(fd)
    except OSError:
        raise PracticeReadbackError("ADAPTER_UNAVAILABLE") from None
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
        raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
    return raw


def _load_pinned(which, source):
    name = "_deeptutor_practice_readback_" + secrets.token_hex(16)
    if name in sys.modules:
        raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
    path = _ROOT / _PINS[which][0]
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    owned = True
    try:
        exec(compile(source, str(path), "exec"), module.__dict__)  # noqa: S102 -- fixed source pin
    except Exception:
        raise PracticeReadbackError("ADAPTER_UNAVAILABLE") from None
    finally:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        else:
            owned = False
    if not owned:
        raise PracticeReadbackError("ADAPTER_UNAVAILABLE")
    return module


def _dependencies(*, initialize):
    """Never replace a successfully loaded practice module in this instance."""
    global _practice, _comparison
    if not initialize and (_practice is None or _comparison is None):
        raise PracticeReadbackError("PREPARATION_REQUIRED")
    practice_source = _read_pinned("practice")
    comparison_source = _read_pinned("comparison")
    if _comparison is None:
        _comparison = _load_pinned("comparison", comparison_source)
    if _practice is None:
        _practice = _load_pinned("practice", practice_source)
    return _practice, _comparison


def _prepared_fingerprint(prepared, practice):
    """Detect changes to the one retained candidate; this is not authentication."""
    if type(prepared) is not practice.PrivatePracticeCandidate:
        raise PracticeReadbackError("PREPARED_UNAVAILABLE")
    try:
        inner = prepared._candidate
        if (practice._candidate_module is None
                or type(inner) is not practice._candidate_module.PrivateCandidate
                or type(inner._raw) is not bytes or not inner._raw or len(inner._raw) > _MAX_SOURCE
                or inner._recovery_receipt_json is not None):
            raise PracticeReadbackError("PREPARED_UNAVAILABLE")
        values = ((inner._raw, _MAX_SOURCE), (inner._candidate_json, _MAX_DOCUMENT_JSON),
                  (inner._material_json, 8192), (inner._create_request_id, 128),
                  (inner._title, 1024), (inner._report_json, 65_536),
                  (inner._source_name, 1024), (prepared._receipt_json, _MAX_PRIVATE_RECEIPT))
        digest = hashlib.sha256()
        for value, maximum in values:
            if type(value) is str:
                # Every Unicode code point needs at least one UTF-8 byte. This
                # first bound avoids encoding an oversized tampered string.
                if len(value) > maximum:
                    raise PracticeReadbackError("PREPARED_UNAVAILABLE")
                value = value.encode("utf-8", "strict")
            elif type(value) is not bytes:
                raise PracticeReadbackError("PREPARED_UNAVAILABLE")
            if len(value) > maximum:
                raise PracticeReadbackError("PREPARED_UNAVAILABLE")
            digest.update(len(value).to_bytes(8, "big"))
            digest.update(value)
        return digest.digest()
    except PracticeReadbackError:
        raise
    except Exception:
        raise PracticeReadbackError("PREPARED_UNAVAILABLE") from None


def prepare_practice_row(data, format, row, material_snapshot, question_id, create_request_id, title):
    """Explicitly prepare one candidate through this instance's cached module.

    An XLSX call can start the existing private child. A failed or unknown
    call does not discard its cached module or recreate its process slot.
    """
    global _latest, _latest_fingerprint
    if not _LOCK.acquire(blocking=False):
        raise PracticeReadbackError("BUSY")
    try:
        # A new selection invalidates the previous candidate even on failure.
        # The caller may still hold its own object; this module retains one.
        _latest = None
        _latest_fingerprint = None
        practice, _ = _dependencies(initialize=True)
        try:
            prepared = practice.prepare_practice_row(data, format, row, material_snapshot, question_id,
                                                     create_request_id, title)
            fingerprint = _prepared_fingerprint(prepared, practice)
        except Exception:
            raise PracticeReadbackError("CANDIDATE_UNAVAILABLE") from None
        _latest = prepared
        _latest_fingerprint = fingerprint
        return prepared
    finally:
        _LOCK.release()


def reconcile(prepared, data, format, row, material_snapshot, question_id, create_request_id, title,
              import_response, original_response, create_response, document_response, view_response):
    """Compare a same-instance prepared object and bounded caller readbacks.

    This does not invoke preparation again, start an XLSX child, or authenticate
    the supplied object, claims or HTTP responses. Source/version conclusions are
    conditional on a trusted host and independently obtained Core responses.
    """
    if not _LOCK.acquire(blocking=False):
        raise PracticeReadbackError("BUSY")
    try:
        practice, comparison = _dependencies(initialize=False)
        if _latest is None or _latest_fingerprint is None:
            raise PracticeReadbackError("PREPARATION_REQUIRED")
        if prepared is not _latest:
            raise PracticeReadbackError("PREPARED_STALE")
        if (type(prepared) is not practice.PrivatePracticeCandidate or type(data) is not bytes
                or not data or len(data) > _MAX_SOURCE or type(format) is not str or format not in _SCOPES
                or type(row) is not int or row < 1 or type(question_id) is not str
                or type(create_request_id) is not str or type(title) is not str):
            raise PracticeReadbackError("INVALID_INPUT")
        try:
            # Check that the same pinned dependencies remain present without
            # replacing either cached module or rerunning the practice parser.
            practice._read_pinned("candidate")
            practice._read_pinned("practice")
            if _prepared_fingerprint(prepared, practice) != _latest_fingerprint:
                raise PracticeReadbackError("PREPARED_MISMATCH")
            original_bytes = prepared.original_source_bytes()
            private = prepared.private_import_receipt()
            report = prepared.report()
            expected_link = ("XLSX_CHILD_SOURCE_LINK_UNVERIFIED" if format == "xlsx"
                             else "PINNED_PARSER_OF_CALLER_BYTES_NOT_AUTHENTICATED")
            if (original_bytes != data or type(private) is not dict
                    or private.get("source_format") != format or type(private.get("source_row")) is not int
                    or private["source_row"] != row or private.get("source_row_scope") != _SCOPES[format]
                    or private.get("source_sha256") != hashlib.sha256(data).hexdigest()
                    or private.get("source_link") != expected_link or type(report) is not dict
                    or report.get("source_link") != expected_link):
                raise PracticeReadbackError("PREPARED_MISMATCH")
        except PracticeReadbackError:
            raise
        except Exception:
            raise PracticeReadbackError("PREPARED_UNAVAILABLE") from None

        try:
            claimed_import = comparison._response(import_response, 202, 4096, "IMPORT_UNAVAILABLE")
            original = comparison._response(original_response, 200, _MAX_SOURCE_JSON, "SOURCE_UNAVAILABLE")
            created = comparison._response(create_response, 201, _MAX_DOCUMENT_JSON, "DOCUMENT_CREATE_UNAVAILABLE")
            document = comparison._response(document_response, 200, _MAX_DOCUMENT_JSON, "DOCUMENT_READ_UNAVAILABLE")
            view = comparison._response(view_response, 200, _MAX_VIEW_JSON, "VIEW_UNAVAILABLE")
            comparison._source_matches(claimed_import, original, data)
        except comparison.ReadbackError as error:
            code = str(error)
            raise PracticeReadbackError(code if code in _ALLOWED_ERRORS else "COMPARISON_UNAVAILABLE") from None
        try:
            expected = prepared.document_create_request(claimed_import)
            metadata = expected["editor_json"]["attrs"]["archeaxis_deeptutor_question"]
            normalized = private.get("normalized_candidate")
            fields = ("question", "question_type", "options", "correct_answer", "explanation")
            if (expected.get("create_request_id") != create_request_id or expected.get("title") != title
                    or not comparison._same_json(metadata.get("source_material"), material_snapshot)
                    or metadata["question"].get("question_id") != question_id or type(normalized) is not dict
                    or any(not comparison._same_json(metadata["question"].get(field), normalized.get(field))
                           for field in fields)):
                raise PracticeReadbackError("PREPARED_MISMATCH")
        except PracticeReadbackError:
            raise
        except Exception:
            raise PracticeReadbackError("PREPARED_UNAVAILABLE") from None
        try:
            created_snapshot = comparison._document_matches(created, expected)
            snapshot = comparison._document_matches(document, expected)
            if (not comparison._same_json(created_snapshot, snapshot)
                    or not comparison._same_json(created.get("editor_json"), document.get("editor_json"))):
                raise PracticeReadbackError("DOCUMENT_MISMATCH")
            question_status, source_status = comparison._view_matches(
                view, snapshot, metadata["source_material"], metadata["question"])
        except PracticeReadbackError:
            raise
        except comparison.ReadbackError as error:
            code = str(error)
            raise PracticeReadbackError(code if code in _ALLOWED_ERRORS else "COMPARISON_UNAVAILABLE") from None
        return {"schema": "archeaxis.deeptutor-practice-readback-comparison/v1",
                "status": "CALLER_SUPPLIED_READBACKS_MATCH_PREPARED_CANDIDATE",
                "source_link": expected_link, "question_status": question_status,
                "source_snapshot_status": source_status,
                "prepared_identity": "LATEST_SAME_INSTANCE_FINGERPRINT_NOT_AUTHENTICATION",
                "raw_response_comparison": "EXACT_BYTES_AND_SHA256",
                "candidate_and_body_comparison": "MATCHED_IN_SUPPLIED_READBACKS",
                "reparse_during_readback": "NOT_INVOKED", "response_identity": "CALLER_SUPPLIED_UNAUTHENTICATED",
                "core_authentication": "NOT_ESTABLISHED", "core_authorization": "NOT_ESTABLISHED",
                "provider_generation": "NOT_ESTABLISHED", "grading": "NOT_INVOKED",
                "independent_mastery": "NOT_ESTABLISHED",
                "document_content_sha256": "FORMAT_AND_REFERENCE_ONLY_NOT_RECOMPUTED",
                "view_digests": "FORMAT_ONLY_NOT_RECOMPUTED", "block_id": "FORMAT_ONLY_NOT_RECOMPUTED",
                "future_currentness": "NOT_ESTABLISHED", "restart_durability": "NOT_ESTABLISHED",
                "readback_atomicity": "NOT_ESTABLISHED",
                "source_and_document_calls": "SEPARATE_DOCUMENT_FAILURE_MAY_LEAVE_SOURCE",
                "cross_instance_process_fence": "NOT_ESTABLISHED",
                "private_row_receipt_persistence": "NOT_ESTABLISHED",
                "privacy_filter": "NOT_APPLIED", "logging_safety": "NOT_ESTABLISHED"}
    finally:
        _LOCK.release()
