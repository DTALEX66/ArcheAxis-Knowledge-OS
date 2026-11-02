"""Characterize current slide projection loss, not a lossless product contract.

This exercises the existing offline Node worker with synthetic inputs. It does
not establish model generation, Core persistence, or installed-runtime behavior.
The selected Node is explicit and is hashed before and after each direct call;
this cannot prevent the executable path being replaced during process startup.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import pytest

from tests.integrations import test_openmaic_scene_builder as scene_builder


ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/learning-providers/openmaic/scene-build-worker.mjs"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
NODE_SHA256 = os.environ.get("ARCHEAXIS_TEST_NODE_SHA256")
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


def _invoke_scene(frame):
    raw = json.dumps(frame, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    _check_node_identity()
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SYSTEMDRIVE") if key in os.environ}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        process = subprocess.run([NODE, str(WORKER)], input=raw, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, timeout=20, check=False, env=env,
                                 cwd=WORKER.parent, creationflags=flags)
    finally:
        _check_node_identity()
    assert process.returncode == 0
    result = json.loads(process.stdout.decode("utf-8"))
    assert result["status"] == "CANDIDATE"
    assert result["input_sha256"] == hashlib.sha256(raw).hexdigest()
    return raw, result


def _assert_slide_projection(frame, result, omitted_values):
    scene = result["scene"]
    canvas = scene["content"]["canvas"]
    assert scene["type"] == "slide" and scene["content"]["type"] == "slide"
    assert canvas["elements"] == frame["content"]["elements"]
    assert canvas["background"] == frame["content"]["background"]
    scene_json = json.dumps(scene, ensure_ascii=False)
    for value in omitted_values:
        assert value not in scene_json


def test_current_slide_projection_omits_remark_and_outline_details():
    """Record the current loss; omission is not a lossless product guarantee."""
    frame = scene_builder.request("slide")
    description = "SYNTHETIC_OUTLINE_DESCRIPTION_ONLY"
    key_point = "SYNTHETIC_OUTLINE_KEY_POINT_ONLY"
    remark = "SYNTHETIC_SLIDE_REMARK_ONLY"
    frame["outline"]["description"] = description
    frame["outline"]["keyPoints"] = [key_point]
    frame["content"]["remark"] = remark

    raw, result = _invoke_scene(frame)
    _assert_slide_projection(frame, result, (description, key_point, remark))

    # Each omitted field independently changes the hash of the actual request
    # bytes. The hash is an identity check, not a recoverable copy of the input.
    for section, field, value in (
        ("outline", "description", description + "_CHANGED"),
        ("outline", "keyPoints", [key_point + "_CHANGED"]),
        ("content", "remark", remark + "_CHANGED"),
    ):
        changed = copy.deepcopy(frame)
        changed[section][field] = value
        changed_raw, changed_result = _invoke_scene(changed)
        assert changed_raw != raw
        assert changed_result["input_sha256"] != result["input_sha256"]
        changed_marker = value[0] if isinstance(value, list) else value
        _assert_slide_projection(changed, changed_result, (description, key_point, remark, changed_marker))
