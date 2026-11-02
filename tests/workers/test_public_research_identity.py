"""Synthetic DOI identity evidence; no public service is contacted."""
import base64
import copy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket

import pytest


ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/machine/public_research.py"
CANDIDATE = ROOT / "services/python-workers/machine/public_research_identity.py"


@pytest.fixture
def candidate():
    spec = importlib.util.spec_from_file_location("research_identity_candidate", CANDIDATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _set_raw(side, raw):
    digest = hashlib.sha256(raw).hexdigest()
    source_id = "src_" + hashlib.sha256(digest.encode("ascii")).hexdigest()[:24]
    side["receipt"]["channels"][0]["raw_source"] = {
        "kind": "source", "source_id": source_id, "sha256": digest}
    side["original"] = {"source_id": source_id, "sha256": digest, "name": "synthetic.json",
                        "media_type": "application/json", "content_base64": base64.b64encode(raw).decode("ascii")}


def _side(provider, *, doi="10.1234/synthetic", request_id=None, encoding="utf-8", compressed=False):
    assert provider in ("openalex", "crossref")
    request_id = request_id or "synthetic_" + provider
    when = "2026-11-02T00:00:00Z"
    if provider == "openalex":
        hit_id = "https://openalex.org/W42"
        raw_data = {"results": [{"id": hit_id, "title": "SYNTHETIC_TITLE_PRIVATE",
                                 "doi": "https://doi.org/" + doi}]}
        endpoint = "https://api.openalex.org/works?search=synthetic&per_page=1"
        license_value = "CC0"
    else:
        hit_id = "https://doi.org/" + doi
        raw_data = {"status": "ok", "message": {"items": [
            {"DOI": doi, "title": ["SYNTHETIC_TITLE_PRIVATE"]}]}}
        endpoint = "https://api.crossref.org/works?query.bibliographic=synthetic&rows=1&select=DOI%2Ctitle%2CURL%2Cpublished"
        license_value = None
    hit = {"id": hit_id, "family": "research", "provider": provider, "title": "SYNTHETIC_TITLE_PRIVATE",
           "url": hit_id, "retrieved_at": when, "content": "metadata", "excerpt": "",
           "locator": None, "license": license_value, "free_access": "free", "upstream_revision": None,
           "representation": "metadata", "truncated": False}
    channel = {"family": "research", "provider": provider, "status": "complete", "retrieved_at": when,
               "request_url": endpoint, "retry_after_seconds": None, "error_code": None, "hits": [hit],
               "raw_source": None, "raw_representation": "http_entity_body_bytes"}
    receipt = {"schema": "archeaxis.public-research-receipt/v1", "request_id": request_id,
               "workspace_id": "a" * 32, "restore_epoch": "initial", "query": "SYNTHETIC_QUERY_PRIVATE",
               "families": ["research"], "limit": 1, "state": "complete", "channels": [channel],
               "reason_code": None, "provider_stop_state": "unknown", "knowledge_admission": "not_executed"}
    side = {"receipt": receipt, "hit_id": hit_id, "original": None}
    raw = json.dumps(raw_data, ensure_ascii=False, separators=(",", ":")).encode(encoding)
    _set_raw(side, gzip.compress(raw, mtime=0) if compressed else raw)
    return side


def test_current_v1_projection_cannot_associate_a_shared_doi():
    spec = importlib.util.spec_from_file_location("research_identity_existing_worker", WORKER)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    openalex_raw = (b'{"results":[{"id":"https://openalex.org/W42",'
                    b'"title":"Synthetic paper","doi":"https://doi.org/10.1234/synthetic"}]}')
    crossref_raw = (b'{"status":"ok","message":{"items":['
                    b'{"DOI":"10.1234/synthetic","title":["Synthetic paper"]}]}}')
    when = "2026-11-02T00:00:00Z"
    openalex = worker._research(worker._json_response(openalex_raw, {}), when, 1)[0]
    crossref = worker._crossref(worker._json_response(crossref_raw, {}), when, 1)[0]
    assert openalex["id"] == "https://openalex.org/W42"
    assert crossref["id"] == "https://doi.org/10.1234/synthetic"
    assert openalex["id"] != crossref["id"]
    assert "doi" not in openalex and "10.1234/synthetic" not in openalex["id"]
    print("SYNTHETIC: shared DOI in raw; OpenAlex v1 projects W42 without DOI; Crossref v1 projects DOI URL")


def test_same_declared_doi_preserves_each_identity_only_when_explicitly_requested(candidate, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("offline comparison attempted a network operation")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    real_open = os.open

    def read_only_open(path, flags, *args, **kwargs):
        forbidden = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        if flags & forbidden:
            pytest.fail("offline comparison attempted a file write")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(candidate.os, "open", read_only_open)
    left, right = _side("openalex"), _side("crossref")
    original_inputs = copy.deepcopy((left, right))
    result = candidate.compare(left, right)
    assert result["status"] == "POSSIBLE_SAME_DECLARED_DOI"
    assert result["reason_code"] == "EXACT_DECLARED_DOI"
    assert result["input_scope"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert result["independent_evidence"] == "UNKNOWN" and result["source_authenticity"] == "NOT_ESTABLISHED"
    assert result["merge"] == result["persistence"] == "NOT_PERFORMED"
    assert result["network"] == "NO_NETWORK_REQUESTS_BY_CANDIDATE"
    assert result["observations"] is None
    shown = json.dumps(result)
    for private in ("SYNTHETIC_QUERY_PRIVATE", "SYNTHETIC_TITLE_PRIVATE", "10.1234/synthetic",
                    "https://openalex.org/W42", left["original"]["sha256"]):
        assert private not in shown
    detailed = candidate.compare(left, right, include_details=True)
    assert detailed["status"] == result["status"]
    oa, cr = detailed["observations"]
    assert oa["hit_id"] == "https://openalex.org/W42" and oa["provider"] == "openalex"
    assert oa["doi_declaration"] == "https://doi.org/10.1234/synthetic"
    assert cr["hit_id"] == "https://doi.org/10.1234/synthetic" and cr["provider"] == "crossref"
    assert cr["doi_declaration"] == "10.1234/synthetic"
    for observed, source in zip((oa, cr), (left, right)):
        assert observed["request_id"] == source["receipt"]["request_id"]
        assert observed["workspace_id"] == source["receipt"]["workspace_id"]
        assert observed["restore_epoch"] == source["receipt"]["restore_epoch"]
        assert observed["raw_source"] == source["receipt"]["channels"][0]["raw_source"]
        assert observed["receipt_scope"] == observed["raw_source_scope"] == "CALLER_SUPPLIED_UNVERIFIED"
        assert observed["raw_sha_check"] == "MATCHED_CALLER_DECLARED_SHA"
        assert observed["doi_status"] == "PROVIDER_DECLARED_UNVERIFIED"
    assert "SYNTHETIC_QUERY_PRIVATE" not in json.dumps(detailed)
    assert "SYNTHETIC_TITLE_PRIVATE" not in json.dumps(detailed)
    assert (left, right) == original_inputs


@pytest.mark.parametrize(("left_encoding", "right_encoding", "compressed"), [
    ("utf-8", "utf-8", False), ("utf-8-sig", "utf-16", True),
    ("utf-16-be", "utf-32-be", False), ("utf-32", "utf-8", True),
])
def test_transport_encoding_and_gzip_preserve_same_string_claim(candidate, left_encoding, right_encoding, compressed):
    left = _side("openalex", encoding=left_encoding, compressed=compressed)
    right = _side("crossref", encoding=right_encoding, compressed=not compressed)
    result = candidate.compare(left, right, include_details=True)
    assert result["status"] == "POSSIBLE_SAME_DECLARED_DOI"
    assert result["observations"][0]["raw_source"]["sha256"] == left["original"]["sha256"]
    assert result["observations"][1]["raw_source"]["sha256"] == right["original"]["sha256"]


def test_current_parser_pin_accepts_unicode_revision_without_changing_raw_identity(candidate):
    left, right = _side("openalex"), _side("crossref")
    raw = (b'{"results":[{"id":"https://openalex.org/W42",'
           b'"doi":"https://doi.org/10.1234/synthetic",'
           br'"updated_date":"2026-\ud83d\ude00"}]}')
    _set_raw(left, raw)
    result = candidate.compare(left, right, include_details=True)
    assert result["status"] == "POSSIBLE_SAME_DECLARED_DOI"
    assert result["observations"][0]["raw_source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["observations"][0]["raw_sha_check"] == "MATCHED_CALLER_DECLARED_SHA"
    assert result["source_authenticity"] == "NOT_ESTABLISHED"


def test_different_declared_epochs_are_retained_without_claiming_currentness(candidate):
    left, right = _side("openalex"), _side("crossref")
    right["receipt"]["restore_epoch"] = "b" * 32
    result = candidate.compare(left, right, include_details=True)
    assert result["status"] == "POSSIBLE_SAME_DECLARED_DOI"
    assert [row["restore_epoch"] for row in result["observations"]] == ["initial", "b" * 32]
    assert all(row["receipt_scope"] == "CALLER_SUPPLIED_UNVERIFIED" for row in result["observations"])
    assert result["source_authenticity"] == "NOT_ESTABLISHED" and result["independent_evidence"] == "UNKNOWN"


def test_unselected_openalex_null_doi_is_retained_as_unknown_not_a_duplicate(candidate):
    left, right = _side("openalex"), _side("crossref")
    raw = {"results": [{"id": left["hit_id"], "doi": "https://doi.org/10.1234/synthetic"},
                       {"id": "https://openalex.org/W43", "doi": None}]}
    _set_raw(left, json.dumps(raw).encode())
    assert candidate.compare(left, right)["status"] == "POSSIBLE_SAME_DECLARED_DOI"


@pytest.mark.parametrize("variant", [
    "missing-original", "missing-hash", "wrong-source-id", "wrong-declared-hash", "wrong-bytes",
    "bad-base64", "empty-original", "duplicate-receipt-hit", "duplicate-raw-w", "missing-raw-w",
    "duplicate-openalex-doi", "duplicate-crossref-doi", "case-collision-crossref", "unselected-duplicate-w",
    "unselected-invalid-w", "unselected-duplicate-oa-doi", "unselected-case-collision-oa-doi",
    "unselected-duplicate-crossref-doi", "unselected-case-collision-crossref", "missing-doi",
    "null-doi", "numeric-doi", "unsafe-openalex-url", "unsafe-dot-segment", "encoded-doi",
    "unicode-doi", "encoded-crossref", "unsafe-crossref-query", "numeric-crossref", "noncanonical-w",
    "different-case", "different-doi", "different-workspace", "same-run-id", "wrong-provider", "wrong-hit-url",
    "unhashable-state", "unhashable-provider", "unknown-receipt-state", "wrong-raw-type", "oversized-base64",
])
def test_ambiguous_unavailable_or_different_claims_are_unknown(candidate, variant):
    left, right = _side("openalex"), _side("crossref")
    oa = {"results": [{"id": left["hit_id"], "doi": "https://doi.org/10.1234/synthetic"}]}
    cr = {"status": "ok", "message": {"items": [{"DOI": "10.1234/synthetic"}]}}
    if variant == "missing-original":
        left["original"] = None
    elif variant == "missing-hash":
        del left["original"]["sha256"]
    elif variant == "wrong-source-id":
        left["original"]["source_id"] = "src_other"
    elif variant == "wrong-declared-hash":
        left["original"]["sha256"] = "0" * 64
    elif variant == "wrong-bytes":
        left["original"]["content_base64"] = base64.b64encode(b"different").decode("ascii")
    elif variant == "bad-base64":
        left["original"]["content_base64"] = "a@@@"
    elif variant == "empty-original":
        left["original"]["content_base64"] = ""
    elif variant == "oversized-base64":
        left["original"]["content_base64"] = "A" * (candidate.MAX_RAW_BASE64 + 1)
    elif variant == "duplicate-receipt-hit":
        hits = left["receipt"]["channels"][0]["hits"]
        hits.append(copy.deepcopy(hits[0]))
    elif variant == "duplicate-raw-w":
        oa["results"].append(copy.deepcopy(oa["results"][0]))
        _set_raw(left, json.dumps(oa).encode())
    elif variant == "missing-raw-w":
        oa["results"][0]["id"] = "https://openalex.org/W43"
        _set_raw(left, json.dumps(oa).encode())
    elif variant == "duplicate-openalex-doi":
        oa["results"].append({"id": "https://openalex.org/W43", "doi": oa["results"][0]["doi"]})
        _set_raw(left, json.dumps(oa).encode())
    elif variant == "duplicate-crossref-doi":
        cr["message"]["items"].append(copy.deepcopy(cr["message"]["items"][0]))
        _set_raw(right, json.dumps(cr).encode())
    elif variant == "case-collision-crossref":
        cr["message"]["items"].append({"DOI": "10.1234/SYNTHETIC"})
        _set_raw(right, json.dumps(cr).encode())
    elif variant == "unselected-duplicate-w":
        oa["results"].extend([{"id": "https://openalex.org/W43", "doi": "https://doi.org/10.2345/one"},
                              {"id": "https://openalex.org/W43", "doi": "https://doi.org/10.2345/two"}])
        _set_raw(left, json.dumps(oa).encode())
    elif variant == "unselected-invalid-w":
        oa["results"].append({"id": "https://openalex.org/W042", "doi": None})
        _set_raw(left, json.dumps(oa).encode())
    elif variant in {"unselected-duplicate-oa-doi", "unselected-case-collision-oa-doi"}:
        second = "10.2345/OTHER" if variant == "unselected-case-collision-oa-doi" else "10.2345/other"
        oa["results"].extend([{"id": "https://openalex.org/W43", "doi": "https://doi.org/10.2345/other"},
                              {"id": "https://openalex.org/W44", "doi": "https://doi.org/" + second}])
        _set_raw(left, json.dumps(oa).encode())
    elif variant in {"unselected-duplicate-crossref-doi", "unselected-case-collision-crossref"}:
        second = "10.2345/OTHER" if variant == "unselected-case-collision-crossref" else "10.2345/other"
        cr["message"]["items"].extend([{"DOI": "10.2345/other"}, {"DOI": second}])
        _set_raw(right, json.dumps(cr).encode())
    elif variant in {"missing-doi", "null-doi", "numeric-doi", "unsafe-openalex-url",
                     "unsafe-dot-segment", "encoded-doi", "unicode-doi"}:
        values = {"missing-doi": None, "null-doi": None, "numeric-doi": 10.1234,
                  "unsafe-openalex-url": "https://user:pass@doi.org/10.1234/synthetic",
                  "unsafe-dot-segment": "https://doi.org/10.1234/../private",
                  "encoded-doi": "https://doi.org/10.1234/%73ynthetic",
                  "unicode-doi": "https://doi.org/10.1234/synthétic"}
        if variant == "missing-doi":
            del oa["results"][0]["doi"]
        else:
            oa["results"][0]["doi"] = values[variant]
        _set_raw(left, json.dumps(oa, ensure_ascii=False).encode())
    elif variant == "encoded-crossref":
        right = _side("crossref", doi="10.1234/%73ynthetic")
    elif variant == "unsafe-crossref-query":
        right = _side("crossref", doi="10.1234/synthetic?private")
    elif variant == "numeric-crossref":
        cr["message"]["items"][0]["DOI"] = 10.1234
        _set_raw(right, json.dumps(cr).encode())
    elif variant == "noncanonical-w":
        left["hit_id"] = "https://openalex.org/W042"
        left["receipt"]["channels"][0]["hits"][0]["id"] = left["hit_id"]
        left["receipt"]["channels"][0]["hits"][0]["url"] = left["hit_id"]
    elif variant == "different-case":
        right = _side("crossref", doi="10.1234/SYNTHETIC")
    elif variant == "different-doi":
        right = _side("crossref", doi="10.1234/other")
    elif variant == "different-workspace":
        right["receipt"]["workspace_id"] = "b" * 32
    elif variant == "same-run-id":
        right["receipt"]["request_id"] = left["receipt"]["request_id"]
    elif variant == "wrong-provider":
        right = _side("openalex", request_id="another_openalex")
    elif variant == "wrong-hit-url":
        left["receipt"]["channels"][0]["hits"][0]["url"] = "https://openalex.org/W999"
    elif variant == "unhashable-state":
        left["receipt"]["state"] = []
    elif variant == "unhashable-provider":
        left["receipt"]["channels"][0]["provider"] = []
    elif variant == "unknown-receipt-state":
        left["receipt"]["state"] = "unknown"
    elif variant == "wrong-raw-type":
        left["receipt"]["channels"][0]["raw_source"] = []
    result = candidate.compare(left, right, include_details=True)
    assert result["status"] == "UNKNOWN" and result["reason_code"] != "EXACT_DECLARED_DOI"
    if variant in {"different-case", "different-doi"}:
        # Distinct declarations do not establish that the underlying works differ.
        assert result["reason_code"] == "DECLARED_DOI_DIFFERENT"
    assert result["independent_evidence"] == "UNKNOWN" and result["merge"] == "NOT_PERFORMED"
    assert "SYNTHETIC_QUERY_PRIVATE" not in json.dumps(result)
    assert "SYNTHETIC_TITLE_PRIVATE" not in json.dumps(result)
    if variant in {"unsafe-openalex-url", "encoded-crossref", "unsafe-crossref-query"}:
        assert "user:pass" not in json.dumps(result) and "?private" not in json.dumps(result)


@pytest.mark.parametrize("raw", [
    b'{"results":[],"results":[]}',
    b'{"results":[],"unused":NaN}',
    b'{"results":[],"unused":1e9999}',
    b'{"results":[],"unused":{"duplicate":1,"duplicate":2}}',
    b'{"results":[],"unused":' + b'[' * 65 + b'0' + b']' * 65 + b'}',
    b'not-json',
])
@pytest.mark.parametrize("compressed", [False, True], ids=["plain", "gzip"])
def test_invalid_original_json_remains_unknown_without_echo(candidate, raw, compressed):
    left, right = _side("openalex"), _side("crossref")
    _set_raw(left, gzip.compress(raw, mtime=0) if compressed else raw)
    result = candidate.compare(left, right, include_details=True)
    assert result["status"] == "UNKNOWN" and result["reason_code"] == "RAW_RESPONSE_INVALID"
    assert result["observations"][0]["doi_declaration"] is None
    assert result["observations"][0]["raw_source"]["sha256"] == left["original"]["sha256"]


def test_fixed_parser_missing_or_tampered_is_unknown(candidate, monkeypatch, tmp_path):
    left, right = _side("openalex"), _side("crossref")
    path = tmp_path / "public_research.py"
    monkeypatch.setattr(candidate, "PARSER_PATH", path)
    assert candidate.compare(left, right)["reason_code"] == "PARSER_IDENTITY_UNCONFIRMED"
    path.write_bytes(WORKER.read_bytes() + b"\n# synthetic tamper\n")
    result = candidate.compare(left, right, include_details=True)
    assert result["status"] == "UNKNOWN" and result["reason_code"] == "PARSER_IDENTITY_UNCONFIRMED"
    assert result["observations"] is None
    same_size = bytearray(WORKER.read_bytes())
    same_size[0] ^= 1
    path.write_bytes(same_size)
    assert candidate.compare(left, right)["reason_code"] == "PARSER_IDENTITY_UNCONFIRMED"


def test_parser_with_hardlinked_file_is_rejected(candidate, monkeypatch, tmp_path):
    # Link only two synthetic copies; never alter the real worker's link count.
    source = tmp_path / "synthetic-original.py"
    linked = tmp_path / "synthetic-hardlink.py"
    source.write_bytes(WORKER.read_bytes())
    try:
        os.link(source, linked)
    except OSError as error:
        pytest.skip(f"synthetic hardlink unavailable: {type(error).__name__}")
    assert linked.stat().st_nlink > 1
    monkeypatch.setattr(candidate, "PARSER_PATH", linked)
    result = candidate.compare(_side("openalex"), _side("crossref"))
    assert result["status"] == "UNKNOWN" and result["reason_code"] == "PARSER_IDENTITY_UNCONFIRMED", (
        "synthetic same-byte hardlink was admitted: " + result["status"])


@pytest.mark.parametrize("kind", ["file", "ancestor"])
def test_parser_with_observed_symlink_is_rejected(candidate, monkeypatch, tmp_path, kind):
    actual_dir = tmp_path / "synthetic-real"
    actual_dir.mkdir()
    actual_file = actual_dir / "public_research.py"
    actual_file.write_bytes(WORKER.read_bytes())
    link = tmp_path / ("synthetic-file-link.py" if kind == "file" else "synthetic-dir-link")
    try:
        link.symlink_to(actual_file if kind == "file" else actual_dir, target_is_directory=kind == "ancestor")
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"synthetic symlink unavailable: {type(error).__name__}")
    path = link if kind == "file" else link / "public_research.py"
    monkeypatch.setattr(candidate, "PARSER_PATH", path)
    result = candidate.compare(_side("openalex"), _side("crossref"))
    assert result["status"] == "UNKNOWN" and result["reason_code"] == "PARSER_IDENTITY_UNCONFIRMED"


@pytest.mark.parametrize("kind", ["file", "ancestor"])
def test_parser_with_observed_windows_reparse_attribute_is_rejected(candidate, monkeypatch, tmp_path, kind):
    directory = tmp_path / "synthetic-parent"
    directory.mkdir()
    path = directory / "public_research.py"
    path.write_bytes(WORKER.read_bytes())
    real_lstat = Path.lstat
    flagged = path if kind == "file" else directory

    class SimulatedReparse:
        def __init__(self, original):
            self.original = original

        def __getattr__(self, name):
            if name == "st_file_attributes":
                return getattr(self.original, name, 0) | 0x400
            return getattr(self.original, name)

    def lstat_with_reparse(component, *args, **kwargs):
        info = real_lstat(component, *args, **kwargs)
        return SimulatedReparse(info) if component == flagged else info

    monkeypatch.setattr(candidate, "PARSER_PATH", path)
    monkeypatch.setattr(Path, "lstat", lstat_with_reparse)
    result = candidate.compare(_side("openalex"), _side("crossref"))
    assert result["status"] == "UNKNOWN" and result["reason_code"] == "PARSER_IDENTITY_UNCONFIRMED"


@pytest.mark.parametrize("field", ["st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink"])
def test_parser_changed_open_handle_identity_is_rejected(candidate, monkeypatch, field):
    real_fstat = os.fstat
    calls = 0

    class ChangedIdentity:
        def __init__(self, original):
            self.original = original

        def __getattr__(self, name):
            value = getattr(self.original, name)
            return value + 1 if name == field else value

    def changing_fstat(fd):
        nonlocal calls
        calls += 1
        info = real_fstat(fd)
        return ChangedIdentity(info) if calls == 2 else info

    monkeypatch.setattr(candidate.os, "fstat", changing_fstat)
    result = candidate.compare(_side("openalex"), _side("crossref"))
    assert calls == 2
    assert result["status"] == "UNKNOWN" and result["reason_code"] == "PARSER_IDENTITY_UNCONFIRMED"


def test_non_boolean_detail_request_is_rejected(candidate):
    result = candidate.compare(_side("openalex"), _side("crossref"), include_details="yes")
    assert result["status"] == "UNKNOWN" and result["reason_code"] == "INPUT_SHAPE_INVALID"
    assert result["observations"] is None
