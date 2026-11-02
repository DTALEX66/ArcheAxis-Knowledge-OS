"""Finite synthetic checks for the unregistered original slide prompt adapter."""
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
from tests.integrations.test_openmaic_slide_normalize import raw_call
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
DONOR = SERVICE / "vendor/scene-content-0.3.28-original/generation"
WORKER = SERVICE / "slide-prompt-worker.mjs"
RUNNER = SERVICE / "slide_prompt_runner.py"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit preverified ARCHEAXIS_TEST_NODE is required")
ORIGINALS = {
    "ORIGINALS.json": "5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3",
    "package.json": "5308b268d06dd27e592de00f02d57b046588df0d6e160f4179788388d5a806d1",
    "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
    "src/scene-prompts.ts": "06a030bff670868992e37d131fe30e0358304eaa37c4b8f27246560b98a6f1ec",
    "src/prompts/index.ts": "2d71a8c8e261b773562b2d2597d61690fa547a80c7aca9f5cc329b49a6c987ab",
    "src/prompts/loader.ts": "584bd51c71c53c02e058df5209d9bcb1f73ff531677a9d7a3aa168d135a43e50",
    "src/interactive-libraries.ts": "1c9f212d7e2010dd3e1f4889efe22825fcb1f52772b056e5a30fc58753f29de1",
    "templates/slide-content/system.md": "d0e800d960111e03448d0f0bacdf40acfefcef02bf8e8f9f4f110ba6377d54a1",
    "templates/slide-content/user.md": "7d7486fed0d897a85273794359cd17383d7b9f2dbca7481134a1519687368c99",
    "snippets/slide-image-instructions.md": "00ba082fb8cf2510bcdc6684e09478778c19b5a00bd6e2818208efa55590db0c",
    "snippets/slide-generated-image-instructions.md": "aed6d0a9ab210562c61183ca29ed7a6635d9c423e8b59a20b59a0d491a8ca0f1",
    "snippets/slide-video-instructions.md": "9a232d6a42e70fc5ac89ec8a8a10420b9c4d5e062287dd3e424e5d9bd934c856",
}
SNIPPETS = [name for name in ORIGINALS if name.startswith("snippets/")]


