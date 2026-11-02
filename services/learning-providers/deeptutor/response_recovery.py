"""Unregistered, offline DeepTutor final-response recovery candidate.

The exact caller-supplied content and the private result may contain answers or
other sensitive material.  They remain in process memory unless the caller
explicitly retrieves and persists them; neither this module nor its digests are
an access-control, confidentiality, provider-origin, or Core authorization
boundary.  No model, network, database, tool, or agentic loop is invoked.
"""
from __future__ import annotations

import __future__
import ast
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from types import SimpleNamespace


ROOT = Path(__file__).absolute().parent
UPSTREAM = ROOT / "upstream"
SCHEMA = "archeaxis.deeptutor-final-response-recovery/v1"
MAX_CONTENT_BYTES = 180_000
MAX_PRIVATE_RECEIPT_BYTES = 512 * 1024
MAX_JSON_NODES = 50_000
MAX_JSON_DEPTH = 32
QUESTION_TYPES = frozenset({"choice", "concept", "fill_in_blank", "short_answer", "written", "coding"})
PINS = {
    "agentic_labels.py": (UPSTREAM / "agentic_labels.py", 7_559,
                          "5b72f0efb922741b8dde7c9082c12778dfb21cf087c431d872d7f4c806705c05"),
    "question_turn_worker.py": (ROOT / "question_turn_worker.py", 24_499,
                               "e77a572778a1738195684dcaa672c7e68afc316a8ac7e6312f9ae4eb6f958570"),
    "question_normalizer.py": (ROOT / "question_normalizer.py", 15_801,
                              "dc60e865e27bb9316dce09bf94ec55a0420503acd2aa31c577557693a81a92a3"),
}
PIPELINE_SHA256 = "b0e11748806225b286cff92a2dbf2f5722aa4538c8dc42138fa81def42cc392f"
_ALLOWED_LABELS = ("THINK", "TOOL", "FINISH")
_RECOVERY_FIRST_LINE = re.compile(r"\A`{1,3}FINISH`{0,3}\r?\n")
_JSON_STRING_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"')
_UPSTREAM_FENCE_PATTERN = r"```(?:json)?\s*(.*?)```"
_ISSUED = object()


