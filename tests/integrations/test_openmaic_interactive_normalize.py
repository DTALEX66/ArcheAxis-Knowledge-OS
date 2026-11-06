"""Finite synthetic checks for the unregistered interactive HTML normalizer.

Only fixed synthetic replies, the pinned Node and the selected vendor bytes run.
The model is never called and nothing is rendered or persisted.
"""
from __future__ import annotations

import base64
import copy
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
DONOR = SERVICE / "vendor/scene-content-0.3.28-original/generation"
WORKER = SERVICE / "interactive-normalize-worker.mjs"
RUNNER = SERVICE / "interactive_normalize_runner.py"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit preverified ARCHEAXIS_TEST_NODE is required")
SCHEMA = "archeaxis.openmaic-interactive-normalize/v1"
WORKER_SHA256 = "a59d60c116bb168f184cf737e40f398bc36966e950f5f8d60523744a34f40826"
ORIGINALS = {
    "ORIGINALS.json": "5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3",
    "package.json": "5308b268d06dd27e592de00f02d57b046588df0d6e160f4179788388d5a806d1",
    "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
    "src/interactive-post-processor.ts": "aeadbe3727b72752b14b138bea8d74db75e670ecca3b313fc40b000442dbc770",
    "src/interactive-script-validator.ts": "351d9f65642932e54a7f4f3e2192967a164dac15637ed0c498d6621125d4839e",
    "src/interactive-library-mapper.ts": "fe4637cc0e32cd557dcdc285017008cfe741e7799478a9c9ec102cc97194b1fe",
    "src/interactive-libraries.ts": "1c9f212d7e2010dd3e1f4889efe22825fcb1f52772b056e5a30fc58753f29de1",
}
# Independently recomputed from the donor's own post-processor on this reply.
PINNED = {
    "input_sha256": "c520b2a224aa1d6293302e5792dbddd9018796ee35e4433186d632428b58e95c",
    "output_sha256": "20c7a9ea851f07d7cffe7408ef9233f49f887fb1b559be4eca49e0ae0ba412c6",
    "output_bytes": 2647,
    "extracted_bytes": 166,
}
MATH_REPLY = (
    "<!DOCTYPE html><html><head><title>t</title></head><body>"
    "<script>const a = 1; function ok(){return a;}</script>"
    "<p>energy $E=mc^2$ and $$a^2+b^2=c^2$$</p>"
    "</body></html>"
)


