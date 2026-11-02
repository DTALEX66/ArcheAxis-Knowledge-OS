"""Offline, bounded reuse of selected DeepTutor 1.7.1 question functions.

The original module is never imported or executed as a whole. This adapter
checks its exact bytes, extracts a reviewed AST whitelist, and compiles only
those pure definitions in a restricted namespace. It does not run a model,
provider, tools or database. CLI output is a practice projection, not a secret
store or proof that a supplied result came from DeepTutor.
"""
from __future__ import annotations

import __future__
import ast
import hashlib
import json
import os
import re
import stat
import sys
from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace

SCHEMA = "archeaxis.deeptutor-question-normalize/v1"
UPSTREAM_SHA256 = "b0e11748806225b286cff92a2dbf2f5722aa4538c8dc42138fa81def42cc392f"
UPSTREAM_SIZE = 93_738
UPSTREAM_ROOT = Path(__file__).absolute().parent / "upstream"
UPSTREAM = UPSTREAM_ROOT / "question_pipeline.py"
MAX_INPUT_BYTES = 240_000
QUESTION_TYPES = frozenset({"choice", "concept", "fill_in_blank", "short_answer", "written", "coding"})


class InvalidRequest(ValueError):
    """Input is outside the bounded adapter contract."""


class UpstreamUnavailable(RuntimeError):
    """The fixed upstream definitions could not be verified or selected."""


def _one(nodes, predicate):
    matches = [node for node in nodes if predicate(node)]
    if len(matches) != 1:
        raise UpstreamUnavailable("upstream definition mismatch")
    return matches[0]