class RecoveryError(ValueError):
    """A fixed error code; never contains caller text or answer values."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _source(name):
    """Bound fixed sources and reject observed links and identity changes."""
    if name not in PINS:
        raise RecoveryError("SOURCE_UNAVAILABLE")
    path, size, expected_sha = PINS[name]
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise RecoveryError("SOURCE_UNAVAILABLE")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise RecoveryError("SOURCE_UNAVAILABLE")
            before.append(info)
        expected = before[-1]
        if (not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1
                or expected.st_size != size or not expected.st_ino):
            raise RecoveryError("SOURCE_UNAVAILABLE")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino, opened.st_size) != (expected.st_dev, expected.st_ino, size)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1):
                raise RecoveryError("SOURCE_UNAVAILABLE")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise RecoveryError("SOURCE_UNAVAILABLE")
            data = bytearray()
            while len(data) <= size:
                chunk = os.read(fd, size + 1 - len(data))
                if not chunk:
                    break
                data.extend(chunk)
            after = os.fstat(fd)
            if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink)
                    != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, 1)):
                raise RecoveryError("SOURCE_UNAVAILABLE")
        finally:
            os.close(fd)
    except OSError:
        raise RecoveryError("SOURCE_UNAVAILABLE") from None
    raw = bytes(data)
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise RecoveryError("SOURCE_UNAVAILABLE")
    return raw


def _one(nodes, predicate):
    found = [node for node in nodes if predicate(node)]
    if len(found) != 1:
        raise RecoveryError("SOURCE_UNAVAILABLE")
    return found[0]


def _audit(nodes):
    for definition in nodes:
        for node in ast.walk(definition):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
                raise RecoveryError("SOURCE_UNAVAILABLE")
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in {"eval", "exec", "open", "__import__", "compile"}):
                raise RecoveryError("SOURCE_UNAVAILABLE")


def _labels():
    """Load exact original labels and recovery without upstream module imports."""
    try:
        tree = ast.parse(_source("agentic_labels.py"), filename="deeptutor-1.7.1/runtime/agentic/labels.py")
        selected = []
        for name in ("_INVISIBLE_PREFIX_CHARS", "_LABEL_SEPARATOR_CHARS"):
            node = _one(tree.body, lambda n: isinstance(n, ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
            if type(ast.literal_eval(node.value)) is not str:
                raise RecoveryError("SOURCE_UNAVAILABLE")
            selected.append(node)
        for name in ("strip_label_probe_prefix", "classify_label", "recover_finished_label", "find_inline_labels"):
            node = _one(tree.body, lambda n: isinstance(n, ast.FunctionDef) and n.name == name and not n.decorator_list)
            selected.append(node)
        _audit(selected)
        module = ast.Module(body=selected, type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {"__name__": "deeptutor_171_labels_subset", "re": re,
                     "__builtins__": {"str": str, "len": len, "tuple": tuple, "list": list}}
        exec(compile(module, "deeptutor-1.7.1/runtime/agentic/labels.py", "exec",
                     flags=__future__.annotations.compiler_flag, dont_inherit=True), namespace)  # noqa: S102
        return namespace
    except RecoveryError:
        raise
    except Exception:
        raise RecoveryError("SOURCE_UNAVAILABLE") from None


def _turn_validator():
    """Reuse only the existing strict response validator, not its loop/model."""
    try:
        tree = ast.parse(_source("question_turn_worker.py"), filename="question_turn_worker.py")
        selected = []
        for name in ("InvalidRequest", "InvalidResponse"):
            node = _one(tree.body, lambda n: isinstance(n, ast.ClassDef) and n.name == name and not n.decorator_list)
            selected.append(node)
        for name in ("_unique", "_nonfinite", "_text", "_strict_response"):
            node = _one(tree.body, lambda n: isinstance(n, ast.FunctionDef) and n.name == name and not n.decorator_list)
            selected.append(node)
        _audit(selected)
        module = ast.Module(body=selected, type_ignores=[])
        ast.fix_missing_locations(module)
        builtins = {"__build_class__": __build_class__, "ValueError": ValueError, "TypeError": TypeError,
                    "UnicodeError": UnicodeError, "RecursionError": RecursionError, "str": str,
                    "len": len, "dict": dict, "set": set, "isinstance": isinstance}
        namespace = {"__name__": "deeptutor_existing_strict_validator", "__builtins__": builtins,
                     "json": json, "re": re}
        exec(compile(module, "question_turn_worker.py", "exec",
                     flags=__future__.annotations.compiler_flag, dont_inherit=True), namespace)  # noqa: S102
        return namespace["_strict_response"]
    except RecoveryError:
        raise
    except Exception:
        raise RecoveryError("SOURCE_UNAVAILABLE") from None


def _normalizer():
    """Fresh namespace; its existing adapter verifies the original pipeline."""
    try:
        source = _source("question_normalizer.py")
        namespace = {"__name__": "deeptutor_existing_private_normalizer", "__file__": str(PINS["question_normalizer.py"][0])}
        exec(compile(source, str(PINS["question_normalizer.py"][0]), "exec"), namespace)  # noqa: S102
        if namespace.get("UPSTREAM_SHA256") != PIPELINE_SHA256:
            raise RecoveryError("SOURCE_UNAVAILABLE")
        return namespace
    except RecoveryError:
        raise
    except Exception:
        raise RecoveryError("SOURCE_UNAVAILABLE") from None


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate")
        value[key] = item
    return value


def _finite(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite")
    return result


def _nonfinite(_value):
    raise ValueError("nonfinite")


def _strict_json(raw):
    try:
        value = json.loads(raw, object_pairs_hook=_unique, parse_float=_finite, parse_constant=_nonfinite)
        stack = [(value, 0)]
        seen = 0
        while stack:
            item, depth = stack.pop()
            seen += 1
            if seen > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
                raise ValueError("structure")
            if type(item) is dict:
                stack.extend((child, depth + 1) for child in item.values())
            elif type(item) is list:
                stack.extend((child, depth + 1) for child in item)
        if type(value) is not dict:
            raise ValueError("object")
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise RecoveryError("INVALID_JSON") from None


def _changes(parsed, normalized):
    """Only fixed field paths, never values, describe known normalization."""
    changes = []
    for field in ("question_type", "question", "correct_answer", "explanation"):
        if parsed[field] != normalized[field]:
            changes.append({"field": field, "change": "upstream_normalized"})
    if "options" not in parsed:
        changes.append({"field": "options", "change": "absent_to_null"})
    elif type(parsed["options"]) is dict and type(normalized["options"]) is dict:
        for key in sorted(parsed["options"].keys() | normalized["options"].keys()):
            if parsed["options"].get(key) != normalized["options"].get(key):
                changes.append({"field": "options." + key, "change": "upstream_normalized"})
    elif parsed["options"] != normalized["options"]:
        changes.append({"field": "options", "change": "upstream_normalized"})
    return changes


def _same_json(left, right):
    """Compare JSON values without Python's bool/int equality shortcuts."""
    try:
        options = {"ensure_ascii": False, "sort_keys": True, "separators": (",", ":"), "allow_nan": False}
        return json.dumps(left, **options) == json.dumps(right, **options)
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise RecoveryError("PARSER_COMPARISON_UNAVAILABLE") from None


