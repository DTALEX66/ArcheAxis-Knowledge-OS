"""Finite synthetic DSL normalization; no model, Core or rendering is run."""
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
from tests.integrations.test_openmaic_interactive_url_map import checked_node, digest, read_bytes, write_new
from tests.integrations.test_openmaic_interactive_html_rewrite_candidate import (
    test_pipe_close_exception_keeps_slot_and_reports_io_failure as exercise_close_exception,
    test_non_os_pipe_io_exception_is_private_and_releases_confirmed_closures as exercise_io_exception,
    test_popen_after_real_spawn_exception_keeps_cleanup_unknown as exercise_spawn_exception,
    test_parent_bounds_each_pipe_and_does_not_reflect_it as exercise_pipe_limit,
    test_thread_construction_exception_closes_unhanded_pipes as exercise_thread_construction,
    test_thread_start_exception_keeps_partial_pipe_cleanup_unknown as exercise_thread_exception,
    test_timeout_during_child_is_not_misreported_as_success as exercise_timeout,
    test_unconfirmed_pipe_cleanup_keeps_instance_fail_closed as exercise_unconfirmed_pipe,
)


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/learning-providers/openmaic"
DONOR = SERVICE / "vendor/scene-content-0.3.28-original/dsl"
WORKER = SERVICE / "slide-normalize-worker.mjs"
RUNNER = SERVICE / "slide_normalize_runner.py"
BUILDER = SERVICE / "scene-build-worker.mjs"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit preverified ARCHEAXIS_TEST_NODE is required")
ORIGINALS = {
    "ORIGINALS.json": "c7564a5741c0807834ebcf77779a50590b927fa8b7e93f49494d1ef8eac6c317",
    "package.json": "847c2f4054034aab29586171872cb64a0f0b4e39db8dd9b8c50cff5e67014c98",
    "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
    "src/normalize.ts": "e4f21f3273d9d65dadd53768afc5049b5473d087d1c525ea804c3d057b5ecf06",
    "src/stage.ts": "b8ce1ac2cff5a37e7fee7b23a1eb4df59499f0357366d80166163d7b32a9fc6a",
}


@pytest.fixture(scope="module")
def stage(tmp_path_factory) -> Path:
    target = tmp_path_factory.mktemp("slide-normalize") / "h"
    for relative, expected in ORIGINALS.items():
        source = DONOR.joinpath(*relative.split("/"))
        raw = read_bytes(source)
        assert digest(raw) == expected
        write_new((target / "vendor/scene-content-0.3.28-original/dsl").joinpath(*relative.split("/")), raw)
    write_new(target / WORKER.name, read_bytes(WORKER))
    return target


@pytest.fixture
def runner(stage):
    module = types.ModuleType("openmaic_slide_normalize_test")
    module.__file__ = str(RUNNER)
    exec(compile(read_bytes(RUNNER), str(RUNNER), "exec"), module.__dict__)
    module.WORKER = stage / WORKER.name
    assert digest(read_bytes(module.WORKER)) == module.WORKER_SHA256
    return module


def scene() -> dict:
    return {"id": "scene_1", "stageId": "stage_1", "outlineId": "outline_1", "type": "slide",
            "title": "合成幻灯片", "order": 1, "actions": [], "createdAt": 1, "updatedAt": 1,
            "content": {"type": "slide", "canvas": {"id": "canvas_1", "viewportSize": 1000,
            "viewportRatio": 0.5625, "theme": {"backgroundColor": "#ffffff", "themeColors": ["#5b9bd5"],
            "fontColor": "#333333", "fontName": "Microsoft YaHei"},
            "elements": [{"id": "text_1", "type": "text", "left": 60, "top": 50, "width": 880,
                          "height": 76, "rotate": 0, "content": "<p>😀合成内容</p>", "defaultFontName": ""},
                         {"id": "text_2", "type": "text", "left": 60, "top": 150, "width": 880,
                          "height": 130, "rotate": 0, "content": "保留", "defaultFontName": "Arial",
                          "defaultColor": "blue"}], "background": {"type": "solid", "color": "#ffffff"}}}}


