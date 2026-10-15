"""Missing WebView exit ACK needs the same live-owned Popen handle's normal exit."""
import ast
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/probes/aaos01_tauri_webdriver_loop.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
scope = {}
nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
         and node.name in {"WebDriverProtocolError", "request_owned_product_exit"}]
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