def encode(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def request(reply: str, widget: str = "simulation", request_id: str = "synthetic") -> bytes:
    return encode({"schema": SCHEMA, "request_id": request_id, "widget_type": widget,
                   "reply_utf8_base64": base64.b64encode(reply.encode("utf-8")).decode("ascii")})


@pytest.fixture(scope="module")
def stage(tmp_path_factory) -> Path:
    target = tmp_path_factory.mktemp("interactive-normalize") / "h"
    stage_sources(target)
    root = target / "vendor/scene-content-0.3.28-original/generation"
    for name in ("src/interactive-post-processor.ts", "src/interactive-script-validator.ts"):
        write_new(root.joinpath(*name.split("/")), read_bytes(DONOR.joinpath(*name.split("/"))))
    write_new(target / WORKER.name, read_bytes(WORKER))
    return target


@pytest.fixture
def runner(stage):
    module = types.ModuleType("openmaic_interactive_normalize_test")
    module.__file__ = str(RUNNER)
    exec(compile(read_bytes(RUNNER), str(RUNNER), "exec"), module.__dict__)
    module.WORKER = stage / WORKER.name
    assert digest(read_bytes(module.WORKER)) == module.WORKER_SHA256
    return module


def raw_call(stage: Path, raw: bytes, override: dict[str, str] | None = None):
    """Synthetic direct child with bounded pipes and this child only."""
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
            pass

    threads = [threading.Thread(target=reader, args=(process.stdout, "stdout", 262_144), daemon=True),
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
    assert not any(thread.is_alive() for thread in threads)
    assert not failures and process.returncode == 0
    return json.loads(streams["stdout"]), streams["stdout"], streams["stderr"]


def test_fixed_original_closure():
    manifest = json.loads(read_bytes(DONOR / "ORIGINALS.json"))
    package = json.loads(read_bytes(DONOR / "package.json"))
    assert package["name"] == "@openmaic/generation" and package["version"] == "0.3.28"
    assert digest(read_bytes(WORKER)) == WORKER_SHA256
    for name, expected in ORIGINALS.items():
        assert digest(read_bytes(DONOR.joinpath(*name.split("/")))) == expected
        if name != "ORIGINALS.json":
            assert manifest["originals"][name] == expected


@requires_node
def test_math_reply_matches_the_pinned_post_processor_output(stage, runner):
    result = runner.run_candidate(request(MATH_REPLY), node_executable=checked_node())
    assert result["status"] == "OBSERVED_CANDIDATE"
    doc = result["candidate"]
    assert result["process"]["direct_child"] == "REAPED" and result["process"]["pipe_threads"] == "JOINED"
    assert result["process"]["descendants"] == "UNKNOWN"
    assert doc["extraction_strategy"] == "COMPLETE_DOCUMENT" and doc["katex_injected"] is True
    assert doc["model_call"] == "NOT_INVOKED" and doc["rendering_authorized"] is False
    assert doc["security_sanitizer"] is False and doc["core_authorization"] == "NOT_ESTABLISHED"
    assert doc["input_sha256"] == PINNED["input_sha256"] and doc["input_bytes"] == len(MATH_REPLY.encode())
    assert doc["extracted_bytes"] == PINNED["extracted_bytes"]
    assert doc["output_sha256"] == PINNED["output_sha256"] and doc["output_bytes"] == PINNED["output_bytes"]
    decoded = base64.b64decode(doc["output_utf8_base64"]).decode("utf-8")
    assert digest(decoded.encode("utf-8")) == PINNED["output_sha256"]
    assert "data-openmaic-katex" in decoded and "\\(" in decoded and "\\[" in decoded


@requires_node
@pytest.mark.parametrize(("reply", "strategy"), [
    ("```html\n<!DOCTYPE html><html><body><p>ok</p>\n```", "FENCED_BLOCK"),
    ("<!DOCTYPE html><html><body><p>ok</p>", "TRIMMED_DOCUMENT"),
])
def test_extraction_strategies_follow_the_donor_order(stage, runner, reply, strategy):
    result = runner.run_candidate(request(reply), node_executable=checked_node())
    assert result["status"] == "OBSERVED_CANDIDATE"
    assert result["candidate"]["extraction_strategy"] == strategy


@requires_node
def test_uncompilable_classic_script_is_refused_without_execution(stage):
    reply = "<!DOCTYPE html><html><head></head><body><script>const = ;</script></body></html>"
    result, output, _ = raw_call(stage, request(reply))
    assert result["status"] == "REJECTED" and result["error_code"] == "INVALID_MODEL_HTML"
    assert result["script_index"] == 1 and b"<script>" not in output


@requires_node
def test_reply_without_html_is_refused(stage):
    result, output, _ = raw_call(stage, request("just prose about a widget"))
    assert result["status"] == "REJECTED" and result["error_code"] == "INVALID_MODEL_HTML"
    assert b"just prose" not in output


@requires_node
def test_unsupported_widget_type_is_named(stage):
    result, _, _ = raw_call(stage, request(MATH_REPLY, widget="procedural-skill"))
    assert result["status"] == "REJECTED" and result["error_code"] == "UNSUPPORTED_WIDGET_TYPE"


@requires_node
def test_reply_must_name_the_requested_widget(stage, runner):
    result = runner.run_candidate(request(MATH_REPLY), node_executable=checked_node())
    assert result["status"] == "OBSERVED_CANDIDATE"
    doc = copy.deepcopy(result["candidate"])
    assert runner._validate_reply(encode(doc), MATH_REPLY.encode(), "synthetic", "simulation")[0] == "OBSERVED_CANDIDATE"
    assert runner._validate_reply(encode(doc), MATH_REPLY.encode(), "synthetic", "game") == (
        "REJECTED", "INVALID_WORKER_REPLY")
    doc["output_sha256"] = "0" * 64
    assert runner._validate_reply(encode(doc), MATH_REPLY.encode(), "synthetic", "simulation") == (
        "REJECTED", "INVALID_WORKER_REPLY")
    doc = copy.deepcopy(result["candidate"])
    doc["extra"] = "SYNTHETIC_PRIVATE"
    assert runner._validate_reply(encode(doc), MATH_REPLY.encode(), "synthetic", "simulation") == (
        "REJECTED", "INVALID_WORKER_REPLY")


@requires_node
@pytest.mark.parametrize("name", ["src/interactive-post-processor.ts", "src/interactive-script-validator.ts"])
@pytest.mark.parametrize("change", ["missing", "tampered"])
def test_selected_originals_are_required(stage, name, change):
    path = stage / "vendor/scene-content-0.3.28-original/generation" / name
    if change == "missing":
        os.unlink(native(path))
    else:
        with open(native(path), "ab") as stream:
            stream.write(b"SYNTHETIC_TAMPER")
    result, output, _ = raw_call(stage, request(MATH_REPLY))
    assert result["status"] == "REJECTED" and result["error_code"] == "UPSTREAM_IDENTITY_MISMATCH"
    assert b"SYNTHETIC_TAMPER" not in output


@requires_node
def test_ambient_asset_override_is_rejected(stage):
    result, _, _ = raw_call(stage, request(MATH_REPLY), override={"INTERACTIVE_ASSET_BASE_URL": "SYNTHETIC_PRIVATE"})
    assert result["status"] == "REJECTED" and result["error_code"] == "ENVIRONMENT_OVERRIDE"


@requires_node
def test_replaced_node_identity_is_rejected_without_spawn(stage, runner, monkeypatch):
    def unexpected_spawn(*_args, **_kwargs):
        raise AssertionError("an unverified Node must not be started")

    monkeypatch.setattr(runner.subprocess, "Popen", unexpected_spawn)
    monkeypatch.setattr(runner, "NODE_SHA256", "0" * 64)
    result = runner.run_candidate(request(MATH_REPLY), node_executable=checked_node())
    assert result["error_code"] == "NODE_IDENTITY_MISMATCH"
    assert result["process"]["direct_child"] == "NOT_STARTED"


@requires_node
def test_oversized_reply_is_refused_before_spawn(stage, runner, monkeypatch):
    def unexpected_spawn(*_args, **_kwargs):
        raise AssertionError("oversized input must not start a child")

    monkeypatch.setattr(runner.subprocess, "Popen", unexpected_spawn)
    result = runner.run_candidate(request(MATH_REPLY + "x" * (runner.MAX_REPLY - len(MATH_REPLY))),
                                  node_executable=checked_node())
    assert result["error_code"] == "INVALID_ARGUMENT" and result["process"]["direct_child"] == "NOT_STARTED"


@requires_node
def test_running_owned_child_cancellation_and_busy_are_observed(stage, runner, monkeypatch):
    source = (b"import {writeFileSync} from 'node:fs';process.stdin.resume();"
              b"process.stdin.on('end',()=>{writeFileSync('synthetic-cancel-ready','OK',{flag:'wx'});"
              b"setInterval(()=>{},1000);});\n")
    script = stage / "synthetic-cancel-worker.mjs"
    write_new(script, source)
    runner.WORKER, runner.WORKER_SHA256 = script, digest(source)
    node = checked_node()
    started, cancel = threading.Event(), threading.Event()
    outcome, owned = {}, []
    original_popen = runner.subprocess.Popen

    def capture(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        owned.append(child)
        started.set()
        return child

    monkeypatch.setattr(runner.subprocess, "Popen", capture)
    first = threading.Thread(target=lambda: outcome.update(
        runner.run_candidate(request(MATH_REPLY), node_executable=node, cancelled=cancel)), daemon=True)
    first.start()
    try:
        assert started.wait(timeout=20)
        ready = stage / "synthetic-cancel-ready"
        deadline = time.monotonic() + 10
        while not os.path.exists(native(ready)):
            assert first.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        busy = runner.run_candidate(request(MATH_REPLY), node_executable=node)
        assert busy["error_code"] == "BUSY_OR_CLEANUP_UNCONFIRMED"
        assert busy["process"]["direct_child"] == "NOT_STARTED"
    finally:
        cancel.set()
        first.join(timeout=10)
        if first.is_alive() and owned and owned[0].poll() is None:
            owned[0].kill()
            first.join(timeout=5)
    assert not first.is_alive()
    assert outcome["status"] == "REJECTED" and outcome["error_code"] == "CANCELLED"
    assert outcome["process"]["direct_child"] == "REAPED"
    assert outcome["process"]["pipe_threads"] == "JOINED" and outcome["process"]["descendants"] == "UNKNOWN"
