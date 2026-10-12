"""Fault-injection and readback assertions; actual Core qualification runs in CI.

These helper tests deliberately use controlled responses and do not claim runtime
idempotency. The candidate runtime probe must independently execute the HTTP loop.
"""
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def probe(monkeypatch):
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        return module

    load("aaos01_office_runtime_loop", ROOT / "scripts/probes/aaos01_office_runtime_loop.py")
    return load("ack_policy_probe", ROOT / "scripts/probes/aaos01_content_policy_runtime_loop.py")


def request(probe):
    return json.dumps({"create_request_id": "fixed_ack_request", "title": "原创",
                       "editor_json": probe.editor("中文")})


def test_ack_injection_discards_body_without_retaining_credentials(probe, monkeypatch):
    opened = []

    class Response:
        status = 201
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def read(self):
            raise AssertionError("discarded acknowledgement body must not be consumed")

    response = Response()

    def open_request(req, timeout):
        opened.append(req)
        assert timeout == 30
        return response

    monkeypatch.setattr(probe.urllib.request, "urlopen", open_request)
    wire = request(probe)
    result = probe.discard_create_ack("http://127.0.0.1:1234", "SYNTHETIC_SECRET",
                                      wire, SimpleNamespace(headers=lambda token: {"x-test-token": token}))
    assert response.closed
    assert opened[0].data == wire.encode("utf-8")
    assert opened[0].method == "POST"
    assert result["ack_body"] == "DISCARDED_UNREAD"
    assert result["request_sha256"] == hashlib.sha256(wire.encode()).hexdigest()
    assert "SYNTHETIC_SECRET" not in json.dumps(result)


def test_ack_injection_fails_closed_on_noncreated_status(probe, monkeypatch):
    class Response:
        status = 409

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(probe.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(AssertionError):
        probe.discard_create_ack("http://127.0.0.1:1234", "fixture", request(probe),
                                  SimpleNamespace(headers=lambda token: {}))


def replay_client(probe, *, duplicate=False, changed=False, extra_version=False):
    wire = request(probe)
    frozen = json.loads(wire)
    identity = "doc_req_" + hashlib.sha256(frozen["create_request_id"].encode()).hexdigest()
    document = {"document_id": identity, "version": 1, "title": frozen["title"],
                "editor_json": frozen["editor_json"], "source_id": None, "source_revision": None}
    rows = [{"document_id": identity, "title": frozen["title"], "version": 1}]
    if duplicate:
        rows.append({**rows[0], "document_id": "unexpected_duplicate"})
    calls = []

    def call(method, path, body=None, expected=200):
        calls.append((method, path, body, expected))
        if path == "/api/v1/documents":
            if method == "POST":
                assert body == wire, "exact serialized request identity must replay"
                return {**copy.deepcopy(document), "document_id": "wrong_ack"} if changed else copy.deepcopy(document)
            return {"documents": copy.deepcopy(rows), "next_cursor": None}
        if path.endswith("/checks"):
            return {"checks": []}
        if path.endswith("/versions/2"):
            assert expected == 404
            assert not extra_version, "unexpected second version"
            return None
        return copy.deepcopy(document)

    return wire, call, calls


def test_replay_gate_accepts_exact_snapshot_and_rechecks_after_restart(probe):
    wire, call, calls = replay_client(probe)
    first = probe.verify_create_replay(call, wire)
    assert probe.verify_create_replay(call, wire, first) == first
    assert len([entry for entry in calls if entry[0] == "POST"]) == 2
    assert len([entry for entry in calls if entry[1].endswith("/versions/2")]) == 2


@pytest.mark.parametrize("failure", ["duplicate", "changed", "extra_version"])
def test_replay_gate_rejects_duplicate_wrong_ack_or_extra_history(probe, failure):
    wire, call, _ = replay_client(probe, **{failure: True})
    with pytest.raises(AssertionError):
        probe.verify_create_replay(call, wire)


def test_document_listing_follows_cursor_and_refuses_repeated_cursor(probe):
    paths = []

    def call(method, path):
        paths.append(path)
        if len(paths) == 1:
            return {"documents": [{"document_id": "first"}], "next_cursor": "opaque/cursor"}
        return {"documents": [{"document_id": "second"}], "next_cursor": None}

    assert probe.document_listing(call) == [{"document_id": "first"}, {"document_id": "second"}]
    assert paths[1] == "/api/v1/documents?cursor=opaque%2Fcursor"
    with pytest.raises(AssertionError, match="cursor repeated"):
        probe.document_listing(lambda *args: {"documents": [], "next_cursor": "same"})
