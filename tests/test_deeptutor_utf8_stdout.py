"""Actual child-pipe checks for three offline DeepTutor JSON interfaces.

Only synthetic content is used. No model, network or Core is involved.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services/learning-providers/deeptutor"
SCRIPTS = {
    "turn": PROVIDER / "question_turn_worker.py",
    "normalizer": PROVIDER / "question_normalizer.py",
    "import": PROVIDER / "practice_import.py",
}
EMOJI = "\U0001f600"
PRIVATE_MARKER = "SYNTHETIC_PRIVATE_MARKER_" + EMOJI


@pytest.fixture
def child_env(tmp_path):
    home = tmp_path / "home"
    temporary = tmp_path / "temporary"
    home.mkdir()
    temporary.mkdir()
    env = {"HOME": str(home), "USERPROFILE": str(home), "TEMP": str(temporary), "TMP": str(temporary),
           "APPDATA": str(home), "LOCALAPPDATA": str(home), "XDG_CONFIG_HOME": str(home),
           "XDG_CACHE_HOME": str(home), "XDG_DATA_HOME": str(home)}
    if sys.platform == "win32":
        env["SystemRoot"] = os.environ["SystemRoot"]
    return env


def request(kind):
    if kind == "turn":
        return {"schema": "archeaxis.deeptutor-question-turn-replay/v1", "request_id": "synthetic_utf8",
                "mode": "capture", "language": "en",
                "plan": {"analysis": "Synthetic", "templates": [
                    {"question_id": "q_1", "topic": "Synthetic " + EMOJI, "question_type": "choice",
                     "difficulty": "easy", "source": "custom", "reference_question": "", "reference_answer": ""}]},
                "question_number": 1, "exploration_trace": "SYNTHETIC_CONTEXT_" + EMOJI,
                "previous_questions": []}
    if kind == "normalizer":
        body = {"question_type": "choice", "question": "Synthetic question " + EMOJI,
                "options": {"A": "one", "B": "two", "C": "three", "D": "four"},
                "correct_answer": "SYNTHETIC_SECRET_KEY", "explanation": "SYNTHETIC_SECRET_EXPLANATION"}
        # Use a valid upstream key while keeping a private explanation sentinel.
        body["correct_answer"] = "B"
        return {"schema": "archeaxis.deeptutor-question-normalize/v1", "request_id": "synthetic_utf8",
                "input": {"kind": "model_text", "question_type": "choice",
                          "text": json.dumps(body, ensure_ascii=False)}}
    row = {"question": "Synthetic question " + EMOJI, "type": "short_answer",
           "answer": "SYNTHETIC_SECRET_KEY", "user_answer": "SYNTHETIC_SECRET_USER",
           "explanation": "SYNTHETIC_SECRET_EXPLANATION", "unused": "SYNTHETIC_SECRET_UNMAPPED"}
    raw = json.dumps([row], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {"schema": "archeaxis.deeptutor-practice-import-preview/v1", "request_id": "synthetic_utf8",
            "format": "json", "data_base64": base64.b64encode(raw).decode("ascii")}


def invoke(kind, body, env, *, forced_ascii=False):
    command = [sys.executable, "-I", "-B"]
    if forced_ascii:
        # A deterministic narrow text stream exposes the same bug even on a
        # system whose normal pipe encoding already happens to be UTF-8.
        command += ["-c", "import runpy,sys;sys.stdout.reconfigure(encoding='ascii',errors='strict');"
                           "runpy.run_path(sys.argv[1],run_name='__main__')", str(SCRIPTS[kind])]
    else:
        command += [str(SCRIPTS[kind])]
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    return subprocess.run(command, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=20, check=False, env=env)


@pytest.mark.parametrize("kind", ["turn", "normalizer", "import"])
@pytest.mark.parametrize("forced_ascii", [False, True], ids=["native-pipe", "ascii-pipe"])
def test_non_gbk_text_has_a_utf8_json_response_without_x_utf8(kind, forced_ascii, child_env):
    run = invoke(kind, request(kind), child_env, forced_ascii=forced_ascii)
    assert run.returncode == 0, run.stderr.decode("utf-8", errors="replace")
    assert run.stderr == b""
    text = run.stdout.decode("utf-8", errors="strict")
    assert text.count("\n") == 1
    result = json.loads(text)
    if kind == "turn":
        assert result["status"] == "CAPTURED"
        assert EMOJI in result["messages"][1]["content"]
        # Capture intentionally returns caller material, so it is not a
        # private-output or logging filter.
        assert "SYNTHETIC_CONTEXT_" + EMOJI in result["messages"][1]["content"]
        assert result["privacy_filter"] == "NOT_APPLIED"
    elif kind == "normalizer":
        assert result["status"] == "CANDIDATE"
        assert result["question"]["question"] == "Synthetic question " + EMOJI
        assert "correct_answer" not in result["question"] and "explanation" not in result["question"]
        assert "SYNTHETIC_SECRET_EXPLANATION" not in text
    else:
        assert result["status"] == "PREVIEW"
        assert result["rows"][0]["question"]["question"] == "Synthetic question " + EMOJI
        assert all(marker not in text for marker in (
            "SYNTHETIC_SECRET_KEY", "SYNTHETIC_SECRET_USER",
            "SYNTHETIC_SECRET_EXPLANATION", "SYNTHETIC_SECRET_UNMAPPED"))


@pytest.mark.parametrize("kind", ["turn", "normalizer", "import"])
@pytest.mark.parametrize("forced_ascii", [False, True], ids=["native-pipe", "ascii-pipe"])
def test_invalid_request_returns_fixed_json_without_private_echo(kind, forced_ascii, child_env):
    invalid = request(kind)
    invalid["unexpected"] = PRIVATE_MARKER
    run = invoke(kind, invalid, child_env, forced_ascii=forced_ascii)
    assert run.returncode == 2 and run.stderr == b""
    text = run.stdout.decode("utf-8", errors="strict")
    result = json.loads(text)
    assert result["status"] == "INVALID_REQUEST" and result["reason_code"] == "INVALID_INPUT"
    assert PRIVATE_MARKER not in text and "SYNTHETIC_PRIVATE_MARKER_" not in text
