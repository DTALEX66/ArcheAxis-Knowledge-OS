"""Offline comparison of caller-supplied Core readbacks with a private candidate.

No response or identity is authenticated here. Inputs can contain answer keys;
only fixed status codes are returned or raised, never the supplied contents.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat


_ROOT = Path(__file__).absolute().parent
_CANDIDATE = "candidate_document.py"
_CANDIDATE_SIZE = 23_478
_CANDIDATE_SHA256 = "96ad414a1d35e842ad42362ea6ba1327ab7dfd8b3bb06d6e5bab39073a25953c"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_DOC_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_BLOCK_ID = re.compile(r"blk_[0-9a-f]{24}\Z")
_MAX_SOURCE_JSON = 320 * 1024
_MAX_DOCUMENT_JSON = 4 * 1024 * 1024
_MAX_VIEW_JSON = 512 * 1024


class ReadbackError(ValueError):
    """A fixed reason code without caller-provided data."""


def _read_candidate_source():
    path = _ROOT / _CANDIDATE
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ReadbackError("ADAPTER_UNAVAILABLE")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise ReadbackError("ADAPTER_UNAVAILABLE")
            before.append(info)
        expected = before[-1]
        if (not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1
                or expected.st_size != _CANDIDATE_SIZE or not expected.st_ino):
            raise ReadbackError("ADAPTER_UNAVAILABLE")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != _CANDIDATE_SIZE):
                raise ReadbackError("ADAPTER_UNAVAILABLE")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise ReadbackError("ADAPTER_UNAVAILABLE")
            chunks = []
            remaining = _CANDIDATE_SIZE + 1
            while remaining:
                chunk = os.read(fd, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            after = os.fstat(fd)
            if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink)
                    != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, 1)):
                raise ReadbackError("ADAPTER_UNAVAILABLE")
        finally:
            os.close(fd)
    except OSError:
        raise ReadbackError("ADAPTER_UNAVAILABLE") from None
    if len(data) != _CANDIDATE_SIZE or hashlib.sha256(data).hexdigest() != _CANDIDATE_SHA256:
        raise ReadbackError("ADAPTER_UNAVAILABLE")
    return data


def _candidate_adapter():
    path = _ROOT / _CANDIDATE
    namespace = {"__name__": "deeptutor_readback_candidate", "__file__": str(path)}
    try:
        exec(compile(_read_candidate_source(), str(path), "exec"), namespace)  # noqa: S102 -- exact pin
    except ReadbackError:
        raise
    except Exception:
        raise ReadbackError("ADAPTER_UNAVAILABLE") from None
    return namespace


def _unique(pairs):
    value = {}
    for key, entry in pairs:
        if key in value:
            raise ValueError("duplicate")
        value[key] = entry
    return value


def _integer(value):
    if len(value) > 32:
        raise ValueError("integer")
    return int(value)


def _float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite")
    return number


def _nonfinite(_value):
    raise ValueError("nonfinite")


def _same_json(left, right):
    """JSON equality with exact scalar types, so true never equals integer 1."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_same_json(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same_json(a, b) for a, b in zip(left, right))
    return left == right


def _bounded_structure(raw):
    """Bound JSON nesting and structural tokens before allocating the tree."""
    depth = 0
    tokens = 0
    quoted = False
    escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                quoted = False
        elif byte == 0x22:
            quoted = True
        elif byte in (0x7B, 0x5B, 0x7D, 0x5D, 0x2C, 0x3A):
            tokens += 1
            if byte in (0x7B, 0x5B):
                depth += 1
            elif byte in (0x7D, 0x5D):
                depth -= 1
            if tokens > 20_000 or depth < 0 or depth > 64:
                return False
    return depth == 0 and not quoted and not escaped


def _valid_unicode(value):
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeError:
                return False
        elif type(item) is dict:
            pending.extend(item.keys())
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
    return True


