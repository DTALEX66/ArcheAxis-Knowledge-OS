"""Synthetic tests of pinned DeepTutor teaching rules in a private worker."""

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services" / "learning-providers" / "deeptutor"
SCRIPT = PROVIDER / "teaching_feedback_worker.py"
SPEC = importlib.util.spec_from_file_location("deeptutor_teaching_feedback_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
worker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = worker
SPEC.loader.exec_module(worker)


@pytest.fixture
def child_env(tmp_path):
    home, temp = tmp_path / "home", tmp_path / "temp"
    home.mkdir()
    temp.mkdir()
    env = {name: str(home) for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
                                       "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME")}
    env.update(TEMP=str(temp), TMP=str(temp))
    if sys.platform == "win32":
        env["SystemRoot"] = os.environ["SystemRoot"]
    return env


def request():
    return {"schema": worker.SCHEMA, "request_id": "synthetic_1", "profile": {},
            "updates": [{"kind": "preference", "op": "upsert", "key": "examples",
                         "text": "Use worked examples", "basis": "learner_report", "evidence": "use examples"}],
            "current_message": "Please use examples now.", "objective_ids": ["objective_1", "objective_2"],
            "focus_objective_id": "objective_1", "session_id": "session_1", "turn_id": "turn_1",
            "include_history": False}


def invoke(value, env, *, raw=None, no_site=False):
    if raw is None:
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    command = [sys.executable, "-I", "-B"] + (["-S"] if no_site else []) + [str(SCRIPT)]
    run = subprocess.run(command, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=env, timeout=20, check=False)
    assert run.stderr == b""
    assert len(run.stdout.splitlines()) == 1
    return run.returncode, json.loads(run.stdout)


def test_two_real_worker_turns_preserve_preferences_and_apply_teaching_feedback(child_env):
    first = request()
    first["profile"] = {"prior_knowledge": "synthetic known", "notes": "keep existing"}
    original = copy.deepcopy(first)
    code, a = invoke(first, child_env)
    assert code == 0 and a["status"] == "UPDATED" and a["changed_fields"] == ["teaching_preferences"]
    assert first == original
    assert a["profile"]["prior_knowledge"] == "synthetic known" and a["profile"]["notes"] == "keep existing"
    preference = a["profile"]["teaching_preferences"]["examples"]
    assert preference["text"] == "Use worked examples" and preference["evidence"] == "use examples"
    assert preference["session_id"] == "session_1" and preference["turn_id"] == "turn_1"
    assert type(preference["updated_at"]) is float and preference["updated_at"] >= 0
    assert a["input_origin"] == "caller_supplied_unverified"
    assert a["update_evidence_verification"] == "nonempty_literal_match_only"
    assert a["existing_profile_evidence_verification"] == "NOT_VERIFIED"
    assert a["evidence_authentication"] == "NOT_ESTABLISHED"
    assert a["persistence"] == "NOT_PERFORMED" and a["core"] == "NOT_CALLED"
    assert a["model_call"] == "NOT_INVOKED" and a["independent_mastery"] == "not_established"
    assert a["output_privacy_filter"] == "NOT_APPLIED"

    second = request()
    second.update(profile=a["profile"], request_id="synthetic_2", turn_id="turn_2",
                  current_message="I still do not see the connection.")
    second["updates"] = [{"kind": "observation", "op": "upsert", "key": "connection",
                          "knowledge_point_id": "objective_1", "text": "Connection unclear",
                          "basis": "learner_report", "strategy": "Definitions only", "outcome": "not_helped",
                          "evidence": "do not see the connection"}]
    code, b = invoke(second, child_env)
    assert code == 0 and b["status"] == "UPDATED" and b["changed_fields"] == ["teaching_observations"]
    assert b["profile"]["teaching_preferences"] == a["profile"]["teaching_preferences"]
    focus = b["guidance"]["teaching_focus"]
    assert focus["knowledge_point_id"] == "objective_1"
    assert focus["observations"][0]["outcome"] == "not_helped"
    assert focus["observations"][0]["strategy"] == "Definitions only"
    assert b["profile"]["updated_at"] == a["profile"]["updated_at"]
    assert b["profile_root_timestamp"] == "not_advanced_by_rule"