def _first_upstream_fence_in_one_string(body, parser):
    """Prove the original parser's first fence match stays in one JSON token."""
    constants = [item for item in parser.__code__.co_consts if type(item) is str and item.startswith("```")]
    if constants != [_UPSTREAM_FENCE_PATTERN]:
        raise RecoveryError("SOURCE_UNAVAILABLE")
    fence = re.search(constants[0], body, re.DOTALL)
    if fence is None:
        return False
    # The caller must first have strictly parsed the entire JSON object.  Thus
    # this tokenizer only locates its original string boundaries; it does not
    # repair or accept malformed JSON.  Escaped quotes/backslashes stay inside
    # their own token, and both match endpoints must be in its content region.
    return any(token.start() + 1 <= fence.start() and fence.end() <= token.end() - 1
               for token in _JSON_STRING_TOKEN.finditer(body))


class PrivateRecovery:
    """Private getters expose original content and possibly an answer key."""

    __slots__ = ("_raw", "_offset", "_report_json", "_receipt_json")

    def __init__(self, raw, offset, report, receipt_json, *, _issued=None):
        if _issued is not _ISSUED:
            raise RecoveryError("RESULT_NOT_PREPARED")
        object.__setattr__(self, "_raw", raw)
        object.__setattr__(self, "_offset", offset)
        object.__setattr__(self, "_report_json", json.dumps(report, ensure_ascii=True, allow_nan=False))
        object.__setattr__(self, "_receipt_json", receipt_json)

    def __setattr__(self, _name, _value):
        raise AttributeError("prepared recovery is immutable")

    def __repr__(self):
        return "<PrivateRecovery: contents withheld>"

    def report(self):
        """Metadata only; it is not authorization or a privacy guarantee."""
        return json.loads(self._report_json)

    def original_bytes(self):
        """Return exact caller-supplied content; it may contain private data."""
        return self._raw

    def body_bytes(self):
        """Return the exact suffix after the selected protocol label."""
        return self._raw[self._offset:]

    def removed_prefix_bytes(self):
        """Return the exact prefix removed for inspection of the final body."""
        return self._raw[:self._offset]

    def private_receipt(self):
        """Explicit private export, including raw content and answer key."""
        return json.loads(self._receipt_json)


