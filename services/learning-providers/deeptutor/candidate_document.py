"""Private, offline preparation of an unverified DeepTutor question document.

The returned object contains an answer key and the exact caller-supplied final
response. It is not a display receipt, an authorization, or a Core write.
"""
from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat


_ROOT = Path(__file__).absolute().parent
_TURN_NAME = "question_turn_worker.py"
_TURN_SIZE = 24_499
_TURN_SHA256 = "e77a572778a1738195684dcaa672c7e68afc316a8ac7e6312f9ae4eb6f958570"
_RECOVERY_NAME = "response_recovery.py"
_RECOVERY_SIZE = 22_259
_RECOVERY_SHA256 = "4887e46b88a32b3145535840adf1e215f741b5c41f8b17d903a282c544f9f4fb"
_MAX_INPUT = 256 * 1024
_MAX_RESPONSE = 180_000
_TOKEN = re.compile(r"[A-Za-z0-9_-]+\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUED = object()


class CandidateError(ValueError):
    """A fixed reason code; never includes supplied text or answer values."""


def _read_pinned(which) -> bytes:
    """Read one fixed adapter, rejecting observed links and identity changes."""
    if which == "turn":
        name, size, digest = _TURN_NAME, _TURN_SIZE, _TURN_SHA256
    elif which == "recovery":
        name, size, digest = _RECOVERY_NAME, _RECOVERY_SIZE, _RECOVERY_SHA256
    else:
        raise CandidateError("SOURCE_UNAVAILABLE")
    path = _ROOT / name
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise CandidateError("SOURCE_UNAVAILABLE")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise CandidateError("SOURCE_UNAVAILABLE")
            before.append(info)
        expected = before[-1]
        if (not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1
                or expected.st_size != size or not expected.st_ino):
            raise CandidateError("SOURCE_UNAVAILABLE")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != size):
                raise CandidateError("SOURCE_UNAVAILABLE")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise CandidateError("SOURCE_UNAVAILABLE")
            chunks = []
            remaining = size + 1
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
                raise CandidateError("SOURCE_UNAVAILABLE")
        finally:
            os.close(fd)
    except OSError:
        raise CandidateError("SOURCE_UNAVAILABLE") from None
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise CandidateError("SOURCE_UNAVAILABLE")
    return data


def _read_turn() -> bytes:
    return _read_pinned("turn")


def _clone_request(value):
    """Copy a bounded JSON tree without retaining caller-owned mutable data."""
    stack = [(value, 0)]
    nodes = 0
    text_bytes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > 1_000 or depth > 32:
            raise CandidateError("INVALID_INPUT")
        if isinstance(item, str):
            if len(item) > _MAX_INPUT:
                raise CandidateError("INVALID_INPUT")
            try:
                text_bytes += len(item.encode("utf-8"))
            except UnicodeError:
                raise CandidateError("INVALID_INPUT") from None
            if text_bytes > _MAX_INPUT:
                raise CandidateError("INVALID_INPUT")
        elif type(item) is dict:
            if len(item) > 1_000 or any(type(key) is not str for key in item):
                raise CandidateError("INVALID_INPUT")
            stack.extend((entry, depth + 1) for pair in item.items() for entry in pair)
        elif type(item) is list:
            if len(item) > 1_000:
                raise CandidateError("INVALID_INPUT")
            stack.extend((entry, depth + 1) for entry in item)
        elif item is None or type(item) is bool:
            pass
        elif type(item) is int and item.bit_length() <= 53:
            pass
        else:
            raise CandidateError("INVALID_INPUT")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > _MAX_INPUT:
            raise CandidateError("INVALID_INPUT")
        return json.loads(encoded)
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise CandidateError("INVALID_INPUT") from None


def _snapshot(value):
    if type(value) is not dict or set(value) != {"document_id", "version", "content_sha256"}:
        raise CandidateError("INVALID_MATERIAL_SNAPSHOT")
    identity, version, digest = value["document_id"], value["version"], value["content_sha256"]
    if (type(identity) is not str or not 1 <= len(identity) <= 128 or not _TOKEN.fullmatch(identity)
            or type(version) is not int or not 1 <= version <= 9_007_199_254_740_991
            or type(digest) is not str or not _SHA.fullmatch(digest)):
        raise CandidateError("INVALID_MATERIAL_SNAPSHOT")
    return {"document_id": identity, "version": version, "content_sha256": digest}


