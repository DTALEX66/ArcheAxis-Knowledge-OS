"""One private, bounded practice-row handoff for a future controlled host.

This is not a registered route and never calls Core, a model, or a database.
Successful stdout contains a document request with the answer and explanation.
The process, its input, and its output must be owned and protected by its host.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import types


SCHEMA = "archeaxis.deeptutor-practice-host-worker/v1"
MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_SOURCE_BASE64 = ((MAX_SOURCE_BYTES + 2) // 3) * 4
# Limits include the one mandatory LF framing byte.
MAX_REQUEST_BYTES = MAX_SOURCE_BASE64 + 65_536
MAX_REPLY_BYTES = 1024 * 1024 + 65_536

_ROOT = Path(__file__).absolute().parent
_ADAPTER_NAME = "practice_candidate_document.py"
_ADAPTER_SIZE = 17_679
_ADAPTER_SHA256 = "219e04721d662198b1fa1169c4be8e3acc63be24e3c7595d3e01847d1c2ead17"
_TOKEN = re.compile(r"[A-Za-z0-9_-]+\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = {"schema", "request_id", "source", "source_row", "material_snapshot",
           "question_id", "create_request_id", "title", "import_receipt"}

_INVALID = (b'{"schema":"archeaxis.deeptutor-practice-host-worker/v1",'
            b'"status":"INVALID_REQUEST","reason_code":"INVALID_INPUT"}\n')
_REJECTED = (b'{"schema":"archeaxis.deeptutor-practice-host-worker/v1",'
             b'"status":"REJECTED","reason_code":"CANDIDATE_REJECTED_OR_UNAVAILABLE"}\n')
_UNAVAILABLE = (b'{"schema":"archeaxis.deeptutor-practice-host-worker/v1",'
                b'"status":"UNAVAILABLE","reason_code":"WORKER_UNAVAILABLE"}\n')


class _InvalidRequest(ValueError):
    pass


class _AdapterUnavailable(RuntimeError):
    pass


class _CandidateRejected(RuntimeError):
    pass


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise _InvalidRequest()
        value[key] = item
    return value


def _invalid_number(_value):
    # The envelope has no floating-point fields, including NaN and Infinity.
    raise _InvalidRequest()


def _bounded_integer(value):
    if len(value) > 100:
        raise _InvalidRequest()
    return int(value)


def _token(value, limit):
    return type(value) is str and 1 <= len(value) <= limit and bool(_TOKEN.fullmatch(value))


def _digest(value):
    return type(value) is str and bool(_SHA256.fullmatch(value))


def _bounded_text(value, limit, *, nonempty=False):
    # A Unicode scalar occupies at least one UTF-8 byte. Check the character
    # count before encoding so an abnormal object is not encoded without bound.
    if (type(value) is not str or len(value) > limit or "\x00" in value
            or (nonempty and not value)):
        return False
    try:
        return len(value.encode("utf-8", "strict")) <= limit
    except UnicodeError:
        return False


def _read_frame(stream):
    """Require a single bounded line and EOF; the host must close stdin."""
    line = stream.readline(MAX_REQUEST_BYTES + 1)
    if not line or len(line) > MAX_REQUEST_BYTES or not line.endswith(b"\n"):
        raise _InvalidRequest()
    if stream.read(1) != b"":
        raise _InvalidRequest()
    try:
        value = json.loads(line.decode("utf-8", "strict"), object_pairs_hook=_unique_object,
                           parse_int=_bounded_integer, parse_float=_invalid_number,
                           parse_constant=_invalid_number)
    except (ValueError, UnicodeError, RecursionError):
        raise _InvalidRequest() from None
    return line, value


def _read_adapter():
    """Read the fixed adapter and check observed identities, size, and digest.

    These checks do not authenticate Python or rule out all concurrent path
    replacement. The future host must independently pin and own this worker.
    """
    path = _ROOT / _ADAPTER_NAME
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise _AdapterUnavailable()
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise _AdapterUnavailable()
            before.append(info)
        expected = before[-1]
        if (not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1
                or expected.st_size != _ADAPTER_SIZE or not expected.st_ino):
            raise _AdapterUnavailable()
        flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
                 | getattr(os, "O_NOFOLLOW", 0))
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or opened.st_size != _ADAPTER_SIZE):
                raise _AdapterUnavailable()
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise _AdapterUnavailable()
            chunks = []
            remaining = _ADAPTER_SIZE + 1
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
                raise _AdapterUnavailable()
        finally:
            os.close(fd)
    except OSError:
        raise _AdapterUnavailable() from None
    if len(raw) != _ADAPTER_SIZE or hashlib.sha256(raw).hexdigest() != _ADAPTER_SHA256:
        raise _AdapterUnavailable()
    return raw


def _load_adapter():
    source = _read_adapter()
    name = "_deeptutor_practice_host_" + secrets.token_hex(16)
    if name in sys.modules:
        raise _AdapterUnavailable()
    module = types.ModuleType(name)
    module.__file__ = str(_ROOT / _ADAPTER_NAME)
    sys.modules[name] = module
    owned = True
    try:
        exec(compile(source, module.__file__, "exec"), module.__dict__)  # noqa: S102 -- fixed source pin
    except Exception:
        raise _AdapterUnavailable() from None
    finally:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        else:
            owned = False
    if not owned or not callable(getattr(module, "prepare_practice_row", None)):
        raise _AdapterUnavailable()
    return module


def _checked_request(value):
    if type(value) is not dict or set(value) != _FIELDS or value["schema"] != SCHEMA:
        raise _InvalidRequest()
    if (not _token(value["request_id"], 128) or not _token(value["question_id"], 256)
            or not _token(value["create_request_id"], 128)
            or type(value["source_row"]) is not int or not 1 <= value["source_row"] <= 502
            or not _bounded_text(value["title"], 1024)):
        raise _InvalidRequest()

    material = value["material_snapshot"]
    if (type(material) is not dict or set(material) != {"document_id", "version", "content_sha256"}
            or not _token(material["document_id"], 128) or type(material["version"]) is not int
            or not 1 <= material["version"] <= 9_007_199_254_740_991
            or not _digest(material["content_sha256"])):
        raise _InvalidRequest()

    source = value["source"]
    if (type(source) is not dict or set(source) != {"format", "content_base64", "sha256"}
            or type(source["format"]) is not str or source["format"] not in {"csv", "tsv", "json"}
            or not _digest(source["sha256"])):
        # XLSX is deliberately rejected: its child/source link and descendant
        # cleanup are not established for this future host protocol.
        raise _InvalidRequest()
    encoded = source["content_base64"]
    if type(encoded) is not str or not encoded or len(encoded) > MAX_SOURCE_BASE64:
        raise _InvalidRequest()
    try:
        encoded_bytes = encoded.encode("ascii", "strict")
        raw = base64.b64decode(encoded_bytes, validate=True)
    except (UnicodeError, ValueError, binascii.Error):
        raise _InvalidRequest() from None
    if (not raw or len(raw) > MAX_SOURCE_BYTES or base64.b64encode(raw) != encoded_bytes
            or hashlib.sha256(raw).hexdigest() != source["sha256"]):
        raise _InvalidRequest()

    receipt = value["import_receipt"]
    if (type(receipt) is not dict or set(receipt) != {"source_id", "sha256", "duplicate"}
            or not _bounded_text(receipt["source_id"], 128, nonempty=True)
            or not _digest(receipt["sha256"]) or receipt["sha256"] != source["sha256"]
            or type(receipt["duplicate"]) is not bool):
        raise _InvalidRequest()
    if not receipt["duplicate"]:
        expected = "src_" + hashlib.sha256(receipt["sha256"].encode("ascii")).hexdigest()[:24]
        if receipt["source_id"] != expected:
            raise _InvalidRequest()
    # A duplicate may legitimately retain an older source ID. This shape and
    # hash check cannot authenticate any receipt supplied to this process.
    return raw, source["format"], material, receipt


def _prepare(value, input_sha256):
    raw, format_name, material, receipt = _checked_request(value)
    adapter = _load_adapter()
    try:
        candidate = adapter.prepare_practice_row(raw, format_name, value["source_row"], material,
                                                 value["question_id"], value["create_request_id"], value["title"])
        document = candidate.document_create_request(receipt)
    except Exception:
        # The original adapter intentionally combines certain invalid-input and
        # unavailable-source cases. Do not infer or echo a detailed cause.
        raise _CandidateRejected() from None
    return {"schema": SCHEMA, "request_id": value["request_id"], "status": "PRIVATE_CANDIDATE",
            "input_sha256": input_sha256, "document_create_request": document,
            "source_link": "PINNED_PARSER_OF_CALLER_BYTES_NOT_AUTHENTICATED",
            "import_receipt": "CALLER_SUPPLIED_NOT_AUTHENTICATED",
            "material_snapshot": "CALLER_DECLARED_NOT_AUTHENTICATED",
            "row_and_loss_receipt": "NOT_RETURNED_OR_PERSISTED_BY_WORKER",
            "core_write": "NOT_EXECUTED", "provider_execution": "NOT_INVOKED",
            "output_privacy_filter": "NOT_APPLIED"}


def main():
    try:
        if len(sys.argv) != 1:
            raise _InvalidRequest()
        line, value = _read_frame(sys.stdin.buffer)
        result = _prepare(value, hashlib.sha256(line).hexdigest())
        wire = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(wire) > MAX_REPLY_BYTES:
            raise _CandidateRejected()
        code = 0
    except _InvalidRequest:
        wire, code = _INVALID, 2
    except _CandidateRejected:
        wire, code = _REJECTED, 2
    except BaseException:
        # A private traceback or exception may include material. A failed
        # interpreter/pipe before this handler remains the host's responsibility.
        wire, code = _UNAVAILABLE, 1
    try:
        sys.stdout.buffer.write(wire)
        sys.stdout.buffer.flush()
    except (OSError, ValueError):
        return 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