def test_noop_and_remove_only_targeted_preference(child_env):
    first = request()
    _, created = invoke(first, child_env)
    retry = request()
    retry["profile"] = created["profile"]
    retry["turn_id"] = "turn_2"
    code, same = invoke(retry, child_env)
    assert code == 0 and same["status"] == "UNCHANGED" and same["changed_fields"] == []
    assert same["profile"] == created["profile"]
    second = copy.deepcopy(created["profile"]["teaching_preferences"]["examples"])
    second.update(text="Keep a second preference", evidence="synthetic statement")
    retry["profile"]["teaching_preferences"]["other"] = second
    retry["updates"] = [{"kind": "preference", "op": "remove", "key": "examples"}]
    retry["current_message"] = ""
    _, removed = invoke(retry, child_env)
    assert removed["status"] == "UPDATED"
    assert removed["profile"]["teaching_preferences"] == {"other": second}
    # This process has no persistent revision: an old caller snapshot can be
    # supplied again. The host must provide Core-bound CAS before durable use.
    _, stale = invoke(first, child_env)
    assert "examples" in stale["profile"]["teaching_preferences"]


@pytest.mark.parametrize("operation", ["remove", "upsert"])
def test_existing_observation_cannot_be_deleted_or_replaced_across_scope(operation, child_env):
    value = request()
    value["objective_ids"] = ["objective_1"]
    value["profile"] = {"teaching_observations": {
        "old": {"knowledge_point_id": "objective_2", "text": "other objective", "updated_at": 1.0}}}
    if operation == "remove":
        value["updates"] = [{"kind": "observation", "op": "remove", "key": "old"}]
    else:
        value["updates"] = [{"kind": "observation", "op": "upsert", "key": "old", "text": "new",
                             "knowledge_point_id": "objective_1", "basis": "tentative"}]
    code, result = invoke(value, child_env)
    assert code == 2 and result == {"schema": worker.SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}


@pytest.mark.parametrize("operation", ["remove", "upsert"])
def test_existing_observation_within_scope_keeps_original_behavior(operation, child_env):
    value = request()
    value["objective_ids"] = ["objective_1"]
    value["profile"] = {"teaching_observations": {
        "old": {"knowledge_point_id": "objective_1", "text": "old", "updated_at": 1.0}}}
    if operation == "remove":
        value["updates"] = [{"kind": "observation", "op": "remove", "key": "old"}]
    else:
        value["updates"] = [{"kind": "observation", "op": "upsert", "key": "old", "text": "new",
                             "knowledge_point_id": "objective_1", "basis": "tentative"}]
    code, result = invoke(value, child_env)
    assert code == 0 and result["status"] == "UPDATED"
    observations = result["profile"]["teaching_observations"]
    if operation == "remove":
        assert "old" not in observations
    else:
        assert observations["old"]["knowledge_point_id"] == "objective_1" and observations["old"]["text"] == "new"


def test_cross_scope_old_observation_rejects_entire_batch(child_env):
    value = request()
    value["objective_ids"] = ["objective_1"]
    value["profile"] = {"teaching_observations": {
        "old": {"knowledge_point_id": "objective_2", "text": "keep", "updated_at": 1.0}}}
    value["updates"].append({"kind": "observation", "op": "remove", "key": "old"})
    original = copy.deepcopy(value)
    code, result = invoke(value, child_env)
    assert code == 2 and result == {"schema": worker.SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}
    assert value == original and "profile" not in result


def test_replacing_observation_is_allowed_when_both_objectives_are_in_scope(child_env):
    value = request()
    value["profile"] = {"teaching_observations": {
        "old": {"knowledge_point_id": "objective_2", "text": "old", "updated_at": 1.0}}}
    value["updates"] = [{"kind": "observation", "op": "upsert", "key": "old", "text": "new",
                         "knowledge_point_id": "objective_1", "basis": "tentative"}]
    code, result = invoke(value, child_env)
    assert code == 0 and result["status"] == "UPDATED"
    assert result["profile"]["teaching_observations"]["old"]["knowledge_point_id"] == "objective_1"


def test_removing_absent_key_is_unchanged_only_after_profile_defaults(child_env):
    value = request()
    value["profile"] = {}
    value["updates"] = [{"kind": "observation", "op": "remove", "key": "missing"}]
    code, result = invoke(value, child_env)
    assert code == 0 and result["status"] == "UNCHANGED" and result["changed_fields"] == []
    assert result["status_scope"] == "teaching_delta_after_profile_defaults_only"
    assert result["profile"] != value["profile"] and "updated_at" in result["profile"]
    assert result["profile"]["teaching_observations"] == {}