def _load_adapter(source: bytes, name: str, path: Path):
    namespace = {"__name__": name, "__file__": str(path)}
    exec(compile(source, str(path), "exec"), namespace)  # noqa: S102 -- exact pinned local adapter
    return namespace


def _normalizer(turn):
    source = turn["_source"]("question_normalizer.py")
    return _load_adapter(source, "deeptutor_private_normalizer", _ROOT / "question_normalizer.py")


def _changes(parsed, normalized):
    """Record compared field paths only, not their potentially private values."""
    changes = []
    for field in ("question_type", "question", "correct_answer", "explanation"):
        if parsed[field] != normalized[field]:
            changes.append({"field": field, "change": "upstream_normalized"})
    if "options" not in parsed:
        changes.append({"field": "options", "change": "absent_to_null"})
    elif isinstance(parsed["options"], dict) and isinstance(normalized["options"], dict):
        for key in sorted(parsed["options"].keys() | normalized["options"].keys()):
            if parsed["options"].get(key) != normalized["options"].get(key):
                changes.append({"field": "options." + key, "change": "upstream_normalized"})
    elif parsed["options"] != normalized["options"]:
        changes.append({"field": "options", "change": "upstream_normalized"})
    if normalized["options"] is None:
        changes.append({"field": "options", "change": "null_to_empty_object_for_core"})
    return changes


class PrivateCandidate:
    """Explicit private getters may reveal answers; never log this object or getters."""

    __slots__ = ("_raw", "_candidate_json", "_material_json", "_create_request_id", "_title", "_report_json",
                 "_source_name", "_recovery_receipt_json")

    def __init__(self, raw, candidate, material, create_request_id, title, report, *,
                 source_name="deeptutor-question-response.json", recovery_receipt=None, _issued=None):
        if _issued is not _ISSUED:
            raise CandidateError("CANDIDATE_NOT_PREPARED")
        object.__setattr__(self, "_raw", raw)
        object.__setattr__(self, "_candidate_json", json.dumps(candidate, ensure_ascii=False, allow_nan=False))
        object.__setattr__(self, "_material_json", json.dumps(material, ensure_ascii=False, allow_nan=False))
        object.__setattr__(self, "_create_request_id", create_request_id)
        object.__setattr__(self, "_title", title)
        object.__setattr__(self, "_report_json", json.dumps(report, ensure_ascii=False, allow_nan=False))
        object.__setattr__(self, "_source_name", source_name)
        object.__setattr__(self, "_recovery_receipt_json", None if recovery_receipt is None else
                           json.dumps(recovery_receipt, ensure_ascii=False, allow_nan=False))

    def __setattr__(self, _name, _value):
        raise AttributeError("prepared candidate is immutable")

    def __repr__(self):
        return "<PrivateCandidate: contents withheld>"

    def report(self):
        """Return conversion metadata; it is not a privacy or secrecy boundary."""
        return json.loads(self._report_json)

    def original_response_bytes(self):
        """Return the exact private caller-supplied response bytes."""
        return self._raw

    def raw_import_request(self):
        """Construct, but do not send, the Core source-import body."""
        return {"name": self._source_name,
                "content_base64": base64.b64encode(self._raw).decode("ascii")}

    def private_recovery_receipt(self):
        """Return the private recovery receipt, if this candidate used recovery.

        It includes the exact original content and answer; this module does not
        persist or authenticate it. The return value is a fresh mutable copy.
        """
        return None if self._recovery_receipt_json is None else json.loads(self._recovery_receipt_json)

    def document_create_request(self, claimed_import_receipt):
        """Construct a Core document request from a caller-declared import receipt.

        Digest equality does not establish that Core has received or stored it.
        Core must independently validate the source ID and its CAS content.
        """
        receipt = claimed_import_receipt
        if type(receipt) is not dict or set(receipt) != {"source_id", "sha256", "duplicate"}:
            raise CandidateError("INVALID_IMPORT_RECEIPT")
        source_id, sha = receipt["source_id"], receipt["sha256"]
        try:
            source_size = len(source_id.encode("utf-8")) if type(source_id) is str else 0
        except UnicodeError:
            raise CandidateError("INVALID_IMPORT_RECEIPT") from None
        if (type(source_id) is not str or not source_id or source_size > 128
                or "\x00" in source_id or type(sha) is not str or not _SHA.fullmatch(sha)
                or type(receipt["duplicate"]) is not bool
                or sha != hashlib.sha256(self._raw).hexdigest()):
            raise CandidateError("INVALID_IMPORT_RECEIPT")
        question = json.loads(self._candidate_json)
        texts = [question["question"]]
        texts.extend(f"{key}. {question['options'][key]}" for key in sorted(question["options"]))
        content = [{"type": "paragraph", "content": [{"type": "text", "text": text}]} for text in texts]
        editor = {"type": "doc", "content": content, "attrs": {"archeaxis_deeptutor_question": {
            "schema": "archeaxis.deeptutor-question/v1", "source_material": json.loads(self._material_json),
            "origin": "user_import_unverified", "question": question}}}
        return {"create_request_id": self._create_request_id, "source_id": source_id,
                "source_revision": sha, "title": self._title, "editor_json": editor}