def encode(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def request():
    return {"outline": {"title": "合成题目 😀", "description": "第一行\r\n第二行 {{literal}}",
                        "key_points": ["一号", "二号"]}, "language_directive": "使用中文"}


def frame(raw: bytes, private=False) -> bytes:
    return encode({"schema": "archeaxis.openmaic-slide-prompt/v1", "include_private": private,
                   "request_utf8_base64": base64.b64encode(raw).decode("ascii")})


@pytest.fixture
def stage(tmp_path_factory):
    target = tmp_path_factory.mktemp("slide-prompt") / "h"
    root = target / "vendor/scene-content-0.3.28-original/generation"
    for name, expected in ORIGINALS.items():
        raw = read_bytes(DONOR.joinpath(*name.split("/")))
        assert digest(raw) == expected
        write_new(root.joinpath(*name.split("/")), raw)
    write_new(target / WORKER.name, read_bytes(WORKER))
    return target


@pytest.fixture
def runner(stage):
    module = types.ModuleType("openmaic_slide_prompt_test")
    module.__file__ = str(RUNNER)
    exec(compile(read_bytes(RUNNER), str(RUNNER), "exec"), module.__dict__)
    module.WORKER = stage / WORKER.name
    assert digest(read_bytes(module.WORKER)) == module.WORKER_SHA256
    return module


def test_fixed_original_closure_and_source_declaration():
    manifest = json.loads(read_bytes(DONOR / "ORIGINALS.json"))
    package = json.loads(read_bytes(DONOR / "package.json"))
    assert package["name"] == "@openmaic/generation" and package["version"] == "0.3.28"
    assert package["license"] == "MIT"
    assert len(SNIPPETS) == 3
    for name, expected in ORIGINALS.items():
        assert digest(read_bytes(DONOR.joinpath(*name.split("/")))) == expected
        if name != "ORIGINALS.json":
            assert manifest["originals"][name] == expected


@requires_node
def test_private_opt_in_matches_independent_original_call_and_default_is_fixed(stage, runner, monkeypatch):
    raw = encode(request())
    monkeypatch.setenv("INTERACTIVE_ASSET_BASE_URL", "SYNTHETIC_PRIVATE_OVERRIDE")
    monkeypatch.setenv("NODE_OPTIONS", "--not-inherited")
    monkeypatch.setenv("NODE_PATH", "SYNTHETIC_PRIVATE_NODE_PATH")
    public = runner.run_candidate(raw, node_executable=checked_node())
    assert public["status"] == "BUILT" and public["candidate"]["private"] is None
    assert public["process"]["direct_child"] == "REAPED" and public["process"]["pipe_threads"] == "JOINED"
    assert public["process"]["descendants"] == "UNKNOWN"
    for needle in ("合成题目", "literal", "SYNTHETIC_PRIVATE_OVERRIDE", "SYNTHETIC_PRIVATE_NODE_PATH"):
        assert needle not in json.dumps(public, ensure_ascii=False)
    private = runner.run_candidate(raw, node_executable=checked_node(), include_private=True)
    assert private["status"] == "BUILT"
    doc = private["candidate"]
    assert doc["scope"] == "CALLER_SUPPLIED_UNVERIFIED" and doc["model_call"] == "NOT_INVOKED"
    assert doc["full_generation"] == "NOT_PERFORMED" and doc["core_authorization"] == "NOT_ESTABLISHED"
    actual = doc["private"]
    assert actual["system_sha256"] == digest(actual["system"].encode("utf-8"))
    assert actual["user_sha256"] == digest(actual["user"].encode("utf-8"))
    assert "合成题目 😀" in actual["user"] and "第一行\r\n第二行 {{literal}}" in actual["user"]
    assert "1. 一号\n2. 二号" in actual["user"] and "1000 × 562.5" in actual["user"]

    # Independent test-only call of the same original function. It uses the
    # already verified staged TS and source templates, and no model or npm code.
    reference = b'''import {registerHooks} from 'node:module';
const base = new URL('./vendor/scene-content-0.3.28-original/generation/', import.meta.url);
registerHooks({resolve(s,c,next) { if(c.parentURL?.startsWith(base.href) && s.startsWith('.') && s.endsWith('.js')) return next(s.slice(0,-3)+'.ts',c); return next(s,c); }});
let chunks=[];for await(const c of process.stdin) chunks.push(c);
let f=JSON.parse(Buffer.concat(chunks)), r=JSON.parse(Buffer.from(f.request_utf8_base64,'base64'));
let m=await import(new URL('./src/scene-prompts.ts',base));
let p=m.buildSlideContentPrompt({imageElementEnabled:false,generatedImageEnabled:false,generatedVideoEnabled:false},
{title:r.outline.title,description:r.outline.description,keyPoints:r.outline.key_points.map((x,i)=>`${i+1}. ${x}`).join('\\n'),elements:'\xef\xbc\x88\xe6\xa0\xb9\xe6\x8d\xae\xe8\xa6\x81\xe7\x82\xb9\xe8\x87\xaa\xe5\x8a\xa8\xe7\x94\x9f\xe6\x88\x90\xef\xbc\x89',assignedImages:'\xe6\x97\xa0\xe5\x8f\xaf\xe7\x94\xa8\xe5\x9b\xbe\xe7\x89\x87\xef\xbc\x8c\xe7\xa6\x81\xe6\xad\xa2\xe6\x8f\x92\xe5\x85\xa5\xe4\xbb\xbb\xe4\xbd\x95 image \xe5\x85\x83\xe7\xb4\xa0',teacherContext:'',languageDirective:r.language_directive});
process.stdout.write(JSON.stringify(p));'''
    reference_path = stage / "synthetic-original-reference.mjs"
    write_new(reference_path, reference)
    code, expected, _, _ = raw_call(reference_path, frame(raw, True))
    assert code == 0
    assert actual["system"] == expected["system"] and actual["user"] == expected["user"]


@pytest.mark.parametrize("addition", [
    {"media": {"generatedVideoEnabled": True}}, {"imageElementEnabled": True},
    {"agents": []}, {"edit": "SYNTHETIC_PRIVATE"}, {"unknown": "SYNTHETIC_PRIVATE"},
])
@requires_node
def test_unsupported_options_are_not_silently_discarded(stage, addition):
    value = request()
    value.update(addition)
    code, result, output, _ = raw_call(stage / WORKER.name, frame(encode(value), True))
    assert code == 0 and result["status"] == "REJECTED" and result["error_code"] == "INVALID_REQUEST"
    assert b"SYNTHETIC_PRIVATE" not in output and result["private"] is None


@requires_node
def test_video_option_inside_outline_is_rejected(stage):
    value = request()
    value["outline"]["mediaGenerations"] = [{"type": "video"}]
    _, result, _, _ = raw_call(stage / WORKER.name, frame(encode(value), True))
    assert result["status"] == "REJECTED" and result["error_code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("raw", [
    b'{"outline":{"title":"one","title":"two","description":"","key_points":[]},"language_directive":""}',
    b'{"outline":{"title":"SYNTHETIC_PRIVATE","description":"","key_points":[]},"language_directive":"","extra":"SYNTHETIC_PRIVATE"}',
    b'{"outline":{"title":"\\ud800","description":"","key_points":[]},"language_directive":""}',
    b'\xff', b'{}',
])
@requires_node
def test_invalid_request_is_not_reflected(stage, raw):
    code, result, output, _ = raw_call(stage / WORKER.name, frame(raw, True))
    assert code == 0 and result["status"] == "REJECTED" and result["error_code"] == "INVALID_REQUEST"
    assert b"SYNTHETIC_PRIVATE" not in output and result["private"] is None


