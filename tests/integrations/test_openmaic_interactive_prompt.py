"""Finite synthetic checks for the unregistered interactive prompt adapter.

Only fixed synthetic outlines and the pinned donor files run here. No model,
HTML, rendering, network, Core route or product persistence is exercised.
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
from tests.integrations.test_openmaic_interactive_url_map import checked_node, digest, read_bytes, write_new
from tests.integrations.test_openmaic_slide_normalize import raw_call

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/learning-providers/openmaic"
DONOR = SERVICE / "vendor/scene-content-0.3.28-original/generation"
WORKER = SERVICE / "interactive-prompt-worker.mjs"
RUNNER = SERVICE / "interactive_prompt_runner.py"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit preverified ARCHEAXIS_TEST_NODE is required")
SCHEMA = "archeaxis.openmaic-interactive-prompt/v1"
WORKER_SHA256 = "cb9ed8a1ae129e1bf3fa389976adeebd4157c626e12458f05495b28d7711b37d"
ORIGINALS = {
    "ORIGINALS.json": "5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3",
    "package.json": "5308b268d06dd27e592de00f02d57b046588df0d6e160f4179788388d5a806d1",
    "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
    "src/prompts/index.ts": "2d71a8c8e261b773562b2d2597d61690fa547a80c7aca9f5cc329b49a6c987ab",
    "src/prompts/loader.ts": "584bd51c71c53c02e058df5209d9bcb1f73ff531677a9d7a3aa168d135a43e50",
    "src/interactive-libraries.ts": "1c9f212d7e2010dd3e1f4889efe22825fcb1f52772b056e5a30fc58753f29de1",
    "templates/simulation-content/system.md": "5d0fbae09a546f9f65e10605c31b73769816a8e8eb5a3282df13c8199101bf41",
    "templates/simulation-content/user.md": "d5a52c8a249351b8438f5edfeac9b95ca0af2da6631be3aedc95b13f1a199bfe",
    "templates/diagram-content/system.md": "98d8b2e59eadb17cfee2f9d55188c901efc7f81d27907287de3568cfaf7120e9",
    "templates/diagram-content/user.md": "a475c7ed074cc80758384676d38891555f9d5213771c4459c9c3fff74894b656",
    "templates/code-content/system.md": "f44e00837b754929f66a55640758630c402600eebe8c3777c3960eedf140b438",
    "templates/code-content/user.md": "5cd48712326d5e1e1e0335f623f1b8770d5b2915dbd2877ec41bfeec49f5d18e",
    "templates/game-content/system.md": "0563c722fd29a0186d7538ed6fe16da07945517673785f04e0d6c8d4f6262cf1",
    "templates/game-content/user.md": "21ece6285e2dcea25f583b4995deef7e0f1aca9ee68aa8623349fdfe6c2ceea6",
    "templates/visualization3d-content/system.md": "874452d98f255c9cda85485a4d95518d250556aa4b6a25b8a53f219b09acb624",
    "templates/visualization3d-content/user.md": "962b8fc01b310a8a7cf00165b0477708d81ab2b9c7388bc0f321eb40bcdd4dcc",
    "snippets/interactive-libraries.md": "35b2291d607f898f52b03e64d233122b64069e9f9f6dd9d019dae3cd3197e239",
    "snippets/interactive-math.md": "3fb6d871d1b22cf3642185807bb99e4efea996ff7e508abc920fd998df1a1f38",
    "snippets/interactive-observation.md": "6c2c0433ba476c08eedff05ea545c29110ca967fa78a1eea20b3f468363963d2",
}
WIDGET_OUTLINES = {
    "simulation": {"concept": "弹性碰撞", "key_variables": ["质量", "速度"]},
    "diagram": {"diagram_type": "flowchart", "node_count": 3, "nodes": ["开始", "处理", "结束"]},
    "code": {"language": "python"},
    "game": {"game_type": "quiz"},
    "visualization3d": {"visualization_type": "custom", "objects": ["球"], "interactions": ["拖拽"]},
}
PINNED = {
    "simulation": ("ed26023031ecdbf6a806e9254e6623ca07f7d345d99f37b04dae4f9e3b5fd17b",
                   "985dfde39d20ce4ae394eac13a09934cc61763e7d02ce30c5c54c2ef9644815a"),
    "diagram": ("f1dff8c675b94aac9257c51cbf406f0eb15909d17ea59a7fca258e052b00e2a8",
                "7a8611d5ff0d40cf32864f1e8ef66accde925419d3c120fec0bc33d382cdd31d"),
    "code": ("07983e9092436cac193f2dca5f9ba4becb2d0d0b0d4996ce7026eee8e435002c",
             "2c3afa8bf8d6b16029e7b483d78a6038adef504337fa2b59a75ccaed27a3ee8f"),
    "game": ("d772f55de7fc3e387d1e012e8aebc14e3cfb12fc05a0f2a6962dfa672d940796",
             "5c841f51885a46674f7857b57148a18f317e376b26ca9e8218ae1ed95e9cd517"),
    "visualization3d": ("7ebc03bed666804e859d428fc59989180e0a8ea872f65b0d6c2fae4ed25eed3f",
                       "3055613c7fc9ed7f8328755a517ae78fcae9b8b4d572f7153c4711bed7aab953"),
}


def encode(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def request(widget="simulation") -> dict:
    return {"outline": {"title": "合成互动标题 😀", "description": "第一行\r\n第二行 {{literal}}",
                        "key_points": ["一号", "二号"], "widget_type": widget,
                        "widget_outline": copy.deepcopy(WIDGET_OUTLINES[widget])},
            "language_directive": "使用简体中文"}


def frame(raw: bytes, private=False) -> bytes:
    return encode({"schema": SCHEMA, "include_private": private,
                   "request_utf8_base64": base64.b64encode(raw).decode("ascii")})


@pytest.fixture
def stage(tmp_path_factory):
    target = tmp_path_factory.mktemp("interactive-prompt") / "h"
    root = target / "vendor/scene-content-0.3.28-original/generation"
    for name, expected in ORIGINALS.items():
        raw = read_bytes(DONOR.joinpath(*name.split("/")))
        assert digest(raw) == expected
        write_new(root.joinpath(*name.split("/")), raw)
    write_new(target / WORKER.name, read_bytes(WORKER))
    return target


@pytest.fixture
def runner(stage):
    module = types.ModuleType("openmaic_interactive_prompt_test")
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
    assert digest(read_bytes(WORKER)) == WORKER_SHA256
    for name, expected in ORIGINALS.items():
        assert digest(read_bytes(DONOR.joinpath(*name.split("/")))) == expected
        if name != "ORIGINALS.json":
            assert manifest["originals"][name] == expected


@requires_node
@pytest.mark.parametrize("widget", sorted(WIDGET_OUTLINES))
def test_each_widget_builds_its_pinned_prompt(stage, runner, widget):
    result = runner.run_candidate(encode(request(widget)), node_executable=checked_node(), include_private=True)
    assert result["status"] == "BUILT"
    assert result["process"]["direct_child"] == "REAPED" and result["process"]["pipe_threads"] == "JOINED"
    doc = result["candidate"]
    assert doc["widget_type"] == widget and doc["model_call"] == "NOT_INVOKED"
    assert doc["html_output"] == "NOT_PRODUCED" and doc["full_generation"] == "NOT_PERFORMED"
    assert doc["core_authorization"] == "NOT_ESTABLISHED"
    assert digest(doc["private"]["system"].encode("utf-8")) == PINNED[widget][0]
    assert digest(doc["private"]["user"].encode("utf-8")) == PINNED[widget][1]
    assert "使用简体中文" in doc["private"]["user"]
    assert "一号\n二号" in doc["private"]["user"]
    if widget == "simulation":
        assert "弹性碰撞" in doc["private"]["user"] and "质量, 速度" in doc["private"]["user"]
    else:
        assert "合成互动标题" in doc["private"]["user"]


@requires_node
@pytest.mark.parametrize("widget", sorted(WIDGET_OUTLINES))
def test_public_result_hides_private_prompt(stage, runner, widget):
    value = request(widget)
    public = runner.run_candidate(encode(value), node_executable=checked_node())
    assert public["status"] == "BUILT" and public["candidate"]["private"] is None
    serialized = json.dumps(public, ensure_ascii=False)
    for needle in ("合成互动标题", "literal", "弹性碰撞", "使用简体中文"):
        assert needle not in serialized


@requires_node
@pytest.mark.parametrize("raw", [
    b'{"outline":{"title":"one","title":"two","description":"","key_points":[],"widget_type":"game"},"language_directive":""}',
    b'{"outline":{"title":"SYNTHETIC_PRIVATE","description":"","key_points":[],"widget_type":"game"},"language_directive":"","extra":"SYNTHETIC_PRIVATE"}',
    b'{"outline":{"title":"\\ud800","description":"","key_points":[],"widget_type":"game"},"language_directive":""}',
    b'\xef\xbb\xbf{"outline":{}}', b'\xff', b'{}',
])
def test_invalid_request_is_not_reflected(stage, raw):
    code, result, output, _ = raw_call(stage / WORKER.name, frame(raw, True))
    assert code == 0 and result["status"] == "REJECTED" and result["error_code"] == "INVALID_REQUEST"
    assert b"SYNTHETIC_PRIVATE" not in output and result["private"] is None


@requires_node
@pytest.mark.parametrize("widget", ["procedural-skill", "custom-html", ""])
def test_unsupported_widget_types_are_named(stage, widget):
    value = request()
    value["outline"]["widget_type"] = widget
    code, result, output, _ = raw_call(stage / WORKER.name, frame(encode(value), True))
    assert code == 0 and result["status"] == "REJECTED" and result["error_code"] == "UNSUPPORTED_WIDGET_TYPE"
    assert result["widget_type"] is None and b"procedural" not in output


@requires_node
@pytest.mark.parametrize("change", [
    {"widget_outline": {"bogus": "SYNTHETIC_PRIVATE"}},
    {"widget_outline": "SYNTHETIC_PRIVATE"},
    {"key_points": ["a"] * 21},
    {"key_points": [None]},
    {"title": ""},
    {"widget_type_extra": "SYNTHETIC_PRIVATE"},
])
def test_outline_shape_is_bounded(stage, change):
    value = request()
    if "widget_type_extra" in change:
        value["outline"]["widget_type_extra"] = change["widget_type_extra"]
    else:
        value["outline"].update(change)
    code, result, output, _ = raw_call(stage / WORKER.name, frame(encode(value), True))
    assert code == 0 and result["status"] == "REJECTED" and result["error_code"] == "INVALID_REQUEST"
    assert b"SYNTHETIC_PRIVATE" not in output


@requires_node
def test_diagram_node_count_bound(stage):
    value = request("diagram")
    value["outline"]["widget_outline"]["node_count"] = 201
    code, result, _, _ = raw_call(stage / WORKER.name, frame(encode(value), True))
    assert code == 0 and result["status"] == "REJECTED" and result["error_code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("name", sorted(n for n in ORIGINALS if n != "ORIGINALS.json"))
@pytest.mark.parametrize("change", ["missing", "tampered"])
@requires_node
def test_fixed_originals_are_required(stage, name, change):
    path = stage / "vendor/scene-content-0.3.28-original/generation" / name
    if change == "missing":
        os.unlink(native(path))
    else:
        with open(native(path), "ab") as stream:
            stream.write(b"SYNTHETIC_TAMPER")
    code, result, output, _ = raw_call(stage / WORKER.name, frame(encode(request()), True))
    assert code == 0 and result["status"] == "REJECTED" and result["error_code"] == "UPSTREAM_IDENTITY_MISMATCH"
    assert b"SYNTHETIC_TAMPER" not in output and result["private"] is None


@requires_node
def test_ambient_asset_override_is_rejected(stage):
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
    env["INTERACTIVE_ASSET_BASE_URL"] = "SYNTHETIC_PRIVATE_OVERRIDE"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    child = subprocess.run([str(checked_node()), str(stage / WORKER.name)],
                           input=frame(encode(request()), True), env=env, cwd=str(stage), shell=False,
                           capture_output=True, timeout=30, creationflags=flags)
    assert child.returncode == 0
    result = json.loads(child.stdout)
    assert result["status"] == "REJECTED" and result["error_code"] == "ENVIRONMENT_OVERRIDE"
    assert b"SYNTHETIC_PRIVATE_OVERRIDE" not in child.stdout + child.stderr


@requires_node
def test_reply_cannot_name_a_different_widget(stage, runner):
    result = runner.run_candidate(encode(request("simulation")), node_executable=checked_node(), include_private=True)
    assert result["status"] == "BUILT"
    doc = copy.deepcopy(result["candidate"])
    assert runner._validate_reply(encode(doc), True, "simulation")[0] == "BUILT"
    assert runner._validate_reply(encode(doc), True, "game") == ("REJECTED", "INVALID_WORKER_REPLY")
    doc["widget_type"] = None
    assert runner._validate_reply(encode(doc), True, "simulation") == ("REJECTED", "INVALID_WORKER_REPLY")


@requires_node
def test_replaced_node_identity_is_rejected_without_spawn(stage, runner, monkeypatch):
    def unexpected_spawn(*_args, **_kwargs):
        raise AssertionError("an unverified Node must not be started")

    monkeypatch.setattr(runner.subprocess, "Popen", unexpected_spawn)
    monkeypatch.setattr(runner, "NODE_SHA256", "0" * 64)
    result = runner.run_candidate(encode(request()), node_executable=checked_node())
    assert result["error_code"] == "NODE_IDENTITY_MISMATCH"
    assert result["process"]["direct_child"] == "NOT_STARTED"


@requires_node
def test_private_reply_validation_rejects_tampering(stage, runner):
    result = runner.run_candidate(encode(request()), node_executable=checked_node(), include_private=True)
    doc = result["candidate"]
    assert runner._validate_reply(encode(doc), True, "simulation")[0] == "BUILT"
    assert runner._validate_reply(encode(doc), False, "simulation") == ("REJECTED", "INVALID_WORKER_REPLY")
    for change in ("hash", "extra", "surrogate"):
        broken = copy.deepcopy(doc)
        if change == "hash":
            broken["private"]["user_sha256"] = "0" * 64
        if change == "extra":
            broken["private"]["extra"] = "SYNTHETIC_PRIVATE"
        if change == "surrogate":
            broken["private"]["user"] = "\ud800"
        serialized = json.dumps(broken, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        assert runner._validate_reply(serialized, True, "simulation") == ("REJECTED", "INVALID_WORKER_REPLY")


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
            owned[0].kill()
            first.join(timeout=5)
    assert not first.is_alive()
    assert outcome["status"] == "REJECTED" and outcome["error_code"] == "CANCELLED"
    assert outcome["process"]["direct_child"] == "REAPED"
    assert outcome["process"]["pipe_threads"] == "JOINED" and outcome["process"]["descendants"] == "UNKNOWN"