def _response(response, status, bound, unavailable):
    if type(response) is not tuple or len(response) != 2:
        raise ReadbackError("INVALID_RESPONSE_ENVELOPE")
    code, raw = response
    if type(code) is not int or type(raw) is not bytes or len(raw) > bound:
        raise ReadbackError("INVALID_RESPONSE_ENVELOPE")
    if code != status:
        raise ReadbackError(unavailable)
    if not _bounded_structure(raw):
        raise ReadbackError("INVALID_RESPONSE_JSON")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                           parse_int=_integer, parse_float=_float, parse_constant=_nonfinite)
    except (ValueError, UnicodeError, RecursionError):
        raise ReadbackError("INVALID_RESPONSE_JSON") from None
    if type(value) is not dict or not _valid_unicode(value):
        raise ReadbackError("INVALID_RESPONSE_JSON")
    return value


def _source_matches(receipt, original, raw):
    if set(receipt) != {"source_id", "sha256", "duplicate"} or type(receipt.get("duplicate")) is not bool:
        raise ReadbackError("SOURCE_MISMATCH")
    if set(original) != {"source_id", "name", "media_type", "sha256", "content_base64"}:
        raise ReadbackError("SOURCE_MISMATCH")
    source_id, digest = receipt.get("source_id"), receipt.get("sha256")
    encoded = original.get("content_base64")
    if (type(source_id) is not str or not source_id or len(source_id) > 128 or "\x00" in source_id
            or type(digest) is not str or not _SHA.fullmatch(digest)
            or original.get("source_id") != source_id or original.get("sha256") != digest
            or type(original.get("name")) is not str or type(original.get("media_type")) is not str
            or type(encoded) is not str):
        raise ReadbackError("SOURCE_MISMATCH")
    # Only newly created source rows have this identity rule. A duplicate can
    # refer to an older, already persisted ID that does not follow it.
    if receipt["duplicate"] is False:
        expected_id = "src_" + hashlib.sha256(digest.encode("ascii")).hexdigest()[:24]
        if source_id != expected_id:
            raise ReadbackError("SOURCE_MISMATCH")
    try:
        data = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (binascii.Error, ValueError, UnicodeError):
        raise ReadbackError("SOURCE_MISMATCH") from None
    if (base64.b64encode(data).decode("ascii") != encoded or data != raw
            or hashlib.sha256(data).hexdigest() != digest):
        raise ReadbackError("SOURCE_MISMATCH")
    return source_id, digest


def _document_matches(document, expected):
    required = {"document_id", "version", "content_sha256", "source_id", "source_revision", "title",
                "revision_basis", "editor_json", "blocks", "text_projection"}
    if not required <= set(document):
        raise ReadbackError("DOCUMENT_MISMATCH")
    identity, version, digest = document.get("document_id"), document.get("version"), document.get("content_sha256")
    # Core uses this exact deterministic identity for an explicitly provided
    # create_request_id. This comparison does not authenticate the receipt.
    expected_id = "doc_req_" + hashlib.sha256(expected["create_request_id"].encode("ascii")).hexdigest()
    if (type(identity) is not str or not _DOC_ID.fullmatch(identity)
            or identity != expected_id
            or type(version) is not int or version != 1
            or type(digest) is not str or not _SHA.fullmatch(digest)
            or document.get("source_id") != expected["source_id"]
            or document.get("source_revision") != expected["source_revision"]
            or document.get("title") != expected["title"]
            or document.get("revision_basis") is not None):
        raise ReadbackError("DOCUMENT_MISMATCH")
    editor = document.get("editor_json")
    want = expected["editor_json"]
    if (type(editor) is not dict or set(editor) != {"type", "content", "attrs"}
            or editor.get("type") != "doc" or not _same_json(editor.get("attrs"), want["attrs"])
            or type(editor.get("content")) is not list or len(editor["content"]) != len(want["content"])):
        raise ReadbackError("DOCUMENT_MISMATCH")
    blocks = document.get("blocks")
    if type(blocks) is not list or len(blocks) != len(want["content"]):
        raise ReadbackError("DOCUMENT_MISMATCH")
    seen = set()
    texts = []
    for index, (node, wanted, block) in enumerate(zip(editor["content"], want["content"], blocks)):
        if type(node) is not dict or set(node) != {"type", "content", "attrs"}:
            raise ReadbackError("DOCUMENT_MISMATCH")
        attributes = node.get("attrs")
        if type(attributes) is not dict or set(attributes) != {"block_id"}:
            raise ReadbackError("DOCUMENT_MISMATCH")
        block_id = attributes.get("block_id")
        if (type(block_id) is not str or not _BLOCK_ID.fullmatch(block_id) or block_id in seen
                or node.get("type") != wanted["type"] or not _same_json(node.get("content"), wanted["content"])):
            raise ReadbackError("DOCUMENT_MISMATCH")
        seen.add(block_id)
        text = wanted["content"][0]["text"]
        texts.append(text)
        if (type(block) is not dict or set(block) != {"block_id", "kind", "ordinal", "node_json", "text_projection", "codec_status"}
                or block.get("block_id") != block_id or block.get("kind") != "paragraph"
                or type(block.get("ordinal")) is not int or block["ordinal"] != index
                or not _same_json(block.get("node_json"), node) or block.get("text_projection") != text
                or block.get("codec_status") != "known"):
            raise ReadbackError("DOCUMENT_MISMATCH")
    if document.get("text_projection") != "\n".join(texts):
        raise ReadbackError("DOCUMENT_MISMATCH")
    return {"document_id": identity, "version": version, "content_sha256": digest}