def _read_upstream():
    """Reject reparse ancestors before opening and compare the opened identity."""
    path = UPSTREAM.absolute()
    if path.parent != UPSTREAM_ROOT.absolute() or path.name != "question_pipeline.py":
        raise UpstreamUnavailable("upstream path mismatch")
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise UpstreamUnavailable("upstream link is not allowed")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise UpstreamUnavailable("upstream ancestor unavailable")
            before.append(info)
        expected = before[-1]
        if not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1 or expected.st_size != UPSTREAM_SIZE or not expected.st_ino:
            raise UpstreamUnavailable("upstream source unavailable")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino) or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise UpstreamUnavailable("upstream identity changed")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise UpstreamUnavailable("upstream ancestor changed")
            chunks = []
            remaining = UPSTREAM_SIZE + 1
            while remaining:
                chunk = os.read(fd, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            source = b"".join(chunks)
        finally:
            os.close(fd)
    except OSError as error:
        raise UpstreamUnavailable("upstream source unavailable") from error
    if len(source) != UPSTREAM_SIZE:
        raise UpstreamUnavailable("upstream source unavailable")
    return source


def _selected_functions():
    """Compile only the pinned pure definitions, with no upstream imports."""
    source = _read_upstream()
    if hashlib.sha256(source).hexdigest() != UPSTREAM_SHA256:
        raise UpstreamUnavailable("upstream source identity mismatch")
    try:
        tree = ast.parse(source, filename="deeptutor-1.7.1/question/pipeline.py")
    except (SyntaxError, ValueError, UnicodeError) as error:
        raise UpstreamUnavailable("upstream source invalid") from error

    question_type = _one(tree.body, lambda n: isinstance(n, ast.ClassDef) and n.name == "QuestionType")
    if question_type.decorator_list or len(question_type.bases) != 1 or not isinstance(question_type.bases[0], ast.Name) or question_type.bases[0].id != "StrEnum":
        raise UpstreamUnavailable("upstream enum mismatch")
    constants = []
    for name, expected in (("_CHOICE_KEYS", ("A", "B", "C", "D")), ("_FILL_IN_BLANK_TOKEN", "____")):
        node = _one(tree.body, lambda n: isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
        try:
            if ast.literal_eval(node.value) != expected:
                raise UpstreamUnavailable("upstream constant mismatch")
        except (ValueError, TypeError, SyntaxError) as error:
            raise UpstreamUnavailable("upstream constant mismatch") from error
        constants.append(node)
    concept = _one(tree.body, lambda n: isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == "_CONCEPT_ANSWERS")
    if (concept.simple != 1 or not isinstance(concept.annotation, ast.Subscript)
            or not isinstance(concept.annotation.value, ast.Name) or concept.annotation.value.id != "frozenset"
            or not isinstance(concept.annotation.slice, ast.Name) or concept.annotation.slice.id != "str"
            or not isinstance(concept.value, ast.Call) or not isinstance(concept.value.func, ast.Name)
            or concept.value.func.id != "frozenset" or len(concept.value.args) != 1 or concept.value.keywords):
        raise UpstreamUnavailable("upstream constant mismatch")
    try:
        if ast.literal_eval(concept.value.args[0]) != {"true", "false"}:
            raise UpstreamUnavailable("upstream constant mismatch")
    except (ValueError, TypeError, SyntaxError) as error:
        raise UpstreamUnavailable("upstream constant mismatch") from error
    constants.append(concept)
    pipeline = _one(tree.body, lambda n: isinstance(n, ast.ClassDef) and n.name == "QuestionPipeline")
    selected = []
    for name, decorator in (("_parse_quiz_payload", "staticmethod"), ("_normalize_quiz_payload", "classmethod"), ("_collect_quiz_issues", "classmethod")):
        method = _one(pipeline.body, lambda n: isinstance(n, ast.FunctionDef) and n.name == name)
        if len(method.decorator_list) != 1 or not isinstance(method.decorator_list[0], ast.Name) or method.decorator_list[0].id != decorator:
            raise UpstreamUnavailable("upstream method mismatch")
        selected.append(method)

    for definition in [question_type, *constants, *selected]:
        for node in ast.walk(definition):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
                raise UpstreamUnavailable("unexpected upstream operation")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "open", "__import__", "compile"}:
                raise UpstreamUnavailable("unexpected upstream operation")
    selected_class = ast.ClassDef(name="SelectedQuestionFunctions", bases=[], keywords=[], body=selected, decorator_list=[])
    module = ast.Module(body=[question_type, *constants, selected_class], type_ignores=[])
    ast.fix_missing_locations(module)
    builtins = {"__build_class__": __build_class__, "str": str, "dict": dict, "set": set,
                "frozenset": frozenset, "len": len, "isinstance": isinstance,
                "staticmethod": staticmethod, "classmethod": classmethod, "bool": bool}
    namespace = {"__name__": "deeptutor_171_question_subset", "__builtins__": builtins,
                 "StrEnum": StrEnum, "json": _StrictJson, "re": re}
    try:
        code = compile(module, "deeptutor-1.7.1/question/pipeline.py", "exec",
                       flags=__future__.annotations.compiler_flag, dont_inherit=True)
        exec(code, namespace)  # noqa: S102
        return namespace["SelectedQuestionFunctions"]
    except (NameError, TypeError, ValueError, KeyError) as error:
        raise UpstreamUnavailable("upstream subset unavailable") from error


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidRequest("duplicate JSON member")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise InvalidRequest("non-finite number")


class _StrictJson:
    """Keep the upstream parser, rejecting ambiguous JSON members/constants."""
    JSONDecodeError = json.JSONDecodeError

    @staticmethod
    def loads(raw):
        return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)

    @staticmethod
    def JSONDecoder():
        return json.JSONDecoder(object_pairs_hook=_unique_object, parse_constant=_invalid_constant)


def _text(value, maximum, *, required=False):
    if not isinstance(value, str) or "\x00" in value:
        raise InvalidRequest("invalid text")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise InvalidRequest("invalid text") from error
    if len(encoded) > maximum or (required and not value.strip()):
        raise InvalidRequest("text outside bounds")
    return value


def _input(value):
    if not isinstance(value, dict) or set(value) != {"schema", "request_id", "input"} or value["schema"] != SCHEMA:
        raise InvalidRequest("invalid request")
    request_id = _text(value["request_id"], 128, required=True)
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id) is None:
        raise InvalidRequest("invalid request identity")
    source = value["input"]
    if not isinstance(source, dict):
        raise InvalidRequest("invalid input")
    if source.get("kind") == "model_text" and set(source) == {"kind", "question_type", "text"}:
        return request_id, source["question_type"], _text(source["text"], MAX_INPUT_BYTES), None
    if source.get("kind") == "pipeline_result" and set(source) == {"kind", "result", "index"}:
        result, index = source["result"], source["index"]
        if not isinstance(result, dict) or type(index) is not int or index < 0:
            raise InvalidRequest("invalid upstream result")
        summary = result.get("summary")
        results = summary.get("results") if isinstance(summary, dict) else None
        if not isinstance(results, list) or len(results) > 32 or index >= len(results):
            raise InvalidRequest("invalid upstream result")
        item = results[index]
        if not isinstance(item, dict) or not isinstance(item.get("qa_pair"), dict) or not isinstance(item.get("metadata", {}), dict):
            raise InvalidRequest("invalid upstream result")
        issues = item.get("metadata", {}).get("issues", [])
        if not isinstance(issues, list):
            raise InvalidRequest("invalid upstream issues")
        return request_id, item["qa_pair"].get("question_type"), item["qa_pair"], issues
    raise InvalidRequest("unsupported input")


