"""Exercise the retained upstream grader, not a stand-in implementation."""

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "services/learning-providers/deeptutor/grade_worker.py"
spec = importlib.util.spec_from_file_location("deeptutor_grade_worker", WORKER)
worker = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(worker)


def request(kind="single_choice", answer="A", expected="A"):
    return {"schema": worker.SCHEMA, "request_id": "synthetic_1", "answer": answer,
            "question": {"question_type": kind, "options": {"A": "one", "B": "two"},
                         "correct_answer": expected}}


@pytest.mark.parametrize("kind,answer,expected,correct", [
    ("single_choice", "one", "A", True),
    ("single_choice", "B", "A", False),
    ("multi_choice", "A,B", "A,B", True),
    ("short_answer", "anything", "A", None),
    ("single_choice", "A", "Z", None),
])
def test_unmodified_upstream_grading_and_unknown_result(kind, answer, expected, correct):
    result = worker.process(request(kind, answer, expected))
    assert result["provider_correct"] is correct
    assert result["independent_mastery"] == "not_established"
    assert result["question_binding"] == "caller_declared_unverified"
    assert "answer" not in result and "correct_answer" not in result


def test_exact_retained_upstream_and_license_identities():
    source = worker._read_upstream()
    assert len(source) == worker.UPSTREAM_SIZE
    assert hashlib.sha256(source).hexdigest() == worker.UPSTREAM_SHA256
    assert hashlib.sha256((WORKER.parent / "LICENSE").read_bytes()).hexdigest() == (
        "cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4"
    )


def test_changed_upstream_bytes_fail_closed(tmp_path, monkeypatch):
    root = tmp_path / "upstream"
    root.mkdir()
    altered = root / "answers.py"
    source = bytearray(worker.UPSTREAM.read_bytes())
    source[-1] ^= 1
    altered.write_bytes(source)
    monkeypatch.setattr(worker, "UPSTREAM_ROOT", root)
    monkeypatch.setattr(worker, "UPSTREAM", altered)
    with pytest.raises(RuntimeError, match="identity mismatch"):
        worker.process(request())


def test_oversized_upstream_is_rejected_before_open(tmp_path, monkeypatch):
    root = tmp_path / "upstream"
    root.mkdir()
    source = root / "answers.py"
    source.write_bytes(b"x" * (worker.UPSTREAM_SIZE + 1))
    monkeypatch.setattr(worker, "UPSTREAM_ROOT", root)
    monkeypatch.setattr(worker, "UPSTREAM", source)
    monkeypatch.setattr(worker.os, "open", lambda *_a, **_k: pytest.fail("oversized source was opened"))
    with pytest.raises(RuntimeError, match="source unavailable"):
        worker._read_upstream()


@pytest.mark.parametrize("target", ["file", "ancestor"])
def test_reparse_is_rejected_before_source_open(monkeypatch, target):
    flagged = worker.UPSTREAM if target == "file" else worker.UPSTREAM_ROOT.parent
    original_lstat = Path.lstat

    def marked(path):
        info = original_lstat(path)
        if path == flagged:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400,
                                   st_dev=info.st_dev, st_ino=info.st_ino,
                                   st_nlink=info.st_nlink, st_size=info.st_size)
        return info

    monkeypatch.setattr(Path, "lstat", marked)
    monkeypatch.setattr(worker.os, "open", lambda *_a, **_k: pytest.fail("reparse source was opened"))
    with pytest.raises(RuntimeError, match="link is not allowed"):
        worker._read_upstream()


def test_hard_linked_upstream_is_rejected_before_open(tmp_path, monkeypatch):
    root = tmp_path / "upstream"
    root.mkdir()
    source = root / "answers.py"
    source.write_bytes(worker.UPSTREAM.read_bytes())
    try:
        os.link(source, root / "second_link.py")
    except OSError as error:
        pytest.skip(f"hard-link fixture unavailable: {type(error).__name__}")
    assert stat.S_ISREG(source.lstat().st_mode) and source.lstat().st_nlink > 1
    monkeypatch.setattr(worker, "UPSTREAM_ROOT", root)
    monkeypatch.setattr(worker, "UPSTREAM", source)
    monkeypatch.setattr(worker.os, "open", lambda *_a, **_k: pytest.fail("hard link was opened"))
    with pytest.raises(RuntimeError, match="source unavailable"):
        worker._read_upstream()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction fixture")
def test_real_windows_ancestor_junction_is_rejected_before_open(tmp_path, monkeypatch):
    real = tmp_path / "real"
    source_root = real / "upstream"
    source_root.mkdir(parents=True)
    (source_root / "answers.py").write_bytes(worker.UPSTREAM.read_bytes())
    junction = tmp_path / "junction"
    made = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(real)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
    if made.returncode != 0:
        pytest.skip(f"Windows junction creation unavailable: exit {made.returncode}")
    monkeypatch.setattr(worker, "UPSTREAM_ROOT", junction / "upstream")
    monkeypatch.setattr(worker, "UPSTREAM", junction / "upstream" / "answers.py")
    monkeypatch.setattr(worker.os, "open", lambda *_a, **_k: pytest.fail("junction target was opened"))
    with pytest.raises(RuntimeError, match="link is not allowed"):
        worker._read_upstream()


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(schema="future"),
    lambda r: r.update(request_id="../wrong"),
    lambda r: r.update(answer="x" * 20_001),
    lambda r: r["question"].update(options={"A": {"nested": "not text"}}),
    lambda r: r["question"].update(extra="unreviewed"),
])
def test_invalid_requests_fail_closed(mutation):
    value = request()
    mutation(value)
    with pytest.raises(worker.InvalidRequest):
        worker.process(value)


def test_actual_isolated_process_handles_result_and_duplicate_json_members():
    def invoke(payload: bytes):
        return subprocess.run([sys.executable, "-I", "-B", str(WORKER)], input=payload,
                              capture_output=True, timeout=10, check=False)
    raw = json.dumps(request()).encode("utf-8") + b"\n"
    good = invoke(raw)
    result = json.loads(good.stdout)
    assert good.returncode == 0 and result["provider_correct"] is True
    assert result["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert "answer" not in result and "correct_answer" not in result
    assert good.stderr == b""
    no_newline = invoke(raw[:-1])
    assert no_newline.returncode == 0
    assert json.loads(no_newline.stdout)["input_sha256"] == hashlib.sha256(raw[:-1]).hexdigest()
    assert json.loads(no_newline.stdout)["input_sha256"] != result["input_sha256"]
    invalid = invoke(b'{"schema":"x","schema":"y"}\n')
    assert invalid.returncode == 2 and json.loads(invalid.stdout)["status"] == "INVALID_REQUEST"
    assert invalid.stderr == b""
    oversized_integer = invoke(b'{"number":' + b'1' * 5000 + b'}\n')
    assert oversized_integer.returncode == 2
    assert json.loads(oversized_integer.stdout)["status"] == "INVALID_REQUEST"
