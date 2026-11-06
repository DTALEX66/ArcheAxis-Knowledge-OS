"""Finite synthetic checks for the unregistered interactive-outline adapter.

Only fixed synthetic replies and pinned donor files run here. No model, scene,
rendering, network, Core route or product persistence is exercised.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import types

import pytest

from tests.integrations.test_openmaic_interactive_url_map import checked_node, digest, read_bytes
from tests.integrations.test_openmaic_slide_normalize import raw_call

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/learning-providers/openmaic"
WORKER = SERVICE / "interactive-outline-worker.mjs"
RUNNER = SERVICE / "interactive_outline_runner.py"
PROMPTS = SERVICE / "vendor/prompts-1.3.0-interactive-outline"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit preverified ARCHEAXIS_TEST_NODE is required")
SCHEMA = "archeaxis.openmaic-interactive-outline/v1"
WORKER_SHA256 = "f8951de94bb50f0e69d444a0ac155a5240ce83dce0e56c1f4afa018ad4adcd83"
PROMPT_ORIGINALS = {
    "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
    "README.md": "39c85ecccdc6d3a534f3d955ea4b1668fcd2ff94a4cade8fb1365ece7f2ff31b",
    "templates/interactive-outlines/system.md": "ca99b9dd10282794126f95dd0e3735a0b13f35a6afdb8cd9e61517cc44c7d938",
    "templates/interactive-outlines/user.md": "3970a0539adffe8e7d78407bc6b67798aa20394452d5d4703b0f0e3723edfa07",
    "snippets/image-instructions.md": "8acf722ec46e57739a8d29f485e542e178295a0ffd8449c38555de7e0469068e",
    "snippets/video-instructions.md": "7e8f1ce6b4b0d680e65ca4a784544e6bdcdd1a659a72466a38c13f2a695e5b79",
    "snippets/media-safety-guidelines.md": "3affbe74b1621faa3fd4cec7587063fcbca374b07f13e91129c74cac8d4c611c",
}
# Render of the fixed capture request below against the pinned template.
PINNED_SYSTEM = "7794e3fdf53d7588e1f0fd22a9c6d79855631fc17eb4488b4983f9883d37ca78"
PINNED_USER = "666c7215359c11de76b4810555a223ff30825ca1074bc7635f81ddf3e66835a6"
CAPTURE = {"schema": SCHEMA, "stage": "capture", "request_id": "request_1",
           "requirement": "用本地材料准备交互课程", "source_text": "合成来源材料"}


def encode(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def mixed_reply() -> str:
    return json.dumps({"languageDirective": "使用简体中文", "courseTitle": "交互课", "outlines": [
        {"id": "o1", "type": "interactive", "title": "流程交互", "description": "演示流程",
         "keyPoints": ["步骤"], "order": 1, "widgetType": "diagram",
         "widgetOutline": {"diagramType": "flowchart", "nodeCount": 4}},
        {"id": "o2", "type": "slide", "title": "总结", "description": "总结要点", "keyPoints": [], "order": 2},
    ]}, ensure_ascii=False)


def replay(binding: dict, value: str) -> dict:
    return {**CAPTURE, "stage": "replay", "binding": binding,
            "reply": {"kind": "caller_supplied", "value": value}}


@pytest.fixture(scope="module")
def runner():
    module = types.ModuleType("openmaic_interactive_outline_test")
    module.__file__ = str(RUNNER)
    exec(compile(read_bytes(RUNNER), str(RUNNER), "exec"), module.__dict__)
    return module


@pytest.fixture(scope="module")
def captured(runner):
    result = runner.run_candidate(encode(CAPTURE), node_executable=checked_node())
    assert result["status"] == "PROMPT_CAPTURED", result
    return result["candidate"]["binding"]


def test_fixed_prompt_closure_is_the_declared_original_bytes():
    manifest = json.loads(read_bytes(PROMPTS / "ORIGINALS.json"))
    assert manifest["license"] == "MIT"
    assert manifest["source_archive_sha256"] == "7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40"
    assert digest(read_bytes(WORKER)) == WORKER_SHA256
    for name, expected in PROMPT_ORIGINALS.items():
        path = PROMPTS.joinpath(*name.split("/"))
        assert digest(read_bytes(path)) == expected


@requires_node
def test_capture_renders_the_donor_interactive_template_with_pinned_digests(runner):
    result = runner.run_candidate(encode(CAPTURE), node_executable=checked_node())
    assert result["status"] == "PROMPT_CAPTURED"
    assert result["process"]["direct_child"] == "REAPED" and result["process"]["pipe_threads"] == "JOINED"
    binding = result["candidate"]["binding"]
    assert binding["schema"] == "archeaxis.openmaic-interactive-outline-binding/v1"
    assert binding["request_id"] == "request_1"
    assert binding["templates_manifest_sha256"] == "aec7ba194977aefb8ca3ffcd41911915eb20eec4695ab7d944b9d6038873aa52"
    assert binding["worker_sha256"] == WORKER_SHA256
    assert digest(binding["system"].encode("utf-8")) == PINNED_SYSTEM
    assert digest(binding["user"].encode("utf-8")) == PINNED_USER
    assert "用本地材料准备交互课程" in binding["user"]
    assert "合成来源材料" in binding["user"]
    # Media instructions were conditional on capabilities this adapter does not have.
    assert "image-instructions" not in binding["system"]


@requires_node
def test_replay_admits_a_mixed_interactive_and_slide_outline(runner, captured):
    result = runner.run_candidate(encode(replay(captured, mixed_reply())), node_executable=checked_node())
    assert result["status"] == "CANDIDATE"
    document = result["candidate"]
    assert document["model_call"] == "NOT_INVOKED" and document["network_performed"] is False
    assert document["core_authorization"] == "NOT_ESTABLISHED"
    assert document["prompt_template"] == "interactive-outlines"
    assert document["exact_json_output"] is True and document["transformations"] == []
    outlines = document["data"]["outlines"]
    assert outlines[0]["type"] == "interactive" and outlines[0]["widgetType"] == "diagram"
    assert outlines[0]["widgetOutline"] == {"diagramType": "flowchart", "nodeCount": 4}
    assert outlines[1]["type"] == "slide" and "widgetType" not in outlines[1]
    assert [item["order"] for item in outlines] == [1, 2]


@requires_node
def test_repair_and_assignment_are_reported_as_transformations(runner, captured):
    fenced = "```json\n" + json.dumps({"languageDirective": "中文", "outlines": [
        {"type": "slide", "title": "T", "description": "D", "keyPoints": []}]}) + "\n```"
    result = runner.run_candidate(encode(replay(captured, fenced)), node_executable=checked_node())
    assert result["status"] == "CANDIDATE"
    document = result["candidate"]
    assert document["exact_json_output"] is False
    assert set(document["transformations"]) == {"UPSTREAM_JSON_REPAIRED", "UNSTABLE_GENERATED_OUTLINE_IDS",
                                                "OUTLINE_ORDER_ASSIGNED"}
    assert document["data"]["outlines"][0]["id"].isascii()


@requires_node
@pytest.mark.parametrize("outlines,kind", [
    ([{"id": "q", "type": "quiz", "title": "T", "description": "D", "keyPoints": [], "order": 1}],
     "OUTLINE_CONTENT_UNSUPPORTED"),
    ([{"id": "p", "type": "interactive", "title": "T", "description": "D", "keyPoints": [], "order": 1,
       "widgetType": "procedural-skill", "widgetOutline": {"task": "x"}}], "OUTLINE_CONTENT_UNSUPPORTED"),
    ([{"id": "s", "type": "slide", "title": "T", "description": "D", "keyPoints": [], "order": 1,
       "widgetType": "diagram"}], "UNKNOWN_OUTLINE_FIELDS"),
    ([{"id": "d", "type": "interactive", "title": "T", "description": "D", "keyPoints": [], "order": 1,
       "widgetType": "diagram", "widgetOutline": {"nodes": [{"id": "n1", "label": "node"}]}}],
     "OUTLINE_CONTENT_UNSUPPORTED"),
    ([{"id": "n", "type": "interactive", "title": "T", "description": "D", "keyPoints": [], "order": 1,
       "widgetType": "diagram", "widgetOutline": {"nodeCount": 201}}], "OUTLINE_CONTENT_UNSUPPORTED"),
    ([{"id": "o", "type": "slide", "title": "T", "description": "D", "keyPoints": [], "order": 2}],
     "OUTLINE_ORDER_OVERWRITTEN"),
])
def test_unsupported_outlines_are_refused_without_text(runner, captured, outlines, kind):
    value = json.dumps({"languageDirective": "中文", "outlines": outlines})
    result = runner.run_candidate(encode(replay(captured, value)), node_executable=checked_node())
    assert result["status"] == "REJECTED"
    assert result["error_code"] == "UNSUPPORTED_OUTPUT"
    assert result["process"]["direct_child"] == "REAPED"


@requires_node
def test_duplicate_outline_ids_are_refused(runner, captured):
    first = {"id": "same", "type": "slide", "title": "A", "description": "D", "keyPoints": [], "order": 1}
    second = {"id": "same", "type": "slide", "title": "B", "description": "D", "keyPoints": [], "order": 2}
    value = json.dumps({"languageDirective": "中文", "outlines": [first, second]})
    result = runner.run_candidate(encode(replay(captured, value)), node_executable=checked_node())
    assert result["status"] == "REJECTED" and result["error_code"] == "UNSUPPORTED_OUTPUT"


@requires_node
def test_a_changed_binding_is_named(runner, captured):
    changed = dict(captured, system=captured["system"] + " ")
    result = runner.run_candidate(encode(replay(changed, mixed_reply())), node_executable=checked_node())
    assert result["status"] == "REJECTED" and result["error_code"] == "BINDING_MISMATCH"


@requires_node
@pytest.mark.parametrize("raw", [
    b'{"schema":"archeaxis.openmaic-interactive-outline/v1","stage":"capture","request_id":"request_1",'
    b'"requirement":"SYNTHETIC_PRIVATE","requirement":"other","source_text":""}',
    b'{"schema":"archeaxis.openmaic-interactive-outline/v1","stage":"capture","request_id":"request_1",'
    b'"requirement":"SYNTHETIC_PRIVATE","source_text":"","extra":"SYNTHETIC_PRIVATE"}',
    b'\xef\xbb\xbf{}', b'\xff', b'{}',
])
def test_invalid_request_is_not_reflected(raw):
    code, result, output, _ = raw_call(WORKER, raw)
    assert code == 2 and result["status"] == "INVALID_REQUEST"
    assert b"SYNTHETIC_PRIVATE" not in output


@requires_node
def test_runner_rejects_arguments_and_a_wrong_node(runner, tmp_path):
    assert runner.run_candidate(encode(CAPTURE), node_executable=tmp_path / "missing-node.exe")["error_code"] == \
        "NODE_IDENTITY_MISMATCH"
    assert runner.run_candidate(b"\xff", node_executable=checked_node())["error_code"] == "INVALID_ARGUMENT"
    assert runner.run_candidate(encode(CAPTURE), node_executable=checked_node(),
                                timeout_seconds=0.1)["error_code"] == "INVALID_ARGUMENT"


@requires_node
def test_a_tampered_prompt_member_is_an_identity_mismatch(tmp_path):
    service = tmp_path / "service"
    shutil.copytree(SERVICE / "vendor/generation-0.3.28-outline", service / "vendor/generation-0.3.28-outline")
    shutil.copytree(SERVICE / "vendor/npm", service / "vendor/npm")
    shutil.copytree(PROMPTS, service / "vendor/prompts-1.3.0-interactive-outline")
    shutil.copyfile(WORKER, service / WORKER.name)
    target = service / "vendor/prompts-1.3.0-interactive-outline/templates/interactive-outlines/system.md"
    target.write_bytes(target.read_bytes() + b"\n")
    code, result, output, _ = raw_call(service / WORKER.name, encode(CAPTURE))
    assert code == 2 and result["status"] == "ADAPTER_IDENTITY_MISMATCH"
