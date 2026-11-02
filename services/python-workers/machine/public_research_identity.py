"""Unregistered offline comparison of caller-supplied public-research records.

No Core identity, authorization, source authenticity, or independence is proven.
The caller keeps its receipts and source originals; this module writes nothing.
"""
from __future__ import annotations

import ast
import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import zlib


SCHEMA = "archeaxis.public-research-identity-candidate/v1"
PARSER_PATH = Path(__file__).absolute().with_name("public_research.py")
PARSER_SHA256 = "cb54f07bb86263fe264809f22817fccb9b7f6705cb26c3a6efde7baa1a3fc321"
PARSER_BYTES = 18_998
MAX_PATH_COMPONENTS = 64
MAX_RAW_BYTES = 128 * 1024
MAX_RAW_BASE64 = 4 * ((MAX_RAW_BYTES + 2) // 3)
MAX_PROVIDER_ITEMS = 512
_PARSER_FUNCTIONS = frozenset({"_unique_object", "_finite_float", "_reject_nonfinite_constant",
                               "_check_json_nesting", "_json_response"})
_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_WORK_ID = re.compile(r"https://openalex\.org/W([1-9][0-9]{0,19})\Z")
_DOI = re.compile(r"10\.[0-9]{4,9}/[A-Za-z0-9][A-Za-z0-9._;()/\-]*\Z")


class _Unknown(Exception):
    def __init__(self, reason):
        self.reason = reason


def _object(value):
    if type(value) is not dict:
        raise _Unknown("INPUT_SHAPE_INVALID")
    return value


def _token(value, maximum=256):
    if type(value) is not str or len(value) > maximum or _TOKEN.fullmatch(value) is None:
        raise _Unknown("INPUT_IDENTITY_INVALID")
    return value


def _sha(value):
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _Unknown("RAW_IDENTITY_INVALID")
    return value


def _parser():
    # Load only the exact parser function definitions from the already-bound
    # worker bytes. Do not execute its transport imports or network entrypoint.
    try:
        path = PARSER_PATH
        if not path.is_absolute() or ".." in path.parts:
            raise _Unknown("PARSER_IDENTITY_UNCONFIRMED")
        components = [*reversed(path.parents), path]
        if len(components) > MAX_PATH_COMPONENTS:
            raise _Unknown("PARSER_IDENTITY_UNCONFIRMED")

        def identity(component, is_file):
            info = component.lstat()
            if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
                    or not info.st_ino or (not is_file and not stat.S_ISDIR(info.st_mode))
                    or (is_file and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                                     or info.st_size != PARSER_BYTES))):
                raise _Unknown("PARSER_IDENTITY_UNCONFIRMED")
            return info

        before = [identity(component, component == path) for component in components]
        expected = before[-1]

        def check_components():
            for component, original in zip(components, before):
                current = identity(component, component == path)
                if ((current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)
                        or (component == path and (current.st_size, current.st_mtime_ns)
                            != (original.st_size, original.st_mtime_ns))):
                    raise _Unknown("PARSER_IDENTITY_UNCONFIRMED")

        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if ((opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
                    != (expected.st_dev, expected.st_ino, PARSER_BYTES, expected.st_mtime_ns)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1):
                raise _Unknown("PARSER_IDENTITY_UNCONFIRMED")
            check_components()
            data = bytearray()
            while len(data) <= PARSER_BYTES:
                chunk = os.read(fd, PARSER_BYTES + 1 - len(data))
                if not chunk:
                    break
                data.extend(chunk)
            after = os.fstat(fd)
            if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink)
                    != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, 1)):
                raise _Unknown("PARSER_IDENTITY_UNCONFIRMED")
            check_components()
        finally:
            os.close(fd)
        source = bytes(data)
        if len(source) != PARSER_BYTES or hashlib.sha256(source).hexdigest() != PARSER_SHA256:
            raise _Unknown("PARSER_IDENTITY_UNCONFIRMED")
        tree = ast.parse(source, filename="<fixed-public-research-parser>")
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in _PARSER_FUNCTIONS]
        if len(functions) != len(_PARSER_FUNCTIONS) or {node.name for node in functions} != _PARSER_FUNCTIONS:
            raise _Unknown("PARSER_IDENTITY_UNCONFIRMED")
        selected = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
        namespace = {"json": json, "math": math, "zlib": zlib,
                     "MAX_RESPONSE": MAX_RAW_BYTES, "MAX_JSON_NESTING": 64}
        exec(compile(selected, "<fixed-public-research-parser>", "exec"), namespace)
        return namespace["_json_response"]
    except _Unknown:
        raise
    except (OSError, ValueError, TypeError, SyntaxError, RecursionError):
        raise _Unknown("PARSER_IDENTITY_UNCONFIRMED") from None


def _doi(value):
    # Deliberately finite ASCII subset. Do not infer equivalence across case,
    # URL escapes, Unicode normalization, path traversal, or malformed values.
    if type(value) is not str or len(value) > 240 or _DOI.fullmatch(value) is None:
        raise _Unknown("DOI_UNSUPPORTED_OR_MISSING")
    suffix = value.split("/", 1)[1]
    if any(part in {"", ".", ".."} for part in suffix.split("/")):
        raise _Unknown("DOI_UNSUPPORTED_OR_MISSING")
    return value


