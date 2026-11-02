"""Rules for the Core scene contract, checked against the real donor projection.

The canonical implementation is Rust Core (`crates/archeaxis-domain/src/course.rs`).
These tests execute the real pinned worker and an unregistered reference derivation
(`scene-contract-report.mjs`) on synthetic inputs, so the derivation rules — named
refusals, projection loss, render contract — are observed against the actual donor
build rather than asserted from reading the Rust source. They do not build a product
course, persist anything in Core, call a model, or qualify an installed app. The Node
executable is explicit and hashed before and after each direct call; this cannot
prevent the path being replaced during process startup.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import pytest

from tests.integrations import test_openmaic_scene_builder as scene_builder


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/learning-providers/openmaic"
WORKER = SERVICE / "scene-build-worker.mjs"
REPORT = SERVICE / "scene-contract-report.mjs"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
NODE_SHA256 = os.environ.get("ARCHEAXIS_TEST_NODE_SHA256")
# The worker bytes this slice reads. Nothing here rewrites or re-pins the donor.
WORKER_SHA256 = "c4a2dad9c96ebd13aa20827410227d2650cda0dac80e3a3927968d1e024779e9"
pytestmark = pytest.mark.skipif(
    not NODE or not NODE_SHA256,
    reason="explicit ARCHEAXIS_TEST_NODE and ARCHEAXIS_TEST_NODE_SHA256 are required",
)


def _check_node_identity():
    assert NODE and NODE_SHA256
    path = Path(NODE)
    assert path.is_absolute(), "ARCHEAXIS_TEST_NODE must be an absolute path"
    assert re.fullmatch(r"[0-9a-f]{64}", NODE_SHA256), "NODE SHA-256 must be lowercase hexadecimal"
    maximum = 512 * 1024 * 1024
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as source:
        while True:
            block = source.read(min(1024 * 1024, maximum + 1 - count))
            if not block:
                break
            count += len(block)
            assert count <= maximum, "Node executable exceeds the identity check budget"
            digest.update(block)
    assert count > 0 and digest.hexdigest() == NODE_SHA256, "Node identity mismatch"


def _run(script: Path, payload: bytes, *args: str) -> tuple[int, dict]:
    _check_node_identity()
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        process = subprocess.run([NODE, str(script), *args], input=payload, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, timeout=20, check=False, env=env,
                                 cwd=SERVICE, creationflags=flags)
    finally:
        _check_node_identity()
    try:
        response = json.loads(process.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise AssertionError(
            f"worker did not return JSON: exit={process.returncode}, "
            f"stderr={process.stderr.decode('utf-8', 'replace')}"
        ) from error
    return process.returncode, response


def _build(frame: dict) -> tuple[bytes, dict]:
    raw = json.dumps(frame, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    code, response = _run(WORKER, raw)
    assert code == 0
    assert response["status"] == "CANDIDATE"
    assert response["input_sha256"] == hashlib.sha256(raw).hexdigest()
    return raw, response


def _report(request: dict, worker_document: dict | None) -> dict:
    payload = json.dumps(
        {"schema": "archeaxis.openmaic-scene-contract-input/v1", "request": request,
         "worker_document": worker_document},
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    code, response = _run(REPORT, payload)
    assert code == 0, response
    assert response["schema"] == "archeaxis.openmaic-scene-contract-report/v1"
    assert response["authority_effect"] == "none_reference_only"
    assert response["canonical_implementation"] == "crates/archeaxis-domain/src/course.rs"
    return response


def _slide_with_geometry() -> dict:
    frame = scene_builder.request("slide")
    frame["content"]["elements"] = [
        {"id": "text1", "type": "text", "content": "<p>合成文本</p>",
         "left": 40, "top": 48, "width": 320, "height": 96, "rotate": 0},
    ]
    return frame


def test_worker_bytes_are_the_pinned_donor_worker():
    assert hashlib.sha256(WORKER.read_bytes()).hexdigest() == WORKER_SHA256


def test_hello_declares_an_unregistered_reference_derivation():
    code, response = _run(REPORT, b"", "--hello")
    assert code == 0
    assert response["capability"] == "course.openmaic.scene-contract"
    assert response["registered"] is False
    assert response["core_transport"] == "NOT_CONNECTED"


def test_slide_reports_the_omissions_the_real_projection_actually_makes():
    frame = _slide_with_geometry()
    description, key_point, remark = (
        "SYNTHETIC_OUTLINE_DESCRIPTION_ONLY",
        "SYNTHETIC_OUTLINE_KEY_POINT_ONLY",
        "SYNTHETIC_SLIDE_REMARK_ONLY",
    )
    frame["outline"]["description"] = description
    frame["outline"]["keyPoints"] = [key_point]
    frame["content"]["remark"] = remark

    _, worker = _build(frame)
    report = _report(frame, worker)
    assert report["status"] == "REPORT"
    assert report["refusal"] is None
    assert report["worker_candidate_observed"] is True
    assert report["projection"]["lossless"] is False
    assert report["projection"]["omitted"] == [
        "content.remark", "outline.description", "outline.keyPoints"]
    # The report is grounded in the actual projection: every reported omission really
    # is absent from the scene the donor builder returned.
    scene_json = json.dumps(worker["scene"], ensure_ascii=False)
    for marker in (description, key_point, remark):
        assert marker not in scene_json
    # The scene itself is still playable text: losing outline metadata is not losing paint.
    assert report["render"]["playable"] is True
    assert report["render"]["renderer"] == "openmaic-canvas-text"
    assert report["render"]["counts"] == {"elements": 1, "questions": 0, "unsupported": 0}


def test_media_and_missing_geometry_are_listed_instead_of_being_dropped():
    frame = _slide_with_geometry()
    frame["content"]["elements"].append({"id": "media1", "type": "image", "src": "https://example.invalid/a.png"})
    _, worker = _build(frame)
    report = _report(frame, worker)
    assert report["render"]["playable"] is False
    assert report["render"]["counts"] == {"elements": 2, "questions": 0, "unsupported": 1}
    assert report["render"]["unsupported"] == [
        {"path": "content.canvas.elements[1]", "reason": "only text elements are rendered"}]

    blank = scene_builder.request("slide")  # the donor fixture has no canvas geometry
    _, blank_worker = _build(blank)
    blank_report = _report(blank, blank_worker)
    assert blank_report["render"]["playable"] is False
    assert blank_report["render"]["unsupported"] == [
        {"path": "content.canvas.elements[0]", "reason": "element needs bounded canvas geometry"}]


def test_quiz_contract_is_playable_and_still_reports_outline_loss():
    frame = scene_builder.request("quiz")
    _, worker = _build(frame)
    report = _report(frame, worker)
    assert report["projection"]["omitted"] == ["outline.description", "outline.keyPoints"]
    assert report["projection"]["lossless"] is False
    assert report["render"]["playable"] is True
    assert report["render"]["renderer"] == "openmaic-quiz-objective"
    assert report["render"]["counts"] == {"elements": 0, "questions": 1, "unsupported": 0}

    # An answer that is not a list of option values cannot be scored safely.
    unsafely_scored = json.loads(json.dumps(frame))
    unsafely_scored["content"]["questions"][0]["answer"] = "A"
    _, unsafely_scored_worker = _build(unsafely_scored)
    unsafely_scored_report = _report(unsafely_scored, unsafely_scored_worker)
    assert unsafely_scored_report["render"]["playable"] is False
    assert unsafely_scored_report["render"]["unsupported"] == [
        {"path": "content.questions[0]", "reason": "answer must be a list of option values"}]


@pytest.mark.parametrize("kind", ["interactive", "pbl"])
def test_interactive_and_pbl_are_named_refusals_not_silent_loss(kind):
    # No worker runs: the contract refuses before a scene could be built or dropped.
    report = _report(scene_builder.request(kind), None)
    assert report["status"] == "REFUSED"
    assert report["refusal"]["reason"] == "UNSUPPORTED_SCENE"
    assert report["refusal"]["scene_type"] == kind
    assert report["refusal"]["supported_scene_types"] == ["slide", "quiz"]
    assert report["worker_candidate_observed"] is False
    assert report["render"] is None


def test_unknown_versions_are_refused_by_name():
    future_request = scene_builder.request("quiz")
    future_request["schema"] = "archeaxis.openmaic-scene-build/v2"
    report = _report(future_request, None)
    assert report["refusal"] == {
        "reason": "UNSUPPORTED_REQUEST_VERSION",
        "declared": "archeaxis.openmaic-scene-build/v2",
        "supported": ["archeaxis.openmaic-scene-build/v1"],
    }

    versioned = scene_builder.request("slide")
    versioned["content"]["schemaVersion"] = 2
    report = _report(versioned, None)
    assert report["status"] == "REFUSED"
    assert report["refusal"]["reason"] == "UNSUPPORTED_SCENE_VERSION"
    assert report["refusal"]["declared"] == 2
    assert report["refusal"]["supported_scene_versions"] == [1]


def test_report_is_derived_from_the_projection_not_from_random_ids_or_clock():
    frame = _slide_with_geometry()
    _, first = _build(frame)
    _, second = _build(frame)
    # The donor canvas ID and timestamps differ between runs.
    assert first["scene"]["content"]["canvas"]["id"] != second["scene"]["content"]["canvas"]["id"]
    assert first["scene"]["createdAt"] != second["scene"]["createdAt"]
    first_report = _report(frame, first)
    second_report = _report(frame, second)
    assert first_report["projection"] == second_report["projection"]
    assert first_report["render"] == second_report["render"]


def test_no_candidate_reply_is_not_read_as_a_lossless_or_playable_scene():
    frame = scene_builder.request("quiz")
    failed = {"schema": "archeaxis.openmaic-scene-build-result/v1", "status": "UPSTREAM_NULL",
              "reason": "upstream builder returned null", "scene": None}
    report = _report(frame, failed)
    assert report["status"] == "NO_CANDIDATE"
    assert report["worker_candidate_observed"] is False
    assert report["projection"]["lossless"] is False
    assert report["render"] is None


@pytest.mark.parametrize("payload", [
    pytest.param(b"{}", id="empty-object"),
    pytest.param(b"\xff", id="invalid-utf8"),
    pytest.param(b" " * 512_001, id="oversized-frame"),
    pytest.param(
        json.dumps({"schema": "archeaxis.openmaic-scene-contract-input/v1", "request": {},
                    "worker_document": None, "extra": True}).encode(),
        id="unknown-field"),
    pytest.param(
        json.dumps({"schema": "archeaxis.openmaic-scene-contract-input/v1", "request": {},
                    "worker_document": None}).encode(),
        id="incomplete-request"),
    pytest.param(
        json.dumps({"schema": "archeaxis.openmaic-scene-contract-input/v1", "request": [],
                    "worker_document": None}).encode(),
        id="request-not-object"),
])
def test_invalid_inputs_are_refused_without_side_effects(payload):
    code, response = _run(REPORT, payload)
    assert code == 2
    assert response["status"] == "INVALID_REQUEST"
    assert response["projection"] is None
    assert response["render"] is None
