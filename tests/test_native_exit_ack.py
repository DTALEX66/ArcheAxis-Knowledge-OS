"""Missing WebView exit ACK needs the same live-owned Popen handle's normal exit."""
import ast
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/probes/aaos01_tauri_webdriver_loop.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
scope = {"re": re, "time": time, "subprocess": subprocess, "json": json, "hashlib": hashlib}
nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
         and node.name in {"WebDriverProtocolError", "request_owned_product_exit", "read_owned_core_shutdown_report", "owned_exit_timeout_snapshot"}]
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), scope)
exit_owned = scope["request_owned_product_exit"]
ProtocolError = scope["WebDriverProtocolError"]


def run_exit(reply=None, *, code=0, before=None, created=77, failure=None):
    host = Mock(pid=12)
    host.poll.side_effect = [before, code]
    host.wait.return_value = code
    if failure:
        host.wait.side_effect = failure
    send = Mock(return_value=reply)
    receipt = {}
    exit_owned(host, {"pid":12, "created":77}, [{"pid":12, "created":created}], send, receipt)
    send.assert_called_once_with()
    host.wait.assert_called_once_with(timeout=15)
    return receipt


@pytest.mark.parametrize("reply,ack", [(None,"MISSING_ON_EXIT"), ({"ok":True,"value":None},"CONFIRMED")])
def test_exit_ack_is_not_the_process_exit_proof(reply, ack):
    receipt = run_exit(reply)
    assert receipt["host_shutdowns"] == [{"pid":12,"created":77,"ack":ack,
        "exited":True,"exit_code":0,"method":"product_exit_application_attached_observer"}]


@pytest.mark.parametrize("reply", [{"ok":False,"error":"refused"}, {}, {"ok":True}, [], "closed"])
def test_explicit_refusal_and_malformed_ack_fail(reply):
    with pytest.raises(AssertionError):
        run_exit(reply)


@pytest.mark.parametrize("options", [{"code":1}, {"before":0}, {"created":78}])
def test_nonzero_exit_early_exit_and_recycled_pid_never_qualify(options):
    with pytest.raises(AssertionError):
        run_exit(**options)


def test_live_host_timeout_never_qualifies():
    with pytest.raises(subprocess.TimeoutExpired):
        run_exit(failure=subprocess.TimeoutExpired("owned-host", 15))


def test_identity_failure_does_not_send_exit_to_another_process():
    host, send = Mock(pid=12), Mock()
    with pytest.raises(AssertionError):
        exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":78}], send, {})
    send.assert_not_called()
    host.wait.assert_not_called()


def test_other_native_commands_keep_missing_ack_as_failure():
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    command = next(node for node in main.body if isinstance(node, ast.FunctionDef) and node.name == "native_command")
    env = {"request":Mock(return_value=None), "session":"owned"}
    exec(compile(ast.Module(body=[command], type_ignores=[]), str(SOURCE), "exec"), env)
    with pytest.raises((AssertionError, TypeError)):
        env["native_command"]("unrelated_command")
    env["request"].assert_called_once()


@pytest.mark.parametrize("error", [OSError("closed"), ProtocolError({"error":"no such window"}),
                                   ProtocolError({"error":"invalid session id"})])
def test_closed_exit_transport_still_requires_normal_owned_exit(error):
    host = Mock(pid=12)
    host.poll.side_effect = [None, 0]
    host.wait.return_value = 0
    send, receipt = Mock(side_effect=error), {}
    exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":77}], send, receipt)
    send.assert_called_once_with()
    host.wait.assert_called_once_with(timeout=15)
    assert receipt["host_shutdowns"][0]["ack"] == "TRANSPORT_CLOSED"


def test_unrelated_protocol_error_is_not_hidden_by_eventual_exit():
    host, send = Mock(pid=12), Mock(side_effect=ProtocolError({"error":"unknown command"}))
    host.poll.return_value = None
    with pytest.raises(ProtocolError):
        exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":77}], send, {})
    send.assert_called_once_with()
    host.wait.assert_not_called()


DETACHED_MESSAGE = ("target frame detached\n  (failed to check if window was closed: "
                    "disconnected: Unable to receive message from renderer)"
                    "\n  (Session info: MicrosoftEdge=154.0.4258.62)")


@pytest.mark.parametrize("code,failure", [(0,None), (1,None),
    (0,subprocess.TimeoutExpired("owned-host",15))])
