"""Negative readback/fault checks; these do not substitute actual Core execution."""
import copy
import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def probe(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts/probes"))
    spec = importlib.util.spec_from_file_location("journal_probe_test", ROOT / "scripts/probes/aaos01_working_state_runtime_loop.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def snapshot(probe):
    state = probe.empty_state()
    state["drafts"] = {"owned-note": {"base_version": 2, "editor_json": {
        "type": "doc", "content": [], "future": {"keep": [None, "中文", 1]}}}}
    state["pending_original"] = {"create_request_id": "fixed-request", "title": "中文", "editor_json": {"type": "doc", "content": []}}
    read = {"schema": "archeaxis.ui-working-state/v1", "workspace_id": "a" * 32,
            "restore_epoch": "initial", "state_revision": 3, "state": copy.deepcopy(state),
            "draft_digests": {"owned-note": "b" * 64}, "recovery_candidates": None,
            "recovery_requires_confirmation": False,
            "pending_document_id": "doc_req_" + hashlib.sha256(b"fixed-request").hexdigest()}
    return state, read


def test_opaque_fields_are_required_not_only_draft_count(probe):
    state, read = snapshot(probe)
    probe.assert_snapshot(read, state)
    del read["state"]["drafts"]["owned-note"]["editor_json"]["future"]
    with pytest.raises(AssertionError, match="opaque"):
        probe.assert_snapshot(read, state)


@pytest.mark.parametrize("field,value", [
    ("pending_document_id", "different-id"), ("draft_digests", {}),
    ("draft_digests", {"owned-note": "not-a-digest"}),
    ("recovery_requires_confirmation", True), ("recovery_candidates", {}),
])
def test_rejects_false_success_readbacks(probe, field, value):
    state, read = snapshot(probe)
    read[field] = value
    with pytest.raises(AssertionError):
        probe.assert_snapshot(read, state)


@pytest.mark.parametrize("field,value", [("workspace_id", "c" * 32), ("restore_epoch", "d" * 32), ("state_revision", 9)])
def test_rejects_wrong_workspace_restore_or_revision(probe, field, value):
    state, previous = snapshot(probe)
    read = copy.deepcopy(previous)
    read["state_revision"] += 1
    read[field] = value
    with pytest.raises(AssertionError):
        probe.assert_snapshot(read, state, previous, 1)


def test_discarded_ack_is_not_consumed_or_called_a_network_failure(probe, monkeypatch):
    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self):
            pytest.fail("fault injection must discard ACK unread")
    monkeypatch.setattr(probe.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    result = probe.discard_ack("http://127.0.0.1:1234", None, type("Client", (), {"headers": staticmethod(lambda _: {})}), {"fixture": "中文"})
    assert result["ack_body"] == "DISCARDED_UNREAD"
    assert result["fault_injection"] == "CLIENT_ACK_BODY_CONSUMPTION_ONLY"
    assert len(result["request_sha256"]) == 64