@pytest.mark.parametrize("name", SNIPPETS + ["ORIGINALS.json", "src/scene-prompts.ts", "src/prompts/loader.ts",
                                              "src/interactive-libraries.ts", "templates/slide-content/user.md"])
@pytest.mark.parametrize("change", ["missing", "tampered"])
@requires_node
def test_disabled_media_still_requires_fixed_originals(stage, name, change):
    path = stage / "vendor/scene-content-0.3.28-original/generation" / name
    if change == "missing":
        os.unlink(native(path))
    else:
        with open(native(path), "ab") as stream:
            stream.write(b"SYNTHETIC_TAMPER")
    code, result, output, _ = raw_call(stage / WORKER.name, frame(encode(request()), True))
    assert code == 0 and result["status"] == "REJECTED" and result["error_code"] == "UPSTREAM_IDENTITY_MISMATCH"
    assert b"SYNTHETIC_TAMPER" not in output and result["private"] is None


@pytest.mark.parametrize("override", ["", "SYNTHETIC_PRIVATE_OVERRIDE"])
@requires_node
def test_worker_rejects_ambient_asset_override_before_constructing(stage, override):
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
    env["INTERACTIVE_ASSET_BASE_URL"] = override
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    child = subprocess.run([str(checked_node()), str(stage / WORKER.name)], input=frame(encode(request()), True),
                           env=env, cwd=str(stage), shell=False, capture_output=True, timeout=30, creationflags=flags)
    assert child.returncode == 0 and len(child.stdout) <= 8192 and len(child.stderr) <= 8192
    result = json.loads(child.stdout)
    assert result["status"] == "REJECTED" and result["error_code"] == "ENVIRONMENT_OVERRIDE"
    assert b"SYNTHETIC_PRIVATE_OVERRIDE" not in child.stdout + child.stderr


@requires_node
def test_replaced_node_identity_is_rejected_without_spawn(stage, runner, monkeypatch):
    def unexpected_spawn(*_args, **_kwargs):
        raise AssertionError("an unverified Node must not be started")

    monkeypatch.setattr(runner.subprocess, "Popen", unexpected_spawn)
    node = checked_node()
    monkeypatch.setattr(runner, "NODE_SHA256", "0" * 64)
    result = runner.run_candidate(encode(request()), node_executable=node)
    assert result["error_code"] == "NODE_IDENTITY_MISMATCH"
    assert result["process"]["direct_child"] == "NOT_STARTED"
    impostor = stage / "node.exe"
    write_new(impostor, b"SYNTHETIC_NOT_NODE")
    result = runner.run_candidate(encode(request()), node_executable=impostor)
    assert result["error_code"] == "NODE_IDENTITY_MISMATCH"
    assert result["process"]["direct_child"] == "NOT_STARTED"


@pytest.mark.parametrize("unc", [r"\\SYNTHETIC.invalid\share\node.exe", r"\\?\UNC\SYNTHETIC.invalid\share\node.exe"])
def test_lexical_unc_rejected_before_filesystem_probe(stage, runner, monkeypatch, unc):
    real_is_symlink = Path.is_symlink

    def deny_unc_probe(self):
        if str(self).startswith(("\\\\", "//")):
            raise AssertionError("UNC must not be probed")
        return real_is_symlink(self)

    def unexpected_spawn(*_args, **_kwargs):
        raise AssertionError("UNC must not be started")

    monkeypatch.setattr(Path, "is_symlink", deny_unc_probe)
    monkeypatch.setattr(runner.subprocess, "Popen", unexpected_spawn)
    result = runner.run_candidate(encode(request()), node_executable=unc)
    assert result["error_code"] == "NODE_IDENTITY_MISMATCH"
    assert result["process"]["direct_child"] == "NOT_STARTED"