def encode(value) -> bytes:
    # Matches ECMAScript's integer spellings for these fixed synthetic values.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def raw_call(worker: Path, raw: bytes, limit: int = 196_608):
    """Run only a fixed synthetic child with bounded stdout/stderr and deadline."""
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    process = subprocess.Popen([str(checked_node()), str(worker)], cwd=str(worker.parent), env=env, shell=False,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=flags)
    streams, errors = {}, []

    def reader(pipe, key, maximum):
        try:
            streams[key] = pipe.read(maximum + 1)
            if len(streams[key]) > maximum:
                process.kill()
        except (OSError, ValueError):
            errors.append("read")

    def writer():
        try:
            process.stdin.write(raw)
            process.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass

    threads = [threading.Thread(target=reader, args=(process.stdout, "stdout", limit), daemon=True),
               threading.Thread(target=reader, args=(process.stderr, "stderr", 8192), daemon=True),
               threading.Thread(target=writer, daemon=True)]
    for thread in threads:
        thread.start()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        raise AssertionError("synthetic owned child exceeded deadline")
    finally:
        for thread in threads:
            thread.join(timeout=5)
    assert not any(thread.is_alive() for thread in threads), "pipe cleanup unknown"
    assert not errors and len(streams["stdout"]) <= limit and len(streams["stderr"]) <= 8192
    return process.returncode, json.loads(streams["stdout"]), streams["stdout"], streams["stderr"]


def frame(raw_scene: bytes) -> bytes:
    return encode({"schema": "archeaxis.openmaic-slide-normalize/v1", "request_id": "synthetic_1",
                   "scene_utf8_base64": base64.b64encode(raw_scene).decode("ascii")})


def assert_private_candidate(result, raw):
    assert result["status"] == "CANDIDATE"
    process, doc = result["process"], result["candidate"]
    assert process["direct_child"] == "REAPED" and process["pipe_threads"] == "JOINED"
    assert process["exit_code"] == 0 and process["descendants"] == "UNKNOWN"
    assert process["network_isolation"] == "NOT_ESTABLISHED"
    assert doc["scope"] == "CALLER_SUPPLIED_UNVERIFIED" and doc["privacy"] == "PRIVATE_INPUT_AND_OUTPUT"
    assert doc["provider_version"] == "1.3.0" and doc["dsl_package_version"] == "0.12.0"
    assert doc["full_scene_generation"] is False and doc["rendering_authorized"] is False
    assert doc["security_sanitizer"] is False and doc["canonical_persistence"] == "NOT_PERFORMED"
    assert doc["core_authorization"] == "NOT_ESTABLISHED" and doc["network_isolation"] == "NOT_ESTABLISHED"
    assert base64.b64decode(doc["input_utf8_base64"], validate=True) == raw
    output = base64.b64decode(doc["output_utf8_base64"], validate=True)
    assert (doc["input_bytes"], doc["input_sha256"]) == (len(raw), digest(raw))
    assert (doc["output_bytes"], doc["output_sha256"]) == (len(output), digest(output))
    patch = doc["byte_patch"]
    inserted = base64.b64decode(patch["insert_base64"], validate=True)
    assert patch["unit"] == "bytes"
    assert raw[:patch["start"]] + inserted + raw[patch["start"] + patch["delete_bytes"]:] == output
    return doc, output