def _base(side):
    side = _object(side)
    if len(side) != 3 or not all(key in side for key in ("receipt", "hit_id", "original")):
        raise _Unknown("INPUT_SHAPE_INVALID")
    receipt = _object(side["receipt"])
    if (receipt.get("schema") != "archeaxis.public-research-receipt/v1"
            or type(receipt.get("state")) is not str or receipt["state"] not in {"complete", "partial"}):
        raise _Unknown("RECEIPT_UNAVAILABLE")
    request_id = _token(receipt.get("request_id"), 128)
    workspace_id = _token(receipt.get("workspace_id"), 128)
    restore_epoch = _token(receipt.get("restore_epoch"), 128)
    hit_id = side["hit_id"]
    if type(hit_id) is not str or not 1 <= len(hit_id) <= 256:
        raise _Unknown("INPUT_IDENTITY_INVALID")
    channels = receipt.get("channels")
    if type(channels) is not list or not 1 <= len(channels) <= 4:
        raise _Unknown("RECEIPT_UNAVAILABLE")
    matches = []
    for channel in channels:
        channel = _object(channel)
        hits = channel.get("hits")
        if type(hits) is not list or len(hits) > 3:
            raise _Unknown("RECEIPT_UNAVAILABLE")
        for hit in hits:
            hit = _object(hit)
            if hit.get("id") == hit_id:
                matches.append((channel, hit))
    if len(matches) != 1:
        raise _Unknown("HIT_MISSING_OR_DUPLICATE")
    channel, hit = matches[0]
    provider = channel.get("provider")
    if (channel.get("family") != "research" or type(provider) is not str or provider not in {"openalex", "crossref"}
            or type(channel.get("status")) is not str or channel["status"] not in {"complete", "limited"}
            or channel.get("raw_representation") != "http_entity_body_bytes"
            or hit.get("family") != "research" or hit.get("provider") != provider
            or hit.get("url") != hit_id):
        raise _Unknown("HIT_IDENTITY_INVALID")
    reference = _object(channel.get("raw_source"))
    if (len(reference) != 3 or not all(key in reference for key in ("kind", "source_id", "sha256"))
            or reference.get("kind") != "source"):
        raise _Unknown("RAW_IDENTITY_INVALID")
    source_id = _token(reference.get("source_id"))
    digest = _sha(reference.get("sha256"))
    if provider == "openalex":
        match = _WORK_ID.fullmatch(hit_id)
        if match is None or int(match.group(1)) > (1 << 64) - 1:
            raise _Unknown("HIT_IDENTITY_INVALID")
    else:
        prefix = "https://doi.org/"
        if not hit_id.startswith(prefix):
            raise _Unknown("HIT_IDENTITY_INVALID")
        _doi(hit_id[len(prefix):])
    return {"request_id": request_id, "workspace_id": workspace_id, "restore_epoch": restore_epoch,
            "provider": provider, "hit_id": hit_id,
            "raw_source": {"kind": "source", "source_id": source_id, "sha256": digest},
            "receipt_scope": "CALLER_SUPPLIED_UNVERIFIED",
            "raw_source_scope": "CALLER_SUPPLIED_UNVERIFIED", "raw_sha_check": "NOT_VERIFIED",
            "doi_declaration": None, "doi_status": "UNKNOWN"}


def _read_original(side, observation, parse):
    original = side.get("original")
    if original is None:
        raise _Unknown("ORIGINAL_MISSING")
    original = _object(original)
    reference = observation["raw_source"]
    if original.get("source_id") != reference["source_id"] or original.get("sha256") != reference["sha256"]:
        raise _Unknown("RAW_IDENTITY_MISMATCH")
    encoded = original.get("content_base64")
    if type(encoded) is not str or len(encoded) > MAX_RAW_BASE64:
        raise _Unknown("RAW_BYTES_UNAVAILABLE")
    try:
        encoded_bytes = encoded.encode("ascii")
        raw = base64.b64decode(encoded_bytes, validate=True)
    except (UnicodeError, binascii.Error, ValueError):
        raise _Unknown("RAW_BYTES_UNAVAILABLE") from None
    if (not raw or len(raw) > MAX_RAW_BYTES or base64.b64encode(raw) != encoded_bytes
            or hashlib.sha256(raw).hexdigest() != reference["sha256"]):
        raise _Unknown("RAW_IDENTITY_MISMATCH")
    observation["raw_sha_check"] = "MATCHED_CALLER_DECLARED_SHA"
    try:
        return parse(raw, {})
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError, zlib.error):
        raise _Unknown("RAW_RESPONSE_INVALID") from None


