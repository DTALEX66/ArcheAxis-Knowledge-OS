"""Private, bounded offline execution of selected DeepTutor teaching rules.

This is a one-request worker, not a public route, authenticated identity,
Core writer, model call, or durable learning profile. Successful output may
contain the caller's private preferences and evidence and must not be logged.
"""
from __future__ import annotations

import __future__
import ast
import builtins
import hashlib
import json
import math
import os
import re
import secrets
import stat
import sys
import time
import types
from pathlib import Path
from typing import Literal

SCHEMA = "archeaxis.deeptutor-teaching-feedback/v1"
MAX_INPUT = 128 * 1024
MAX_OUTPUT = 192 * 1024
UPSTREAM_ROOT = Path(__file__).absolute().parent / "upstream"
SOURCES = {
    "teaching.py": (8_374, "79839b2d29c16146ba4ca6eba438941eacdd8cef2920ebca81e8541305013b4b"),
    "learning_models.py": (31_784, "97d4cd701700c31aaf421900fa3b403ac1b5fe334e70d884a5159d998c4b8507"),
}
_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_KEY = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_PROFILE_FIELDS = {"prior_knowledge", "target_level", "time_budget", "preferences", "teaching_strategy", "notes",
                   "teaching_preferences", "teaching_observations", "updated_at"}
_PREFERENCE_FIELDS = {"text", "evidence", "session_id", "turn_id", "updated_at"}
_OBSERVATION_FIELDS = {"knowledge_point_id", "text", "basis", "strategy", "outcome", "evidence", "session_id",
                       "turn_id", "updated_at"}


class InvalidInput(ValueError):
    """A bounded input or state failed without including its value."""