@requires_node
def test_original_dsl_defaults_and_replayable_private_bytes(runner, monkeypatch):
    monkeypatch.setenv("NODE_OPTIONS", "--must-not-be-inherited")
    monkeypatch.setenv("NODE_PATH", "SYNTHETIC_PRIVATE_PATH")
    original = scene()
    before = copy.deepcopy(original)
    raw = json.dumps(original, ensure_ascii=False, indent=2).encode("utf-8")
    doc, output = assert_private_candidate(runner.run_candidate(raw, node_executable=checked_node()), raw)
    assert original == before
    normalized = json.loads(output)
    first, second = normalized["content"]["canvas"]["elements"]
    assert first["defaultFontName"] == "Microsoft YaHei" and first["defaultColor"] == "#333333"
    assert second == original["content"]["canvas"]["elements"][1]
    assert doc["semantic_changes"] == [
        {"path": "/content/canvas/elements/0/defaultFontName", "kind": "EMPTY_REPLACED_WITH_DEFAULT"},
        {"path": "/content/canvas/elements/0/defaultColor", "kind": "ABSENT_FILLED_WITH_DEFAULT"},
    ]
    for key in ("id", "stageId", "outlineId", "createdAt", "updatedAt"):
        assert normalized[key] == original[key]
    assert normalized["content"]["canvas"]["id"] == original["content"]["canvas"]["id"]
    # Repeating the original normalizer on its own serialized output changes no
    # content; this does not claim scene-builder retry bytes are stable.
    again, repeated = assert_private_candidate(runner.run_candidate(output, node_executable=checked_node()), output)
    assert repeated == output and again["semantic_changes"] == []
    assert again["byte_patch"] == {"unit": "bytes", "start": len(output), "delete_bytes": 0, "insert_base64": ""}


@requires_node
def test_existing_builder_scene_can_be_normalized_without_core_or_model(runner):
    assert digest(read_bytes(BUILDER)) == "c4a2dad9c96ebd13aa20827410227d2650cda0dac80e3a3927968d1e024779e9"
    assert digest(read_bytes(SERVICE / "vendor/generation-0.3.28/scene-builder.ts")) == \
        "e550ed528f9a017ea0fa1f9cc4a01f7eb22d541d5ada067967d3434393d1bf0a"
    assert digest(read_bytes(SERVICE / "vendor/generation-0.3.28/nanoid.mjs")) == \
        "d5d678dfcecc9a4c0f4dae6555c30b4d0ef41a87b00d4d16d744f31ddae6c16e"
    selected = scene()["content"]["canvas"]["elements"]
    request = {"schema": "archeaxis.openmaic-scene-build/v1", "request_id": "synthetic_1", "attempt": 1,
               "source": {"document_id": "synthetic_doc", "version": 1, "content_sha256": "a" * 64},
               "stage_id": "stage_1", "scene_id": "scene_1",
               "outline": {"id": "outline_1", "type": "slide", "title": "合成幻灯片", "description": "合成",
                           "keyPoints": ["合成"], "order": 1}, "content": {"elements": selected}, "actions": []}
    code, built, _, _ = raw_call(BUILDER, encode(request), limit=1_000_000)
    assert code == 0 and built["status"] == "CANDIDATE"
    assert built["model_call"] == "NOT_INVOKED" and built["canonical_bindings_verified"] is False
    assert built["source_binding"] == "client_declared_unverified" and built["retry_bytes_stable"] is False
    raw = encode(built["scene"])
    doc, output = assert_private_candidate(runner.run_candidate(raw, node_executable=checked_node()), raw)
    normalized = json.loads(output)
    assert normalized["id"] == "scene_1" and normalized["stageId"] == "stage_1"
    assert normalized["outlineId"] == "outline_1" and normalized["actions"] == []
    assert normalized["content"]["canvas"]["id"] == built["scene"]["content"]["canvas"]["id"]
    assert len(doc["semantic_changes"]) == 2