def prepare_candidate(replay_request, original_response_bytes, material_snapshot, create_request_id, title):
    """Re-run the pinned question turn and privately construct its Core candidate.

    Both the request and source identity are caller declarations. There is no
    network, model, SQLite, provider authority or persistent write here.
    """
    request = _clone_request(replay_request)
    material = _snapshot(material_snapshot)
    if (type(original_response_bytes) is not bytes or not original_response_bytes
            or len(original_response_bytes) > _MAX_RESPONSE
            or type(create_request_id) is not str or not 1 <= len(create_request_id) <= 128
            or not _TOKEN.fullmatch(create_request_id) or type(title) is not str):
        raise CandidateError("INVALID_INPUT")
    try:
        raw_text = original_response_bytes.decode("utf-8")
        title_size = len(title.encode("utf-8"))
    except UnicodeError:
        raise CandidateError("INVALID_INPUT") from None
    if title_size > 1024 or "\x00" in title or type(request) is not dict or request.get("mode") != "replay":
        raise CandidateError("INVALID_INPUT")
    if request.get("response_body") != raw_text:
        raise CandidateError("RESPONSE_BYTES_MISMATCH")
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # question-turn uses asyncio.run; fail before constructing a coroutine.
        raise CandidateError("ACTIVE_EVENT_LOOP_UNSUPPORTED")

    try:
        turn = _load_adapter(_read_turn(), "deeptutor_private_question_turn", _ROOT / _TURN_NAME)
        request_id, plan, number, _, _ = turn["_request"](request)
        template = plan.templates[number - 1]
        # Every invocation owns a freshly compiled module namespace and class.
        # This captures the original private pair before the worker projects it.
        factory = turn["_question_class"]
        captured = []

        def capture_factory(loop):
            cls, language = factory(loop)
            original = cls._payload_to_qa_pair

            def capture_pair(instance, *args, **kwargs):
                pair = original(instance, *args, **kwargs)
                captured.append(pair)
                return pair

            cls._payload_to_qa_pair = capture_pair
            return cls, language

        turn["_question_class"] = capture_factory
        receipt = turn["process"](request)
        if (len(captured) != 1 or receipt.get("status") != "CANDIDATE"
                or receipt.get("request_id") != request_id or receipt.get("mode") != "replay"):
            raise CandidateError("TURN_RESULT_MISMATCH")
        pair = captured[0]
        if getattr(pair, "question_id", None) != template.question_id or getattr(pair, "metadata", {}).get("issues"):
            raise CandidateError("TURN_RESULT_MISMATCH")
        normalizer = _normalizer(turn)
        private = normalizer["_candidate"]({"schema": normalizer["SCHEMA"], "request_id": request_id,
            "input": {"kind": "model_text", "question_type": template.question_type, "text": raw_text}})
        if private.get("status") != "CANDIDATE" or private.get("request_id") != request_id:
            raise CandidateError("NORMALIZATION_MISMATCH")
        normalized = private["candidate"]
        fields = ("question_type", "question", "options", "correct_answer", "explanation")
        if (type(normalized) is not dict or set(normalized) != set(fields)
                or any(getattr(pair, field, object()) != normalized[field] for field in fields)):
            raise CandidateError("NORMALIZATION_MISMATCH")
        visible = {"question_id": template.question_id, "question": normalized["question"],
                   "question_type": normalized["question_type"], "options": normalized["options"]}
        if receipt.get("question") != visible:
            raise CandidateError("TURN_RESULT_MISMATCH")
        parsed = turn["_strict_response"](raw_text, template)
    except CandidateError:
        raise
    except Exception:
        # Never return exception details: they may contain caller material.
        raise CandidateError("TURN_UNAVAILABLE_OR_REJECTED") from None

    changes = _changes(parsed, normalized)
    if isinstance(normalized["options"], dict) and list(normalized["options"]) != sorted(normalized["options"]):
        changes.append({"field": "options", "change": "body_projection_sorted_by_key"})
    question = {"question_id": template.question_id, "question": normalized["question"],
                "question_type": normalized["question_type"],
                "options": copy.deepcopy(normalized["options"]) if normalized["options"] is not None else {},
                "correct_answer": normalized["correct_answer"], "explanation": normalized["explanation"]}
    report = {"schema": "archeaxis.deeptutor-candidate-preparation/v1",
              "status": "PRIVATE_CANDIDATE_PREPARED", "origin": "CALLER_SUPPLIED_UNVERIFIED",
              "material_snapshot": "CALLER_DECLARED_UNVERIFIED", "core_authorization": "NOT_ESTABLISHED",
              "model_call": "NOT_INVOKED", "provider_generation": "NOT_ESTABLISHED",
              "independent_mastery": "NOT_ESTABLISHED", "original_response_bytes": "IN_MEMORY_ONLY",
              "original_replay_envelope_bytes": "NOT_SUPPLIED", "core_source_import": "NOT_EXECUTED",
              "core_document_write": "NOT_EXECUTED", "conversion_report_persisted": False,
              "source_and_document_calls": "SEPARATE_DOCUMENT_FAILURE_MAY_LEAVE_SOURCE",
              "request_binding": "AT_CONSTRUCTION_ONLY_MUTABLE_AFTER_RETURN_NOT_VERIFIED_BY_CORE",
              "body_projection": "QUESTION_THEN_OPTIONS_ASCII_KEY_ORDER_INITIAL_ONLY",
              "body_attrs_consistency": "NOT_CONTINUOUSLY_ENFORCED_BY_CORE",
              "invocation": "SYNCHRONOUS_REQUIRES_NO_RUNNING_EVENT_LOOP",
              "unmapped_response_fields": [],
              "response_field_scope": "STRICT_FINAL_JSON_FIELDS_ONLY_UNKNOWN_FIELDS_REJECTED",
              "replay_context_in_document": "NOT_PRESERVED", "changes": changes,
              "grading": "UNASSESSED_EMPTY_OPTIONS_UNGRADED" if normalized["options"] is None else "NOT_ASSESSED",
              "privacy_filter": "NOT_APPLIED", "logging_safety": "NOT_ESTABLISHED"}
    return PrivateCandidate(original_response_bytes, question, material, create_request_id, title, report, _issued=_ISSUED)


