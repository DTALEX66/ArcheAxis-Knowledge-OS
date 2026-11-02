"""Synthetic offline replay of the pinned DeepTutor single-question step.

These tests do not run a model, establish source authorization, or exercise
the Core. The caller-authored final body is not proof of provider generation.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services/learning-providers/deeptutor"
WORKER = PROVIDER / "question_turn_worker.py"
GRADER = PROVIDER / "grade_worker.py"
ARCHIVE = ROOT / ".project-local/archives/owner-inputs/20261101-learning-platform-sources/DeepTutor-1.7.1.zip"
SPEC = importlib.util.spec_from_file_location("deeptutor_question_turn_test", WORKER)
assert SPEC is not None and SPEC.loader is not None
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


@pytest.fixture
def isolated_env(tmp_path):
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


def request(language="en"):
    return {"schema": worker.SCHEMA, "request_id": "synthetic_1", "mode": "capture", "language": language,
            "plan": {"analysis": "Synthetic plan", "templates": [
                {"question_id": "q_1", "topic": "Synthetic arithmetic", "question_type": "choice",
                 "difficulty": "easy", "source": "custom", "reference_question": "", "reference_answer": ""}]},
            "question_number": 1, "exploration_trace": "Synthetic 2+2=4.", "previous_questions": []}


def choice():
    return {"question_type": "choice", "question": "  What is 2+2?  ",
            "options": {"A": "3", "B": " 4 ", "C": "5", "D": "6"},
            "correct_answer": "B", "explanation": "Synthetic explanation."}


def invoke(body, env, *, raw=None, target=WORKER):
    data = raw if raw is not None else json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    run = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(target)],
                         input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         timeout=20, check=False, env=env)
    assert run.stderr == b""
    assert len(run.stdout.splitlines()) == 1
    return run.returncode, json.loads(run.stdout), data


def replay(capture_request, captured, body):
    value = copy.deepcopy(capture_request)
    value.update(mode="replay", expected_prompt_sha256=captured["prompt_sha256"], response_body=body)
    return value


DIRECTIVES = {
    "en": "[Language] Write ALL reader-facing text (titles, prose, explanations, hints, transitions, quiz stems, "
          "options, etc.) in English. Do NOT switch languages even if the source material, JSON keys, or examples "
          "in this prompt are in another language. Keep proper nouns (people, products, formula symbols) in their original form.",
    "zh": "[语言要求 / Language] 请严格使用中文（简体）撰写所有面向读者的文本（标题、正文、解释、提示、过渡句、"
          "题干、选项等），即使参考资料、JSON 字段名或英文术语出现在 prompt 中也不得切换语言；"
          "保留必要的专有名词原文（如人名、产品名、公式中的变量符号等）即可，其余一律使用中文（简体）。",
}


@pytest.mark.parametrize("language", ["en", "zh"])
def test_original_prompt_capture_and_strict_choice_replay(language, isolated_env):
    source = request(language)
    code, captured, _ = invoke(source, isolated_env)
    assert code == 0 and captured["status"] == "CAPTURED"
    assert captured["origin"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert captured["model_call"] == captured["upstream_agentic_loop"] == "NOT_INVOKED"
    assert captured["upstream_method"] == "QuestionPipeline._quiz_one"
    assert captured["tool_execution"] == captured["repair"] == "NOT_INVOKED"
    assert captured["grounding"] == captured["question_uniqueness"] == captured["answer_correctness"] == "NOT_VERIFIED"
    assert captured["core_authorization"] == captured["independent_mastery"] == "NOT_ESTABLISHED"
    assert captured["privacy_filter"] == "NOT_APPLIED" and captured["logging_safety"] == "NOT_ESTABLISHED"
    assert captured["original_input_preserved"] is False and captured["loss_receipt"] == "NOT_GENERATED"

    # Compare every prompt byte against the retained upstream YAML and the
    # independently stated language directive for this fixed synthetic plan.
    original = yaml.safe_load((PROVIDER / "upstream" / f"question_pipeline.{language}.yaml").read_bytes())
    tool_list = "- 无" if language == "zh" else "- none"
    system = original["quiz_step"]["system"].format(
        question_number=1, total_questions=1, kb_note="", tool_list=tool_list).rstrip()
    user = original["quiz_step"]["user_template"].format(
        question_id="q_1", topic="Synthetic arithmetic", question_type="choice", difficulty="easy",
        exploration_trace="Synthetic 2+2=4.",
        plan_summary="Analysis: Synthetic plan\n  - [q_1] (choice/easy) Synthetic arithmetic",
        previous_questions=original["empty"]["no_previous_questions"],
        reference_block=original["empty"]["no_reference"])
    expected = [{"role": "system", "content": system + "\n\n" + DIRECTIVES[language]},
                {"role": "user", "content": user}]
    assert captured["messages"] == expected
    wire = json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert captured["prompt_sha256"] == hashlib.sha256(wire).hexdigest()

    body = json.dumps(choice(), ensure_ascii=False)
    code, result, _ = invoke(replay(source, captured, body), isolated_env)
    assert code == 0 and result["status"] == "CANDIDATE"
    assert result["prompt_sha256"] == captured["prompt_sha256"]
    assert result["question"] == {"question_id": "q_1", "question": "What is 2+2?",
                                  "question_type": "choice", "options": {"A": "3", "B": "4", "C": "5", "D": "6"}}
    assert "correct_answer" not in result["question"] and "explanation" not in result["question"]
    assert body not in json.dumps(result)
    assert result["prompt_binding"] == "UNKEYED_TEXT_ONLY_NOT_SOURCE_OR_AUTHENTICATION"


def test_prompt_binding_detects_changed_topic_without_reflecting_response(isolated_env):
    source = request()
    _, captured, _ = invoke(source, isolated_env)
    altered = replay(source, captured, json.dumps(choice()))
    altered["plan"]["templates"][0]["topic"] = "Different synthetic topic"
    code, result, _ = invoke(altered, isolated_env)
    assert code == 2 and result == {"schema": worker.SCHEMA, "status": "REJECTED", "reason_code": "PROMPT_MISMATCH"}
    assert "Synthetic" not in json.dumps(result)


def test_prompt_hash_is_not_an_injective_binding_to_the_original_inputs(isolated_env):
    source = request()
    item = source["plan"]["templates"][0]
    item.update(source="mimic", reference_question="  Synthetic reference  ", reference_answer="  Synthetic key  ")
    _, first, _ = invoke(source, isolated_env)
    other = copy.deepcopy(source)
    other["plan"]["templates"][0].update(reference_question="Synthetic reference", reference_answer="Synthetic key")
    _, second, _ = invoke(other, isolated_env)
    assert first["messages"] == second["messages"]
    assert first["prompt_sha256"] == second["prompt_sha256"]
    code, result, _ = invoke(replay(other, first, json.dumps(choice())), isolated_env)
    assert code == 0 and result["status"] == "CANDIDATE"
    assert result["prompt_binding"] == "UNKEYED_TEXT_ONLY_NOT_SOURCE_OR_AUTHENTICATION"


@pytest.mark.parametrize("body", [
    '{"question_type":"choice","question":"Q","question":"other","correct_answer":"B","explanation":"E"}',
    '{"question_type":"choice","question":"Q","correct_answer":"B","explanation":"E","options":{},"x":1}',
    '{"question_type":"concept","question":"Q","correct_answer":"true","explanation":"E"}',
    '{"question_type":"choice","question":"Q","correct_answer":"B","explanation":"E","options":{"A":"a","B":"b","C":"c","D":"d"}} trailing',
    '\x60\x60\x60json\n{"question":"Q"}\n\x60\x60\x60',
    '\x60\x60FINISH\x60\x60\n{"question":"Q"}',
    '{"question_type":"choice","question":"Q","correct_answer":"B","explanation":"E","options":{"A":"a","B":"b","C":"c","D":"d","D":"x"}}',
    '{"question_type":"choice","question":"Q","correct_answer":"Z","explanation":"E","options":{"A":"a","B":"b","C":"c","D":"d"}}',
    '{"question_type":"choice","question":"Q","correct_answer":"B","explanation":"E","options":{"A":"a","B":"b","C":"c","D":NaN}}',
])
def test_invalid_final_body_is_rejected_without_reflecting_it(body, isolated_env):
    source = request()
    _, captured, _ = invoke(source, isolated_env)
    code, result, _ = invoke(replay(source, captured, body), isolated_env)
    assert code == 2 and result == {"schema": worker.SCHEMA, "status": "REJECTED", "reason_code": "INVALID_RESPONSE"}


def test_invalid_envelope_and_extra_stdin_do_not_echo_unknown_content(isolated_env):
    bad = request()
    bad["unexpected"] = "SYNTHETIC_PRIVATE_MARKER"
    code, result, _ = invoke(bad, isolated_env)
    assert code == 2 and result["status"] == "INVALID_REQUEST"
    assert "SYNTHETIC_PRIVATE_MARKER" not in json.dumps(result)
    body = json.dumps(request()).encode() + b"\n" + b'{"unexpected":"SYNTHETIC_PRIVATE_MARKER"}\n'
    code, result, _ = invoke(None, isolated_env, raw=body)
    assert code == 2 and result["status"] == "INVALID_REQUEST"
    assert "SYNTHETIC_PRIVATE_MARKER" not in json.dumps(result)


@pytest.mark.parametrize("kind,question,answer", [
    ("concept", "A synthetic proposition.", "true"),
    ("fill_in_blank", "The result is ____.", "four"),
    ("short_answer", "Explain the synthetic example.", "A short synthetic reference."),
    ("written", "Discuss the synthetic example.", "A longer synthetic reference."),
    ("coding", "Write a synthetic function.", "return 4"),
])
def test_nonchoice_question_types_keep_the_upstream_question_view(kind, question, answer, isolated_env):
    source = request()
    source["plan"]["templates"][0]["question_type"] = kind
    code, captured, _ = invoke(source, isolated_env)
    assert code == 0 and captured["status"] == "CAPTURED"
    body = {"question_type": kind, "question": question, "correct_answer": answer,
            "explanation": "Synthetic explanation."}
    code, result, _ = invoke(replay(source, captured, json.dumps(body)), isolated_env)
    assert code == 0 and result["status"] == "CANDIDATE"
    assert result["question"] == {"question_id": "q_1", "question": question,
                                  "question_type": kind, "options": None}
    # The raw DTOs do not connect directly: the grader requires a dictionary.
    # This local test alone supplies the reference and maps null to an empty
    # dictionary; it does not bind the key to a trusted Core question.
    grade = {"schema": "archeaxis.deeptutor-practice-grade/v1", "request_id": "synthetic_1",
             "question": {"question_type": kind, "options": result["question"]["options"],
                          "correct_answer": answer}, "answer": "synthetic learner answer"}
    rejected_code, rejected, _ = invoke(grade, isolated_env, target=GRADER)
    assert rejected_code == 2 and rejected == {
        "schema": "archeaxis.deeptutor-practice-grade/v1",
        "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}
    grade["question"]["options"] = {}
    grade_code, observed, raw = invoke(grade, isolated_env, target=GRADER)
    assert grade_code == 0 and observed["status"] == "OBSERVED"
    assert observed["provider_correct"] is None
    assert observed["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert observed["question_binding"] == "caller_declared_unverified"
    assert observed["independent_mastery"] == "not_established"


def test_additional_invalid_blank_and_subjective_options_are_rejected(isolated_env):
    for kind, body in [
        ("fill_in_blank", {"question_type": "fill_in_blank", "question": "____ and ____",
                           "correct_answer": "four", "explanation": "E"}),
        ("fill_in_blank", {"question_type": "fill_in_blank", "question": "_____",
                           "correct_answer": "four", "explanation": "E"}),
        ("short_answer", {"question_type": "short_answer", "question": "Explain.",
                          "correct_answer": "A reference", "explanation": "E", "options": {"A": "x"}}),
        ("short_answer", {"question_type": "short_answer", "question": "Explain.",
                          "correct_answer": " N/A ", "explanation": "E"}),
        ("short_answer", {"question_type": "short_answer", "question": "Explain.",
                          "correct_answer": "A reference", "explanation": " N/A "}),
        ("short_answer", {"question_type": "short_answer", "question": "  [Generation failed] synthetic",
                          "correct_answer": "A reference", "explanation": "E"}),
        ("concept", {"question_type": "concept", "question": "A proposition.",
                     "correct_answer": "yes", "explanation": "E"}),
    ]:
        source = request()
        source["plan"]["templates"][0]["question_type"] = kind
        _, captured, _ = invoke(source, isolated_env)
        code, result, _ = invoke(replay(source, captured, json.dumps(body)), isolated_env)
        assert code == 2 and result["status"] == "REJECTED"
        assert result["reason_code"] == "INVALID_RESPONSE"


@pytest.mark.parametrize("first,second", [
    ("same", " same "),
    ("Alpha   Beta", "alpha beta"),
    ("B", "right"),
    ("B. right", "right"),
    ("B) right", "right"),
    ("straße", "STRASSE"),
])
def test_choice_alias_collisions_are_rejected(first, second, isolated_env):
    source = request()
    _, captured, _ = invoke(source, isolated_env)
    body = choice()
    body["options"] = {"A": first, "B": second, "C": "third", "D": "fourth"}
    code, result, _ = invoke(replay(source, captured, json.dumps(body)), isolated_env)
    assert code == 2 and result == {"schema": worker.SCHEMA, "status": "REJECTED",
                                    "reason_code": "INVALID_RESPONSE"}


def test_original_validator_and_grader_expose_duplicate_choice_ambiguity(isolated_env):
    spec = importlib.util.spec_from_file_location("original_choice_normalizer_test", PROVIDER / "question_normalizer.py")
    assert spec is not None and spec.loader is not None
    normalizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(normalizer)
    functions = normalizer._selected_functions()
    raw = {"question_type": "choice", "question": "Which?", "correct_answer": "B", "explanation": "E",
           "options": {"A": "same", "B": " same ", "C": "third", "D": "fourth"}}
    template = SimpleNamespace(question_type="choice")
    normalized = functions._normalize_quiz_payload(template, raw)
    assert normalized["options"]["A"] == normalized["options"]["B"] == "same"
    assert functions._collect_quiz_issues(template, normalized) == []
    grade = {"schema": "archeaxis.deeptutor-practice-grade/v1", "request_id": "synthetic_ambiguity",
             "question": {"question_type": "choice", "options": normalized["options"],
                          "correct_answer": "B"}, "answer": "same"}
    code, by_text, _ = invoke(grade, isolated_env, target=GRADER)
    grade["answer"] = "B"
    code_by_key, by_key, _ = invoke(grade, isolated_env, target=GRADER)
    assert code == code_by_key == 0
    assert by_text["provider_correct"] is False and by_key["provider_correct"] is True


def test_option_text_may_match_its_own_label_without_cross_option_collision(isolated_env):
    source = request()
    _, captured, _ = invoke(source, isolated_env)
    body = choice()
    body["options"] = {"A": "A", "B": "B", "C": "C", "D": "D"}
    code, result, _ = invoke(replay(source, captured, json.dumps(body)), isolated_env)
    assert code == 0 and result["status"] == "CANDIDATE"


@pytest.mark.parametrize("field,value", [
    ("mode", []), ("language", {}), ("question_number", True),
])
def test_invalid_envelope_types_are_input_errors(field, value, isolated_env):
    source = request()
    source[field] = value
    code, result, _ = invoke(source, isolated_env)
    assert code == 2 and result["status"] == "INVALID_REQUEST"


@pytest.mark.parametrize("field,value", [
    ("question_type", []), ("difficulty", {}), ("source", []),
])
def test_invalid_template_types_are_input_errors(field, value, isolated_env):
    source = request()
    source["plan"]["templates"][0][field] = value
    code, result, _ = invoke(source, isolated_env)
    assert code == 2 and result["status"] == "INVALID_REQUEST"


@pytest.mark.parametrize("answer,expected", [("B", True), ("A", False)])
def test_replayed_choice_can_be_checked_by_the_fixed_original_grader(answer, expected, isolated_env):
    source = request()
    _, captured, _ = invoke(source, isolated_env)
    original = choice()
    code, candidate, _ = invoke(replay(source, captured, json.dumps(original)), isolated_env)
    assert code == 0 and candidate["status"] == "CANDIDATE"
    # The test owns the supplied key; this is not a Core-owned question or a
    # proof that the model or upstream provider created the question.
    grade = {"schema": "archeaxis.deeptutor-practice-grade/v1", "request_id": "synthetic_1",
             "question": {"question_type": candidate["question"]["question_type"],
                          "options": candidate["question"]["options"],
                          "correct_answer": original["correct_answer"]}, "answer": answer}
    code, result, raw = invoke(grade, isolated_env, target=GRADER)
    assert code == 0 and result["status"] == "OBSERVED" and result["provider_correct"] is expected
    assert result["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["question_binding"] == "caller_declared_unverified"
    assert result["independent_mastery"] == "not_established"


def test_changed_source_is_refused_before_any_prompt(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    upstream = source_dir / "upstream"
    upstream.mkdir()
    filename = "question_pipeline.en.yaml"
    original = (PROVIDER / "upstream" / filename).read_bytes()
    target = upstream / filename
    target.write_bytes(original)
    monkeypatch.setattr(worker, "ROOT", source_dir)
    monkeypatch.setattr(worker, "UPSTREAM", upstream)
    assert worker._source(filename) == original
    target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(worker.UpstreamUnavailable, match="digest mismatch"):
        worker._source(filename)
    target.write_bytes(original + b"x")
    with pytest.raises(worker.UpstreamUnavailable):
        worker._source(filename)


def test_missing_yaml_reader_is_unavailable_without_fallback(monkeypatch):
    monkeypatch.setattr(worker, "yaml", None)
    with pytest.raises(worker.UpstreamUnavailable, match="YAML reader unavailable"):
        worker.process(request())


def test_new_retained_sources_match_exact_owner_zip_members():
    if not ARCHIVE.is_file():
        pytest.skip("Owner ZIP is a separately retained local input")
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == (
        "9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262")
    paths = {
        "question_pipeline.en.yaml": "DeepTutor-1.7.1/deeptutor/agents/question/prompts/en/pipeline.yaml",
        "question_pipeline.zh.yaml": "DeepTutor-1.7.1/deeptutor/agents/question/prompts/zh/pipeline.yaml",
        "question_language.py": "DeepTutor-1.7.1/deeptutor/services/prompt/language.py",
    }
    with zipfile.ZipFile(ARCHIVE) as source:
        for name, member in paths.items():
            assert len([entry for entry in source.infolist() if entry.filename == member]) == 1
            raw = (PROVIDER / "upstream" / name).read_bytes()
            assert raw == source.read(member)
            assert len(raw) == worker.PINS[name][0]
            assert hashlib.sha256(raw).hexdigest() == worker.PINS[name][1]
