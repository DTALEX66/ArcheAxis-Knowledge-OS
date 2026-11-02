"""Synthetic offline import preview; no Core, provider, model, or network."""

import base64
import builtins
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
SCRIPT = ROOT / "services" / "learning-providers" / "deeptutor" / "practice_import.py"
SPEC = importlib.util.spec_from_file_location("deeptutor_practice_import_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


def source_json(rows):
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def synthetic_row():
    return {"question": "Explain.", "type": "short_answer", "answer": "SYNTHETIC_KEY",
            "user_answer": "SYNTHETIC_USER_ANSWER", "explanation": "SYNTHETIC_EXPLANATION",
            "unused": "SYNTHETIC_UNMAPPED"}


@pytest.fixture
def child_env(tmp_path):
    home = tmp_path / "home"
    temporary = tmp_path / "temp"
    home.mkdir()
    temporary.mkdir()
    env = {"HOME": str(home), "USERPROFILE": str(home), "TEMP": str(temporary), "TMP": str(temporary),
           "APPDATA": str(home), "LOCALAPPDATA": str(home), "XDG_CONFIG_HOME": str(home),
           "XDG_CACHE_HOME": str(home), "XDG_DATA_HOME": str(home)}
    if sys.platform == "win32":
        env["SystemRoot"] = os.environ["SystemRoot"]
    return env


def test_exact_upstream_source_license_and_redacted_ephemeral_preview():
    assert hashlib.sha256(adapter.UPSTREAM.read_bytes()).hexdigest() == adapter.UPSTREAM_SHA256
    assert hashlib.sha256((SCRIPT.parent / "LICENSE").read_bytes()).hexdigest() == (
        "cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4"
    )
    raw = source_json([synthetic_row()])
    private = adapter._private_preview(raw, "json")
    assert private.source == raw and private.source_sha256 == hashlib.sha256(raw).hexdigest()
    assert private.rows[0]["raw"] == synthetic_row()
    assert private.rows[0]["unmapped"] == [{"key": "unused", "value": "SYNTHETIC_UNMAPPED",
                                            "reason": "not_selected_by_upstream"}]
    assert private.rows[0]["candidate"]["correct_answer"] == "SYNTHETIC_KEY"
    assert private.rows[0]["candidate"]["user_answer"] == "SYNTHETIC_USER_ANSWER"
    result = adapter.preview_bytes(raw, "json")
    assert result["source_within_size_limit"] is True and "source_byte_length" not in result
    assert result["source_row_scope"] == "json_array_index_one_based"
    assert "source_sha256" not in result and "upstream_question_id" not in result["rows"][0]
    assert result["original_bytes_persisted"] is False and result["restart_recovery"] == "not_available"
    assert result["unmapped_values_persisted"] is False
    assert result["origin"] == "caller_declared_unverified"
    assert result["provider_run"] == result["model_call"] == "NOT_INVOKED"
    assert result["independent_mastery"] == "not_established"
    row = result["rows"][0]
    assert row["source_row"] == 1 and row["source_field_count"] == 6 and row["unselected_top_level_field_count"] == 1
    assert result["preview_id"].startswith("preview_") and result["preview_id_scope"] == "ephemeral_not_content_binding"
    assert result["upstream_identity_in_receipt"] is False
    assert row["question"] == {"question": "Explain.", "question_type": "short_answer", "options": {}}
    rendered = json.dumps(result, ensure_ascii=False)
    assert all(value not in rendered for value in ("SYNTHETIC_KEY", "SYNTHETIC_USER_ANSWER",
                                                   "SYNTHETIC_EXPLANATION", "SYNTHETIC_UNMAPPED"))


def test_original_import_id_binds_the_unsecret_normalized_question_fields():
    raw = source_json([{"question": "Which?", "question_type": "mcq", "options": {"A": "first", "B": "second"},
                        "correct_answer": "second"}])
    result = adapter._private_preview(raw, "json").rows[0]["candidate"]
    assert result["question_type"] == "single_choice" and result["correct_answer"] == "B"
    identity = {key: result[key] for key in ("question", "question_type", "options", "correct_answer")}
    expected = "import:" + hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert result["question_id"] == expected
    changed = source_json([{"question": "Which?", "question_type": "mcq", "options": {"A": "first", "B": "second"},
                            "correct_answer": "first"}])
    assert adapter._private_preview(changed, "json").rows[0]["candidate"]["question_id"] != expected


def test_answer_dependent_identity_can_be_guessed_and_is_excluded_from_display():
    first = {"question": "Which?", "question_type": "mcq", "options": {"A": "first", "B": "second"},
             "correct_answer": "first"}
    second = {**first, "correct_answer": "second"}
    first_id = adapter._private_preview(source_json([first]), "json").rows[0]["candidate"]["question_id"]
    raw = source_json([second])
    private = adapter._private_preview(raw, "json")
    second_id = private.rows[0]["candidate"]["question_id"]
    assert first_id != second_id
    visible = json.dumps(adapter.preview_bytes(raw, "json"))
    assert first_id not in visible and second_id not in visible
    assert private.source_sha256 not in visible and "source_sha256" not in visible


@pytest.mark.parametrize("format,delimiter", [("csv", ","), ("tsv", "\t")])
def test_original_tabular_normalization_and_skipped_record_trace(format, delimiter):
    lines = [delimiter.join(parts) for parts in [
        ["question", "question_type", "A", "B", "answer", "user_answer", "unused"],
        ["First?", "single_choice", "one", "two", "B", "A", "extra"],
        ["", "", "", "", "", "", ""],
        ["Second?", "single_choice", "up", "down", "A", "B", "more"],
    ]]
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    result = adapter.preview_bytes(raw, format)
    assert result["source_row_scope"] == "tabular_record_index_one_based_including_header"
    assert result["skipped_source_rows"] == [3]
    assert [row["source_row"] for row in result["rows"]] == [2, 4]
    assert [row["unselected_top_level_field_count"] for row in result["rows"]] == [1, 1]
    assert result["rows"][0]["question"]["options"] == {"A": "one", "B": "two"}
    private = adapter._private_preview(raw, format)
    assert private.source == raw and private.rows[0]["candidate"]["correct_answer"] == "B"


def test_gb18030_and_chinese_aliases_use_original_normalizer():
    raw = "题目,题型,选项A,选项B,答案,备注\n问题,单选,甲,乙,乙,保留但不展示\n".encode("gb18030")
    private = adapter._private_preview(raw, "csv")
    candidate = private.rows[0]["candidate"]
    assert candidate["question_type"] == "single_choice" and candidate["correct_answer"] == "B"
    assert private.rows[0]["unmapped"][0]["value"] == "保留但不展示"
    assert "保留但不展示" not in json.dumps(adapter.preview_bytes(raw, "csv"), ensure_ascii=False)


def test_alias_collisions_and_unselected_fields_are_counted_and_retained_privately():
    raw = source_json([{"question": "overwritten", "题干": "unused alias", " Question ": "effective",
                        "answer": "unused answer alias", "correct_answer": "reference", "type": "short_answer"}])
    private = adapter._private_preview(raw, "json")
    assert private.rows[0]["candidate"]["question"] == "effective"
    assert [field["key"] for field in private.rows[0]["unmapped"]] == ["question", "题干", "answer"]
    result = adapter.preview_bytes(raw, "json")
    assert result["rows"][0]["unselected_top_level_field_count"] == 3
    assert result["rows"][0]["source_field_count"] == 6
    assert "unused answer alias" not in json.dumps(result)


def test_selected_option_column_override_is_reported_without_old_value_leak():
    raw = source_json([{"question": "Which?", "question_type": "single_choice", "correct_answer": "A",
                        "options": {"A": "SYNTHETIC_OLD", "B": "second"}, "A": "replacement"}])
    private = adapter._private_preview(raw, "json")
    assert private.rows[0]["raw"]["options"]["A"] == "SYNTHETIC_OLD"
    assert private.rows[0]["candidate"]["options"]["A"] == "replacement"
    assert private.rows[0]["option_changes"] == [{"key": "A", "old": "SYNTHETIC_OLD",
                                                   "new": "replacement", "reason": "option_column_override"}]
    result = adapter.preview_bytes(raw, "json")
    assert result["rows"][0]["unselected_top_level_field_count"] == 0
    assert result["rows"][0]["known_option_changes_count"] == 1
    assert result["rows"][0]["other_selected_values_compared"] is False
    assert "SYNTHETIC_OLD" not in json.dumps(result)


@pytest.mark.parametrize("header", [
    "question,question,answer",
    " Question ,question,answer",
])
def test_duplicate_csv_headers_fail_closed_after_upstream_normalization(header):
    raw = (header + "\n" + ",".join(["x"] * len(header.split(","))) + "\n").encode("utf-8")
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(raw, "csv")


def test_distinct_full_width_header_is_preserved_as_unselected():
    raw = "question,A,B,Ａ,answer\nWhich?,one,two,synthetic extra,A\n".encode("utf-8")
    private = adapter._private_preview(raw, "csv")
    assert private.rows[0]["candidate"]["options"] == {"A": "one", "B": "two"}
    assert private.rows[0]["unmapped"][0]["value"] == "synthetic extra"
    assert adapter.preview_bytes(raw, "csv")["rows"][0]["unselected_top_level_field_count"] == 1


@pytest.mark.parametrize("before,after", [
    (b"MAX_BYTES = 5 * 1024 * 1024", b"MAX_BYTES = 6 * 1024 * 1024"),
    (b"MAX_BYTES = 5 * 1024 * 1024", b"MAX_BYTES = __import__('os')"),
    (b"MAX_ROWS = 500", b"MAX_ROWS = 500 + 0"),
])
def test_unexpected_constant_ast_is_rejected_without_executing_it(monkeypatch, before, after):
    source = adapter.UPSTREAM.read_bytes()
    assert source.count(before) == 1
    monkeypatch.setattr(adapter, "_read_original", lambda: source.replace(before, after, 1))
    with pytest.raises(adapter.UpstreamUnavailable, match="constant mismatch"):
        adapter._selected_functions()


@pytest.mark.parametrize("raw,format", [
    (b'[{"question":"Q","question":"duplicate","answer":"A"}]', "json"),
    (b'[{"question":"Q","answer":"x","extra":NaN}]', "json"),
    (b'[{"question":"Q","answer":"x","extra":1e9999}]', "json"),
    (b'[{"question":"Q","answer":"x"}]', "xlsx"),
    (b'[{"question":"Q","answer":"x"}]', "../json"),
    (b'question,answer\nQ,A,extra\n', "csv"),
    (b'question,,answer\nQ,ignored,A\n', "csv"),
    (b'question,answer\nFirst?,"B\nSecond?,A\n', "csv"),
    (b"", "json"),
])
def test_ambiguous_oversized_or_unsupported_inputs_fail_closed(raw, format):
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(raw, format)


def test_oversized_input_fails_closed_without_a_huge_pytest_id():
    with pytest.raises(adapter.InvalidInput):
        adapter.preview_bytes(b"x" * (adapter.MAX_BYTES + 1), "csv")


def test_missing_answer_is_a_redacted_row_error_with_source_identity():
    raw = source_json([{"question": "Why?", "type": "short_answer", "answer": "", "extra": "SENTINEL"}])
    result = adapter.preview_bytes(raw, "json")
    assert adapter._private_preview(raw, "json").source_sha256 == hashlib.sha256(raw).hexdigest()
    assert "source_sha256" not in result
    assert result["rows"][0]["status"] == "REJECTED"
    assert result["rows"][0]["issue_codes"] == ["upstream_row_invalid"]
    assert result["rows"][0]["unselected_top_level_field_count"] == 1
    assert "SENTINEL" not in json.dumps(result)


def test_changed_source_and_reparse_ancestor_are_rejected_before_use(tmp_path, monkeypatch):
    root = tmp_path / "upstream"
    root.mkdir()
    original = bytearray(adapter.UPSTREAM.read_bytes())
    original[-1] ^= 1
    (root / "importing.py").write_bytes(original)
    monkeypatch.setattr(adapter, "UPSTREAM_ROOT", root)
    monkeypatch.setattr(adapter, "UPSTREAM", root / "importing.py")
    with pytest.raises(adapter.UpstreamUnavailable, match="identity mismatch"):
        adapter.preview_bytes(source_json([synthetic_row()]), "json")
    lstat = Path.lstat

    def flagged(path):
        info = lstat(path)
        if path == root:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400,
                                   st_dev=info.st_dev, st_ino=info.st_ino,
                                   st_nlink=info.st_nlink, st_size=info.st_size)
        return info

    monkeypatch.setattr(Path, "lstat", flagged)
    monkeypatch.setattr(adapter.os, "open", lambda *_a, **_k: pytest.fail("reparse ancestor was opened"))
    with pytest.raises(adapter.UpstreamUnavailable):
        adapter.preview_bytes(source_json([synthetic_row()]), "json")


