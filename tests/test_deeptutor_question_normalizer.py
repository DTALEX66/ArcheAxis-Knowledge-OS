"""Offline 1.7.1 parser subset; no provider, model, or database is run."""

import builtins
import ast
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
SCRIPT = ROOT / "services" / "learning-providers" / "deeptutor" / "question_normalizer.py"
SPEC = importlib.util.spec_from_file_location("deeptutor_question_normalizer_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
normalizer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(normalizer)


def choice():
    return {"question": "Which option?", "question_type": "choice",
            "options": {"a": "first", "b": "second", "c": "third", "d": "fourth"},
            "correct_answer": "second", "explanation": "SENTINEL_EXPLANATION"}


def request(raw, kind="choice"):
    return {"schema": normalizer.SCHEMA, "request_id": "synthetic_1",
            "input": {"kind": "model_text", "question_type": kind, "text": raw}}


def pipeline_result(pair, metadata=None):
    return {"schema": normalizer.SCHEMA, "request_id": "synthetic_1", "input": {
        "kind": "pipeline_result", "index": 0,
        "result": {"mode": "custom", "response": "SENTINEL_RESPONSE",
                   "summary": {"results": [{"qa_pair": pair, "metadata": metadata or {}}]}}}}


def test_exact_upstream_bytes_and_original_choice_normalization_with_redacted_view():
    assert hashlib.sha256(normalizer.UPSTREAM.read_bytes()).hexdigest() == normalizer.UPSTREAM_SHA256
    payload = request("prefix\n```json\n" + json.dumps(choice()) + "\n```\ntrailing prose")
    private = normalizer._candidate(payload)
    assert private["status"] == "CANDIDATE"
    assert private["candidate"]["correct_answer"] == "B"
    assert private["candidate"]["options"] == {"A": "first", "B": "second", "C": "third", "D": "fourth"}
    view = normalizer.process(payload)
    assert view["status"] == "CANDIDATE"
    assert view["origin"] == "caller_declared_unverified"
    assert view["provider_run"] == view["model_call"] == "NOT_INVOKED"
    assert view["projection_scope"] == "single_question_bounded"
    assert view["original_input_preserved"] is False and view["unselected_fields_preserved"] is False
    assert view["loss_receipt"] == "NOT_GENERATED"
    assert "correct_answer" not in view["question"] and "explanation" not in view["question"]
    assert "SENTINEL_" not in json.dumps(view)


def test_actual_pipeline_result_shape_preserves_null_options_and_unknown_source():
    pair = {"question_id": "q_1", "question": "Is this true?", "question_type": "concept",
            "options": None, "correct_answer": "正确", "explanation": "SENTINEL_EXPLANATION",
            "difficulty": "medium", "concentration": "topic"}
    payload = pipeline_result(pair)
    private = normalizer._candidate(payload)
    assert private["candidate"]["correct_answer"] == "true"
    assert private["candidate"]["options"] is None
    view = normalizer.process(payload)
    assert view["question"]["options"] is None
    assert view["question"]["question_type"] == "concept"
    assert "SENTINEL_" not in json.dumps(view)


def test_original_annotated_concept_constant_is_selected():
    tree = ast.parse(normalizer.UPSTREAM.read_bytes())
    definitions = [node for node in tree.body if isinstance(node, ast.AnnAssign)
                   and isinstance(node.target, ast.Name) and node.target.id == "_CONCEPT_ANSWERS"]
    assert len(definitions) == 1
    payload = request(json.dumps({"question": "Is it true?", "correct_answer": "正确", "explanation": "reason"}), kind="concept")
    assert normalizer._candidate(payload)["candidate"]["correct_answer"] == "true"


@pytest.mark.parametrize("payload", [
    request("not json"),
    request(json.dumps({**choice(), "options": {"A": "first", "B": "second"}})),
    request(json.dumps({**choice(), "correct_answer": "Z"})),
    request(json.dumps({**choice(), "question": "[Generation failed] topic"})),
    pipeline_result(choice(), {"issues": ["missing_correct_answer"]}),
])
def test_failed_or_reported_broken_candidates_are_not_projected(payload):
    view = normalizer.process(payload)
    assert view["status"] == "REJECTED"
    assert view["issue_codes"]
    assert "question" not in view
    assert "SENTINEL_" not in json.dumps(view)


@pytest.mark.parametrize("raw", [
    '{"question":"Q","question":"other","correct_answer":"A","explanation":"E"}',
    '{"question":"Q","correct_answer":"A","explanation":"E","extra":NaN}',
])
def test_ambiguous_model_json_fails_closed(raw):
    with pytest.raises(normalizer.InvalidRequest):
        normalizer.process(request(raw))


def test_untrusted_shapes_and_upstream_source_tampering_fail_closed(tmp_path, monkeypatch):
    with pytest.raises(normalizer.InvalidRequest):
        normalizer.process(request(json.dumps({**choice(), "options": {"A": {"nested": "value"}}})))
    with pytest.raises(normalizer.InvalidRequest):
        normalizer.process(request(json.dumps(choice()), kind=["choice"]))
    with pytest.raises(normalizer.InvalidRequest):
        normalizer.process({**request(json.dumps(choice())), "provider_verified": True})
    original = normalizer.UPSTREAM.read_bytes()
    root = tmp_path / "upstream"
    root.mkdir()
    changed = bytearray(original)
    changed[-1] ^= 1
    replacement = root / "question_pipeline.py"
    replacement.write_bytes(changed)
    monkeypatch.setattr(normalizer, "UPSTREAM_ROOT", root)
    monkeypatch.setattr(normalizer, "UPSTREAM", replacement)
    with pytest.raises(normalizer.UpstreamUnavailable):
        normalizer.process(request(json.dumps(choice())))


def test_selection_never_imports_upstream_or_reads_configuration(monkeypatch):
    original_import = builtins.__import__
    original_open = normalizer.os.open
    permitted = normalizer.UPSTREAM.absolute()

    def checked_import(name, *args, **kwargs):
        if name == "deeptutor" or name.startswith("deeptutor."):
            raise AssertionError("upstream package import is forbidden")
        return original_import(name, *args, **kwargs)

    def checked_open(path, *args, **kwargs):
        if Path(path).absolute() != permitted:
            raise AssertionError("unexpected file access")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", checked_import)
    monkeypatch.setattr(normalizer.os, "open", checked_open)
    assert normalizer.process(request(json.dumps(choice())))["status"] == "CANDIDATE"


@pytest.mark.parametrize("target", ["file", "ancestor"])
def test_reparse_flags_are_rejected_before_source_open(monkeypatch, target):
    flagged = normalizer.UPSTREAM if target == "file" else normalizer.UPSTREAM_ROOT.parent
    original_lstat = Path.lstat

    def marked(path):
        info = original_lstat(path)
        if path == flagged:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400,
                                   st_dev=info.st_dev, st_ino=info.st_ino,
                                   st_nlink=info.st_nlink, st_size=info.st_size)
        return info

    def refuse_open(*_args, **_kwargs):
        raise AssertionError("source was opened before rejecting reparse")

    monkeypatch.setattr(Path, "lstat", marked)
    monkeypatch.setattr(normalizer.os, "open", refuse_open)
    with pytest.raises(normalizer.UpstreamUnavailable):
        normalizer._read_upstream()


