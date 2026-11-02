"""SRT timestamp controls through the production-shaped subtitle transport."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/python-workers/document/worker_subtitles.py"


def invoke(tmp_path, raw):
    staging = tmp_path / "staging"
    (staging / "input").mkdir(parents=True)
    (staging / "output").mkdir()
    digest = hashlib.sha256(raw).hexdigest()
    source = staging / "input" / digest
    source.write_bytes(raw)
    request = {
        "schema": "archeaxis.worker-request/v1", "type": "job_request",
        "request_id": "srt-request", "job_id": "srt-job", "attempt": 1,
        "protocol_minor": 0, "capability": "subtitles.structure",
        "capability_version": "1", "deadline_ms": 30000,
        "inputs": [{"uri": f"job://input/{digest}", "sha256": digest,
                    "media_type": "application/x-subrip"}],
        "parameters": {},
    }
    env = {"SystemRoot": os.environ["SystemRoot"]} if os.name == "nt" else {}
    env.update(TEMP=str(staging), TMP=str(staging))
    process = subprocess.run(
        [sys.executable, "-B", "-S", str(WORKER), "--staging-root", str(staging)],
        input=json.dumps(request) + "\n", capture_output=True, text=True, encoding="utf-8",
        timeout=30, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=env,
    )
    lines = process.stdout.splitlines()
    assert len(lines) == 2
    hello, response = map(json.loads, lines)
    assert hello["capabilities"] == ["subtitles.structure"]
    assert source.read_bytes() == raw
    return process, response, staging / "output"


@pytest.mark.parametrize("timing", [
    b"00:00:03,000 --> 00:00:02,000",
    b"00:00:60,000 --> 00:01:01,000",
    b"00:60:00,000 --> 01:01:00,000",
    b"00:00:00,000 --> 00:00:60,000",
    b"00:00:00,000 --> 00:60:00,000",
])
def test_invalid_srt_timing_is_not_reported_as_success(tmp_path, timing):
    raw = b"1\n00:00:00,000 --> 00:00:01,000\nSynthetic before\n\n2\n" + timing + b"\nSynthetic invalid\n"
    process, response, output = invoke(tmp_path, raw)
    assert process.returncode == 1
    assert response["status"] == "failed" and response["outputs"] == []
    assert list(output.iterdir()) == []


def test_valid_srt_boundary_and_zero_duration_keep_exact_time(tmp_path):
    raw = (b"1\n00:59:59,9 --> 01:00:00,25\nSynthetic boundary\n\n"
           b"2\n01:00:00,250 --> 01:00:00,250\nSynthetic zero\n")
    process, response, output = invoke(tmp_path, raw)
    assert process.returncode == 0 and response["status"] == "succeeded"
    outputs = {item["kind"]: item for item in response["outputs"]}
    assert (output / outputs["text"]["sha256"]).read_bytes() == b"Synthetic boundary\nSynthetic zero\n"
    receipt = json.loads((output / outputs["loss_report"]["sha256"]).read_bytes())
    cues = receipt["params"]["worker_structure"]
    assert [(cue["offset_ms"], cue["duration_ms"]) for cue in cues] == [(3599900, 350), (3600250, 0)]


@pytest.mark.parametrize("timing", [
    b"100:00:00,000 --> 00:00:01,000",
    b"00:00:00,000 --> 00:00:01,2345",
    b"00:00:00,0000 --> 00:00:01,000",
    b"9999999999:00:00,000 --> 9999999999:00:01,000",
])
def test_srt_time_tokens_are_not_silently_truncated(tmp_path, timing):
    raw = b"1\n" + timing + b"\nSynthetic timestamp\n"
    process, response, output = invoke(tmp_path, raw)
    assert process.returncode == 1
    assert response["status"] == "failed" and response["outputs"] == []
    assert list(output.iterdir()) == []


def test_long_srt_hours_and_trailing_position_data_preserve_time(tmp_path):
    raw = (b"1\n100:00:00,125 --> 100:00:01,375 X1:10 X2:20\n"
           b"Synthetic long duration\n")
    process, response, output = invoke(tmp_path, raw)
    assert process.returncode == 0 and response["status"] == "succeeded"
    outputs = {item["kind"]: item for item in response["outputs"]}
    receipt = json.loads((output / outputs["loss_report"]["sha256"]).read_bytes())
    cue = receipt["params"]["worker_structure"][0]
    assert (cue["offset_ms"], cue["duration_ms"]) == (360000125, 1250)
    assert "SRT timing suffixes" in receipt["loss_note"]


@pytest.mark.parametrize("timing", [
    b"-00:00:01,000 --> 00:00:02,000",
    b"prefix 00:00:00,000 --> 00:00:01,000",
    b"00:00:00,000 --> 00:00:01,000,999",
    b"00:00:00,000 --> 00:00:01,000.5",
    b"00:00:00,000 --> 00:00:01,000extra",
    b"00:00:00,000 --> 00:00:01,000 --> 00:00:02,000",
])
def test_srt_time_line_does_not_hide_non_whitespace_fragments(tmp_path, timing):
    raw = b"1\n" + timing + b"\nSynthetic timestamp\n"
    process, response, output = invoke(tmp_path, raw)
    assert process.returncode == 1
    assert response["status"] == "failed" and response["outputs"] == []
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("milliseconds,expected_status", [(b"991", "succeeded"), (b"992", "failed")])
def test_srt_maximum_precise_timestamp(tmp_path, milliseconds, expected_status):
    timecode = b"2501999792:59:00," + milliseconds
    raw = b"1\n" + timecode + b" --> " + timecode + b"\nSynthetic limit\n"
    process, response, output = invoke(tmp_path, raw)
    assert response["status"] == expected_status
    if expected_status == "failed":
        assert process.returncode == 1 and response["outputs"] == []
        assert list(output.iterdir()) == []
    else:
        assert process.returncode == 0
        outputs = {item["kind"]: item for item in response["outputs"]}
        receipt = json.loads((output / outputs["loss_report"]["sha256"]).read_bytes())
        cue = receipt["params"]["worker_structure"][0]
        assert (cue["offset_ms"], cue["duration_ms"]) == ((1 << 53) - 1, 0)


def test_srt_invalid_timing_does_not_echo_large_index_into_error_frame(tmp_path):
    index = b"9" * (1024 * 1024 + 128)
    raw = index + b"\nnot-a-time\nSynthetic body\n"
    process, response, output = invoke(tmp_path, raw)
    assert process.returncode == 1 and response["status"] == "failed"
    stdout_bytes = len(process.stdout.encode("utf-8"))
    assert stdout_bytes < 8192
    assert "9" * 128 not in process.stdout and "Synthetic body" not in process.stdout
    assert response["outputs"] == [] and list(output.iterdir()) == []


@pytest.mark.parametrize("space", ["", " ", "\t", "\u00a0", "\u2003"])
def test_srt_arrow_whitespace_remains_compatible(tmp_path, space):
    raw = f"1\n00:00:00,000{space}-->{space}00:00:01,000\nSynthetic text\n".encode("utf-8")
    process, response, output = invoke(tmp_path, raw)
    assert process.returncode == 0 and response["status"] == "succeeded"
    outputs = {item["kind"]: item for item in response["outputs"]}
    receipt = json.loads((output / outputs["loss_report"]["sha256"]).read_bytes())
    cue = receipt["params"]["worker_structure"][0]
    assert (cue["offset_ms"], cue["duration_ms"]) == (0, 1000)