@requires_node
def test_worker_independently_checks_node_identity(stage):
    source = read_bytes(stage / WORKER.name)
    actual = b"ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
    assert source.count(actual) == 1
    probe = stage / "synthetic-wrong-node-hash.mjs"
    write_new(probe, source.replace(actual, b"0" * 64))
    _, result, _, _ = raw_call(probe, frame(encode(request())))
    assert result["status"] == "REJECTED" and result["error_code"] == "NODE_IDENTITY_MISMATCH"


@requires_node
def test_input_byte_boundary_and_rejection_before_spawn(stage, runner):
    data = encode(request())
    exact = data + b" " * (runner.MAX_REQUEST - len(data))
    result = runner.run_candidate(exact, node_executable=checked_node())
    assert result["status"] == "BUILT" and result["candidate"]["private"] is None
    result = runner.run_candidate(exact + b" ", node_executable=checked_node())
    assert result["error_code"] == "INVALID_ARGUMENT" and result["process"]["direct_child"] == "NOT_STARTED"


@requires_node
def test_original_file_growth_after_open_has_bounded_read(stage):
    source = read_bytes(stage / WORKER.name)
    anchor = b"    const buffer = Buffer.allocUnsafe(before.size + 1);"
    assert source.count(anchor) == 1
    # Test-only instrumentation creates the race after fstat on an isolated
    # synthetic fixture, and records an oversized request or readFileSync(fd).
    # It does not alter a preserved source file or inject caller data.
    injection = b'''    if (name === 'snippets/slide-image-instructions.md') {
      fs.appendFileSync(target, Buffer.alloc(16384, 65));
      fs.writeFileSync('synthetic-growth-observed', 'yes');
      let observed = 0, calls = 0;
      const oldRead = fs.readSync.bind(fs), oldWhole = fs.readFileSync.bind(fs);
      fs.readSync = (...args) => {
        if (args[0] === fd && args[3] > before.size + 1 - observed)
          fs.writeFileSync('synthetic-read-bound-broken', 'oversized request');
        const count = oldRead(...args);
        if (args[0] === fd) {
          calls += 1; observed += count;
          fs.writeFileSync('synthetic-target-read.json', JSON.stringify({calls, bytes: observed}));
        }
        return count;
      };
      fs.readFileSync = (...args) => {
        if (args[0] === fd) fs.writeFileSync('synthetic-read-bound-broken', 'whole file read');
        return oldWhole(...args);
      };
    }
'''
    probe = stage / "synthetic-growing-source.mjs"
    write_new(probe, source.replace(anchor, injection + anchor))
    target = stage / "vendor/scene-content-0.3.28-original/generation/snippets/slide-image-instructions.md"
    original_size = len(read_bytes(target))
    _, result, output, _ = raw_call(probe, frame(encode(request()), True))
    assert result["status"] == "REJECTED" and result["error_code"] == "UPSTREAM_IDENTITY_MISMATCH"
    assert os.path.exists(native(stage / "synthetic-growth-observed"))
    assert len(read_bytes(target)) == original_size + 16384
    observed = json.loads(read_bytes(stage / "synthetic-target-read.json"))
    assert type(observed["calls"]) is int and observed["calls"] > 0
    assert observed["bytes"] == original_size + 1
    assert not os.path.exists(native(stage / "synthetic-read-bound-broken"))
    assert result["private"] is None and b"synthetic-growth-observed" not in output