def test_subset_never_imports_donor_module_or_opens_configuration(monkeypatch):
    original_import = builtins.__import__
    original_open = adapter.os.open
    permitted = adapter.UPSTREAM.absolute()

    def guarded_import(name, *args, **kwargs):
        if name == "deeptutor" or name.startswith("deeptutor.") or name == "openpyxl":
            raise AssertionError("forbidden upstream import")
        return original_import(name, *args, **kwargs)

    def guarded_open(path, *args, **kwargs):
        if Path(path).absolute() != permitted:
            raise AssertionError("unexpected file access")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(adapter.os, "open", guarded_open)
    assert adapter.preview_bytes(source_json([synthetic_row()]), "json")["rows"][0]["status"] == "CANDIDATE"


def test_isolated_byte_protocol_returns_no_answer_or_unmapped_values(tmp_path, child_env):
    raw = source_json([synthetic_row()])
    envelope = {"schema": adapter.SCHEMA, "request_id": "synthetic_1", "format": "json",
                "data_base64": base64.b64encode(raw).decode("ascii")}
    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    run = subprocess.run([sys.executable, "-I", "-B", "-S", "-X", "utf8", str(SCRIPT)],
                         input=json.dumps(envelope).encode("utf-8") + b"\n", env=child_env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
    assert run.returncode == 0 and not run.stderr
    result = json.loads(run.stdout)
    assert result["status"] == "PREVIEW" and result["request_id"] == "synthetic_1"
    assert "source_sha256" not in result and "upstream_question_id" not in result["rows"][0]
    assert b"SYNTHETIC_KEY" not in run.stdout and b"SYNTHETIC_USER_ANSWER" not in run.stdout
    assert b"SYNTHETIC_UNMAPPED" not in run.stdout
    assert sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*")) == before
