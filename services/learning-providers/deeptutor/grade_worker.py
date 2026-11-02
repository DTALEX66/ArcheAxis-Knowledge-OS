"""Bounded, offline adapter for DeepTutor 1.7.1's unmodified practice grader.

One JSON request line produces one JSON response. This isolated worker neither
opens the product database nor requests material, credentials, or a model.
Core must separately own admission, cancellation and any persisted result.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

SCHEMA = "archeaxis.deeptutor-practice-grade/v1"
UPSTREAM_SHA256 = "fdfbaee6cd0fa2c0f31de9a792e220e6989434fc1f44359db3e6afc62cd2472f"
UPSTREAM_SIZE = 1_538
MAX_REQUEST_BYTES = 256 * 1024
MAX_ANSWER_BYTES = 20_000
MAX_OPTION_BYTES = 20_000
UPSTREAM_ROOT = Path(__file__).absolute().parent / "upstream"
UPSTREAM = UPSTREAM_ROOT / "answers.py"


class InvalidRequest(ValueError):
    """A request is outside the worker's finite input contract."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidRequest("duplicate JSON member")
        result[key] = value
    return result


def _bounded_text(value: object, maximum: int, *, empty: bool = True) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise InvalidRequest("invalid text")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise InvalidRequest("invalid UTF-8 text") from error
    if len(encoded) > maximum or (not empty and not value.strip()):
        raise InvalidRequest("text outside bounds")
    return value


def _read_upstream() -> bytes:
    """Bound the fixed source and reject observed links before opening it.

    The subsequent identity checks narrow replacement races; they are not a
    filesystem sandbox or a guarantee against every concurrent ancestor change.
    """
    path = UPSTREAM.absolute()
    if path.parent != UPSTREAM_ROOT.absolute() or path.name != "answers.py":
        raise RuntimeError("upstream practice grader path mismatch")
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise RuntimeError("upstream practice grader link is not allowed")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise RuntimeError("upstream practice grader ancestor unavailable")
            before.append(info)
        expected = before[-1]
        if (not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1
                or expected.st_size != UPSTREAM_SIZE or not expected.st_ino):
            raise RuntimeError("upstream practice grader source unavailable")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or opened.st_size != UPSTREAM_SIZE):
                raise RuntimeError("upstream practice grader identity changed")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise RuntimeError("upstream practice grader ancestor changed")
            source = bytearray()
            while len(source) <= UPSTREAM_SIZE:
                chunk = os.read(fd, UPSTREAM_SIZE + 1 - len(source))
                if not chunk:
                    break
                source.extend(chunk)
        finally:
            os.close(fd)
    except OSError as error:
        raise RuntimeError("upstream practice grader source unavailable") from error
    source = bytes(source)
    if len(source) != UPSTREAM_SIZE or hashlib.sha256(source).hexdigest() != UPSTREAM_SHA256:
        raise RuntimeError("upstream practice grader identity mismatch")
    return source


def _upstream_grader():
    """Execute only the fixed reviewed bytes, not an input-selected file."""
    source = _read_upstream()
    namespace: dict[str, object] = {"__name__": "deeptutor_171_practice_answers"}
    # The hash pins these bytes to the retained, inspected upstream module;
    # it is not a code-execution interface for worker requests.
    exec(compile(source, str(UPSTREAM), "exec"), namespace)  # noqa: S102
    grader = namespace.get("check_answer")
    if not callable(grader):
        raise RuntimeError("upstream practice grader unavailable")
    return grader


def process(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"schema", "request_id", "question", "answer"}:
        raise InvalidRequest("invalid request envelope")
    try:
        if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_REQUEST_BYTES:
            raise InvalidRequest("request exceeds bounds")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as error:
        raise InvalidRequest("invalid request encoding") from error
    if value["schema"] != SCHEMA:
        raise InvalidRequest("unsupported request schema")
    request_id = _bounded_text(value["request_id"], 128, empty=False)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id):
        raise InvalidRequest("invalid request identity")
    question = value["question"]
    if not isinstance(question, dict) or set(question) != {"question_type", "options", "correct_answer"}:
        raise InvalidRequest("invalid question envelope")
    kind = _bounded_text(question["question_type"], 128)
    correct_answer = _bounded_text(question["correct_answer"], MAX_ANSWER_BYTES)
    answer = _bounded_text(value["answer"], MAX_ANSWER_BYTES)
    options = question["options"]
    if not isinstance(options, dict) or len(options) > 64:
        raise InvalidRequest("invalid options")
    clean_options: dict[str, str] = {}
    for key, text in options.items():
        clean_options[_bounded_text(key, 256, empty=False)] = _bounded_text(text, MAX_OPTION_BYTES)
    # Never return the answer key or learner answer. Upstream returns None for
    # subjective, missing-key or malformed-key questions; do not coerce it.
    correct = _upstream_grader()(
        {"question_type": kind, "options": clean_options, "correct_answer": correct_answer}, answer
    )
    if correct is not None and type(correct) is not bool:
        raise RuntimeError("upstream practice grader returned an invalid result")
    return {"schema": SCHEMA, "request_id": request_id, "status": "OBSERVED",
            "provider": "deeptutor", "adapter_version": "1.7.1",
            "upstream_member_sha256": UPSTREAM_SHA256, "provider_correct": correct,
            "question_binding": "caller_declared_unverified", "independent_mastery": "not_established"}


def main() -> int:
    try:
        raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
        if not raw or len(raw) > MAX_REQUEST_BYTES:
            raise InvalidRequest("empty or oversized request")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(InvalidRequest("non-finite number")))
        result = process(value)
        # Bind the successful response to the exact line received (including a
        # trailing newline if present). This digest is not an answer secret.
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    except (ValueError, UnicodeDecodeError, RecursionError):
        result = {"schema": SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}
        code = 2
    except (OSError, RuntimeError, SyntaxError, TypeError):
        result = {"schema": SCHEMA, "status": "UNAVAILABLE", "reason_code": "UPSTREAM_UNAVAILABLE"}
        code = 1
    else:
        code = 0
    sys.stdout.write(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