def prepare_recovered_candidate(replay_request, original_response_bytes, material_snapshot, create_request_id, title,
                                *, completed, finish_reason, tool_calls, function_call, allow_recovery=False):
    """Prepare only an opt-in label-recovered response using the original parser.

    The complete labeled content is the source. Recovery and the existing
    question-turn replay are independently run again on each call. Terminal and
    tool state are caller declarations; no provider, Core or storage is used.
    """
    if allow_recovery is not True:
        raise CandidateError("RECOVERY_NOT_ENABLED")
    if (completed is not True or type(finish_reason) is not str or finish_reason != "stop"
            or not (tool_calls is None or (type(tool_calls) is list and not tool_calls))
            or function_call is not None):
        raise CandidateError("INVALID_TERMINAL_DECLARATION")
    # Capture the only accepted list value, so the helper never retains a
    # caller-owned mutable tool_calls list.
    selected_tools = None if tool_calls is None else []
    request = _clone_request(replay_request)
    try:
        turn = _load_adapter(_read_turn(), "deeptutor_recovery_request_turn", _ROOT / _TURN_NAME)
        _, plan, number, _, _ = turn["_request"](request)
        question_type = plan.templates[number - 1].question_type
    except CandidateError:
        raise
    except Exception:
        raise CandidateError("TURN_UNAVAILABLE_OR_REJECTED") from None
    try:
        recovery = _load_adapter(_read_pinned("recovery"), "deeptutor_candidate_recovery", _ROOT / _RECOVERY_NAME)
        recovered = recovery["prepare_response"](original_response_bytes, question_type, completed=completed,
            finish_reason=finish_reason, tool_calls=selected_tools, function_call=function_call,
            allow_recovery=True, allow_parser_fallback=False)
        recovery_report = recovered.report()
        if (recovery_report.get("strict_label") != "NONE"
                or recovery_report.get("recovery") != "OPT_IN_UPSTREAM_RESEARCH_HELPER_SUBSET"
                or recovery_report.get("parser_path") != "ORIGINAL_MODEL_TEXT_PARSER"):
            raise CandidateError("RECOVERY_PATH_UNSUPPORTED")
        body, prefix = recovered.body_bytes(), recovered.removed_prefix_bytes()
        private_receipt = recovered.private_receipt()
        if (recovered.original_bytes() != original_response_bytes or not prefix
                or prefix + body != original_response_bytes
                or private_receipt.get("content_sha256") != hashlib.sha256(original_response_bytes).hexdigest()
                or private_receipt.get("body_sha256") != hashlib.sha256(body).hexdigest()
                or private_receipt.get("body_byte_offset") != len(prefix)
                or private_receipt.get("content_base64") != base64.b64encode(original_response_bytes).decode("ascii")
                or private_receipt.get("removed_prefix_base64") != base64.b64encode(prefix).decode("ascii")):
            raise CandidateError("RECOVERY_RESULT_MISMATCH")
    except CandidateError:
        raise
    except Exception:
        # The recovery adapter and its source checks may encounter private input.
        raise CandidateError("RECOVERY_UNAVAILABLE_OR_REJECTED") from None
    try:
        if request.get("response_body") != body.decode("utf-8", "strict"):
            raise CandidateError("RESPONSE_BYTES_MISMATCH")
    except UnicodeError:
        raise CandidateError("RECOVERY_RESULT_MISMATCH") from None

    # This is the unchanged, complete replay + independent normalizer path. It
    # expects the body bytes and does not receive a fabricated import receipt.
    prepared = prepare_candidate(request, body, material_snapshot, create_request_id, title)
    question = json.loads(prepared._candidate_json)
    normalized = private_receipt.get("private_candidate")
    fields = {"question_type", "question", "options", "correct_answer", "explanation"}
    if type(normalized) is not dict or set(normalized) != fields:
        raise CandidateError("RECOVERY_RESULT_MISMATCH")
    if (any(question[field] != normalized[field] for field in fields - {"options"})
            or question["options"] != ({} if normalized["options"] is None else normalized["options"])):
        raise CandidateError("RECOVERY_RESULT_MISMATCH")
    report = prepared.report()
    report.update({"original_response_bytes": "THIS_ADAPTER_DOES_NOT_PERSIST",
                   "source_bytes": "COMPLETE_LABELED_CALLER_CONTENT",
                   "label_recovery": "OPT_IN_UPSTREAM_RESEARCH_HELPER_SUBSET",
                   "parser_path": "ORIGINAL_MODEL_TEXT_PARSER",
                   "completion_and_tools": "CALLER_DECLARED_UNVERIFIED",
                   "recovery_receipt_persistence": "NOT_ESTABLISHED_BY_ADAPTER_OR_CORE"})
    return PrivateCandidate(original_response_bytes, question, json.loads(prepared._material_json),
        create_request_id, title, report, source_name="deeptutor-question-response.txt",
        recovery_receipt=private_receipt, _issued=_ISSUED)