class Unavailable(RuntimeError):
    """The fixed source, dependency, or selected definition is unavailable."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput("duplicate JSON member")
        result[key] = value
    return result


def _number(text):
    value = float(text)
    if not math.isfinite(value):
        raise InvalidInput("non-finite number")
    return value


def _integer(text):
    if len(text) > 100:
        raise InvalidInput("integer outside bounds")
    return int(text)


def _invalid_constant(_text):
    raise InvalidInput("non-finite number")


def _read_original(name):
    """Refuse observed links/reparse ancestors and read only bounded pinned bytes."""
    if name not in SOURCES:
        raise Unavailable("source unavailable")
    expected_size, expected_sha = SOURCES[name]
    path = (UPSTREAM_ROOT / name).absolute()
    if path.parent != UPSTREAM_ROOT.absolute():
        raise Unavailable("source unavailable")
    components = [*reversed(path.parents), path]
    try:
        before = []
        for component in components:
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise Unavailable("source unavailable")
            if component != path and not stat.S_ISDIR(info.st_mode):
                raise Unavailable("source unavailable")
            before.append(info)
        expected = before[-1]
        if (not stat.S_ISREG(expected.st_mode) or expected.st_nlink != 1
                or expected.st_size != expected_size or not expected.st_ino):
            raise Unavailable("source unavailable")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != expected_size):
                raise Unavailable("source unavailable")
            for component, original in zip(components, before):
                current = component.lstat()
                if (stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & 0x400
                        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)):
                    raise Unavailable("source unavailable")
            data = bytearray()
            while len(data) <= expected_size:
                chunk = os.read(fd, expected_size + 1 - len(data))
                if not chunk:
                    break
                data.extend(chunk)
        finally:
            os.close(fd)
    except OSError:
        raise Unavailable("source unavailable") from None
    source = bytes(data)
    if len(source) != expected_size or hashlib.sha256(source).hexdigest() != expected_sha:
        raise Unavailable("source unavailable")
    return source


def _one(tree, name, expected):
    found = [node for node in tree.body if isinstance(node, expected) and node.name == name]
    if len(found) != 1:
        raise Unavailable("source definition unavailable")
    return found[0]


def _selected_rules():
    """Build a private module from a hash-pinned AST whitelist, not top-level imports."""
    module = None
    try:
        from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
    except ImportError:
        raise Unavailable("dependency unavailable") from None
    try:
        models = ast.parse(_read_original("learning_models.py"), filename="deeptutor-1.7.1/learning/models.py")
        teaching = ast.parse(_read_original("teaching.py"), filename="deeptutor-1.7.1/learning/teaching.py")
        selected = [_one(models, name, ast.ClassDef) for name in
                    ("TeachingPreference", "TeachingObservation", "LearnerProfile")]
        selected.append(_one(teaching, "TeachingUpdate", ast.ClassDef))
        selected.extend(_one(teaching, name, ast.FunctionDef) for name in
                        ("parse_teaching_updates", "apply_teaching_updates", "teaching_guidance"))
        for definition in selected:
            if isinstance(definition, ast.ClassDef):
                if (definition.decorator_list or len(definition.bases) != 1
                        or not isinstance(definition.bases[0], ast.Name) or definition.bases[0].id != "BaseModel"):
                    raise Unavailable("source definition unavailable")
            for node in ast.walk(definition):
                if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
                    raise Unavailable("source operation unavailable")
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id in {"eval", "exec", "open", "__import__", "compile"}):
                    raise Unavailable("source operation unavailable")
        module = types.ModuleType("_deeptutor_171_teaching_" + secrets.token_hex(12))
        allowed_builtins = {name: getattr(builtins, name) for name in (
            "__build_class__", "object", "str", "float", "bool", "dict", "list", "set", "tuple", "int",
            "ValueError", "isinstance", "len", "any", "all", "getattr", "classmethod")}
        module.__dict__.update({"BaseModel": BaseModel, "ConfigDict": ConfigDict, "Field": Field,
                                "field_validator": field_validator, "model_validator": model_validator,
                                "Literal": Literal, "time": time, "__builtins__": allowed_builtins})
        # The module name is private to this dedicated worker process; Pydantic
        # needs it to resolve the original postponed type annotations.
        sys.modules[module.__name__] = module
        definitions = ast.Module(body=selected, type_ignores=[])
        ast.fix_missing_locations(definitions)
        code = compile(definitions, "deeptutor-1.7.1/learning/selected.py", "exec",
                       flags=__future__.annotations.compiler_flag, dont_inherit=True)
        exec(code, module.__dict__)  # noqa: S102 - exact pinned definitions only
        for name in ("TeachingPreference", "TeachingObservation", "LearnerProfile", "TeachingUpdate"):
            module.__dict__[name].model_rebuild(raise_errors=True)
        return module
    except Unavailable:
        if module is not None:
            sys.modules.pop(module.__name__, None)
        raise
    except Exception:
        if module is not None:
            sys.modules.pop(module.__name__, None)
        raise Unavailable("source definitions unavailable") from None


def _text(value, maximum, *, nonempty=False, trimmed=False):
    if type(value) is not str or "\x00" in value:
        raise InvalidInput("invalid text")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        raise InvalidInput("invalid text") from None
    if size > maximum or (nonempty and not value.strip()) or (trimmed and value != value.strip()):
        raise InvalidInput("text outside bounds")
    return value


def _identity(value):
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        raise InvalidInput("invalid identity")


def _timestamp(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise InvalidInput("invalid timestamp")


def _profile_shape(value):
    if type(value) is not dict or set(value) - _PROFILE_FIELDS:
        raise InvalidInput("invalid profile")
    for name in ("prior_knowledge", "target_level", "time_budget", "preferences", "notes"):
        if name in value:
            _text(value[name], 8_192)
    if "teaching_strategy" in value and value["teaching_strategy"] not in {"probe_first", "teach_first"}:
        raise InvalidInput("invalid strategy")
    if "updated_at" in value:
        _timestamp(value["updated_at"])
    for field, allowed, required, maximum in (
        ("teaching_preferences", _PREFERENCE_FIELDS, {"text", "evidence", "updated_at"}, 6),
        ("teaching_observations", _OBSERVATION_FIELDS, {"knowledge_point_id", "text", "updated_at"}, 12),
    ):
        records = value.get(field, {})
        if type(records) is not dict or len(records) > maximum:
            raise InvalidInput("profile records outside bounds")
        for key, record in records.items():
            if type(key) is not str or _KEY.fullmatch(key) is None or type(record) is not dict:
                raise InvalidInput("invalid profile record")
            if set(record) - allowed or not required <= set(record):
                raise InvalidInput("invalid profile record")
            _timestamp(record["updated_at"])
            for item, text in record.items():
                if item != "updated_at":
                    _text(text, 8_192)


def _updates_shape(value):
    if type(value) is not list or not 1 <= len(value) <= 6:
        raise InvalidInput("updates outside bounds")
    for item in value:
        if type(item) is not dict:
            raise InvalidInput("invalid update")
        kind, op = item.get("kind"), item.get("op")
        if kind not in {"preference", "observation"} or op not in {"upsert", "remove"}:
            raise InvalidInput("invalid update")
        if op == "remove":
            required = allowed = {"kind", "op", "key"}
        elif kind == "preference":
            required = allowed = {"kind", "op", "key", "text", "basis", "evidence"}
        else:
            required = {"kind", "op", "key", "text", "knowledge_point_id"}
            allowed = required | {"basis", "strategy", "outcome", "evidence"}
        if set(item) - allowed or not required <= set(item):
            raise InvalidInput("invalid update")
        for name, text in item.items():
            _text(text, 8_192, trimmed=name in {"text", "knowledge_point_id", "strategy", "evidence"})


def _preserved(original, normalized):
    """Every supplied profile field must survive upstream validation unchanged."""
    if type(original) is dict:
        return type(normalized) is dict and all(key in normalized and _preserved(value, normalized[key])
                                                for key, value in original.items())
    if type(original) is list:
        return type(normalized) is list and len(original) == len(normalized) and all(
            _preserved(a, b) for a, b in zip(original, normalized))
    if type(original) in (int, float) and type(normalized) in (int, float):
        return original == normalized
    return type(original) is type(normalized) and original == normalized


def process(value):
    """Process one private caller-supplied turn; returned content is sensitive."""
    fields = {"schema", "request_id", "profile", "updates", "current_message", "objective_ids",
              "focus_objective_id", "session_id", "turn_id", "include_history"}
    if type(value) is not dict or set(value) != fields or value["schema"] != SCHEMA:
        raise InvalidInput("invalid envelope")
    for key in ("request_id", "session_id", "turn_id"):
        _identity(value[key])
    _profile_shape(value["profile"])
    _updates_shape(value["updates"])
    _text(value["current_message"], 16_384)
    objectives = value["objective_ids"]
    if type(objectives) is not list or not 1 <= len(objectives) <= 128:
        raise InvalidInput("invalid objectives")
    for objective in objectives:
        _text(objective, 800, nonempty=True, trimmed=True)
        if len(objective) > 200:
            raise InvalidInput("invalid objective")
    if len(set(objectives)) != len(objectives):
        raise InvalidInput("duplicate objective")
    _text(value["focus_objective_id"], 800, nonempty=True, trimmed=True)
    if value["focus_objective_id"] not in objectives or type(value["include_history"]) is not bool:
        raise InvalidInput("invalid focus")
    rules = _selected_rules()
    try:
        profile = rules.LearnerProfile.model_validate(value["profile"])
        initial = profile.model_dump(mode="json")
        if not _preserved(value["profile"], initial):
            raise InvalidInput("profile would be changed")
        updates = rules.parse_teaching_updates(value["updates"], value["current_message"])
        scope = set(objectives)
        # Upstream validates an upsert's new objective but does not check the
        # prior observation before remove or before replacing an existing key.
        # Keep that source unchanged and refuse cross-scope mutation here.
        for item in updates:
            if item.kind == "observation":
                old = profile.teaching_observations.get(item.key)
                if old is not None and old.knowledge_point_id not in scope:
                    raise InvalidInput("existing observation outside scope")
        delta = rules.apply_teaching_updates(profile, updates, scope,
                                             session_id=value["session_id"], turn_id=value["turn_id"])
        updated = profile.model_copy(deep=True, update=delta)
        guidance = rules.teaching_guidance(updated, value["focus_objective_id"],
                                           include_history=value["include_history"])
        result_profile = updated.model_dump(mode="json")
    except InvalidInput:
        raise
    except Exception:
        # Pydantic errors can include the supplied values; never relay them.
        raise InvalidInput("teaching update rejected") from None
    finally:
        sys.modules.pop(rules.__name__, None)
    return {"schema": SCHEMA, "request_id": value["request_id"], "status": "UPDATED" if delta else "UNCHANGED",
            "status_scope": "teaching_delta_after_profile_defaults_only",
            "changed_fields": sorted(delta), "profile": result_profile, "guidance": guidance,
            "input_origin": "caller_supplied_unverified",
            "update_evidence_verification": "nonempty_literal_match_only",
            "existing_profile_evidence_verification": "NOT_VERIFIED", "evidence_authentication": "NOT_ESTABLISHED",
            "timestamp_source": "existing_caller_claim_new_worker_wall_clock_unverified",
            "profile_root_timestamp": "not_advanced_by_rule",
            "persistence": "NOT_PERFORMED", "core": "NOT_CALLED", "model_call": "NOT_INVOKED",
            "independent_mastery": "not_established", "output_privacy_filter": "NOT_APPLIED",
            "source_members": {name: digest for name, (_size, digest) in SOURCES.items()}}


def main():
    try:
        raw = sys.stdin.buffer.readline(MAX_INPUT + 1)
        if not raw or len(raw) > MAX_INPUT or sys.stdin.buffer.read(1):
            raise InvalidInput("invalid request framing")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_float=_number,
                           parse_int=_integer, parse_constant=_invalid_constant)
        result = process(value)
        wire = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        if len(wire) + 1 > MAX_OUTPUT:  # Include the terminating LF in the wire limit.
            raise Unavailable("output exceeds bounds")
    except (InvalidInput, ValueError, TypeError, UnicodeError, RecursionError):
        wire = json.dumps({"schema": SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"},
                          separators=(",", ":")).encode("utf-8")
        code = 2
    except Exception:
        wire = json.dumps({"schema": SCHEMA, "status": "UNAVAILABLE", "reason_code": "UPSTREAM_UNAVAILABLE"},
                          separators=(",", ":")).encode("utf-8")
        code = 1
    else:
        code = 0
    sys.stdout.buffer.write(wire + b"\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