def prepare_response(content_bytes, question_type, *, completed, finish_reason, tool_calls, function_call,
                     allow_recovery=False, allow_parser_fallback=False):
    """Validate a caller-declared final response; recovery is opt-in only.

    ``content_bytes`` are only the content supplied here, not a complete HTTP
    response or proof of what any provider produced.  The caller's completion
    and tool declarations cannot be authenticated by this function.
    """
    if (type(content_bytes) is not bytes or not content_bytes or len(content_bytes) > MAX_CONTENT_BYTES
            or type(question_type) is not str or question_type not in QUESTION_TYPES
            or type(completed) is not bool or completed is not True
            or type(finish_reason) is not str or finish_reason != "stop"
            or not (tool_calls is None or (type(tool_calls) is list and not tool_calls))
            or function_call is not None or type(allow_recovery) is not bool
            or type(allow_parser_fallback) is not bool):
        raise RecoveryError("INVALID_INPUT_OR_TERMINAL")
    try:
        content = content_bytes.decode("utf-8", "strict")
    except UnicodeError:
        raise RecoveryError("INVALID_INPUT_OR_TERMINAL") from None
    if "\x00" in content:
        raise RecoveryError("INVALID_INPUT_OR_TERMINAL")

    labels = _labels()
    try:
        selected = labels["classify_label"](content, allowed_labels=_ALLOWED_LABELS, final=True)
        recovered = False
        recovery_header_end = None
        if selected is None:
            if not allow_recovery:
                raise RecoveryError("RECOVERY_DISABLED")
            # This intentionally narrower subset avoids inventing an action
            # label from prefaces, cross-line fences, or arbitrary punctuation.
            match = _RECOVERY_FIRST_LINE.match(content)
            if match is None:
                raise RecoveryError("RECOVERY_FORMAT_UNSUPPORTED")
            recovery_header_end = match.end()
            selected = labels["recover_finished_label"](content, allowed_labels=_ALLOWED_LABELS)
            if selected is None:
                raise RecoveryError("RECOVERY_FORMAT_UNSUPPORTED")
            recovered = True
        label, body = selected
        if label != "FINISH":
            raise RecoveryError("NON_FINAL_LABEL")
        if labels["find_inline_labels"](body, allowed_labels=_ALLOWED_LABELS):
            raise RecoveryError("MULTIPLE_LABELS")
        if not body or not content.endswith(body):
            raise RecoveryError("CONTENT_DELTA_UNAVAILABLE")
        prefix_text = content[:len(content) - len(body)]
        if (recovered and (len(prefix_text) < recovery_header_end
                or any(char not in " \t\r\n" for char in prefix_text[recovery_header_end:]))):
            raise RecoveryError("RECOVERY_FORMAT_UNSUPPORTED")
        prefix = prefix_text.encode("utf-8")
        body_bytes = body.encode("utf-8")
        if prefix + body_bytes != content_bytes:
            raise RecoveryError("CONTENT_DELTA_UNAVAILABLE")
        parsed = _strict_json(body)
        validate = _turn_validator()
        strict_parsed = validate(body, SimpleNamespace(question_type=question_type))
        if not _same_json(strict_parsed, parsed):
            raise RecoveryError("VALIDATION_MISMATCH")
        normalizer = _normalizer()
        functions = normalizer["_selected_functions"]()
        upstream_parsed = functions._parse_quiz_payload(body)
        if type(upstream_parsed) is not dict:
            raise RecoveryError("PARSER_UNAVAILABLE")
        if _same_json(upstream_parsed, parsed):
            candidate = normalizer["_candidate"]({"schema": normalizer["SCHEMA"], "request_id": "response_recovery",
                "input": {"kind": "model_text", "question_type": question_type, "text": body}})
            if (type(candidate) is not dict or candidate.get("status") != "CANDIDATE"
                    or candidate.get("request_id") != "response_recovery" or type(candidate.get("candidate")) is not dict):
                raise RecoveryError("QUESTION_REJECTED")
            normalized = candidate["candidate"]
            parser_path = "ORIGINAL_MODEL_TEXT_PARSER"
        else:
            if not allow_parser_fallback:
                raise RecoveryError("ORIGINAL_PARSER_MISMATCH")
            if not _first_upstream_fence_in_one_string(body, functions._parse_quiz_payload):
                raise RecoveryError("PARSER_MISMATCH_UNSUPPORTED")
            template = SimpleNamespace(question_type=question_type)
            normalized = functions._normalize_quiz_payload(template, parsed)
            issues = functions._collect_quiz_issues(template, normalized)
            if type(issues) is not list or issues:
                raise RecoveryError("QUESTION_REJECTED")
            parser_path = "OPT_IN_STRICT_OBJECT_NORMALIZATION"
        fields = {"question_type", "question", "correct_answer", "explanation", "options"}
        if type(normalized) is not dict or set(normalized) != fields:
            raise RecoveryError("VALIDATION_MISMATCH")
        # Bound every retained field to the same validated body and the exact
        # fixed original normalizer behavior for the supported strict inputs.
        if (normalized["question_type"] != question_type
                or normalized["question"] != parsed["question"].strip()
                or normalized["correct_answer"] != parsed["correct_answer"].strip()
                or normalized["explanation"] != parsed["explanation"].strip()):
            raise RecoveryError("VALIDATION_MISMATCH")
        if question_type == "choice":
            expected_options = {key: parsed["options"][key].strip() for key in ("A", "B", "C", "D")}
            if normalized["options"] != expected_options:
                raise RecoveryError("VALIDATION_MISMATCH")
        elif normalized["options"] is not None:
            raise RecoveryError("VALIDATION_MISMATCH")
        changes = _changes(parsed, normalized)
    except RecoveryError:
        raise
    except Exception:
        # Validators and JSON errors may contain caller-supplied values.
        raise RecoveryError("QUESTION_REJECTED_OR_UNAVAILABLE") from None

    report = {"schema": SCHEMA, "status": "PRIVATE_CANDIDATE", "strict_label": "NONE" if recovered else "FINISH",
              "recovery": "OPT_IN_UPSTREAM_RESEARCH_HELPER_SUBSET" if recovered else "NOT_NEEDED_STRICT_RAW_UNCHANGED",
              "parser_path": parser_path,
              "origin": "CALLER_SUPPLIED_UNVERIFIED", "completion_and_tools": "CALLER_DECLARED_UNVERIFIED",
              "agentic_loop": "NOT_INVOKED", "provider_generation": "NOT_ESTABLISHED",
              "model_call": "NOT_INVOKED", "tool_execution": "NOT_INVOKED", "core_authorization": "NOT_ESTABLISHED",
              "answer_correctness": "NOT_VERIFIED", "independent_mastery": "NOT_ESTABLISHED",
              "original_content": "THIS_ADAPTER_DOES_NOT_PERSIST", "caller_persistence": "NOT_ESTABLISHED",
              "provider_envelope": "NOT_SUPPLIED",
              "privacy_filter": "NOT_APPLIED", "logging_safety": "NOT_ESTABLISHED"}
    receipt = {**report, "content_base64": base64.b64encode(content_bytes).decode("ascii"),
               "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
               "body_byte_offset": len(prefix), "body_sha256": hashlib.sha256(body_bytes).hexdigest(),
               "removed_prefix_base64": base64.b64encode(prefix).decode("ascii"),
               "normalization_changes": changes, "private_candidate": normalized,
               "source_sha256": {name: spec[2] for name, spec in PINS.items()},
               "upstream_pipeline_sha256": PIPELINE_SHA256,
               "digest_privacy": "UNSALTED_DIGEST_MAY_BE_GUESSABLE"}
    try:
        serialized = json.dumps(receipt, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > MAX_PRIVATE_RECEIPT_BYTES:
            raise RecoveryError("PRIVATE_RECEIPT_LIMIT")
    except RecoveryError:
        raise
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise RecoveryError("PRIVATE_RECEIPT_UNAVAILABLE") from None
    return PrivateRecovery(content_bytes, len(prefix), report, serialized, _issued=_ISSUED)
