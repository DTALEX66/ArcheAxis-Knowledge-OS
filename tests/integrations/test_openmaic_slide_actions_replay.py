"""Original slide action branch with synthetic replies; no execution or model."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/learning-providers/openmaic/slide-actions-replay-worker.mjs"
VENDOR = WORKER.parent / "vendor"
DONOR = VENDOR / "generation-0.3.28-slide-actions"
SOURCE = VENDOR / "scene-content-0.3.28-original/generation/src/scene-generator.ts"
UPSTREAM = WORKER.parent / "upstream/OpenMAIC-1.3.0/packages/@openmaic/generation"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(
    not NODE, reason="explicit ARCHEAXIS_TEST_NODE is required; PATH is not searched")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def invoke(frame: dict | bytes) -> tuple[int, dict]:
    assert NODE and Path(NODE).is_absolute(), "ARCHEAXIS_TEST_NODE must be an absolute path"
    raw = frame if isinstance(frame, bytes) else json.dumps(frame, ensure_ascii=False).encode("utf-8")
    process = subprocess.run([NODE, str(WORKER)], input=raw, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=20, check=False)
    try:
        body = json.loads(process.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise AssertionError(
            f"missing JSON result: exit={process.returncode}, "
            f"stderr={process.stderr.decode('utf-8', 'replace')}") from error
    return process.returncode, body


def frame() -> dict:
    return {"schema": "archeaxis.openmaic-slide-actions-prompt/v1", "stage": "capture",
            "request_id": "prompt_1",
            "outline": {"id": "outline_1", "type": "slide", "title": "合成幻灯片",
                        "description": "测试", "keyPoints": ["练习"], "order": 1},
            "content": {"elements": [{"id": "text_1", "type": "text", "content": "合成要点"},
                        {"id": "image_1", "type": "image"}],
                        "background": {"type": "solid", "color": "#ffffff"}},
            "language_directive": "中文"}


def capture() -> dict:
    code, result = invoke(frame())
    assert code == 0 and result["status"] == "PROMPT_CAPTURED", result
    return result


def replay(reply: str, binding: dict) -> tuple[int, dict]:
    data = frame()
    data["stage"] = "replay"
    data["binding"] = binding
    data["reply"] = {"kind": "caller_supplied", "value": reply}
    return invoke(data)


def test_the_original_manifest_and_excerpts_are_byte_identical():
    raw = (DONOR / "ORIGINALS.json").read_bytes()
    record = json.loads(raw)
    assert sha(raw) == "0d8cf44c2259d908b5f4708b20fcd4c176e676a3a695c189a256623a5215e81e"
    assert record["license"] == "MIT" and len(record["originals"]) == 7
    for relative, expected in record["originals"].items():
        assert sha((DONOR / relative).read_bytes()) == expected
        assert sha((UPSTREAM / relative).read_bytes()) == expected
    assert record["source_file"] == "../scene-content-0.3.28-original/generation/src/scene-generator.ts"
    assert sha(SOURCE.read_bytes()) == record["source_sha256"]
    adapted = (DONOR / record["adapted_file"]).read_bytes()
    assert sha(adapted) == record["adapted_sha256"]
    assert [(item["start_line"], item["end_line"]) for item in record["excerpts"]] == [
        (1781, 1783), (1793, 1821), (1943, 1965), (1984, 2035), (2040, 2066)]
    lines = SOURCE.read_bytes().splitlines(keepends=True)
    for excerpt in record["excerpts"]:
        original = b"".join(lines[excerpt["start_line"] - 1:excerpt["end_line"]])
        assert sha(original) == excerpt["sha256"] and adapted.count(original) == 1
    assert b"export async function replaySlideActionsBranch(" in adapted


@requires_node
def test_prompt_capture_binds_the_original_slide_action_prompt():
    result = capture()
    binding = result["binding"]
    assert result["schema"] == "archeaxis.openmaic-slide-actions-prompt-result/v1"
    assert result["stage"] == "capture" and result["callback_count"] == 1
    assert binding["schema"] == "archeaxis.openmaic-slide-actions-prompt-binding/v1"
    assert binding["system"].startswith("# Slide Action Generator")
    assert 'id: "text_1", type: "text"' in binding["user"]
    assert 'id: "image_1", type: "image"' in binding["user"]
    assert binding["system_sha256"] == sha(binding["system"].encode("utf-8"))
    assert binding["user_sha256"] == sha(binding["user"].encode("utf-8"))
    assert binding["worker_sha256"] == sha(WORKER.read_bytes())
    assert binding["scene_actions_manifest_sha256"] == sha((DONOR / "ORIGINALS.json").read_bytes())
    assert result["model_call"] == "NOT_INVOKED" and result["action_execution"] == "NOT_PERFORMED"
    assert "human_review_required" not in result and result["data"] is None


@requires_node
def test_prompt_replay_admits_only_speech_and_real_focus_targets():
    binding = capture()["binding"]
    code, result = replay(json.dumps([
        {"type": "action", "name": "spotlight", "params": {"elementId": "text_1"}},
        {"type": "text", "content": " 开场 "},
        {"type": "action", "name": "laser", "params": {"elementId": "image_1"}},
    ], ensure_ascii=False), binding)
    assert code == 0 and result["status"] == "CANDIDATE", result
    assert [item["type"] for item in result["data"]["actions"]] == ["spotlight", "speech", "laser"]
    assert result["data"]["actions"][0]["elementId"] == "text_1"
    assert result["data"]["actions"][1]["text"] == "开场"
    assert set(result["transformations"]) == {"UNSTABLE_GENERATED_ACTION_IDS", "SPEECH_TRIMMED"}
    assert result["action_execution"] == "NOT_PERFORMED" and result["rendering_authorized"] is False
    assert result["human_review_required"] is True


@requires_node
def test_prompt_replay_refuses_every_other_named_verb_by_name():
    binding = capture()["binding"]
    for action in ({"type": "action", "name": "play_video", "params": {"elementId": "image_1"}},
                   {"type": "action", "name": "discussion", "params": {"topic": "Talk"}}):
        code, result = replay(json.dumps([action], ensure_ascii=False), binding)
        assert code == 2 and result["status"] == "UNSUPPORTED_ACTION" and result["data"] is None


@requires_node
def test_prompt_replay_quarantines_a_rewritten_focus_target():
    binding = capture()["binding"]
    code, result = replay(json.dumps([
        {"type": "action", "name": "spotlight", "params": {"elementId": "missing_9"}},
        {"type": "text", "content": "x"}], ensure_ascii=False), binding)
    assert code == 2 and result["status"] == "UNSUPPORTED_OR_FILTERED_NOT_ADMITTED"
    assert result["data"] is None


@requires_node
def test_prompt_replay_admits_a_donor_repaired_reply_as_non_exact():
    binding = capture()["binding"]
    code, result = replay('```json\n[{"type":"text","content":"围栏开场"}]\n```', binding)
    assert code == 0 and result["status"] == "CANDIDATE", result
    assert result["exact_json_output"] is False
    assert "UPSTREAM_JSON_REPAIRED" in result["transformations"]
    assert "UPSTREAM_NORMALIZATIONS_UNRECONSTRUCTED" in result["transformations"]
    assert result["data"]["actions"][0]["text"] == "围栏开场"


@requires_node
def test_prompt_replay_refuses_a_changed_binding_before_running_the_branch():
    binding = dict(capture()["binding"])
    binding["worker_sha256"] = "0" * 64
    code, result = replay('[{"type":"text","content":"x"}]', binding)
    assert code == 2 and result["status"] == "BINDING_MISMATCH"
    assert result["data"] is None and result.get("calls") is None


@requires_node
def test_changed_donor_member_is_rejected_before_replay(tmp_path):
    assert NODE and Path(NODE).is_absolute()
    copy = tmp_path / "worker-copy"
    copy.mkdir()
    shutil.copy2(WORKER, copy / WORKER.name)
    for member in ["generation-0.3.28-outline", "generation-0.3.28-slide-actions",
                   "dsl-0.12.0-actions", "npm"]:
        shutil.copytree(VENDOR / member, copy / "vendor" / member)
    changed = copy / "vendor/generation-0.3.28-slide-actions/templates/slide-actions/system.md"
    changed.write_bytes(changed.read_bytes() + b"\nchanged\n")
    process = subprocess.run([NODE, str(copy / WORKER.name), "--hello"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=10, check=False)
    assert process.returncode != 0 and process.stdout == b""
    assert b"UPSTREAM_MEMBER_IDENTITY_MISMATCH" in process.stderr