def _declared_doi(side, observation, parse):
    data = _read_original(side, observation, parse)
    if observation["provider"] == "openalex":
        if "error" in data:
            raise _Unknown("RAW_RESPONSE_INVALID")
        items = data.get("results")
        if type(items) is not list or len(items) > MAX_PROVIDER_ITEMS or any(type(item) is not dict for item in items):
            raise _Unknown("RAW_RESPONSE_INVALID")
        work_ids = set()
        for item in items:
            work_id = item.get("id")
            match = _WORK_ID.fullmatch(work_id) if type(work_id) is str else None
            if match is None or int(match.group(1)) > (1 << 64) - 1:
                raise _Unknown("RAW_RESPONSE_INVALID")
            if work_id in work_ids:
                raise _Unknown("RAW_HIT_MISSING_OR_DUPLICATE")
            work_ids.add(work_id)
        matches = [item for item in items if item.get("id") == observation["hit_id"]]
        if len(matches) != 1:
            raise _Unknown("RAW_HIT_MISSING_OR_DUPLICATE")
        declared = matches[0].get("doi")
        prefix = "https://doi.org/"
        if type(declared) is not str or not declared.startswith(prefix):
            raise _Unknown("DOI_UNSUPPORTED_OR_MISSING")
        identifier = _doi(declared[len(prefix):])
        seen_dois = set()
        for item in items:
            other = item.get("doi")
            if other is None:
                continue
            if type(other) is not str or not other.startswith(prefix):
                raise _Unknown("DOI_UNSUPPORTED_OR_MISSING")
            other_id = _doi(other[len(prefix):])
            comparison_key = other_id.lower()
            if comparison_key in seen_dois:
                raise _Unknown("RAW_DOI_DUPLICATE")
            seen_dois.add(comparison_key)
    else:
        message = data.get("message")
        if type(message) is not dict or data.get("status") != "ok":
            raise _Unknown("RAW_RESPONSE_INVALID")
        items = message.get("items")
        if type(items) is not list or len(items) > MAX_PROVIDER_ITEMS or any(type(item) is not dict for item in items):
            raise _Unknown("RAW_RESPONSE_INVALID")
        identifier = _doi(observation["hit_id"].removeprefix("https://doi.org/"))
        matches = []
        seen_dois = set()
        for item in items:
            candidate = _doi(item.get("DOI"))
            comparison_key = candidate.lower()
            if comparison_key in seen_dois:
                raise _Unknown("RAW_DOI_DUPLICATE")
            seen_dois.add(comparison_key)
            if comparison_key == identifier.lower():
                matches.append(candidate)
        if len(matches) != 1:
            raise _Unknown("RAW_HIT_MISSING_OR_DUPLICATE")
        if matches[0] != identifier:
            raise _Unknown("DECLARED_DOI_DIFFERENT")
        declared = matches[0]
    observation["doi_declaration"] = declared
    observation["doi_status"] = "PROVIDER_DECLARED_UNVERIFIED"
    return identifier


def compare(left, right, *, include_details=False):
    """Compare two supplied v1 receipt/original pairs without I/O except parser read.

    Each side is exactly {receipt, hit_id, original}; original is the existing
    source_original result or None. Detailed identities require explicit opt-in.
    All returned claims remain caller-supplied and unverified by Core.
    """
    result = {"schema": SCHEMA, "status": "UNKNOWN", "reason_code": "INPUT_SHAPE_INVALID",
              "input_scope": "CALLER_SUPPLIED_UNVERIFIED", "independent_evidence": "UNKNOWN",
              "source_authenticity": "NOT_ESTABLISHED", "merge": "NOT_PERFORMED",
              "network": "NO_NETWORK_REQUESTS_BY_CANDIDATE", "persistence": "NOT_PERFORMED", "observations": None}
    if type(include_details) is not bool:
        return result
    observations = [None, None]
    identifiers = [None, None]
    errors = []
    try:
        parse = _parser()
    except _Unknown as error:
        result["reason_code"] = error.reason
        return result
    for index, side in enumerate((left, right)):
        try:
            observations[index] = _base(side)
            identifiers[index] = _declared_doi(side, observations[index], parse)
        except _Unknown as error:
            errors.append(error.reason)
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
            errors.append("INPUT_SHAPE_INVALID")
    if include_details:
        result["observations"] = observations
    if errors:
        result["reason_code"] = errors[0]
    elif observations[0]["workspace_id"] != observations[1]["workspace_id"]:
        result["reason_code"] = "WORKSPACE_MISMATCH"
    elif observations[0]["request_id"] == observations[1]["request_id"]:
        # The current route queries Crossref only after OpenAlex cannot return
        # hits; two successful hits sharing one frozen request are inconsistent.
        result["reason_code"] = "RUN_ID_COLLISION"
    elif {observations[0]["provider"], observations[1]["provider"]} != {"openalex", "crossref"}:
        result["reason_code"] = "PROVIDER_PAIR_UNSUPPORTED"
    elif identifiers[0] != identifiers[1]:
        result["reason_code"] = "DECLARED_DOI_DIFFERENT"
    else:
        result["status"] = "POSSIBLE_SAME_DECLARED_DOI"
        result["reason_code"] = "EXACT_DECLARED_DOI"
    return result