@pytest.mark.parametrize("old_evidence", ["", "SYNTHETIC_PRIOR_NOT_IN_CURRENT_MESSAGE"])
def test_existing_profile_evidence_is_not_presented_as_checked(old_evidence, child_env):
    value = request()
    value["profile"] = {"teaching_observations": {
        "old": {"knowledge_point_id": "objective_1", "text": "prior claim", "updated_at": 1.0,
                "basis": "learner_report", "outcome": "helped", "strategy": "example",
                "evidence": old_evidence}}}
    code, result = invoke(value, child_env)
    assert code == 0 and result["status"] == "UPDATED"
    assert result["guidance"]["teaching_focus"]["observations"][0]["evidence"] == old_evidence
    assert result["update_evidence_verification"] == "nonempty_literal_match_only"
    assert result["existing_profile_evidence_verification"] == "NOT_VERIFIED"
    assert result["evidence_authentication"] == "NOT_ESTABLISHED"
    assert result["independent_mastery"] == "not_established"


def test_literal_quote_does_not_prove_semantic_support(child_env):
    value = request()
    value["current_message"] = "I hate examples"
    value["updates"][0]["text"] = "Use examples"
    value["updates"][0]["evidence"] = "examples"
    code, result = invoke(value, child_env)
    # This is the original substring rule's known limitation, not an
    # assessment that the preference reflects the learner's intent.
    assert code == 0 and result["status"] == "UPDATED"
    assert result["profile"]["teaching_preferences"]["examples"]["text"] == "Use examples"
    assert result["update_evidence_verification"] == "nonempty_literal_match_only"
    assert result["evidence_authentication"] == "NOT_ESTABLISHED"


def test_current_focus_and_optional_history_remain_distinct(child_env):
    value = request()
    value["profile"] = {"teaching_observations": {
        "other": {"knowledge_point_id": "objective_2", "text": "other objective", "updated_at": 100.0,
                  "outcome": "unknown"},
        "current": {"knowledge_point_id": "objective_1", "text": "current objective", "updated_at": 200.0,
                    "outcome": "unknown"},
    }}
    _, current = invoke(value, child_env)
    assert set(current["guidance"]["teaching_observations"]) == {"current"}
    assert [item["key"] for item in current["guidance"]["teaching_focus"]["observations"]] == ["current"]
    value["include_history"] = True
    _, history = invoke(value, child_env)
    assert set(history["guidance"]["teaching_observations"]) == {"current", "other"}
    assert [item["key"] for item in history["guidance"]["teaching_focus"]["observations"]] == ["current"]


def test_capacity_boundary_and_latest_three_focus_notes(child_env):
    value = request()
    value["profile"] = {"teaching_preferences": {
        f"existing_{i}": {"text": "keep", "evidence": "prior statement", "updated_at": float(i + 1)}
        for i in range(5)}, "teaching_observations": {
        f"note_{i}": {"knowledge_point_id": "objective_1", "text": f"note {i}", "updated_at": float(i + 1)}
        for i in range(11)}}
    code, six = invoke(value, child_env)
    assert code == 0 and len(six["profile"]["teaching_preferences"]) == 6
    value["profile"] = six["profile"]
    value["updates"] = [{"kind": "observation", "op": "upsert", "key": "note_new", "text": "new note",
                         "knowledge_point_id": "objective_1", "basis": "tentative"}]
    code, twelve = invoke(value, child_env)
    assert code == 0 and len(twelve["profile"]["teaching_observations"]) == 12
    focus = twelve["guidance"]["teaching_focus"]["observations"]
    records = twelve["profile"]["teaching_observations"]
    expected = sorted(records, key=lambda key: records[key]["updated_at"], reverse=True)[:3]
    assert len(focus) == 3 and [item["key"] for item in focus] == expected
    assert twelve["independent_mastery"] == "not_established"