@pytest.mark.parametrize(("value", "expected"), [("\u0085", "CANDIDATE"), ("\ufeff", "UNSUPPORTED_SCENE")])
@requires_node
def test_ecmascript_trim_matches_runner_for_unicode_whitespace(runner, value, expected):
    synthetic = scene()
    synthetic["content"]["canvas"]["elements"][0]["content"] = value
    if expected == "CANDIDATE":
        synthetic["title"] = value
        synthetic["content"]["canvas"]["elements"][0]["defaultFontName"] = value
    assert runner._text(value, 16000) is (expected == "CANDIDATE")
    assert runner._supported_scene(synthetic) is (expected == "CANDIDATE")
    raw = encode(synthetic)
    result = runner.run_candidate(raw, node_executable=checked_node())
    if expected == "CANDIDATE":
        doc, output = assert_private_candidate(result, raw)
        assert json.loads(output)["content"]["canvas"]["elements"][0]["content"] == value
        assert json.loads(output)["content"]["canvas"]["elements"][0]["defaultFontName"] == value
        assert doc["source_verification"] == "VERIFIED_SELECTED_MEMBERS"
    else:
        assert result["status"] == "REJECTED" and result["error_code"] == expected


@requires_node
def test_unsupported_and_malformed_scenes_do_not_reflect_private_input(runner):
    sentinel = "SYNTHETIC_PRIVATE_SCENE"
    cases = []
    for change in ("unknown", "media", "action", "duplicate", "bad_font", "geometry", "background", "active"):
        value = scene()
        value["title"] = sentinel
        elements = value["content"]["canvas"]["elements"]
        if change == "unknown": value["unexpected"] = sentinel
        if change == "media": elements[0]["type"] = "image"
        if change == "action": value["actions"] = [{"type": "speech", "text": sentinel}]
        if change == "duplicate": elements[1]["id"] = elements[0]["id"]
        if change == "bad_font": elements[0]["defaultFontName"] = None
        if change == "geometry": elements[0]["width"] = -1
        if change == "background": value["content"]["canvas"]["background"] = {"type": "gradient"}
        if change == "active": elements[0]["content"] = "<script>" + sentinel + "</script>"
        cases.append((encode(value), "UNSUPPORTED_SCENE"))
    valid = encode(scene())
    cases.extend([(b"\xff" + sentinel.encode(), "INVALID_SCENE"),
                  (b"\xef\xbb\xbf" + valid, "INVALID_SCENE"),
                  (valid.replace(b'"rotate":0', b'"rotate":-0', 1), "INVALID_SCENE"),
                  (valid.replace(b'"rotate":0', b'"rotate":0.0', 1), "INVALID_SCENE"),
                  (valid.replace(b'"width":880', b'"width":1e400', 1), "INVALID_SCENE"),
                  (valid.replace(b'"id":"scene_1"', b'"id":"scene_1","\\u0069d":"other"', 1), "INVALID_SCENE")])
    for raw, reason in cases:
        result = runner.run_candidate(raw, node_executable=checked_node())
        assert result["status"] == "REJECTED" and result["error_code"] == reason
        assert sentinel not in json.dumps(result) and base64.b64encode(sentinel.encode()).decode() not in json.dumps(result)
        assert "candidate" not in result and result["process"]["direct_child"] == "REAPED"
    oversized = runner.run_candidate(b"x" * 16_385, node_executable=checked_node())
    assert oversized["status"] == "REJECTED" and oversized["process"]["direct_child"] == "NOT_STARTED"


@requires_node
def test_frame_duplicate_keys_unknown_fields_and_noncanonical_base64_are_rejected(stage):
    encoded = base64.b64encode(encode(scene()))
    prefix = b'{"schema":"archeaxis.openmaic-slide-normalize/v1","request_id":"ok",'
    cases = [
        prefix + b'"request_\\u0069d":"SYNTHETIC_SECRET","scene_utf8_base64":"' + encoded + b'"}',
        prefix + b'"scene_utf8_base64":"' + encoded + b'","extra":"SYNTHETIC_SECRET"}',
        prefix + b'"scene_utf8_base64":"Zh=="}',
    ]
    for raw in cases:
        code, result, stdout, stderr = raw_call(stage / WORKER.name, raw)
        assert code == 0 and result["status"] == "REJECTED" and result["error_code"] == "INVALID_REQUEST"
        assert result["source_verification"] == "NOT_ASSERTED"
        assert b"SYNTHETIC_SECRET" not in stdout + stderr and encoded not in stdout + stderr
        assert "input_utf8_base64" not in result and "output_utf8_base64" not in result