def _candidate(value):
    """Return a private candidate for a future Core-owned importer, never a receipt."""
    try:
        if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_INPUT_BYTES:
            raise InvalidRequest("request exceeds bounds")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as error:
        raise InvalidRequest("invalid request encoding") from error
    request_id, kind, raw, reported_issues = _input(value)
    if not isinstance(kind, str) or kind not in QUESTION_TYPES:
        raise InvalidRequest("unsupported question type")
    functions = _selected_functions()
    if reported_issues:
        return {"request_id": request_id, "status": "REJECTED", "issue_codes": ["upstream_reported_issues"]}
    try:
        payload = functions._parse_quiz_payload(raw) if isinstance(raw, str) else raw
    except (RecursionError, TypeError, ValueError) as error:
        raise InvalidRequest("invalid upstream payload") from error
    if not isinstance(payload, dict):
        raise InvalidRequest("invalid upstream payload")
    clean = {}
    for field, maximum in (("question", 128_000), ("correct_answer", 20_000), ("explanation", 128_000)):
        clean[field] = _text(payload.get(field, ""), maximum)
    options = payload.get("options")
    if options is not None:
        if not isinstance(options, dict) or len(options) > 64:
            raise InvalidRequest("invalid options")
        clean["options"] = {_text(k, 256, required=True): _text(v, 20_000) for k, v in options.items()}
    else:
        clean["options"] = None
    try:
        template = SimpleNamespace(question_type=kind)
        normalized = functions._normalize_quiz_payload(template, clean)
        issues = functions._collect_quiz_issues(template, normalized)
    except (NameError, TypeError, ValueError, AttributeError) as error:
        raise UpstreamUnavailable("upstream subset failed") from error
    if normalized["question"].startswith("[Generation failed]") or normalized["correct_answer"] == "N/A" or normalized["explanation"] == "N/A":
        issues = [*issues, "upstream_placeholder"]
    if issues:
        return {"request_id": request_id, "status": "REJECTED", "issue_codes": issues}
    return {"request_id": request_id, "status": "CANDIDATE", "candidate": normalized}


def process(value):
    """Return only the display fields; caller-provided source is unverified."""
    result = _candidate(value)
    output = {"schema": SCHEMA, "request_id": result["request_id"], "status": result["status"],
              "upstream_member_sha256": UPSTREAM_SHA256, "origin": "caller_declared_unverified",
              "provider_run": "NOT_INVOKED", "model_call": "NOT_INVOKED", "independent_mastery": "not_established",
              "projection_scope": "single_question_bounded", "original_input_preserved": False,
              "unselected_fields_preserved": False, "loss_receipt": "NOT_GENERATED"}
    if result["status"] == "REJECTED":
        output["issue_codes"] = result["issue_codes"]
    else:
        candidate = result["candidate"]
        output["question"] = {key: candidate[key] for key in ("question", "question_type", "options")}
    return output


def main():
    try:
        raw = sys.stdin.buffer.readline(MAX_INPUT_BYTES + 1)
        if not raw or len(raw) > MAX_INPUT_BYTES:
            raise InvalidRequest("empty or oversized input")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(InvalidRequest("non-finite number")))
        result = process(value)
        code = 0 if result["status"] == "CANDIDATE" else 2
    except (InvalidRequest, ValueError, UnicodeDecodeError, RecursionError):
        result = {"schema": SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}
        code = 2
    except (UpstreamUnavailable, OSError, SyntaxError, TypeError):
        result = {"schema": SCHEMA, "status": "UNAVAILABLE", "reason_code": "UPSTREAM_UNAVAILABLE"}
        code = 1
    # The worker protocol is UTF-8 regardless of the host's text console code page.
    wire = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(wire + b"\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