@requires_node
def test_partial_pipe_writes_complete_without_losing_private_input(stage, runner, monkeypatch):
    original_popen = runner.subprocess.Popen
    counts = []

    class PartialInput:
        def __init__(self, stream):
            self.stream = stream

        def write(self, data):
            counts.append(len(data))
            return self.stream.write(data[:13])

        def close(self):
            self.stream.close()

    def partial_popen(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        child.stdin = PartialInput(child.stdin)
        return child

    monkeypatch.setattr(runner.subprocess, "Popen", partial_popen)
    result = runner.run_candidate(encode(request()), node_executable=checked_node(), include_private=True)
    assert len(counts) > 1 and result["status"] == "BUILT"
    assert "合成题目 😀" in result["candidate"]["private"]["user"]


@requires_node
def test_private_reply_validation_rejects_tampering_and_extra_data(stage, runner):
    result = runner.run_candidate(encode(request()), node_executable=checked_node(), include_private=True)
    assert result["status"] == "BUILT"
    doc = result["candidate"]
    assert runner._validate_reply(encode(doc), True)[0] == "BUILT"
    assert runner._validate_reply(encode(doc), False) == ("REJECTED", "INVALID_WORKER_REPLY")
    for change in ("hash", "extra", "surrogate"):
        broken = copy.deepcopy(doc)
        if change == "hash": broken["private"]["user_sha256"] = "0" * 64
        if change == "extra": broken["private"]["extra"] = "SYNTHETIC_PRIVATE"
        if change == "surrogate": broken["private"]["user"] = "\ud800"
        serialized = json.dumps(broken, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        assert runner._validate_reply(serialized, True) == ("REJECTED", "INVALID_WORKER_REPLY")


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
        runner.run_candidate(encode(request()), node_executable=node, cancelled=cancel)), daemon=True)
    first.start()
    try:
        assert started.wait(timeout=20)
        ready = stage / "synthetic-cancel-ready"
        deadline = time.monotonic() + 10
        while not os.path.exists(native(ready)):
            assert first.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        busy = runner.run_candidate(encode(request()), node_executable=node)
        assert busy["error_code"] == "BUSY_OR_CLEANUP_UNCONFIRMED"
        assert busy["process"]["direct_child"] == "NOT_STARTED"
    finally:
        cancel.set()
        first.join(timeout=10)
        if first.is_alive() and owned and owned[0].poll() is None:
            # The test holds the original handle, never a PID reopened later.
            owned[0].kill()
            first.join(timeout=5)
    assert not first.is_alive()
    assert outcome["status"] == "REJECTED" and outcome["error_code"] == "CANCELLED"
    assert outcome["process"]["direct_child"] == "REAPED"
    assert outcome["process"]["pipe_threads"] == "JOINED" and outcome["process"]["descendants"] == "UNKNOWN"


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
@requires_node
def test_owned_child_output_limits(stage, runner, stream):
    exercise_pipe_limit(stage, runner, stream)


@requires_node
def test_owned_child_timeout(stage, runner, monkeypatch):
    exercise_timeout(stage, runner, monkeypatch)


@requires_node
def test_spawn_exception_retains_unknown_slot(stage, runner, monkeypatch):
    exercise_spawn_exception(stage, runner, monkeypatch)


@pytest.mark.parametrize(("stream", "exception_type"),
                         [(stream, error) for error in (OSError, RuntimeError) for stream in ("stdout", "stderr", "stdin")]
                         + [("stdout", SystemExit)])
@requires_node
def test_close_exception_retains_unknown_slot(stage, runner, monkeypatch, stream, exception_type):
    exercise_close_exception(stage, runner, monkeypatch, stream, exception_type)


@pytest.mark.parametrize("unhanded_close_fails", [False, True])
@requires_node
def test_thread_construction_closes_only_unhanded_pipes(stage, runner, monkeypatch, unhanded_close_fails, capsys):
    exercise_thread_construction(stage, runner, monkeypatch, unhanded_close_fails, capsys)


@pytest.mark.parametrize("start_then_raise", [False, True])
@requires_node
def test_partial_thread_start_keeps_unknown_slot(stage, runner, monkeypatch, start_then_raise):
    exercise_thread_exception(stage, runner, monkeypatch, start_then_raise)


@pytest.mark.parametrize(("stream", "exception_type"),
                         [(stream, RuntimeError) for stream in ("stdout", "stderr", "stdin")] + [("stdin", SystemExit)])
@requires_node
def test_non_os_pipe_io_is_private(stage, runner, monkeypatch, stream, exception_type, capsys):
    exercise_io_exception(stage, runner, monkeypatch, stream, exception_type, capsys)


@requires_node
@pytest.mark.skipif(os.name != "nt", reason="the shared helper checks the Windows pipe boundary")
def test_unconfirmed_pipe_cleanup_remains_fail_closed(stage, runner, monkeypatch):
    exercise_unconfirmed_pipe(stage, runner, monkeypatch)