@requires_node
def test_tampered_missing_source_and_bad_node_fail_closed(stage, runner):
    fake = stage / "node.exe"
    write_new(fake, b"SYNTHETIC_FAKE_NODE")
    result = runner.run_candidate(encode(scene()), node_executable=fake)
    assert result["error_code"] == "NODE_IDENTITY_MISMATCH" and result["process"]["direct_child"] == "NOT_STARTED"
    worker = stage / WORKER.name
    original_worker = read_bytes(worker)
    try:
        with open(native(worker), "wb") as stream:
            stream.write(original_worker + b"\n// SYNTHETIC_TAMPER\n")
        result = runner.run_candidate(encode(scene()), node_executable=checked_node())
        assert result["error_code"] == "WORKER_IDENTITY_MISMATCH"
        assert result["process"]["direct_child"] == "NOT_STARTED"
    finally:
        with open(native(worker), "wb") as stream:
            stream.write(original_worker)
    donor = stage / "vendor/scene-content-0.3.28-original/dsl/src/normalize.ts"
    original = read_bytes(donor)
    try:
        with open(native(donor), "wb") as stream:
            stream.write(original + b"\n// SYNTHETIC_TAMPER\n")
        result = runner.run_candidate(encode(scene()), node_executable=checked_node())
        assert result["error_code"] == "UPSTREAM_IDENTITY_MISMATCH"
    finally:
        with open(native(donor), "wb") as stream:
            stream.write(original)
    stage_file = stage / "vendor/scene-content-0.3.28-original/dsl/src/stage.ts"
    hold = stage_file.with_name("stage.ts.synthetic-held")
    os.replace(native(stage_file), native(hold))
    try:
        result = runner.run_candidate(encode(scene()), node_executable=checked_node())
        assert result["error_code"] == "UPSTREAM_IDENTITY_MISMATCH"
    finally:
        os.replace(native(hold), native(stage_file))


@requires_node
def test_runner_rejects_forged_results_and_private_rejection_echo(runner):
    raw = encode(scene())
    doc, _ = assert_private_candidate(runner.run_candidate(raw, node_executable=checked_node()), raw)
    valid = encode(doc)
    assert runner._validate_reply(valid, raw, doc["request_id"])[0] == "CANDIDATE"
    for change in ("input", "patch", "change", "extra", "boolean"):
        bad = copy.deepcopy(doc)
        if change == "input": bad["input_sha256"] = "0" * 64
        if change == "patch": bad["byte_patch"]["start"] += 1
        if change == "change": bad["semantic_changes"] = []
        if change == "extra": bad["SYNTHETIC_PRIVATE"] = "secret"
        if change == "boolean": bad["input_bytes"] = True
        assert runner._validate_reply(encode(bad), raw, doc["request_id"]) == ("REJECTED", "INVALID_WORKER_REPLY")