def invalid_case(name):
    value = request()
    value["current_message"] += " SYNTHETIC_PRIVATE_INPUT"
    if name == "unquoted_evidence":
        value["updates"][0]["evidence"] = "never said"
    elif name == "tentative_preference":
        value["updates"][0]["basis"] = "tentative"
    elif name == "foreign_objective":
        value["updates"] = [{"kind": "observation", "op": "upsert", "key": "x", "text": "note",
                             "knowledge_point_id": "foreign", "basis": "tentative"}]
    elif name == "duplicate_key":
        value["updates"].append(copy.deepcopy(value["updates"][0]))
    elif name == "unknown_profile":
        value["profile"]["unknown"] = "SYNTHETIC_PRIVATE_INPUT"
    elif name == "unknown_record":
        value["profile"]["teaching_preferences"] = {"k": {"text": "x", "evidence": "x", "updated_at": 1,
                                                             "unknown": "SYNTHETIC_PRIVATE_INPUT"}}
    elif name == "unknown_update":
        value["updates"][0]["unknown"] = "SYNTHETIC_PRIVATE_INPUT"
    elif name == "whitespace_loss":
        value["updates"][0]["text"] = " silently trimmed "
    elif name == "duplicate_objective":
        value["objective_ids"].append("objective_1")
    elif name == "wrong_focus":
        value["focus_objective_id"] = "foreign"
    elif name == "nonboolean_history":
        value["include_history"] = 0
    elif name == "too_many_updates":
        value["updates"] *= 7
    elif name == "remove_extra_field":
        value["updates"] = [{"kind": "preference", "op": "remove", "key": "x", "text": "lost"}]
    elif name == "missing_record_time":
        value["profile"]["teaching_preferences"] = {"x": {"text": "x", "evidence": "x"}}
    elif name == "unproven_strategy_result":
        value["updates"] = [{"kind": "observation", "op": "upsert", "key": "x", "text": "note",
                             "knowledge_point_id": "objective_1", "basis": "tentative",
                             "strategy": "example", "outcome": "helped"}]
    elif name == "preference_capacity":
        value["profile"]["teaching_preferences"] = {
            f"existing_{i}": {"text": "keep", "evidence": "prior statement", "updated_at": 1.0}
            for i in range(6)}
    elif name == "observation_capacity":
        value["profile"]["teaching_observations"] = {
            f"existing_{i}": {"knowledge_point_id": "objective_1", "text": "keep", "updated_at": 1.0}
            for i in range(12)}
        value["updates"] = [{"kind": "observation", "op": "upsert", "key": "new", "text": "new",
                             "knowledge_point_id": "objective_1", "basis": "tentative"}]
    elif name == "invalid_second_operation":
        value["updates"].append({"kind": "observation", "op": "upsert", "key": "bad", "text": "note",
                                 "knowledge_point_id": "foreign", "basis": "tentative"})
    else:
        raise AssertionError("unknown synthetic case")
    return value


@pytest.mark.parametrize("name", ["unquoted_evidence", "tentative_preference", "foreign_objective",
                                  "duplicate_key", "unknown_profile", "unknown_record", "unknown_update",
                                  "whitespace_loss", "duplicate_objective", "wrong_focus", "nonboolean_history",
                                  "too_many_updates", "remove_extra_field", "missing_record_time",
                                  "unproven_strategy_result", "preference_capacity", "observation_capacity",
                                  "invalid_second_operation"])
def test_invalid_turns_are_atomic_and_never_echo_private_input(name, child_env):
    value = invalid_case(name)
    original = copy.deepcopy(value)
    code, result = invoke(value, child_env)
    assert code == 2 and result == {"schema": worker.SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}
    assert "SYNTHETIC_PRIVATE_INPUT" not in json.dumps(result)
    assert value == original


def test_malformed_json_duplicate_nonfinite_and_extra_frames_do_not_echo(child_env):
    secret = b'SYNTHETIC_PRIVATE_INPUT'
    payloads = [b'{"x":"' + secret + b'","x":1}\n',
                b'{"x":NaN,"private":"' + secret + b'"}\n',
                b'{"x":1e9999,"private":"' + secret + b'"}\n',
                b'{"x":"' + secret + b'"}\n{}\n',
                b'x' * (worker.MAX_INPUT + 1)]
    for raw in payloads:
        code, result = invoke(None, child_env, raw=raw)
        assert code == 2 and result["status"] == "INVALID_REQUEST"
        assert secret.decode() not in json.dumps(result)


