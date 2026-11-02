"""Synthetic parser-to-original-grader checks, without Core or model execution.

The input is caller-authored; using pinned upstream functions does not prove
that DeepTutor generated the question or establish independent mastery.
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services" / "learning-providers" / "deeptutor"
NORMALIZER = PROVIDER / "question_normalizer.py"
WORKER = PROVIDER / "grade_worker.py"
GRADE_SCHEMA = "archeaxis.deeptutor-practice-grade/v1"
GRADE_UPSTREAM_SHA = "fdfbaee6cd0fa2c0f31de9a792e220e6989434fc1f44359db3e6afc62cd2472f"
SPEC = importlib.util.spec_from_file_location("deeptutor_question_grade_synthetic", NORMALIZER)
assert SPEC is not None and SPEC.loader is not None
normalizer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(normalizer)


@pytest.fixture
def worker_env(tmp_path):
    home = tmp_path / "worker-home"
    temporary = tmp_path / "worker-temp"
    home.mkdir()
    temporary.mkdir()
    # Do not pass through the caller's account/configuration environment.
    env = {"HOME": str(home), "USERPROFILE": str(home), "TEMP": str(temporary), "TMP": str(temporary),
           "APPDATA": str(home), "LOCALAPPDATA": str(home), "XDG_CONFIG_HOME": str(home),
           "XDG_CACHE_HOME": str(home), "XDG_DATA_HOME": str(home)}
    if sys.platform == "win32":
        env["SystemRoot"] = os.environ["SystemRoot"]
    return env


def model_text(kind, value):
    return {"schema": normalizer.SCHEMA, "request_id": "synthetic_bridge_1", "input": {
        "kind": "model_text", "question_type": kind,
        "text": "prefix\n```json\n" + json.dumps(value, ensure_ascii=False) + "\n```",
    }}


def choice(key="乙"):
    return {"question": "Which option?", "options": {"a": "甲", "b": "乙", "c": "丙", "d": "丁"},
            "correct_answer": key, "explanation": "synthetic explanation"}


def stage(request, answer, worker_env):
    """Test-only use of the private candidate; never an installed product bridge."""
    result = normalizer._candidate(request)
    if result["status"] != "CANDIDATE":
        return result, None, None, None
    candidate = result["candidate"]
    # The original parser represents non-choice options as null; the worker's
    # finite DTO requires a dictionary. Both mean no options to its grader.
    question = {"question_type": candidate["question_type"],
                "options": candidate["options"] if candidate["options"] is not None else {},
                "correct_answer": candidate["correct_answer"]}
    body = {"schema": GRADE_SCHEMA, "request_id": result["request_id"],
            "question": question, "answer": answer}
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    run = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(WORKER)],
                         input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         timeout=15, check=False, env=worker_env)
    assert run.returncode == 0 and run.stderr == b""
    assert len(run.stdout.splitlines()) == 1
    response = json.loads(run.stdout)
    assert response["schema"] == GRADE_SCHEMA and response["status"] == "OBSERVED"
    assert response["request_id"] == result["request_id"]
    assert response["provider"] == "deeptutor" and response["adapter_version"] == "1.7.1"
    assert response["upstream_member_sha256"] == GRADE_UPSTREAM_SHA
    assert response["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert response["input_sha256"] != hashlib.sha256(raw[:-1]).hexdigest()
    assert response["question_binding"] == "caller_declared_unverified"
    assert response["independent_mastery"] == "not_established"
    assert "answer" not in response and "correct_answer" not in response and "question" not in response
    return result, body, response, raw


@pytest.mark.parametrize("answer,expected", [("乙", True), ("A", False), ("", False)])
def test_same_normalized_choice_is_scored_by_original_worker(answer, expected, worker_env):
    request = model_text("choice", choice())
    candidate, body, response, raw = stage(request, answer, worker_env)
    assert candidate["candidate"]["correct_answer"] == "B"
    assert candidate["candidate"]["options"] == {"A": "甲", "B": "乙", "C": "丙", "D": "丁"}
    assert body["question"] == {key: candidate["candidate"][key]
                                for key in ("question_type", "options", "correct_answer")}
    assert json.loads(raw)["question"] == body["question"]
    assert response["provider_correct"] is expected
    view = normalizer.process(request)
    assert view["origin"] == "caller_declared_unverified"
    assert view["provider_run"] == view["model_call"] == "NOT_INVOKED"
    assert view["independent_mastery"] == "not_established"
    assert "correct_answer" not in view["question"]


@pytest.mark.parametrize("kind,question,expected_key", [
    ("short_answer", {"question": "Explain.", "correct_answer": "synthetic reference",
                      "explanation": "synthetic explanation"}, "synthetic reference"),
    ("concept", {"question": "Is it true?", "correct_answer": "正确",
                 "explanation": "synthetic explanation"}, "true"),
])
def test_subjective_or_no_options_stays_unknown(kind, question, expected_key, worker_env):
    candidate, body, response, _raw = stage(model_text(kind, question), "synthetic learner answer", worker_env)
    assert candidate["candidate"]["options"] is None
    assert body["question"]["options"] == {}
    assert body["question"]["correct_answer"] == expected_key
    assert response["provider_correct"] is None


def test_missing_reference_is_rejected_before_any_worker(monkeypatch, worker_env):
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("worker must not start"))
    result, body, response, raw = stage(model_text("choice", choice("")), "A", worker_env)
    assert result["status"] == "REJECTED" and "missing_correct_answer" in result["issue_codes"]
    assert body is response is raw is None


def test_reported_upstream_issues_cannot_reach_worker(monkeypatch, worker_env):
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("worker must not start"))
    request = {"schema": normalizer.SCHEMA, "request_id": "synthetic_bridge_1", "input": {
        "kind": "pipeline_result", "index": 0, "result": {"summary": {"results": [
            {"qa_pair": {**choice(), "question_type": "choice"}, "metadata": {"issues": ["invalid"]}}
        ]}}}}
    result, body, response, raw = stage(request, "B", worker_env)
    assert result["status"] == "REJECTED" and result["issue_codes"] == ["upstream_reported_issues"]
    assert body is response is raw is None


def test_modified_pipeline_source_cannot_reach_worker(tmp_path, monkeypatch, worker_env):
    source = bytearray(normalizer.UPSTREAM.read_bytes())
    source[-1] ^= 1
    root = tmp_path / "upstream"
    root.mkdir()
    (root / "question_pipeline.py").write_bytes(source)
    monkeypatch.setattr(normalizer, "UPSTREAM_ROOT", root)
    monkeypatch.setattr(normalizer, "UPSTREAM", root / "question_pipeline.py")
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("worker must not start"))
    with pytest.raises(normalizer.UpstreamUnavailable, match="identity mismatch"):
        stage(model_text("choice", choice()), "B", worker_env)
