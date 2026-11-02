"""Synthetic private-pipe controls; no actual Core, model, or user material."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services" / "learning-providers" / "deeptutor"
WORKER = PROVIDER / "practice_host_worker.py"
SCHEMA = "archeaxis.deeptutor-practice-host-worker/v1"
MAX_SOURCE = 5 * 1024 * 1024
MAX_REQUEST = ((MAX_SOURCE + 2) // 3) * 4 + 65_536
MAX_REPLY = 1024 * 1024 + 65_536
PRIVATE_TITLE = "SYNTHETIC_PRIVATE_TITLE"
PRIVATE_USER_ANSWER = "SYNTHETIC_PRIVATE_USER_ANSWER"
PRIVATE_UNUSED = "SYNTHETIC_PRIVATE_UNUSED"


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


def source_and_row(format_name):
    if format_name == "json":
        rows = [{"question": "Synthetic question?", "question_type": "single_choice",
                 "options": {"A": "first", "B": "second"}, "correct_answer": "B",
                 "explanation": "SYNTHETIC_PRIVATE_EXPLANATION", "user_answer": PRIVATE_USER_ANSWER,
                 "unused": PRIVATE_UNUSED}]
        return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 1
    delimiter = "," if format_name == "csv" else "\t"
    rows = [["question", "question_type", "A", "B", "answer", "user_answer", "unused"],
            ["Synthetic question?", "single_choice", "first", "second", "B", PRIVATE_USER_ANSWER, PRIVATE_UNUSED]]
    return ("\n".join(delimiter.join(row) for row in rows) + "\n").encode("utf-8"), 2


def synthetic_receipt(raw, *, duplicate=False, source_id=None):
    sha = hashlib.sha256(raw).hexdigest()
    # Synthetic shape only; this test does not invoke or authenticate Core.
    if source_id is None:
        source_id = "src_" + hashlib.sha256(sha.encode("ascii")).hexdigest()[:24]
    return {"source_id": source_id, "sha256": sha, "duplicate": duplicate}


def request_for(raw, format_name="json", row=1, *, receipt=None):
    return {"schema": SCHEMA, "request_id": "synthetic_request_1",
            "source": {"format": format_name, "content_base64": base64.b64encode(raw).decode("ascii"),
                       "sha256": hashlib.sha256(raw).hexdigest()},
            "source_row": row,
            "material_snapshot": {"document_id": "synthetic_material", "version": 3, "content_sha256": "1" * 64},
            "question_id": "synthetic_question", "create_request_id": "synthetic_create", "title": PRIVATE_TITLE,
            "import_receipt": receipt if receipt is not None else synthetic_receipt(raw)}


def wire_for(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8") + b"\n"


def run_worker(wire, env, *, script=WORKER, blocked=False):
    if blocked:
        # These hooks exercise ordinary network/child/SQLite entry points for
        # the synthetic case; they are not an OS sandbox or process-tree test.
        launcher = ("import runpy,socket,sqlite3,subprocess,sys\n"
                    "def forbidden(*args,**kwargs): raise RuntimeError('blocked')\n"
                    "class ForbiddenPopen(subprocess.Popen):\n"
                    " def __init__(self,*args,**kwargs): raise RuntimeError('blocked')\n"
                    "socket.socket.connect=forbidden\n"
                    "socket.socket.connect_ex=forbidden\n"
                    "socket.socket.sendto=forbidden\n"
                    "socket.create_connection=forbidden\n"
                    "sqlite3.connect=forbidden\n"
                    "subprocess.Popen=ForbiddenPopen\n"
                    "script=sys.argv[1]\n"
                    "sys.argv=[script]\n"
                    "runpy.run_path(script,run_name='__main__')\n")
        command = [sys.executable, "-I", "-B", "-S", "-c", launcher, str(script)]
    else:
        command = [sys.executable, "-I", "-B", "-S", str(script)]
    return subprocess.run(command, input=wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=env, timeout=60, check=False)


def result_of(child):
    assert child.stderr == b""
    assert child.stdout.endswith(b"\n") and child.stdout.count(b"\n") == 1
    assert len(child.stdout) <= MAX_REPLY
    return json.loads(child.stdout.decode("utf-8", "strict"))


@pytest.mark.parametrize("format_name", ["json", "csv", "tsv"])
def test_real_private_child_reuses_candidate_and_binds_exact_frame(format_name, child_env):
    raw, row = source_and_row(format_name)
    request = request_for(raw, format_name, row)
    wire = wire_for(request)
    child = run_worker(wire, child_env)
    assert child.returncode == 0
    result = result_of(child)
    assert result["schema"] == SCHEMA and result["status"] == "PRIVATE_CANDIDATE"
    assert result["request_id"] == request["request_id"]
    assert result["input_sha256"] == hashlib.sha256(wire).hexdigest()
    assert result["import_receipt"] == "CALLER_SUPPLIED_NOT_AUTHENTICATED"
    assert result["material_snapshot"] == "CALLER_DECLARED_NOT_AUTHENTICATED"
    assert result["row_and_loss_receipt"] == "NOT_RETURNED_OR_PERSISTED_BY_WORKER"
    assert result["core_write"] == "NOT_EXECUTED" and result["provider_execution"] == "NOT_INVOKED"
    document = result["document_create_request"]
    assert document["source_id"] == request["import_receipt"]["source_id"]
    assert document["source_revision"] == hashlib.sha256(raw).hexdigest()
    assert document["create_request_id"] == request["create_request_id"] and document["title"] == PRIVATE_TITLE
    attrs = document["editor_json"]["attrs"]["archeaxis_deeptutor_question"]
    assert attrs["origin"] == "user_import_unverified" and attrs["source_material"] == request["material_snapshot"]
    assert attrs["question"]["question_id"] == request["question_id"]
    assert attrs["question"]["correct_answer"] == "B"
    assert [item["content"][0]["text"] for item in document["editor_json"]["content"]] == [
        "Synthetic question?", "A. first", "B. second"]
    # The key and explanation above are intentionally private output. The
    # unselected source data and learner answer are not forwarded as results.
    assert PRIVATE_USER_ANSWER.encode() not in child.stdout and PRIVATE_UNUSED.encode() not in child.stdout
    assert request["source"]["content_base64"].encode() not in child.stdout


def test_non_ascii_source_and_reply_do_not_depend_on_console_encoding(child_env):
    raw = "题目,题型,选项A,选项B,答案\n问题,单选,甲,乙,乙\n".encode("gb18030")
    request = request_for(raw, "csv", 2)
    request["title"] = "合成标题😀"
    child = run_worker(wire_for(request), child_env)
    assert child.returncode == 0
    result = result_of(child)
    assert result["document_create_request"]["title"] == request["title"]
    question = result["document_create_request"]["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]
    assert question["question"] == "问题" and question["correct_answer"] == "B"


def test_existing_duplicate_source_id_is_not_forced_to_new_id_formula(child_env):
    raw, row = source_and_row("json")
    receipt = synthetic_receipt(raw, duplicate=True, source_id="historical_source_42")
    child = run_worker(wire_for(request_for(raw, row=row, receipt=receipt)), child_env)
    assert child.returncode == 0
    assert result_of(child)["document_create_request"]["source_id"] == "historical_source_42"


def test_source_row_selection_changes_question_from_the_same_source(child_env):
    rows = [{"question": "First?", "question_type": "short_answer", "correct_answer": "first key"},
            {"question": "Second?", "question_type": "short_answer", "correct_answer": "second key"}]
    raw = json.dumps(rows, separators=(",", ":")).encode()
    outputs = []
    for row in (1, 2):
        child = run_worker(wire_for(request_for(raw, row=row)), child_env)
        assert child.returncode == 0
        outputs.append(result_of(child)["document_create_request"]["editor_json"]["attrs"]
                       ["archeaxis_deeptutor_question"]["question"])
    assert [(value["question"], value["correct_answer"]) for value in outputs] == [
        ("First?", "first key"), ("Second?", "second key")]


@pytest.mark.parametrize("case", ["empty", "no_lf", "extra_frame", "duplicate_key", "nan", "float",
                                  "unknown_field", "bad_utf8", "oversized_integer"])
def test_invalid_frames_return_fixed_error_without_reflecting_input(case, child_env):
    raw, row = source_and_row("json")
    request = request_for(raw, row=row)
    request["request_id"] = "SYNTHETIC_PRIVATE_REQUEST_ID"
    wire = wire_for(request)
    if case == "empty":
        wire = b""
    elif case == "no_lf":
        wire = wire[:-1]
    elif case == "extra_frame":
        wire += b"{}\n"
    elif case == "duplicate_key":
        wire = wire.replace(b'"source_row":1', b'"source_row":1,"source_row":1', 1)
    elif case == "nan":
        wire = wire.replace(b'"source_row":1', b'"source_row":NaN', 1)
    elif case == "float":
        wire = wire.replace(b'"source_row":1', b'"source_row":1.0', 1)
    elif case == "unknown_field":
        request["unexpected"] = "SYNTHETIC_PRIVATE_UNKNOWN"
        wire = wire_for(request)
    elif case == "bad_utf8":
        wire = b'\xff\n'
    else:
        wire = wire.replace(b'"source_row":1', b'"source_row":' + b"1" * 101, 1)
    child = run_worker(wire, child_env)
    assert child.returncode == 2
    result = result_of(child)
    assert result == {"schema": SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}
    assert b"SYNTHETIC_PRIVATE" not in child.stdout + child.stderr


@pytest.mark.parametrize("case", ["source_sha", "receipt_sha", "first_source_id", "receipt_flag", "bad_base64",
                                  "noncanonical_base64", "empty_source", "xlsx", "question_id", "create_id",
                                  "row_bool", "row_upper", "material_extra", "material_bool", "title_surrogate"])
def test_invalid_fields_fail_closed_without_returning_a_document(case, child_env):
    raw, row = source_and_row("json")
    request = request_for(raw, row=row)
    if case == "source_sha":
        request["source"]["sha256"] = "0" * 64
    elif case == "receipt_sha":
        request["import_receipt"]["sha256"] = "0" * 64
    elif case == "first_source_id":
        request["import_receipt"]["source_id"] = "src_incorrect"
    elif case == "receipt_flag":
        request["import_receipt"]["duplicate"] = 0
    elif case == "bad_base64":
        request["source"]["content_base64"] = "@@@="
    elif case == "noncanonical_base64":
        request["source"]["content_base64"] += "="
    elif case == "empty_source":
        request = request_for(b"", row=row)
    elif case == "xlsx":
        request["source"]["format"] = "xlsx"
    elif case == "question_id":
        request["question_id"] = "import:" + "a" * 64
    elif case == "create_id":
        request["create_request_id"] = "bad id"
    elif case == "row_bool":
        request["source_row"] = True
    elif case == "row_upper":
        request["source_row"] = 503
    elif case == "material_extra":
        request["material_snapshot"]["unknown"] = "SYNTHETIC_PRIVATE_UNKNOWN"
    elif case == "material_bool":
        request["material_snapshot"]["version"] = True
    else:
        request["title"] = "\ud800"
    # ensure_ascii=True allows a deliberately unpaired surrogate to reach the
    # child as a JSON escape without the test process failing to encode it.
    wire = json.dumps(request, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("ascii") + b"\n"
    child = run_worker(wire, child_env)
    assert child.returncode == 2
    result = result_of(child)
    assert result["status"] == "INVALID_REQUEST" and "document_create_request" not in result
    assert b"SYNTHETIC_PRIVATE" not in child.stdout + child.stderr


def test_selected_missing_row_self_reference_and_bad_original_are_rejected_privately(child_env):
    raw, _ = source_and_row("json")
    requests = [request_for(raw, row=2), request_for(raw)]
    create_id = requests[1]["create_request_id"]
    requests[1]["material_snapshot"]["document_id"] = "doc_req_" + hashlib.sha256(create_id.encode("ascii")).hexdigest()
    invalid_original = b'[{"question":NaN}]'
    requests.append(request_for(invalid_original))
    for request in requests:
        child = run_worker(wire_for(request), child_env)
        assert child.returncode == 2
        result = result_of(child)
        assert result["status"] == "REJECTED" and result["reason_code"] == "CANDIDATE_REJECTED_OR_UNAVAILABLE"
        assert b"SYNTHETIC_PRIVATE" not in child.stdout + child.stderr


def test_single_source_at_5_mib_and_over_limit_stay_in_memory(child_env):
    # Trailing JSON whitespace makes the source exactly 5 MiB while retaining a
    # small valid row. No large workbook or file is created on disk.
    raw, row = source_and_row("json")
    raw += b" " * (MAX_SOURCE - len(raw))
    wire = wire_for(request_for(raw, row=row))
    assert len(raw) == MAX_SOURCE and len(wire) <= MAX_REQUEST
    child = run_worker(wire, child_env)
    assert child.returncode == 0 and result_of(child)["status"] == "PRIVATE_CANDIDATE"
    too_large = raw + b" "
    rejected = run_worker(wire_for(request_for(too_large, row=row)), child_env)
    assert rejected.returncode == 2 and result_of(rejected)["status"] == "INVALID_REQUEST"


@pytest.mark.parametrize("case", ["exact_frame_limit", "one_over_frame_limit", "space_after_lf"])
def test_frame_limit_and_eof_with_real_child_do_not_echo_private_input(case, child_env):
    raw, row = source_and_row("json")
    request = request_for(raw, row=row)
    request["request_id"] = "SYNTHETIC_PRIVATE_REQUEST_ID"
    initial = wire_for(request)
    if case == "space_after_lf":
        wire = initial + b" "
    else:
        # Whitespace before LF is legal trailing JSON whitespace. It tests
        # the frame limit independently of the much smaller decoded source.
        extra = 1 if case == "one_over_frame_limit" else 0
        wire = initial[:-1] + b" " * (MAX_REQUEST - len(initial) + extra) + b"\n"
        assert len(wire) == MAX_REQUEST + extra
    child = run_worker(wire, child_env)
    result = result_of(child)
    if case == "exact_frame_limit":
        assert child.returncode == 0 and result["status"] == "PRIVATE_CANDIDATE"
        assert result["input_sha256"] == hashlib.sha256(wire).hexdigest()
    else:
        assert child.returncode == 2
        assert result == {"schema": SCHEMA, "status": "INVALID_REQUEST", "reason_code": "INVALID_INPUT"}
        assert b"SYNTHETIC_PRIVATE" not in child.stdout + child.stderr


def test_synthetic_path_needs_no_socket_child_process_or_sqlite_connection(child_env):
    raw, row = source_and_row("json")
    child = run_worker(wire_for(request_for(raw, row=row)), child_env, blocked=True)
    assert child.returncode == 0 and result_of(child)["status"] == "PRIVATE_CANDIDATE"


@pytest.mark.parametrize("relative", ["practice_candidate_document.py", "candidate_document.py",
                                      "practice_import.py", "upstream/importing.py"])
@pytest.mark.parametrize("damage", ["missing", "same_length_tamper"])
def test_each_pinned_source_missing_or_tampered_fails_in_isolated_copy(relative, damage, child_env, tmp_path):
    isolated = tmp_path / "isolated"
    (isolated / "upstream").mkdir(parents=True)
    shutil.copyfile(WORKER, isolated / WORKER.name)
    for name in ("practice_candidate_document.py", "candidate_document.py", "practice_import.py",
                 "upstream/importing.py"):
        if name == relative and damage == "missing":
            continue
        data = (PROVIDER / name).read_bytes()
        if name == relative:
            changed = bytearray(data)
            changed[0] ^= 1
            data = bytes(changed)
            assert len(data) == (PROVIDER / name).stat().st_size
        (isolated / name).write_bytes(data)
    raw, row = source_and_row("json")
    child = run_worker(wire_for(request_for(raw, row=row)), child_env, script=isolated / WORKER.name)
    assert child.returncode in (1, 2)
    result = result_of(child)
    assert result["status"] in {"UNAVAILABLE", "REJECTED"}
    assert "document_create_request" not in result and b"SYNTHETIC_PRIVATE" not in child.stdout + child.stderr