def test_hard_linked_upstream_is_rejected_before_open(tmp_path, monkeypatch):
    root = tmp_path / "upstream"
    root.mkdir()
    source = root / "question_pipeline.py"
    source.write_bytes(normalizer.UPSTREAM.read_bytes())
    try:
        os.link(source, root / "second_link.py")
    except OSError as error:
        pytest.skip(f"hard-link fixture unavailable: {type(error).__name__}")
    assert stat.S_ISREG(source.lstat().st_mode) and source.lstat().st_nlink > 1
    monkeypatch.setattr(normalizer, "UPSTREAM_ROOT", root)
    monkeypatch.setattr(normalizer, "UPSTREAM", source)
    monkeypatch.setattr(normalizer.os, "open", lambda *_args, **_kwargs: pytest.fail("hard link was opened"))
    with pytest.raises(normalizer.UpstreamUnavailable):
        normalizer._read_upstream()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction fixture")
def test_real_windows_ancestor_junction_is_rejected_before_open(tmp_path, monkeypatch):
    real = tmp_path / "real"
    source_root = real / "upstream"
    source_root.mkdir(parents=True)
    (source_root / "question_pipeline.py").write_bytes(normalizer.UPSTREAM.read_bytes())
    junction = tmp_path / "junction"
    made = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(real)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
    if made.returncode != 0:
        pytest.skip(f"Windows junction creation unavailable: exit {made.returncode}")
    monkeypatch.setattr(normalizer, "UPSTREAM_ROOT", junction / "upstream")
    monkeypatch.setattr(normalizer, "UPSTREAM", junction / "upstream" / "question_pipeline.py")
    monkeypatch.setattr(normalizer.os, "open", lambda *_args, **_kwargs: pytest.fail("junction target was opened"))
    with pytest.raises(normalizer.UpstreamUnavailable):
        normalizer._read_upstream()


def test_actual_isolated_cli_emits_one_redacted_line_and_rejects_duplicates():
    command = [sys.executable, "-I", "-B", "-X", "utf8", str(SCRIPT)]
    payload = json.dumps(request(json.dumps(choice())), ensure_ascii=False).encode("utf-8") + b"\n"
    run = subprocess.run(command, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
    assert run.returncode == 0
    lines = run.stdout.splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["status"] == "CANDIDATE"
    assert b"SENTINEL_" not in run.stdout and not run.stderr
    duplicate = b'{"schema":"x","schema":"y","request_id":"a","input":{}}\n'
    bad = subprocess.run(command, input=duplicate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
    assert bad.returncode == 2
    assert json.loads(bad.stdout)["status"] == "INVALID_REQUEST"