def _view_matches(view, snapshot, material, question):
    fields = {"schema", "question_document", "question_status", "source_material", "source_snapshot_status",
              "source_reference", "question_document_origin", "authorization_effect", "question_version",
              "visible_sha256", "question", "origin", "provider_identity", "provider_executed", "independent_mastery"}
    visible = {key: question[key] for key in ("question_id", "question", "question_type", "options")}
    version = view.get("question_version")
    visible_sha = view.get("visible_sha256")
    if (set(view) != fields or view.get("schema") != "archeaxis.deeptutor-question-view/v1"
            or not _same_json(view.get("question_document"), snapshot) or not _same_json(view.get("source_material"), material)
            or type(view.get("question_status")) is not str or view["question_status"] not in {"current", "historical"}
            or type(view.get("source_snapshot_status")) is not str or view["source_snapshot_status"] not in {"current", "historical", "unavailable"}
            or view.get("source_reference") != "declared_unverified" or view.get("question_document_origin") != "unverified"
            or view.get("authorization_effect") != "none" or view.get("origin") != "user_import_unverified"
            or view.get("provider_identity") != "unverified" or view.get("provider_executed") is not False
            or view.get("independent_mastery") != "not_established" or not _same_json(view.get("question"), visible)
            or type(version) is not str or not version.startswith("sha256:") or not _SHA.fullmatch(version[7:])
            or type(visible_sha) is not str or not _SHA.fullmatch(visible_sha)):
        raise ReadbackError("VIEW_MISMATCH")
    return view["question_status"], view["source_snapshot_status"]


def reconcile(replay_request, original_response_bytes, material_snapshot, create_request_id, title,
              import_response, original_response, create_response, document_response, view_response):
    """Compare bounded, caller-provided (HTTP status, raw JSON bytes) responses.

    This function neither makes requests nor authenticates the caller or Core.
    The specified document read must be for the version in the create response.
    """
    return _reconcile(replay_request, original_response_bytes, material_snapshot, create_request_id, title,
                      import_response, original_response, create_response, document_response, view_response, None)


def reconcile_recovered(replay_request, original_response_bytes, material_snapshot, create_request_id, title,
                        import_response, original_response, create_response, document_response, view_response,
                        *, completed, finish_reason, tool_calls, function_call, allow_recovery=False):
    """Rebuild an opt-in label recovery and compare caller-supplied readbacks.

    The source bytes must include the label. Parser fallback is never enabled.
    This does not authenticate the responses, terminal state or Core.
    """
    declaration = {"completed": completed, "finish_reason": finish_reason, "tool_calls": tool_calls,
                   "function_call": function_call, "allow_recovery": allow_recovery}
    return _reconcile(replay_request, original_response_bytes, material_snapshot, create_request_id, title,
                      import_response, original_response, create_response, document_response, view_response, declaration)