def test_exact_exit_frame_detach_still_requires_owned_natural_exit_zero(code, failure):
    host = Mock(pid=12)
    host.poll.side_effect = [None, code]
    host.wait.return_value = code
    if failure:
        host.wait.side_effect = failure
    send = Mock(side_effect=ProtocolError({"error":"target frame detached", "message":DETACHED_MESSAGE}))
    receipt = {}
    if code or failure:
        with pytest.raises((AssertionError, subprocess.TimeoutExpired)):
            exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":77}], send, receipt)
    else:
        exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":77}], send, receipt)
        assert receipt["host_shutdowns"][0]["exited"] is True
        attempt = receipt["requested_product_exits"][0]
        assert {key: attempt[key] for key in ("pid", "created", "requested", "ack", "error_type")} == {
            "pid":12, "created":77, "requested":True, "ack":"TRANSPORT_CLOSED",
            "error_type":"target frame detached"}
        assert attempt["attempt_number"] == 1 and attempt["wait_result"] == "RETURNED"
        assert attempt["wait_timeout_seconds"] == attempt["shared_exit_budget_seconds"] == 15
    host.wait.assert_called_once_with(timeout=15)


@pytest.mark.parametrize("value", [
    {"error":"unknown error", "message":DETACHED_MESSAGE},
    {"error":"target frame detached"},
    {"error":"target frame detached", "message":None},
    {"error":"target frame detached", "message":"target frame detached"},
    {"error":"target frame detached", "message":DETACHED_MESSAGE.replace("window was closed", "renderer crashed")},
    {"error":"target frame detached", "message":DETACHED_MESSAGE + "\nother renderer error"},
])
def test_other_frame_detach_or_renderer_failures_are_not_expected_exit(value):
    host, send = Mock(pid=12), Mock(side_effect=ProtocolError(value))
    host.poll.return_value = None
    with pytest.raises(ProtocolError):
        exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":77}], send, {})
    host.wait.assert_not_called()


def test_detach_never_bypasses_creation_guard_or_requests_exit_of_recycled_pid():
    host = Mock(pid=12)
    send = Mock(side_effect=ProtocolError({"error":"target frame detached", "message":DETACHED_MESSAGE}))
    with pytest.raises(AssertionError):
        exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":78}], send, {})
    send.assert_not_called()
    host.wait.assert_not_called()


def test_frame_detach_from_an_ordinary_command_still_propagates():
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    command = next(node for node in main.body if isinstance(node, ast.FunctionDef) and node.name == "native_command")
    env = {"request":Mock(side_effect=ProtocolError({
        "error":"target frame detached", "message":DETACHED_MESSAGE})), "session":"owned"}
    exec(compile(ast.Module(body=[command], type_ignores=[]), str(SOURCE), "exec"), env)
    with pytest.raises(ProtocolError):
        env["native_command"]("unrelated_command")


def test_zero_remaining_budget_preserves_first_timeout_before_cleanup_attempt():
    host = Mock(pid=12)
    host.poll.return_value = None
    first_error = subprocess.TimeoutExpired("owned-host", 0)
    host.wait.side_effect = first_error
    receipt = {}
    send = Mock(return_value={"ok": True, "value": None})
    confirm = Mock(return_value=0)
    observe = Mock(return_value={"stage": "AFTER_WAIT_TIMEOUT_BEFORE_CLEANUP_RETRY"})
    with pytest.raises(subprocess.TimeoutExpired) as raised:
        exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":77}], send, receipt,
                   confirm_synthetic=confirm, diagnose_timeout=observe)
    assert raised.value is first_error
    send.assert_called_once_with()
    confirm.assert_called_once_with(receipt["requested_product_exits"][0], 15)
    observe.assert_called_once_with()
    host.wait.assert_called_once_with(timeout=0)
    attempt = receipt["requested_product_exits"][0]
    assert attempt["ack"] == "CONFIRMED" and attempt["wait_result"] == "TIMEOUT"
    assert attempt["shared_exit_budget_seconds"] == 15 and attempt["wait_timeout_seconds"] == 0
    assert attempt["confirmation_observation"]["owned_yes_posted"] is False
    assert attempt["timeout_snapshot"]["stage"] == "AFTER_WAIT_TIMEOUT_BEFORE_CLEANUP_RETRY"
    assert attempt["wait_elapsed_ms"] >= 0 and attempt["request_to_timeout_ms"] >= 0
    assert "host_shutdowns" not in receipt and "ok" not in receipt
    # Existing finally cleanup may succeed; it must not rewrite the failed attempt.
    host.poll.side_effect = [None, 0]
    host.wait.side_effect = None
    host.wait.return_value = 0
    exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":77}], send, receipt)
    assert len(receipt["requested_product_exits"]) == 2
    assert receipt["requested_product_exits"][0] is attempt and attempt["wait_result"] == "TIMEOUT"
    assert receipt["requested_product_exits"][1]["wait_result"] == "RETURNED"
    assert len(receipt["host_shutdowns"]) == 1 and receipt["host_shutdowns"][0]["exit_code"] == 0
    assert "ok" not in receipt


