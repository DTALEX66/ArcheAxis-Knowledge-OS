"""Real upstream outline function with synthetic replies; no Core or model qualification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "services/learning-providers/openmaic/outline-replay-worker.mjs"
DONOR = WORKER.parent / "vendor/generation-0.3.28-outline"
ARCHIVE = ROOT / ".project-local/archives/owner-inputs/20261101-learning-platform-sources/OpenMAIC-1.3.0.zip"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit ARCHEAXIS_TEST_NODE is required; PATH is not searched")


def invoke(frame: dict | bytes, *args: str) -> tuple[int, dict]:
    assert NODE and Path(NODE).is_absolute(), "ARCHEAXIS_TEST_NODE must be an absolute path"
    raw = frame if isinstance(frame, bytes) else json.dumps(frame, ensure_ascii=False).encode("utf-8")
    process = subprocess.run([NODE, str(WORKER), *args], input=raw, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=20, check=False)
    try:
        body = json.loads(process.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as error:
        raise AssertionError(f"missing JSON result: exit={process.returncode}, stderr={process.stderr.decode('utf-8', 'replace')}") from error
    return process.returncode, body


def frame(reply: dict | None = None) -> dict:
    outline = {"id": "outline_1", "type": "quiz", "title": "示例", "description": "离线合成",
               "keyPoints": ["核对"], "order": 1}
    return {"schema": "archeaxis.openmaic-outline-replay/v1", "request_id": "request_1",
            "requirement": "用本地材料准备课程", "source_text": "合成来源材料",
            "reply": reply or {"kind": "synthetic_response", "value": json.dumps({
                "languageDirective": "中文", "courseTitle": "示例课程", "outlines": [outline]}, ensure_ascii=False)}}


def capture_frame() -> dict:
    return {"schema": "archeaxis.openmaic-outline-prompt/v1", "stage": "capture",
            "request_id": "prompt_request_1", "requirement": "从材料生成知识检查", "source_text": "合成来源材料"}


def replay_frame(capture: dict, binding: dict, value: str | None = None) -> dict:
    if value is None:
        value = frame()["reply"]["value"]
    return {**capture, "stage": "replay", "binding": binding,
            "reply": {"kind": "caller_supplied", "value": value}}


def capture_prompt() -> tuple[dict, dict]:
    request = capture_frame()
    code, result = invoke(request)
    assert code == 0 and result["status"] == "PROMPT_CAPTURED", result
    return request, result["binding"]


def test_every_vendored_file_is_the_exact_mit_licensed_archive_member():
    if not ARCHIVE.is_file():
        pytest.skip("local-only original absent in a Git clone/CI (Git-ignored .project-local input); "
                    "this skip is NOT evidence of byte identity")
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == "7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40"
    manifest = json.loads((DONOR / "ORIGINALS.json").read_text(encoding="utf-8"))
    assert manifest["license"] == "MIT"
    assert manifest["generation_version"] == "0.3.28"
    with zipfile.ZipFile(ARCHIVE) as archive:
        for relative, expected in manifest["originals"].items():
            original = archive.read(manifest["source_prefix"] + relative)
            assert hashlib.sha256(original).hexdigest() == expected
            assert (DONOR / relative).read_bytes() == original


@requires_node
def test_locked_upstream_nanoid_honors_default_and_explicit_lengths():
    assert NODE and Path(NODE).is_absolute()
    adapter = (WORKER.parent / "vendor/npm/nanoid-5.1.14/index.js").as_uri()
    source = 'const m=await import(process.argv[1]); process.stdout.write(JSON.stringify([m.nanoid(),m.nanoid(8),m.nanoid(0)]));'
    process = subprocess.run([NODE, "--input-type=module", "-e", source, adapter], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=10, check=False)
    assert process.returncode == 0, process.stderr.decode("utf-8", "replace")
    default_id, eight_id, empty_id = json.loads(process.stdout.decode("utf-8"))
    assert len(default_id) == 21
    assert len(eight_id) == 8
    assert empty_id == ""
    assert all(c.isascii() and (c.isalnum() or c in "_-") for c in default_id + eight_id)


@requires_node
def test_real_outline_function_processes_a_synthetic_reply_without_model_or_network():
    data = frame()
    code, result = invoke(data)
    assert code == 0, result
    assert result["status"] == "CANDIDATE"
    assert result["input"] == data
    assert result["data"]["outlines"][0]["id"] == "outline_1"
    assert result["data"]["outlines"][0]["type"] == "quiz"
    assert len(result["calls"]) == 1
    assert len(result["calls"][0]["system_sha256"]) == 64
    assert result["model_call"] == "NOT_INVOKED"
    assert result["response_origin"] == "SYNTHETIC_REPLAY"
    assert result["response_origin_verification"] == "CALLER_DECLARED_UNVERIFIED"
    assert result["returned_content_may_include_source_material"] is True
    assert result["output_privacy_filter"] == "NOT_APPLIED" and result["logging_safety"] == "NOT_ESTABLISHED"
    assert result["network_performed"] is False
    assert result["core_task"] == "NOT_CONNECTED"
    assert result["full_generation_chain"] is False
    assert result["jsonrepair_dependency"] == "LOCKED_3.13.3"
    assert result["nanoid_dependency"] == "LOCKED_5.1.14"
    observed = subprocess.run([NODE, "-p", "process.versions.node"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=10, check=False)
    assert observed.returncode == 0
    node_version = observed.stdout.decode("utf-8").strip()
    assert result["runtime"]["node_version"] == node_version
    assert int(node_version.split(".")[0]) >= 24
    assert result["runtime"]["register_hooks_available"] is True
    assert result["runtime"]["original_typescript_imported"] is True
    assert result["runtime"]["locked_npm_members_checked"] is True
    assert result["runtime"]["upstream_members_checked"] is True
    print(f"Explicit Node {node_version}: registerHooks and upstream TypeScript import observed in replay process")


@requires_node
@pytest.mark.parametrize("second_id,expected_exit,expected_status", [
    ("same", 2, "UNSUPPORTED_OUTPUT"),
    ("different", 0, "CANDIDATE"),
])
def test_legacy_multi_outline_identity_and_observation(second_id, expected_exit, expected_status):
    first = {"id": "same", "type": "quiz", "title": "First", "description": "D1", "keyPoints": [], "order": 1}
    second = {"id": second_id, "type": "quiz", "title": "Second", "description": "D2", "keyPoints": [], "order": 2}
    reply = json.dumps({"languageDirective": "中文", "outlines": [first, second]}, ensure_ascii=False)
    request = frame({"kind": "synthetic_response", "value": reply})
    request["source_text"] = "SYNTHETIC_SOURCE_CONTAINS_DATA"
    code, result = invoke(request)
    assert code == expected_exit and result["status"] == expected_status
    assert result["input"] == request and result["input"]["reply"]["value"] == reply
    assert result["response_origin"] == "SYNTHETIC_REPLAY"
    assert result["response_origin_verification"] == "CALLER_DECLARED_UNVERIFIED"
    assert result["returned_content_may_include_source_material"] is True
    assert result["output_privacy_filter"] == "NOT_APPLIED" and result["logging_safety"] == "NOT_ESTABLISHED"
    assert result["model_call"] == "NOT_INVOKED" and result["core_task"] == "NOT_CONNECTED"
    if second_id == "same":
        assert result["data"] is None
        assert result["observed_upstream"]["outlines"] == [first, second]
        assert result["differences"] == [{"kind": "DUPLICATE_OUTLINE_ID", "outline_index": 1,
            "first_outline_index": 0, "id": "same"}]
    else:
        assert [outline["id"] for outline in result["data"]["outlines"]] == ["same", "different"]


@requires_node
def test_upstream_default_language_and_identity_changes_are_explicit():
    response = [{"type": "slide", "title": "示例", "description": "文本", "keyPoints": [], "order": 99}]
    code, result = invoke(frame({"kind": "synthetic_response", "value": json.dumps(response, ensure_ascii=False)}))
    assert code == 0, result
    assert set(result["transformations"]) >= {"DEFAULT_LANGUAGE_DIRECTIVE", "UNSTABLE_GENERATED_OUTLINE_IDS", "OUTLINE_ORDER_ASSIGNED"}
    assert result["data"]["outlines"][0]["order"] == 1
    assert result["retry_bytes_stable"] is False


@requires_node
def test_synthetic_callback_failure_and_upstream_parse_failure_are_not_candidates():
    code, failed = invoke(frame({"kind": "synthetic_error"}))
    assert code == 2
    assert failed["status"] == "UPSTREAM_FAILURE"
    assert failed["model_call"] == "NOT_INVOKED"
    assert "SYNTHETIC_REPLAY_FAILURE" in failed["upstream_reported_error"]
    code, malformed = invoke(frame({"kind": "synthetic_response", "value": "not JSON"}))
    assert code == 2
    assert malformed["status"] == "UPSTREAM_FAILURE"
    assert malformed["data"] is None


@requires_node
def test_recovered_truncated_response_is_quarantined():
    truncated = '[{"id":"one","type":"slide","title":"T","description":"D","keyPoints":[]}'
    code, result = invoke(frame({"kind": "synthetic_response", "value": truncated}))
    assert code == 2
    assert result["status"] == "UPSTREAM_RECOVERY_NOT_ADMITTED"
    assert result["upstream_reported_success"] is True
    assert result["data"] is None
    assert result["input"]["reply"]["value"] == truncated


@requires_node
def test_locked_jsonrepair_recovers_trailing_comma_but_result_is_quarantined():
    # The upstream built-in attempt does not remove this trailing comma; this
    # succeeds only when the retained jsonrepair function actually runs.
    malformed = '{"outlines":[{"id":"q","type":"quiz","title":"T","description":"D","keyPoints":[],}]}'
    code, result = invoke(frame({"kind": "synthetic_response", "value": malformed}))
    assert code == 2
    assert result["status"] == "UPSTREAM_RECOVERY_NOT_ADMITTED"
    assert result["upstream_reported_success"] is True
    assert result["data"] is None
    assert result["input"]["reply"]["value"] == malformed


def test_selected_npm_members_retain_audited_byte_identities_and_licenses():
    npm = WORKER.parent / "vendor/npm"
    expected = {
        "jsonrepair-3.13.3": ("ISC", "sha512-BTznj0owIt2CBAH/LTo7+1I5pMvl1e1033LRl/HUowlZmJOIhzC0zbX5bxMngLkfT4WnzPP26QnW5wMr2g9tsQ=="),
        "nanoid-5.1.14": ("MIT", "sha512-5c8l8kVzqpnDPaicbEop/fV0Q1w16FmbWtVhMqugTozAwYdlIQojWH5a/M7UfziFmGdQRrUdV+EPzc9Xng3VAQ=="),
    }
    for package, (license_name, sri) in expected.items():
        root = npm / package
        record = json.loads((root / "SOURCE.json").read_text(encoding="utf-8"))
        assert record["license"] == license_name and record["archive_sri"] == sri
        assert record["scripts_executed"] is False
        for relative, identity in record["files"].items():
            data = (root / relative).read_bytes()
            assert len(data) == identity["bytes"]
            assert hashlib.sha256(data).hexdigest() == identity["sha256"]


@requires_node
@pytest.mark.parametrize("relative,reason", [
    ("vendor/npm/jsonrepair-3.13.3/lib/esm/index.js", b"LOCKED_NPM_MEMBER_IDENTITY_MISMATCH"),
    ("vendor/generation-0.3.28-outline/src/outline-generator.ts", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("vendor/generation-0.3.28-outline/templates/requirements-to-outlines/system.md", b"UPSTREAM_MEMBER_IDENTITY_MISMATCH"),
    ("vendor/generation-0.3.28-outline/ORIGINALS.json", b"UPSTREAM_MANIFEST_IDENTITY_MISMATCH"),
    ("outline-prompt-guard.mjs", b"OUTLINE_GUARD_IDENTITY_MISMATCH"),
])
def test_changed_member_is_refused_before_replay(tmp_path, relative, reason):
    assert NODE and Path(NODE).is_absolute()
    copy = tmp_path / "worker-copy"
    copy.mkdir()
    shutil.copy2(WORKER, copy / WORKER.name)
    shutil.copy2(WORKER.parent / "outline-prompt-guard.mjs", copy / "outline-prompt-guard.mjs")
    shutil.copytree(WORKER.parent / "vendor/generation-0.3.28-outline", copy / "vendor/generation-0.3.28-outline")
    shutil.copytree(WORKER.parent / "vendor/npm", copy / "vendor/npm")
    changed = copy / relative
    changed.write_bytes(changed.read_bytes() + b"\n// changed\n")
    process = subprocess.run([NODE, str(copy / WORKER.name), "--hello"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=10, check=False)
    assert process.returncode != 0
    assert process.stdout == b""
    assert reason in process.stderr


@requires_node
@pytest.mark.parametrize("reply", [
    '{"outlines":[],"outl\\u0069nes":[]}',
    json.dumps({"outlines": [{"id": "x", "type": "future", "title": "x", "description": "x", "keyPoints": []}]}),
    json.dumps({"outlines": [{"id": "x", "type": "slide", "title": "x", "description": "x", "keyPoints": [], "mediaGenerations": [{"id": "m"}]}]}),
])
def test_ambiguous_unknown_and_media_output_are_refused(reply):
    code, result = invoke(frame({"kind": "synthetic_response", "value": reply}))
    assert code == 2
    assert result["status"] in {"INVALID_RESPONSE", "UNSUPPORTED_OUTPUT"}
    assert result["data"] is None


@requires_node
def test_bad_identity_oversized_input_and_duplicate_frame_are_refused():
    bad = frame()
    bad["request_id"] = "../outside"
    assert invoke(bad)[1]["status"] == "INVALID_REQUEST"
    assert invoke(b" " * 256_001)[1]["status"] == "INVALID_REQUEST"
    duplicated = json.dumps(frame()).replace('"request_id": "request_1"', '"request_id": "request_1", "request_\\u0069d": "other"').encode()
    assert invoke(duplicated)[1]["status"] == "INVALID_REQUEST"


@requires_node
def test_prompt_capture_and_bound_caller_reply_use_the_actual_upstream_function():
    request, binding = capture_prompt()
    assert binding["schema"] == "archeaxis.openmaic-outline-prompt-binding/v1"
    assert binding["request_id"] == request["request_id"]
    assert binding["upstream_manifest_sha256"] == hashlib.sha256((DONOR / "ORIGINALS.json").read_bytes()).hexdigest()
    assert binding["worker_sha256"] == hashlib.sha256(WORKER.read_bytes()).hexdigest()
    assert binding["guard_sha256"] == hashlib.sha256((WORKER.parent / "outline-prompt-guard.mjs").read_bytes()).hexdigest()
    assert binding["system"] and binding["user"]
    assert request["source_text"] in binding["user"]
    assert binding["system_sha256"] == hashlib.sha256(binding["system"].encode()).hexdigest()
    assert binding["user_sha256"] == hashlib.sha256(binding["user"].encode()).hexdigest()
    replay = replay_frame(request, binding)
    code, result = invoke(replay)
    assert code == 0 and result["status"] == "CANDIDATE" and result["callback_count"] == 1, result
    assert "input" not in result and result["request_id"] == replay["request_id"]
    assert result["data"]["outlines"][0]["id"] == "outline_1"
    assert result["response_origin"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert result["model_call"] == "NOT_INVOKED" and result["network_performed"] is False
    assert result["core_task"] == "NOT_CONNECTED" and result["core_authorization"] == "NOT_ESTABLISHED"
    assert result["canonical_bindings_verified"] is False and result["persisted"] is False
    assert result["identity_scope"] == "UNKEYED_COMPARISON_ONLY" and result["sandbox"] == "NOT_ESTABLISHED"
    assert result["binding_authentication"] == "NOT_PROVIDED" and result["source_snapshot_authority"] == "CALLER_DECLARED_ONLY"
    assert result["returned_content_may_include_source_material"] is True
    assert result["output_privacy_filter"] == "NOT_APPLIED" and result["logging_safety"] == "NOT_ESTABLISHED"


@requires_node
@pytest.mark.parametrize("field", ["system", "user"])
def test_changed_prompt_is_rejected_even_when_its_unkeyed_digest_is_recomputed(field):
    request, binding = capture_prompt()
    binding[field] += "tampered"
    binding[field + "_sha256"] = hashlib.sha256(binding[field].encode()).hexdigest()
    code, result = invoke(replay_frame(request, binding))
    assert code == 2 and result["status"] == "CALLBACK_REJECTED"
    assert result["reason"] == "PROMPT_MISMATCH" and result["data"] is None


@requires_node
@pytest.mark.parametrize("field", ["input_sha256", "upstream_manifest_sha256", "npm_members_sha256", "worker_sha256", "guard_sha256"])
def test_changed_input_or_donor_binding_is_rejected(field):
    request, binding = capture_prompt()
    binding[field] = "0" * 64
    code, result = invoke(replay_frame(request, binding))
    assert code == 2 and result["status"] == "BINDING_MISMATCH" and result["data"] is None


@requires_node
def test_changed_requirement_or_source_cannot_use_a_prior_capture():
    request, binding = capture_prompt()
    for field in ("requirement", "source_text", "request_id"):
        altered = {**request, field: request[field] + "changed"}
        code, result = invoke(replay_frame(altered, binding))
        assert code == 2 and result["status"] == "BINDING_MISMATCH" and result["data"] is None


@requires_node
def test_changed_source_with_recomputed_identity_still_fails_prompt_comparison():
    request, binding = capture_prompt()
    altered = {**request, "source_text": "different source"}
    # Match the worker's fixed field order, without treating this digest as an authorization.
    identity = json.dumps({"request_id": altered["request_id"], "requirement": altered["requirement"],
                           "source_text": altered["source_text"]}, ensure_ascii=False, separators=(",", ":"))
    binding["input_sha256"] = hashlib.sha256(identity.encode()).hexdigest()
    code, result = invoke(replay_frame(altered, binding))
    assert code == 2 and result["status"] == "CALLBACK_REJECTED" and result["reason"] == "PROMPT_MISMATCH"


@requires_node
def test_unkeyed_identity_is_not_authentication_when_distinct_sources_give_the_same_prompt():
    request = {**capture_frame(), "source_text": ""}
    code, captured = invoke(request)
    assert code == 0 and captured["status"] == "PROMPT_CAPTURED"
    altered = {**request, "source_text": "None"}
    binding = captured["binding"]
    identity = json.dumps({"request_id": altered["request_id"], "requirement": altered["requirement"],
                           "source_text": altered["source_text"]}, ensure_ascii=False, separators=(",", ":"))
    binding["input_sha256"] = hashlib.sha256(identity.encode()).hexdigest()
    code, result = invoke(replay_frame(altered, binding))
    assert code == 0 and result["status"] == "CANDIDATE"
    assert result["identity_scope"] == "UNKEYED_COMPARISON_ONLY" and result["binding_authentication"] == "NOT_PROVIDED"
    assert result["source_snapshot_authority"] == "CALLER_DECLARED_ONLY"
    assert result["core_task"] == "NOT_CONNECTED" and result["core_authorization"] == "NOT_ESTABLISHED"
    assert result["canonical_bindings_verified"] is False and result["persisted"] is False


@requires_node
def test_donor_changed_after_capture_is_refused_before_replay(tmp_path):
    request, binding = capture_prompt()
    copy = tmp_path / "worker-copy"
    copy.mkdir()
    shutil.copy2(WORKER, copy / WORKER.name)
    shutil.copy2(WORKER.parent / "outline-prompt-guard.mjs", copy / "outline-prompt-guard.mjs")
    for member in ("generation-0.3.28-outline", "npm"):
        shutil.copytree(WORKER.parent / "vendor" / member, copy / "vendor" / member)
    changed = copy / "vendor/generation-0.3.28-outline/templates/requirements-to-outlines/user.md"
    changed.write_bytes(changed.read_bytes() + b"changed")
    raw = json.dumps(replay_frame(request, binding), ensure_ascii=False).encode("utf-8")
    process = subprocess.run([NODE, str(copy / WORKER.name)], input=raw, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=20, check=False)
    assert process.returncode != 0 and process.stdout == b""
    assert b"UPSTREAM_MEMBER_IDENTITY_MISMATCH" in process.stderr


@requires_node
def test_callback_guard_rejects_extra_callbacks_and_nonempty_images():
    guard = (WORKER.parent / "outline-prompt-guard.mjs").as_uri()
    source = '''
const {createPromptGuard}=await import(process.argv[1]);
const a=createPromptGuard(null,()=>"ok"); await a.callback("system","user",undefined);
try { await a.callback("system","user",undefined); } catch {}
const b=createPromptGuard(null,()=>"ok");
try { await b.callback("system","user",[{id:"image"}]); } catch {}
process.stdout.write(JSON.stringify({extra:a.state,images:b.state}));
'''
    process = subprocess.run([NODE, "--input-type=module", "-e", source, guard], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=10, check=False)
    assert process.returncode == 0, process.stderr.decode("utf-8", "replace")
    observations = json.loads(process.stdout.decode("utf-8"))
    assert observations["extra"]["calls"] == 2 and observations["extra"]["failure"] == "MULTIPLE_CALLBACKS"
    assert observations["images"]["calls"] == 1 and observations["images"]["failure"] == "IMAGES_UNSUPPORTED"


@requires_node
def test_prompt_request_refuses_images_wrong_reply_kind_and_oversized_reply():
    request, binding = capture_prompt()
    assert invoke({**request, "images": [{"id": "x"}]})[1]["status"] == "INVALID_REQUEST"
    replay = replay_frame(request, binding)
    replay["reply"]["kind"] = "synthetic_response"
    assert invoke(replay)[1]["status"] == "INVALID_REQUEST"
    replay["reply"] = {"kind": "caller_supplied", "value": "x" * 120_001}
    assert invoke(replay)[1]["status"] == "INVALID_REQUEST"


@requires_node
@pytest.mark.parametrize("stage", ["capture", "replay"])
def test_invalid_prompt_request_never_reflects_unknown_or_nested_secret_sentinels(stage):
    request, binding = capture_prompt()
    sentinels = ["SYN_SECRET_ID_37", "SYN_SECRET_REQUIREMENT_37", "SYN_SECRET_SOURCE_37",
                 "SYN_SECRET_UNKNOWN_37", "SYN_SECRET_PROMPT_37", "SYN_SECRET_REPLY_37"]
    invalid = {**request, "request_id": sentinels[0], "requirement": sentinels[1],
               "source_text": sentinels[2], "unknown": {"nested": sentinels[3]}}
    if stage == "replay":
        binding["system"] = sentinels[4]
        invalid = replay_frame(invalid, binding, sentinels[5])
    code, result = invoke(invalid)
    assert code == 2 and result["status"] == "INVALID_REQUEST"
    assert "input" not in result and result["request_id"] is None and result["stage"] is None
    serialized = json.dumps(result, ensure_ascii=False)
    assert all(sentinel not in serialized for sentinel in sentinels)


@requires_node
def test_binding_mismatch_receipt_does_not_reflect_prompt_material_or_reply():
    request, binding = capture_prompt()
    altered = {**request, "source_text": "SYN_SECRET_MATERIAL_91"}
    binding["system"] = "SYN_SECRET_PROMPT_91"
    replay = replay_frame(altered, binding, "SYN_SECRET_REPLY_91")
    code, result = invoke(replay)
    assert code == 2 and result["status"] == "BINDING_MISMATCH"
    serialized = json.dumps(result, ensure_ascii=False)
    assert all(sentinel not in serialized for sentinel in ("SYN_SECRET_MATERIAL_91", "SYN_SECRET_PROMPT_91", "SYN_SECRET_REPLY_91"))


@requires_node
def test_repaired_responses_are_admitted_only_with_a_declared_transformation():
    request, binding = capture_prompt()
    repaired_marks = ["UPSTREAM_JSON_REPAIRED", "UPSTREAM_NORMALIZATIONS_UNRECONSTRUCTED"]
    # A reply the donor can repair but that carries no usable outline data stays
    # out: repair is admitted, an unusable course is not.
    unusable = '{"outlines":[],}'
    code, rejected = invoke(replay_frame(request, binding, unusable))
    assert code == 2 and rejected["status"] == "UPSTREAM_RESULT_NOT_ADMITTED"
    assert rejected["data"] is None and rejected["original_reply"] == unusable
    assert rejected["transformations"] == repaired_marks
    assert rejected["differences"][0]["kind"] == "OUTLINE_COUNT_OR_SHAPE_UNSUPPORTED"
    # A code-fenced but complete reply is what a real local model returns; it is
    # admitted as a candidate that says the model bytes were not exact JSON and
    # that the donor's normalisations could not be enumerated.
    fenced = (
        "```json\n"
        '{"languageDirective":"Teach in Chinese.","courseTitle":"间隔复习入门",'
        '"outlines":[{"id":"scene_1","type":"slide","title":"原理","description":"讲解原理",'
        '"keyPoints":["概念","依据"],"order":1}]}'
        "\n```"
    )
    code, admitted = invoke(replay_frame(request, binding, fenced))
    assert code == 0 and admitted["status"] == "CANDIDATE"
    assert admitted["exact_json_output"] is False
    assert admitted["transformations"] == repaired_marks
    assert admitted["data"]["outlines"][0]["id"] == "scene_1"
    duplicate = '{"outlines":[],"outl\\u0069nes":[]}'
    code, result = invoke(replay_frame(request, binding, duplicate))
    assert code == 2 and result["status"] == "INVALID_RESPONSE" and result["data"] is None


@requires_node
@pytest.mark.parametrize("change,kind", [
    ({"unknown": "retained only in raw response"}, "UNKNOWN_OUTLINE_FIELDS"),
    ({"mediaGenerations": "not-an-array"}, "INVALID_MEDIA_GENERATIONS_DROPPED"),
    ({"order": 99}, "OUTLINE_ORDER_OVERWRITTEN"),
])
def test_unknown_or_lost_outline_data_is_preserved_but_never_admitted(change, kind):
    request, binding = capture_prompt()
    original = {"id": "one", "type": "quiz", "title": "T", "description": "D", "keyPoints": [],
                "order": 1, **change}
    raw = json.dumps({"languageDirective": "中文", "outlines": [original]}, ensure_ascii=False)
    replay = replay_frame(request, binding, raw)
    code, result = invoke(replay)
    assert code == 2 and result["status"] == "UPSTREAM_RESULT_NOT_ADMITTED" and result["data"] is None
    assert result["original_reply"] == raw and result["observed_upstream"]["outlines"][0]["id"] == "one"
    assert kind in {difference["kind"] for difference in result["differences"]}


@requires_node
def test_unknown_root_field_and_course_title_trimming_are_reported_and_not_admitted():
    request, binding = capture_prompt()
    outline = {"id": "one", "type": "quiz", "title": "T", "description": "D", "keyPoints": [], "order": 1}
    reply = {"languageDirective": "中文", "courseTitle": "  标题  ", "outlines": [outline],
             "unknownRoot": "not discarded silently"}
    replay = replay_frame(request, binding, json.dumps(reply, ensure_ascii=False))
    code, result = invoke(replay)
    assert code == 2 and result["status"] == "UPSTREAM_RESULT_NOT_ADMITTED" and result["original_reply"] == replay["reply"]["value"]
    assert result["observed_upstream"]["courseTitle"] == "标题" and result["data"] is None
    assert {item["kind"] for item in result["differences"]} == {"UNKNOWN_RESPONSE_FIELDS", "COURSE_TITLE_NORMALIZED"}


@requires_node
def test_duplicate_outline_ids_are_quarantined_with_the_actual_upstream_output():
    request, binding = capture_prompt()
    first = {"id": "same", "type": "quiz", "title": "First", "description": "D1", "keyPoints": [], "order": 1}
    second = {"id": "same", "type": "quiz", "title": "Second", "description": "D2", "keyPoints": [], "order": 2}
    raw = json.dumps({"languageDirective": "中文", "outlines": [first, second]}, ensure_ascii=False)
    code, result = invoke(replay_frame(request, binding, raw))
    assert code == 2 and result["status"] == "UPSTREAM_RESULT_NOT_ADMITTED" and result["data"] is None
    assert result["original_reply"] == raw
    assert [item["id"] for item in result["observed_upstream"]["outlines"]] == ["same", "same"]
    assert {"kind": "DUPLICATE_OUTLINE_ID", "outline_index": 1, "first_outline_index": 0, "id": "same"} in result["differences"]