def test_real_worker_output_limit_includes_final_newline(child_env):
    # A valid, substantial input causes the original guidance to repeat notes
    # across profile, history and current focus. The root field below is output
    # exactly once, so one ASCII byte changes the actual wire by one byte.
    symbol = "🧪"
    objective = symbol * 200
    value = request()
    value.update(current_message="", objective_ids=[objective], focus_objective_id=objective,
                 include_history=True, updates=[{"kind": "preference", "op": "remove", "key": "missing"}])
    value["profile"] = {
        "prior_knowledge": "", "target_level": "a" * 8192, "time_budget": "a" * 8192,
        "preferences": "a" * 8192, "notes": "", "updated_at": 1.0,
        "teaching_preferences": {
            f"p{i}": {"text": symbol * 400, "evidence": symbol * 300, "updated_at": 1.0}
            for i in range(6)},
        "teaching_observations": {
            f"o{i}": {"knowledge_point_id": objective, "text": symbol * 400, "strategy": symbol * 300,
                      "evidence": symbol * 300, "basis": "tentative", "outcome": "unknown", "updated_at": 1.0}
            for i in range(12)},
    }

    def wire_request():
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"

    def run():
        raw = wire_request()
        assert len(raw) <= worker.MAX_INPUT
        result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT)], input=raw,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=child_env,
                                timeout=20, check=False)
        assert result.stderr == b""
        return result

    baseline = run()
    assert baseline.returncode == 0 and json.loads(baseline.stdout)["status"] == "UNCHANGED"
    padding = worker.MAX_OUTPUT - len(baseline.stdout)
    assert 1 <= padding < 8192
    value["profile"]["prior_knowledge"] = "a" * padding
    exact = run()
    assert exact.returncode == 0 and json.loads(exact.stdout)["status"] == "UNCHANGED"
    assert len(exact.stdout) == worker.MAX_OUTPUT and exact.stdout.endswith(b"\n")
    value["profile"]["prior_knowledge"] += "a"
    overflow = run()
    assert overflow.returncode == 1 and json.loads(overflow.stdout) == {
        "schema": worker.SCHEMA, "status": "UNAVAILABLE", "reason_code": "UPSTREAM_UNAVAILABLE"}
    assert len(overflow.stdout) <= worker.MAX_OUTPUT


def test_missing_pydantic_fails_closed_without_fallback(child_env):
    code, result = invoke(request(), child_env, no_site=True)
    assert code == 1 and result == {"schema": worker.SCHEMA, "status": "UNAVAILABLE",
                                    "reason_code": "UPSTREAM_UNAVAILABLE"}


def test_pinned_sources_and_synthetic_modification_are_rejected(tmp_path, monkeypatch):
    root = tmp_path / "upstream"
    root.mkdir()
    for name, (size, sha) in worker.SOURCES.items():
        data = (PROVIDER / "upstream" / name).read_bytes()
        assert len(data) == size and hashlib.sha256(data).hexdigest() == sha
        (root / name).write_bytes(data)
    modified = bytearray((root / "teaching.py").read_bytes())
    modified[-1] ^= 1
    (root / "teaching.py").write_bytes(modified)
    monkeypatch.setattr(worker, "UPSTREAM_ROOT", root)
    with pytest.raises(worker.Unavailable):
        worker._selected_rules()


def test_reparse_source_ancestor_is_refused_before_open(tmp_path, monkeypatch):
    root = tmp_path / "upstream"
    root.mkdir()
    monkeypatch.setattr(worker, "UPSTREAM_ROOT", root)
    actual_lstat = Path.lstat

    def flagged(path):
        info = actual_lstat(path)
        if path == root:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400,
                                   st_dev=info.st_dev, st_ino=info.st_ino)
        return info

    monkeypatch.setattr(Path, "lstat", flagged)
    monkeypatch.setattr(worker.os, "open", lambda *_a, **_k: pytest.fail("reparse path opened"))
    with pytest.raises(worker.Unavailable):
        worker._read_original("teaching.py")


def test_altered_selected_definition_cannot_import(monkeypatch):
    original = worker._read_original
    source = original("teaching.py")
    marker = b"def parse_teaching_updates(raw: list[dict], learner_message: str) -> list[TeachingUpdate]:"
    assert source.count(marker) == 1
    changed = source.replace(marker, marker + b"\n    import os", 1)
    monkeypatch.setattr(worker, "_read_original", lambda name: changed if name == "teaching.py" else original(name))
    with pytest.raises(worker.Unavailable):
        worker._selected_rules()
