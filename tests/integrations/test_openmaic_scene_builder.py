"""Offline upstream scene construction; not model, Core, or installed-runtime qualification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/learning-providers/openmaic/scene-build-worker.mjs"
VENDOR = WORKER.parent / "vendor/generation-0.3.28"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node runtime is not available")


def invoke(data: bytes | dict, *args: str) -> tuple[int, dict]:
    raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
    result = subprocess.run([NODE, str(WORKER), *args], input=raw, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=20, check=False)
    try:
        response = json.loads(result.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise AssertionError(f"worker did not return JSON: exit={result.returncode}, stderr={result.stderr.decode('utf-8', 'replace')}") from error
    return result.returncode, response


def request(kind: str = "quiz") -> dict:
    content = {"questions": [{"id": "q1", "type": "single", "question": "哪项是原件？",
                               "options": [{"label": "原件", "value": "A"}, {"label": "猜测", "value": "B"}], "answer": ["A"]}]}
    if kind == "slide":
        content = {"elements": [{"id": "text1", "type": "text", "content": "<p>你好</p>"}],
                   "background": {"type": "solid", "color": "#ffffff"}}
    if kind == "interactive":
        content = {"html": "<script>notExecuted()</script>", "widgetType": "simulation"}
    if kind == "pbl":
        content = {"projectV2": {"id": "project1", "title": "外部实践"}}
    return {"schema": "archeaxis.openmaic-scene-build/v1", "request_id": "request_1", "attempt": 1,
            "source": {"document_id": "doc_1", "version": 1, "content_sha256": "a" * 64},
            "stage_id": "stage_1", "scene_id": "scene_1", "outline": {"id": "outline_1", "type": kind,
            "title": "测试场景", "description": "离线合成输入", "keyPoints": ["核对来源"], "order": 2},
            "content": content, "actions": []}


def test_vendored_builder_and_license_are_bound_to_intake():
    assert hashlib.sha256((VENDOR / "scene-builder.ts").read_bytes()).hexdigest() == "e550ed528f9a017ea0fa1f9cc4a01f7eb22d541d5ada067967d3434393d1bf0a"
    assert hashlib.sha256((VENDOR / "LICENSE").read_bytes()).hexdigest() == "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19"


def test_hello_is_explicitly_not_a_core_connection():
    code, response = invoke(b"", "--hello")
    assert code == 0
    assert response["capability"] == "course.openmaic.scene-build"
    assert response["upstream_generation"] == "0.3.28"
    assert response["core_transport"] == "NOT_CONNECTED"


@pytest.mark.parametrize("kind", ["quiz", "slide", "interactive", "pbl"])
def test_real_upstream_builder_returns_inert_candidates(kind):
    frame = request(kind)
    raw = json.dumps(frame, ensure_ascii=False).encode("utf-8")
    code, response = invoke(raw)
    assert code == 0
    assert response["status"] == "CANDIDATE"
    assert response["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert response["scene"]["id"] == frame["scene_id"]
    assert response["scene"]["stageId"] == frame["stage_id"]
    assert response["scene"]["type"] == kind
    assert response["scene"]["outlineId"] == frame["outline"]["id"]
    assert response["source"] == frame["source"]
    assert response["source_binding"] == "client_declared_unverified"
    assert response["model_call"] == "NOT_INVOKED"
    assert response["canonical_bindings_verified"] is False
    assert response["human_review_required"] is True
    assert response["active_content_executed"] is False
    assert response["rendering_authorized"] is False
    if kind == "interactive":
        assert response["scene"]["content"]["html"] == frame["content"]["html"]


def test_fixed_scene_identity_does_not_claim_byte_idempotence():
    first_code, first = invoke(request("slide"))
    second_code, second = invoke(request("slide"))
    assert first_code == second_code == 0
    assert first["scene"]["id"] == second["scene"]["id"] == "scene_1"
    assert len(first["scene"]["content"]["canvas"]["id"]) == 21
    assert first["retry_bytes_stable"] is False
    assert second["retry_bytes_stable"] is False


def test_upstream_null_is_not_reported_as_a_generated_course():
    frame = request("quiz")
    frame["content"] = {"html": "some unrelated payload"}
    code, response = invoke(frame)
    assert code == 2
    assert response["status"] == "UPSTREAM_NULL"
    assert response["scene"] is None
    assert response["model_call"] == "NOT_INVOKED"


@pytest.mark.parametrize("change", [
    lambda frame: frame["source"].update(content_sha256="badhash"),
    lambda frame: frame["outline"].update(type="future"),
    lambda frame: frame.update(scene_id="../../outside"),
    lambda frame: frame.update(attempt=0),
    lambda frame: frame.update(actions=[{"type": "x"}] * 101),
    lambda frame: frame.update(extra="unrecognized"),
])
def test_invalid_identity_unknown_kind_and_budget_are_refused(change):
    frame = request()
    change(frame)
    code, response = invoke(frame)
    assert code == 2
    assert response["status"] == "INVALID_REQUEST"
    assert response["scene"] is None


def test_duplicate_escaped_identity_invalid_utf8_and_oversized_frames_are_refused():
    raw = json.dumps(request()).replace('"scene_id": "scene_1"', '"scene_id": "scene_1", "scene_\\u0069d": "other"').encode()
    assert invoke(raw)[1]["status"] == "INVALID_REQUEST"
    assert invoke(b"\xff")[1]["status"] == "INVALID_REQUEST"
    assert invoke(b" " * 256_001)[1]["status"] == "INVALID_REQUEST"