def test_passive_observer_failure_does_not_replace_original_timeout_or_leak_message():
    host = Mock(pid=12)
    host.poll.return_value = None
    error = subprocess.TimeoutExpired("owned-host", 15)
    host.wait.side_effect = error
    receipt = {}
    observe = Mock(side_effect=ValueError("PRIVATE_DIAGNOSTIC_TEXT"))
    with pytest.raises(subprocess.TimeoutExpired) as raised:
        exit_owned(host, {"pid":12,"created":77}, [{"pid":12,"created":77}],
                   Mock(return_value=None), receipt, diagnose_timeout=observe)
    assert raised.value is error
    assert receipt["requested_product_exits"][0]["timeout_snapshot_error_type"] == "ValueError"
    assert "PRIVATE_DIAGNOSTIC_TEXT" not in json.dumps(receipt)
    host.wait.assert_called_once_with(timeout=15)


def shutdown_fixture():
    return {"pid": 44, "method": "session_http", "outcome": "GRACEFUL",
            "request_acknowledged": True, "forced_attempted": False,
            "return_code": 0, "wait_reaped": True, "elapsed_ms": 123}


def test_shutdown_snapshot_reads_only_allowlisted_metadata_and_marks_stale_possibility(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    value = dict(shutdown_fixture(), secret="PRIVATE_BODY", error="PRIVATE_ERROR")
    (data / "core-shutdown-result.json").write_text(json.dumps(value), encoding="utf-8")
    report = scope["read_owned_core_shutdown_report"](tmp_path)
    assert report["status"] == "READ_OK" and report["report"] == shutdown_fixture()
    assert report["attribution"] == "FILE_SNAPSHOT_ONLY_MAY_PREDATE_THIS_HOST_EXIT"
    assert "PRIVATE" not in json.dumps(report)


@pytest.mark.parametrize("contents,status", [(b"not-json", "INVALID_JSON"),
    (b"x" * 16385, "TOO_LARGE"), (b'{}', "INVALID_SCHEMA"),
    (json.dumps(dict(shutdown_fixture(), outcome="PRIVATE_RAW_ERROR")).encode(), "INVALID_SCHEMA"),
    (json.dumps(dict(shutdown_fixture(), pid=True)).encode(), "INVALID_SCHEMA"),
    (json.dumps(dict(shutdown_fixture(), method=[])).encode(), "INVALID_SCHEMA"),
    (json.dumps({key: value for key, value in shutdown_fixture().items() if key != "return_code"}).encode(), "INVALID_SCHEMA")])
def test_shutdown_snapshot_rejects_unbounded_or_malformed_metadata(tmp_path, contents, status):
    data = tmp_path / "data"
    data.mkdir()
    (data / "core-shutdown-result.json").write_bytes(contents)
    report = scope["read_owned_core_shutdown_report"](tmp_path)
    assert report["status"] == status and "report" not in report
    assert "PRIVATE" not in json.dumps(report)


def test_shutdown_snapshot_missing_or_link_never_reads_other_files(tmp_path, monkeypatch):
    assert scope["read_owned_core_shutdown_report"](tmp_path) == {"status": "MISSING"}
    monkeypatch.setattr(Path, "is_symlink", lambda self: self.name == "data")
    monkeypatch.setattr(Path, "open", Mock(side_effect=AssertionError("must not open link")))
    assert scope["read_owned_core_shutdown_report"](tmp_path) == {"status": "REFUSED_LINK"}


def test_timeout_snapshot_never_enumerates_recycled_pid_windows(tmp_path, monkeypatch):
    host = Mock(pid=12)
    host.poll.return_value = None
    monkeypatch.setitem(scope, "native_process_rows", lambda: [{"pid":12, "created":78}])
    load = Mock(side_effect=AssertionError("foreign windows must not be read"))
    monkeypatch.setitem(scope, "load", load)
    monkeypatch.setitem(scope, "REPO", tmp_path)
    snapshot = scope["owned_exit_timeout_snapshot"](host, {"pid":12,"created":77}, tmp_path)
    assert snapshot["same_creation_observed"] is False and "windows" not in snapshot
    assert snapshot["observed_processes"] == [{"pid":12, "created":78}]
    assert snapshot["core_shutdown_result"]["status"] == "MISSING"
    load.assert_not_called()