@requires_node
def test_real_child_busy_and_cancel_are_bounded(stage, runner, monkeypatch):
    source = (b"import {writeFileSync} from 'node:fs';process.stdin.resume();"
              b"process.stdin.on('end',()=>{writeFileSync('slide-concurrent-ready','OK',{flag:'wx'});"
              b"setInterval(()=>{},1000);});\n")
    worker = stage / "synthetic-slide-wait.mjs"
    write_new(worker, source)
    runner.WORKER, runner.WORKER_SHA256 = worker, digest(source)
    node = checked_node()
    spawned, cancel, second_cancel = threading.Event(), threading.Event(), threading.Event()
    outcome, other = {}, {}
    real_popen = runner.subprocess.Popen

    def start(*args, **kwargs):
        assert kwargs["shell"] is False and "NODE_OPTIONS" not in kwargs["env"]
        if os.name == "nt": assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW
        process = real_popen(*args, **kwargs)
        spawned.set()
        return process

    monkeypatch.setattr(runner.subprocess, "Popen", start)
    first = threading.Thread(target=lambda: outcome.update(
        runner.run_candidate(encode(scene()), node_executable=node, cancelled=cancel)), daemon=True)
    second = threading.Thread(target=lambda: other.update(
        runner.run_candidate(encode(scene()), node_executable=node, cancelled=second_cancel)), daemon=True)
    first.start()
    try:
        assert spawned.wait(timeout=20)
        ready = stage / "slide-concurrent-ready"
        ready_deadline = time.monotonic() + 10
        while not os.path.exists(native(ready)):
            assert first.is_alive() and time.monotonic() < ready_deadline, "stdin close was not observed"
            time.sleep(0.01)
        second.start()
        second.join(timeout=2)
        assert not second.is_alive() and other["error_code"] == "BUSY_OR_CLEANUP_UNCONFIRMED"
        assert other["process"]["direct_child"] == "NOT_STARTED"
    finally:
        cancel.set()
        second_cancel.set()
        first.join(timeout=10)
        if second.ident is not None: second.join(timeout=10)
    assert not first.is_alive() and not second.is_alive()
    assert outcome["error_code"] == "CANCELLED" and outcome["process"]["direct_child"] == "REAPED"
    assert outcome["process"]["pipe_threads"] == "JOINED" and outcome["process"]["descendants"] == "UNKNOWN"


@requires_node
@pytest.mark.skipif(os.name != "nt", reason="the shared helper checks the Windows pipe boundary")
def test_unconfirmed_pipe_cleanup_remains_fail_closed(stage, runner, monkeypatch):
    # The same real-pipe regression already used by the HTML runner; its
    # synthetic holder is a sibling with its own original Popen handle.
    exercise_unconfirmed_pipe(stage, runner, monkeypatch)


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
@requires_node
def test_owned_child_output_limits_remain_bounded(stage, runner, stream):
    exercise_pipe_limit(stage, runner, stream)


@requires_node
def test_owned_child_timeout_remains_bounded(stage, runner, monkeypatch):
    exercise_timeout(stage, runner, monkeypatch)


@requires_node
def test_spawn_exception_retains_unknown_child_slot(stage, runner, monkeypatch):
    exercise_spawn_exception(stage, runner, monkeypatch)


@pytest.mark.parametrize(("stream", "exception_type"),
                         [(stream, error) for error in (OSError, RuntimeError) for stream in ("stdout", "stderr", "stdin")]
                         + [("stdout", SystemExit)])
@requires_node
def test_close_exception_retains_unknown_pipe_slot(stage, runner, monkeypatch, stream, exception_type):
    exercise_close_exception(stage, runner, monkeypatch, stream, exception_type)


@pytest.mark.parametrize("unhanded_close_fails", [False, True])
@requires_node
def test_thread_construction_closes_unhanded_pipes(stage, runner, monkeypatch, unhanded_close_fails, capsys):
    exercise_thread_construction(stage, runner, monkeypatch, unhanded_close_fails, capsys)


@pytest.mark.parametrize("start_then_raise", [False, True])
@requires_node
def test_partial_thread_start_retains_unknown_pipe_slot(stage, runner, monkeypatch, start_then_raise):
    exercise_thread_exception(stage, runner, monkeypatch, start_then_raise)


@pytest.mark.parametrize(("stream", "exception_type"),
                         [(stream, RuntimeError) for stream in ("stdout", "stderr", "stdin")]
                         + [("stdin", SystemExit)])
@requires_node
def test_non_os_pipe_io_is_private_with_confirmed_close(stage, runner, monkeypatch, stream, exception_type, capsys):
    exercise_io_exception(stage, runner, monkeypatch, stream, exception_type, capsys)
