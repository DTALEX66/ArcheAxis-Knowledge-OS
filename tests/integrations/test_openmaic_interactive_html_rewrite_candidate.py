"""Finite synthetic tests for an unregistered, private HTML rewrite candidate.

No browser, actual caller material, network, Core, or input HTML script is run.
The explicit Node identity and selected vendor bytes are checked by the runner.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import types

import pytest

from scripts.release.tauri_portable_candidate import native
from tests.integrations.test_openmaic_interactive_url_map import (
    checked_node,
    digest,
    read_bytes,
    stage_sources,
    write_new,
)


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/learning-providers/openmaic"
WORKER = SERVICE / "interactive-html-rewrite-worker.mjs"
RUNNER = SERVICE / "interactive_html_rewrite_runner.py"
SCHEMA = "archeaxis.openmaic-interactive-html-rewrite/v1"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit preverified ARCHEAXIS_TEST_NODE is required")


@pytest.fixture(scope="module")
def candidate_stage(tmp_path_factory) -> Path:
    stage = tmp_path_factory.mktemp("html-candidate") / "h"
    stage_sources(stage)
    write_new(stage / WORKER.name, read_bytes(WORKER))
    return stage


@pytest.fixture
def runner(candidate_stage):
    module = types.ModuleType("openmaic_html_candidate_runner_test")
    module.__file__ = str(RUNNER)
    # Compile in memory so this test creates no __pycache__ beside the source.
    exec(compile(read_bytes(RUNNER), str(RUNNER), "exec"), module.__dict__)
    module.WORKER = candidate_stage / WORKER.name
    assert digest(read_bytes(module.WORKER)) == module.WORKER_SHA256
    return module


def request(html: bytes, request_id: str = "synthetic") -> bytes:
    return (json.dumps({"schema": SCHEMA, "request_id": request_id,
                        "html_utf8_base64": base64.b64encode(html).decode("ascii")},
                       separators=(",", ":")) + "\n").encode("ascii")


def raw_call(stage: Path, raw: bytes, *, override: dict[str, str] | None = None):
    """Synthetic direct child; bound both pipes and kill/wait this child only."""
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
    if override:
        env.update(override)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    process = subprocess.Popen([str(checked_node()), str(stage / WORKER.name)], cwd=str(stage), env=env,
                               shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=flags)
    streams: dict[str, bytes] = {}
    failures: list[str] = []

    def reader(pipe, key, limit):
        try:
            streams[key] = pipe.read(limit + 1)
            if len(streams[key]) > limit:
                process.kill()
        except (OSError, ValueError):
            failures.append("read")

    def writer():
        try:
            process.stdin.write(raw)
            process.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            # An intentionally early rejection may close the input pipe.
            pass

    threads = [threading.Thread(target=reader, args=(process.stdout, "stdout", 65_536), daemon=True),
               threading.Thread(target=reader, args=(process.stderr, "stderr", 8_192), daemon=True),
               threading.Thread(target=writer, daemon=True)]
    for thread in threads:
        thread.start()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        raise AssertionError("synthetic owned child exceeded its deadline")
    finally:
        for thread in threads:
            thread.join(timeout=5)
    assert not any(thread.is_alive() for thread in threads), "synthetic pipe cleanup unknown"
    assert not failures and process.returncode == 0
    assert len(streams["stdout"]) <= 65_536 and len(streams["stderr"]) <= 8_192
    return json.loads(streams["stdout"]), streams["stdout"], streams["stderr"]


def assert_process_reaped(result):
    process = result["process"]
    assert process["direct_child"] == "REAPED"
    assert process["pipe_threads"] == "JOINED"
    assert process["descendants"] == "UNKNOWN"
    assert process["network_isolation"] == "NOT_ESTABLISHED"


@requires_node
def test_candidate_preserves_byte_patch_and_reports_partial_scope(runner, monkeypatch):
    # This source is synthetic; it is never rendered. The two ambient settings
    # are not inherited by the child. The marker is a limited sentinel, not a
    # general proof that arbitrary HTML is safe to execute.
    monkeypatch.setenv("NODE_OPTIONS", "--this-option-must-not-be-inherited")
    monkeypatch.setenv("INTERACTIVE_ASSET_BASE_URL", "https://ambient.invalid")
    original = (
        '<p>😀outside\r\nkeep</p>'
        "<script SRC='https://unpkg.com/chart.js@4' integrity='sha384-old' "
        "crossorigin='use-credentials'></script>"
        '<img src="https://outside.invalid/private.png">'
        '<script src="https://unpkg.com/chart.js@4" src="https://hidden.invalid/x.js"></script>'
        '<style>\r\n@import "https://unpkg.com/chart.js@4";\r\n</style>'
        "<script>process.stdout.write('SYNTHETIC_EXECUTED_MARKER');"
        "globalThis.__AAOS_SYNTHETIC_SCRIPT_MARKER = true;</script>"
    ).encode("utf-8")
    result = runner.run_candidate(original, node_executable=checked_node())
    assert result["status"] == "OBSERVED_CANDIDATE"
    assert_process_reaped(result)
    assert result["process"]["exit_code"] == 0 and not result["process"]["termination_requested"]
    doc = result["candidate"]
    assert doc["scope"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert doc["privacy"] == "PRIVATE_INPUT_AND_OUTPUT"
    assert doc["original_preservation"] == "CALLER_RESPONSIBILITY"
    assert doc["unmatched_hosts_scope"] == "PARTIAL_REFERENCES_ONLY"
    assert doc["resource_availability"] == "NOT_VERIFIED"
    assert doc["network_isolation"] == "NOT_ESTABLISHED"
    assert doc["security_sanitizer"] is False and doc["core_authorization"] == "NOT_ESTABLISHED"
    assert "input_script_executed" not in doc
    output = base64.b64decode(doc["output_utf8_base64"], validate=True)
    patch = doc["patch"]
    assert patch["unit"] == "bytes"
    insert = base64.b64decode(patch["insert_base64"], validate=True)
    assert original[:patch["start"]] + insert + original[patch["start"] + patch["delete_bytes"]:] == output
    assert doc["input_sha256"] == digest(original) and doc["output_sha256"] == digest(output)
    assert doc["input_bytes"] == len(original) and doc["output_bytes"] == len(output)
    assert b"sha384-old" in original and b"sha384-old" not in output
    assert b"crossorigin='use-credentials'" in original and b'crossorigin="anonymous"' in output
    assert b"outside\r\nkeep" in output
    assert b"\r" not in output.split(b"<style>", 1)[1].split(b"</style>", 1)[0]
    assert b"outside.invalid/private.png" in output and b"hidden.invalid/x.js" in output
    # If this particular synthetic script ran in the Node process, the marker
    # would precede/corrupt its single JSON response and runner validation fails.
    assert b"SYNTHETIC_EXECUTED_MARKER" in output
    assert doc["upstream_unmatched_external_hosts"] == {}


@requires_node
def test_unmatched_hosts_cover_only_scanned_references(runner):
    html = b'<script src="https://listed.invalid/a.js"></script><img src="https://unscanned.invalid/a.png">'
    result = runner.run_candidate(html, node_executable=checked_node())
    assert result["status"] == "OBSERVED_CANDIDATE"
    assert result["candidate"]["upstream_unmatched_external_hosts"] == {"listed.invalid": 1}
    assert result["candidate"]["unmatched_hosts_scope"] == "PARTIAL_REFERENCES_ONLY"


@requires_node
def test_invalid_frames_and_private_sentinels_are_not_reflected(candidate_stage):
    secret = b"SYNTHETIC_PRIVATE_SENTINEL"
    encoded = base64.b64encode(secret)
    prefix = b'{"schema":"' + SCHEMA.encode() + b'","request_id":"ok",'
    cases = [
        (prefix + b'"request_\\u0069d":"SYNTHETIC_PRIVATE_SENTINEL","html_utf8_base64":""}', "INVALID_REQUEST"),
        (prefix + b'"html_utf8_base64":"' + encoded + b'","extra":"SYNTHETIC_PRIVATE_SENTINEL"}', "INVALID_REQUEST"),
        (prefix + b'"html_utf8_base64":"Zh=="}', "INVALID_REQUEST"),
        (request(b"\xff" + secret), "UNSUPPORTED_HTML"),
        (request(b"\xef\xbb\xbf" + secret), "UNSUPPORTED_HTML"),
        (request(b"\0" + secret), "UNSUPPORTED_HTML"),
        (request(b"x" * 8_193), "INVALID_REQUEST"),
        (request(b"<style>/*# SoUrCeMaPpInGuRl=data:application/json;base64,AA== */</style>" + secret),
         "UNSUPPORTED_SOURCE_MAP"),
    ]
    for raw, code in cases:
        result, stdout, stderr = raw_call(candidate_stage, raw)
        assert result["status"] == "REJECTED" and result["error_code"] == code
        assert result["source_verification"] == "NOT_ASSERTED"
        assert secret not in stdout + stderr and encoded not in stdout + stderr
        assert "input_sha256" not in result and "output_utf8_base64" not in result
    result, stdout, stderr = raw_call(candidate_stage, request(b"<p>ordinary</p>"),
                                     override={"INTERACTIVE_ASSET_BASE_URL": "https://wrong.invalid"})
    assert result["status"] == "REJECTED" and result["error_code"] == "ENVIRONMENT_OVERRIDE"
    assert b"wrong.invalid" not in stdout + stderr


@requires_node
def test_bounded_input_and_reply_validation(runner):
    original = b"x" * 8_192
    result = runner.run_candidate(original, node_executable=checked_node())
    assert result["status"] == "OBSERVED_CANDIDATE"
    doc = result["candidate"]
    assert base64.b64decode(doc["output_utf8_base64"]) == original
    assert doc["patch"] == {"unit": "bytes", "start": 8_192, "delete_bytes": 0, "insert_base64": ""}
    valid = json.dumps(doc, separators=(",", ":")).encode()
    assert runner._validate_reply(valid, original, doc["request_id"])[0] == "OBSERVED_CANDIDATE"
    changed = dict(doc, unexpected="SYNTHETIC_PRIVATE")
    assert runner._validate_reply(json.dumps(changed).encode(), original, doc["request_id"]) == (
        "REJECTED", "INVALID_WORKER_REPLY")
    changed = dict(doc, input_bytes=True)
    assert runner._validate_reply(json.dumps(changed).encode(), original, doc["request_id"])[0] == "REJECTED"
    changed = dict(doc, patch=dict(doc["patch"], start=0))
    assert runner._validate_reply(json.dumps(changed).encode(), original, doc["request_id"])[0] == "REJECTED"
    duplicate = valid[:-1] + b',"status":"OBSERVED_CANDIDATE"}'
    assert runner._validate_reply(duplicate, original, doc["request_id"])[0] == "REJECTED"
    too_big = runner.run_candidate(b"x" * 8_193, node_executable=checked_node())
    assert too_big["status"] == "REJECTED" and too_big["process"]["direct_child"] == "NOT_STARTED"


@requires_node
def test_identity_or_dependency_tampering_is_refused(candidate_stage, runner):
    fake_node = candidate_stage / "node.exe"
    write_new(fake_node, b"SYNTHETIC_FAKE_NODE")
    result = runner.run_candidate(b"<p>safe</p>", node_executable=fake_node)
    assert result["error_code"] == "NODE_IDENTITY_MISMATCH"
    assert result["process"]["direct_child"] == "NOT_STARTED"

    worker = candidate_stage / WORKER.name
    original = read_bytes(worker)
    try:
        with open(native(worker), "wb") as stream:
            stream.write(original + b"\n// SYNTHETIC_TAMPER\n")
        result = runner.run_candidate(b"<p>safe</p>", node_executable=checked_node())
        assert result["error_code"] == "WORKER_IDENTITY_MISMATCH"
        assert result["process"]["direct_child"] == "NOT_STARTED"
    finally:
        with open(native(worker), "wb") as stream:
            stream.write(original)

    dependency = candidate_stage / "vendor/npm/nanoid-3.3.19/non-secure/index.cjs"
    original = read_bytes(dependency)
    try:
        with open(native(dependency), "wb") as stream:
            stream.write(original + b"\n// SYNTHETIC_TAMPER\n")
        result = runner.run_candidate(b"<p>safe</p>", node_executable=checked_node())
        assert result["status"] == "REJECTED" and result["error_code"] == "DEPENDENCY_IDENTITY_MISMATCH"
        assert_process_reaped(result)
    finally:
        with open(native(dependency), "wb") as stream:
            stream.write(original)


def fake_worker(stage: Path, runner, name: str, source: bytes):
    # Test-only replacement; the real runner exposes no worker path in its API.
    path = stage / name
    write_new(path, source)
    runner.WORKER = path
    runner.WORKER_SHA256 = digest(source)


def assert_busy_without_wait(runner, node):
    outcome = {}
    caller = threading.Thread(target=lambda: outcome.update(
        runner.run_candidate(b"synthetic", node_executable=node)), daemon=True)
    caller.start()
    caller.join(timeout=2)
    assert not caller.is_alive(), "caller waited on an uncertain cleanup"
    assert outcome["status"] == "REJECTED" and outcome["error_code"] == "BUSY_OR_CLEANUP_UNCONFIRMED"
    assert outcome["process"]["direct_child"] == "NOT_STARTED"


@requires_node
def test_popen_after_real_spawn_exception_keeps_cleanup_unknown(candidate_stage, runner, monkeypatch):
    fake_worker(candidate_stage, runner, "synthetic-spawn-exception.mjs",
                b"process.stdin.resume();setTimeout(()=>process.exit(0),15000);\n")
    node = checked_node()
    real_popen = runner.subprocess.Popen
    owned = []

    def spawn_then_raise(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        owned.append(child)  # the test owns the original process handle
        raise OSError("SYNTHETIC_PRIVATE_SPAWN_ERROR")

    monkeypatch.setattr(runner.subprocess, "Popen", spawn_then_raise)
    try:
        result = runner.run_candidate(b"synthetic", node_executable=node)
        assert len(owned) == 1 and result["status"] == "REJECTED"
        assert result["error_code"] == "INTERNAL_FAILURE"
        assert result["process"]["direct_child"] == "UNKNOWN"
        assert result["process"]["pipe_threads"] == "UNKNOWN"
        assert "SYNTHETIC_PRIVATE_SPAWN_ERROR" not in json.dumps(result)
        assert_busy_without_wait(runner, node)
    finally:
        for child in owned:
            if child.poll() is None:
                try:
                    child.kill()
                except OSError:
                    pass
            child.wait(timeout=5)
            for pipe in (child.stdin, child.stdout, child.stderr):
                if pipe and not pipe.closed:
                    pipe.close()


@pytest.mark.parametrize(("stream", "exception_type"),
                         [(stream, error) for error in (OSError, RuntimeError) for stream in ("stdout", "stderr", "stdin")]
                         + [("stdout", SystemExit)])
@requires_node
def test_pipe_close_exception_keeps_slot_and_reports_io_failure(candidate_stage, runner, monkeypatch, stream, exception_type):
    fake_worker(candidate_stage, runner, "synthetic-close-exception-" + stream + "-" + exception_type.__name__ + ".mjs",
                b"process.stdin.resume();process.stdin.on('end',()=>process.stdout.write('{}'));\n")
    node = checked_node()
    real_popen = runner.subprocess.Popen
    owned = []

    class CloseFails:
        def __init__(self, original, close_first):
            self.stream = original
            self.close_first = close_first

        def read(self, size):
            return self.stream.read(size)

        def write(self, data):
            return self.stream.write(data)

        def close(self):
            # stdin must actually reach EOF for the synthetic child to exit;
            # the caller still cannot infer successful closure after an error.
            if self.close_first:
                self.stream.close()
            raise exception_type("SYNTHETIC_PRIVATE_CLOSE_ERROR")

    def with_failing_close(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        original = getattr(child, stream)
        replacement = CloseFails(original, stream == "stdin")
        setattr(child, stream, replacement)
        owned.append((child, original, replacement))
        return child

    monkeypatch.setattr(runner.subprocess, "Popen", with_failing_close)
    try:
        result = runner.run_candidate(b"synthetic", node_executable=node)
        assert result["status"] == "REJECTED" and result["error_code"] == "PIPE_IO_FAILED"
        # A joined thread is observed; actual pipe closure remains unconfirmed.
        assert result["process"]["direct_child"] == "REAPED"
        assert result["process"]["pipe_threads"] == "JOINED"
        assert "SYNTHETIC_PRIVATE_CLOSE_ERROR" not in json.dumps(result)
        assert_busy_without_wait(runner, node)
    finally:
        for child, original, replacement in owned:
            if child.poll() is None:
                try:
                    child.kill()
                except OSError:
                    pass
            child.wait(timeout=5)
            if not original.closed:
                original.close()
            for pipe in (child.stdin, child.stdout, child.stderr):
                if pipe is not replacement and pipe and not pipe.closed:
                    pipe.close()


@pytest.mark.parametrize(("stream", "exception_type"),
                         [(stream, RuntimeError) for stream in ("stdout", "stderr", "stdin")]
                         + [("stdin", SystemExit)])
@requires_node
def test_non_os_pipe_io_exception_is_private_and_releases_confirmed_closures(
        candidate_stage, runner, monkeypatch, stream, exception_type, capsys):
    fake_worker(candidate_stage, runner, "synthetic-io-exception-" + stream + "-" + exception_type.__name__ + ".mjs",
                b"process.stdin.resume();process.stdin.on('end',()=>process.stdout.write('{}'));\n")
    node = checked_node()
    real_popen = runner.subprocess.Popen
    input_closed = threading.Event()
    owned = []

    class TrackedInput:
        def __init__(self, original):
            self.original = original

        def write(self, data):
            if stream == "stdin":
                raise exception_type("SYNTHETIC_PRIVATE_PIPE_IO")
            return self.original.write(data)

        def close(self):
            try:
                self.original.close()
            finally:
                input_closed.set()

    class FaultyRead:
        def __init__(self, original):
            self.original = original

        def read(self, _size):
            if not input_closed.wait(timeout=10):
                raise exception_type("SYNTHETIC_PRIVATE_PIPE_IO")
            raise exception_type("SYNTHETIC_PRIVATE_PIPE_IO")

        def close(self):
            self.original.close()

    def with_failing_io(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        originals = (child.stdin, child.stdout, child.stderr)
        child.stdin = TrackedInput(originals[0])
        if stream == "stdout":
            child.stdout = FaultyRead(originals[1])
        if stream == "stderr":
            child.stderr = FaultyRead(originals[2])
        owned.append((child, originals))
        return child

    monkeypatch.setattr(runner.subprocess, "Popen", with_failing_io)
    try:
        result = runner.run_candidate(b"synthetic", node_executable=node)
        assert result["status"] == "REJECTED" and result["error_code"] == "PIPE_IO_FAILED"
        assert result["process"]["direct_child"] == "REAPED" and result["process"]["pipe_threads"] == "JOINED"
        assert "SYNTHETIC_PRIVATE_PIPE_IO" not in json.dumps(result)
        captured = capsys.readouterr()
        assert "SYNTHETIC_PRIVATE_PIPE_IO" not in captured.out + captured.err
        # The injected I/O error's close paths did complete; this instance can
        # accept another already-cancelled request without spawning a process.
        cancelled = threading.Event()
        cancelled.set()
        after = runner.run_candidate(b"synthetic", node_executable=node, cancelled=cancelled)
        assert after["error_code"] == "CANCELLED" and after["process"]["direct_child"] == "NOT_STARTED"
    finally:
        for child, originals in owned:
            if child.poll() is None:
                try:
                    child.kill()
                except OSError:
                    pass
            child.wait(timeout=5)
            for pipe in originals:
                if pipe and not pipe.closed:
                    pipe.close()


def _observed_owned_child(real_popen, owned, closes, *args, **kwargs):
    child = real_popen(*args, **kwargs)
    originals = {name: getattr(child, name) for name in ("stdout", "stderr", "stdin")}

    class ObservedPipe:
        def __init__(self, name, original):
            self.name, self.original = name, original

        def __getattr__(self, name):
            return getattr(self.original, name)

        def close(self):
            closes.append((self.name, threading.get_ident()))
            self.original.close()

    for name, original in originals.items():
        setattr(child, name, ObservedPipe(name, original))
    owned.append((child, originals))  # retain only this test's original Popen handle
    return child


def _clean_owned_children(owned, readers):
    for child, _ in owned:
        if child.poll() is None:
            try:
                child.kill()
            except OSError:
                pass
        child.wait(timeout=5)
    for thread in readers:
        thread.join(timeout=5)
        assert not thread.is_alive(), "test-owned reader cleanup unknown"
    for _, originals in owned:
        for pipe in originals.values():
            if pipe and not pipe.closed:
                pipe.close()


@pytest.mark.parametrize("unhanded_close_fails", [False, True])
@requires_node
def test_thread_construction_exception_closes_unhanded_pipes(
        candidate_stage, runner, monkeypatch, unhanded_close_fails, capsys):
    fake_worker(candidate_stage, runner, "synthetic-thread-construction-exception-" + str(unhanded_close_fails) + ".mjs",
                b"process.stdin.resume();setTimeout(()=>process.exit(0),15000);\n")
    node = checked_node()
    real_popen, real_thread = runner.subprocess.Popen, threading.Thread
    owned, closes = [], []
    caller_ident = threading.get_ident()
    close_attempted = threading.Event()

    class FailingClose:
        def __init__(self, original):
            self.original = original

        def __getattr__(self, name):
            return getattr(self.original, name)

        def close(self):
            close_attempted.set()
            raise RuntimeError("SYNTHETIC_PRIVATE_UNHANDED_CLOSE_ERROR")

    def capture(*args, **kwargs):
        child = _observed_owned_child(real_popen, owned, closes, *args, **kwargs)
        if unhanded_close_fails:
            child.stderr = FailingClose(child.stderr)
        return child

    def fail_second_construction(*args, **kwargs):
        target, values = kwargs.get("target"), kwargs.get("args", ())
        if getattr(target, "__name__", "") == "read_pipe" and len(values) >= 2 and values[1] == "stderr":
            raise RuntimeError("SYNTHETIC_PRIVATE_CONSTRUCTION_ERROR")
        return real_thread(*args, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", capture)
    monkeypatch.setattr(threading, "Thread", fail_second_construction)
    try:
        result = runner.run_candidate(b"synthetic", node_executable=node)
        assert result["status"] == "REJECTED" and result["error_code"] == "INTERNAL_FAILURE"
        assert result["process"]["direct_child"] == "REAPED"
        assert result["process"]["pipe_threads"] == "UNKNOWN"
        assert len(owned) == 1 and owned[0][1]["stdout"].closed and owned[0][1]["stdin"].closed
        assert owned[0][1]["stderr"].closed is (not unhanded_close_fails)
        assert close_attempted.is_set() is unhanded_close_fails
        expected_closes = ("stdout", "stdin") if unhanded_close_fails else ("stdout", "stderr", "stdin")
        assert set(closes) == {(name, caller_ident) for name in expected_closes}
        assert "SYNTHETIC_PRIVATE_CONSTRUCTION_ERROR" not in json.dumps(result)
        captured = capsys.readouterr()
        assert "SYNTHETIC_PRIVATE_UNHANDED_CLOSE_ERROR" not in captured.out + captured.err
        assert_busy_without_wait(runner, node)
    finally:
        _clean_owned_children(owned, [])


@pytest.mark.parametrize("start_then_raise", [False, True])
@requires_node
def test_thread_start_exception_keeps_partial_pipe_cleanup_unknown(
        candidate_stage, runner, monkeypatch, start_then_raise):
    fake_worker(candidate_stage, runner, "synthetic-thread-exception-" + str(start_then_raise) + ".mjs",
                b"process.stdin.resume();setTimeout(()=>process.exit(0),15000);\n")
    node = checked_node()
    real_popen, real_start = runner.subprocess.Popen, threading.Thread.start
    owned, closes, started_readers = [], [], []
    caller_ident = threading.get_ident()

    def capture(*args, **kwargs):
        return _observed_owned_child(real_popen, owned, closes, *args, **kwargs)

    def fail_second_reader(thread, *args, **kwargs):
        target = getattr(thread, "_target", None)
        values = getattr(thread, "_args", ())
        if getattr(target, "__name__", "") == "read_pipe" and len(values) >= 2:
            if values[1] == "stderr":
                if start_then_raise:
                    real_start(thread, *args, **kwargs)
                    started_readers.append(thread)
                raise RuntimeError("SYNTHETIC_PRIVATE_THREAD_ERROR")
            if values[1] == "stdout":
                result = real_start(thread, *args, **kwargs)
                started_readers.append(thread)
                return result
        return real_start(thread, *args, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", capture)
    monkeypatch.setattr(threading.Thread, "start", fail_second_reader)
    try:
        result = runner.run_candidate(b"synthetic", node_executable=node)
        assert result["status"] == "REJECTED" and result["error_code"] == "INTERNAL_FAILURE"
        assert result["process"]["direct_child"] == "REAPED"
        assert result["process"]["pipe_threads"] == "UNKNOWN"
        assert len(owned) == 1 and owned[0][1]["stdin"].closed and owned[0][1]["stdout"].closed
        assert ("stdin", caller_ident) in closes
        assert ("stderr", caller_ident) not in closes  # its start may have succeeded
        if not start_then_raise:
            assert not owned[0][1]["stderr"].closed
        assert started_readers and not any(thread.is_alive() for thread in started_readers)
        assert "SYNTHETIC_PRIVATE_THREAD_ERROR" not in json.dumps(result)
        assert_busy_without_wait(runner, node)
    finally:
        _clean_owned_children(owned, started_readers)


@requires_node
def test_cancellation_after_spawn_reaps_only_owned_child(candidate_stage, runner, monkeypatch):
    fake_worker(candidate_stage, runner, "synthetic-wait.mjs",
                b"process.stdin.resume(); setInterval(() => {}, 1000);\n")
    cancelled = threading.Event()
    real_popen = runner.subprocess.Popen

    def start_then_cancel(*args, **kwargs):
        assert kwargs["shell"] is False
        assert kwargs["stdin"] == kwargs["stdout"] == kwargs["stderr"] == subprocess.PIPE
        assert "NODE_OPTIONS" not in kwargs["env"] and "NODE_PATH" not in kwargs["env"]
        assert "INTERACTIVE_ASSET_BASE_URL" not in kwargs["env"]
        if os.name == "nt":
            assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW
        child = real_popen(*args, **kwargs)
        cancelled.set()
        return child

    monkeypatch.setattr(runner.subprocess, "Popen", start_then_cancel)
    result = runner.run_candidate(b"SYNTHETIC_PRIVATE", node_executable=checked_node(), cancelled=cancelled)
    # Cancellation can race the first stdin flush. A failing close is reported
    # as an I/O cleanup failure and must keep the slot closed.
    assert result["status"] == "REJECTED" and result["error_code"] in ("CANCELLED", "PIPE_IO_FAILED")
    assert_process_reaped(result)
    assert result["process"]["termination_requested"] is True
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result)
    if result["error_code"] == "PIPE_IO_FAILED":
        after = runner.run_candidate(b"synthetic", node_executable=checked_node(), cancelled=cancelled)
        assert after["error_code"] == "BUSY_OR_CLEANUP_UNCONFIRMED"


@requires_node
def test_concurrent_busy_rejection_never_queues_waiting_caller(candidate_stage, runner, monkeypatch):
    fake_worker(candidate_stage, runner, "synthetic-concurrent.mjs",
                b"import {writeFileSync} from 'node:fs';process.stdin.resume();"
                b"process.stdin.on('end',()=>{writeFileSync('concurrent-ready','OK',{flag:'wx'});"
                b"setInterval(()=>{},1000);});\n")
    node = checked_node()
    started = threading.Event()
    cancelled = threading.Event()
    second_cancelled = threading.Event()
    real_popen = runner.subprocess.Popen
    outcome = {}
    second_outcome = {}

    def notify_spawn(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        started.set()
        return child

    monkeypatch.setattr(runner.subprocess, "Popen", notify_spawn)
    first = threading.Thread(target=lambda: outcome.update(
        runner.run_candidate(b"<p>first</p>", node_executable=node, cancelled=cancelled)), daemon=True)
    second = threading.Thread(target=lambda: second_outcome.update(
        runner.run_candidate(b"<p>second</p>", node_executable=node, cancelled=second_cancelled)), daemon=True)
    first.start()
    try:
        assert started.wait(timeout=20), "first test-owned child did not start"
        ready = candidate_stage / "concurrent-ready"
        ready_deadline = time.monotonic() + 10
        while not os.path.exists(native(ready)):
            assert first.is_alive() and time.monotonic() < ready_deadline, "stdin close was not observed"
            time.sleep(0.01)
        second.start()
        second.join(timeout=2)
        assert not second.is_alive(), "busy caller was left waiting"
        assert second_outcome["status"] == "REJECTED"
        assert second_outcome["error_code"] == "BUSY_OR_CLEANUP_UNCONFIRMED"
        assert second_outcome["process"]["direct_child"] == "NOT_STARTED"
    finally:
        cancelled.set()
        second_cancelled.set()
        first.join(timeout=10)
        if second.ident is not None:
            second.join(timeout=10)
    assert not first.is_alive(), "test-owned caller did not finish after cancellation"
    assert not second.is_alive(), "test-owned busy caller did not finish after cancellation"
    assert outcome["status"] == "REJECTED" and outcome["error_code"] == "CANCELLED"
    assert_process_reaped(outcome)
    already_cancelled = threading.Event()
    already_cancelled.set()
    after = runner.run_candidate(b"<p>after</p>", node_executable=node, cancelled=already_cancelled)
    assert after["error_code"] == "CANCELLED" and after["process"]["direct_child"] == "NOT_STARTED"


@requires_node
@pytest.mark.skipif(os.name != "nt", reason="checks the Windows pipe boundary")
def test_unconfirmed_pipe_cleanup_keeps_instance_fail_closed(candidate_stage, runner, monkeypatch):
    # The holder is a *sibling* of the runner's child, not its descendant. Both
    # receive the SAME anonymous pipe's write end. The ready file is written
    # only after the holder has successfully written synthetic bytes to it.
    fake_worker(candidate_stage, runner, "synthetic-held-pipe.mjs",
                b"process.stdin.resume(); process.stdin.on('end',()=>process.exit(0));\n")
    holder_script = candidate_stage / "synthetic-pipe-holder.mjs"
    write_new(holder_script,
              b"import {writeSync,writeFileSync} from 'node:fs';"
              b"writeSync(1,'SYNTHETIC_PIPE_HELD');"
              b"writeFileSync('holder-ready','READY',{flag:'wx'});"
              b"process.stdin.resume();process.stdin.on('end',()=>process.exit(0));"
              b"setTimeout(()=>process.exit(0),15000);\n")
    node = checked_node()
    real_popen = runner.subprocess.Popen
    read_fd, write_fd = os.pipe()
    state = {"read_fd": read_fd, "write_fd": write_fd, "worker": None, "first": None}
    holder = None
    outcome = {}
    first_cancelled = threading.Event()
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
    try:
        holder = real_popen([str(node), str(holder_script)], cwd=str(candidate_stage), env=env,
                            shell=False, stdin=subprocess.PIPE, stdout=write_fd, stderr=subprocess.DEVNULL,
                            close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW)
        ready = candidate_stage / "holder-ready"
        ready_deadline = time.monotonic() + 10
        while not os.path.exists(native(ready)):
            assert holder.poll() is None, "test-owned pipe holder exited before writing"
            assert time.monotonic() < ready_deadline, "test-owned pipe holder did not become ready"
            time.sleep(0.01)
        assert read_bytes(ready) == b"READY" and holder.poll() is None

        def use_same_pipe(*args, **kwargs):
            assert kwargs["stdout"] == subprocess.PIPE and state["write_fd"] is not None
            kwargs["stdout"] = state["write_fd"]
            try:
                child = real_popen(*args, **kwargs)
                state["worker"] = child
                child.stdout = os.fdopen(state["read_fd"], "rb")
                state["read_fd"] = None  # the runner now owns this read end
                return child
            finally:
                os.close(state["write_fd"])
                state["write_fd"] = None  # the test parent no longer holds a write end

        monkeypatch.setattr(runner.subprocess, "Popen", use_same_pipe)
        first = threading.Thread(target=lambda: outcome.update(
            runner.run_candidate(b"<p>synthetic</p>", node_executable=node,
                                 cancelled=first_cancelled)), daemon=True)
        state["first"] = first
        first.start()
        first.join(timeout=20)
        assert not first.is_alive(), "pipe cleanup left the first caller waiting"
        result = outcome
        assert result["status"] == "REJECTED" and result["error_code"] == "PIPE_CLEANUP_UNKNOWN"
        assert result["process"]["direct_child"] == "REAPED" and result["process"]["exit_code"] == 0
        assert result["process"]["pipe_threads"] == "UNKNOWN"
        assert result["process"]["descendants"] == "UNKNOWN"
        assert state["read_fd"] is None and state["write_fd"] is None
        assert holder.poll() is None, "pipe holder exited before the boundary was observed"
        busy_outcome = {}
        busy = threading.Thread(target=lambda: busy_outcome.update(
            runner.run_candidate(b"<p>second</p>", node_executable=node)), daemon=True)
        busy.start()
        busy.join(timeout=2)
        assert not busy.is_alive(), "unconfirmed cleanup left the caller waiting"
        assert busy_outcome["error_code"] == "BUSY_OR_CLEANUP_UNCONFIRMED"
        assert busy_outcome["process"]["direct_child"] == "NOT_STARTED"

        # Closing this owned child's stdin releases its same-pipe write end.
        holder.stdin.close()
        assert holder.wait(timeout=5) == 0
        again = runner.run_candidate(b"<p>third</p>", node_executable=node)
        assert again["error_code"] == "BUSY_OR_CLEANUP_UNCONFIRMED"
    finally:
        cleanup_unknown = False
        first_cancelled.set()
        if holder is not None:
            try:
                if holder.stdin and not holder.stdin.closed:
                    holder.stdin.close()
            except (OSError, ValueError):
                pass
            try:
                holder.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # This is the original Popen handle created by this test, not a
                # process reopened by PID after a possible identity change.
                try:
                    holder.kill()
                except OSError:
                    pass
                try:
                    holder.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    cleanup_unknown = True
            except OSError:
                cleanup_unknown = True
        worker = state["worker"]
        if worker is not None:
            try:
                if worker.poll() is None:
                    try:
                        worker.kill()
                    except OSError:
                        pass
                worker.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                cleanup_unknown = True
        if state["first"] is not None:
            state["first"].join(timeout=5)
            cleanup_unknown |= state["first"].is_alive()
        # Only close parent-owned descriptors after the runner thread has
        # stopped, so no concurrent spawn can reuse a stale descriptor number.
        if state["first"] is None or not state["first"].is_alive():
            for name in ("write_fd", "read_fd"):
                if state[name] is not None:
                    try:
                        os.close(state[name])
                        state[name] = None
                    except OSError:
                        cleanup_unknown = True
        assert not cleanup_unknown, "test-owned pipe or direct-process cleanup unconfirmed"


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
@requires_node
def test_parent_bounds_each_pipe_and_does_not_reflect_it(candidate_stage, runner, stream):
    limit = runner.MAX_STDOUT if stream == "stdout" else runner.MAX_STDERR
    repetitions = limit // len("SYNTHETIC_SECRET") + 128
    body = (f"process.stdin.resume(); process.stdin.on('end', () => {{ "
            f"process.{stream}.write('SYNTHETIC_SECRET'.repeat({repetitions})); "
            f"setInterval(() => {{}}, 1000); }});\n").encode()
    fake_worker(candidate_stage, runner, "synthetic-overflow-" + stream + ".mjs", body)
    result = runner.run_candidate(b"<p>synthetic</p>", node_executable=checked_node())
    assert result["status"] == "REJECTED" and result["error_code"] == "OUTPUT_LIMIT_EXCEEDED"
    assert_process_reaped(result)
    assert "SYNTHETIC_SECRET" not in json.dumps(result)


@requires_node
def test_timeout_during_child_is_not_misreported_as_success(candidate_stage, runner, monkeypatch):
    fake_worker(candidate_stage, runner, "synthetic-timeout.mjs",
                b"process.stdin.resume(); setInterval(() => {}, 1000);\n")
    # This case isolates owned-child timing; fixed Node is checked separately by
    # checked_node and identity/tamper tests, rather than racing its large hash.
    node = checked_node()
    monkeypatch.setattr(runner, "_identity", lambda *_args, **_kwargs: True)
    result = runner.run_candidate(b"<p>synthetic</p>", node_executable=node, timeout_seconds=3)
    assert result["status"] == "REJECTED" and result["error_code"] == "DEADLINE_EXCEEDED"
    assert_process_reaped(result)
    assert result["process"]["termination_requested"] is True