def _reconcile(replay_request, original_response_bytes, material_snapshot, create_request_id, title,
               import_response, original_response, create_response, document_response, view_response, declaration):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise ReadbackError("ACTIVE_EVENT_LOOP_UNSUPPORTED")
    claimed_import = _response(import_response, 202, 4096, "IMPORT_UNAVAILABLE")
    original = _response(original_response, 200, _MAX_SOURCE_JSON, "SOURCE_UNAVAILABLE")
    created = _response(create_response, 201, _MAX_DOCUMENT_JSON, "DOCUMENT_CREATE_UNAVAILABLE")
    document = _response(document_response, 200, _MAX_DOCUMENT_JSON, "DOCUMENT_READ_UNAVAILABLE")
    view = _response(view_response, 200, _MAX_VIEW_JSON, "VIEW_UNAVAILABLE")
    if type(original_response_bytes) is not bytes or len(original_response_bytes) > 180_000:
        raise ReadbackError("INVALID_INPUT")
    _source_matches(claimed_import, original, original_response_bytes)
    try:
        adapter = _candidate_adapter()
        if declaration is None:
            candidate = adapter["prepare_candidate"](replay_request, original_response_bytes,
                material_snapshot, create_request_id, title)
        else:
            candidate = adapter["prepare_recovered_candidate"](replay_request, original_response_bytes,
                material_snapshot, create_request_id, title, **declaration)
        expected = candidate.document_create_request(claimed_import)
    except ReadbackError:
        raise
    except Exception:
        raise ReadbackError("CANDIDATE_UNAVAILABLE") from None
    created_snapshot = _document_matches(created, expected)
    snapshot = _document_matches(document, expected)
    if not _same_json(created_snapshot, snapshot) or not _same_json(created.get("editor_json"), document.get("editor_json")):
        raise ReadbackError("DOCUMENT_MISMATCH")
    metadata = expected["editor_json"]["attrs"]["archeaxis_deeptutor_question"]
    question_status, source_status = _view_matches(view, snapshot, metadata["source_material"], metadata["question"])
    result = {"schema": "archeaxis.deeptutor-candidate-readback-comparison/v1",
            "status": "CALLER_SUPPLIED_READBACKS_MATCH_LOCAL_EXPECTATIONS",
            "question_status": question_status, "source_snapshot_status": source_status,
            "response_identity": "CALLER_SUPPLIED_UNAUTHENTICATED",
            "core_authentication": "NOT_ESTABLISHED", "core_authorization": "NOT_ESTABLISHED",
            "provider_generation": "NOT_ESTABLISHED", "independent_mastery": "NOT_ESTABLISHED",
            "raw_response_comparison": "EXACT_BYTES_AND_SHA256",
            "candidate_and_body_comparison": "MATCHED_IN_SUPPLIED_READBACKS",
            "document_content_sha256": "FORMAT_AND_REFERENCE_ONLY_NOT_RECOMPUTED",
            "view_digests": "FORMAT_ONLY_NOT_RECOMPUTED", "block_id": "FORMAT_ONLY_NOT_RECOMPUTED",
            "future_currentness": "NOT_ESTABLISHED", "restart_durability": "NOT_ESTABLISHED",
            "new_provider_execution": "NOT_AUTHORIZED", "privacy_filter": "NOT_APPLIED",
            "logging_safety": "NOT_ESTABLISHED"}
    if declaration is not None:
        result.update({"label_recovery": "OPT_IN_UPSTREAM_RESEARCH_HELPER_SUBSET",
                       "parser_path": "ORIGINAL_MODEL_TEXT_PARSER",
                       "completion_and_tools": "CALLER_DECLARED_UNVERIFIED",
                       "recovery_policy_persistence": "NOT_ESTABLISHED_BY_COMPARISON"})
    return result
