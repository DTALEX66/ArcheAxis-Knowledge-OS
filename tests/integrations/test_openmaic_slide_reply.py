"""Synthetic checks for the unregistered upstream text-reply candidate."""
from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path

import pytest

from scripts.release.tauri_portable_candidate import native
from tests.integrations.test_openmaic_interactive_url_map import digest, read_bytes, write_new
from tests.integrations.test_openmaic_slide_normalize import raw_call

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/learning-providers/openmaic"
WORKER = SERVICE / "slide-reply-worker.mjs"
WORKER_SHA256 = "3281029743fcd71673d5b2fbc6aadf3324edc3d66ac0cfa8eb0e28ba73ace0eb"
NODE = os.environ.get("ARCHEAXIS_TEST_NODE")
requires_node = pytest.mark.skipif(not NODE, reason="explicit preverified ARCHEAXIS_TEST_NODE is required")
GEN = "vendor/scene-content-0.3.28-original/generation"
DSL = "vendor/scene-content-0.3.28-original/dsl"
NPM = "vendor/npm/jsonrepair-3.13.3"
FILES = {
    GEN: {
        "ORIGINALS.json": "5679a80166d41114448ab35a1e2128a56baca7c9611218af590c81f3889d1ce3",
        "package.json": "5308b268d06dd27e592de00f02d57b046588df0d6e160f4179788388d5a806d1",
        "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
        "src/json-repair.ts": "dd0cfb6b1224e28c0e96ac5437e06074f5159ab5ec2cb93d4c81784bafcbedff",
        "src/logger.ts": "f8fd9136c2d5a31881c7c00d8a1f1804ba04af5f9d76c85888296e2d0b481306",
    },
    DSL: {
        "ORIGINALS.json": "c7564a5741c0807834ebcf77779a50590b927fa8b7e93f49494d1ef8eac6c317",
        "package.json": "847c2f4054034aab29586171872cb64a0f0b4e39db8dd9b8c50cff5e67014c98",
        "LICENSE": "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
        "src/normalize.ts": "e4f21f3273d9d65dadd53768afc5049b5473d087d1c525ea804c3d057b5ecf06",
        "src/stage.ts": "b8ce1ac2cff5a37e7fee7b23a1eb4df59499f0357366d80166163d7b32a9fc6a",
    },
    NPM: {
        "SOURCE.json": "11533c9ff27380455269407795ca6dd72a9c997ae4b4efa0285110ac23e60453",
        "LICENSE.md": "fd50f5abb7eeb614c8d1293b9f239a5238d7536e3a9a9a8929a082c82d12b3fd",
        "package.json": "34af00e07186a9ca212bd1065572bbc8d961937728f1a32551ed9016e0e01f41",
        "lib/esm/index.js": "523d175b61d8517fd3ba90cd2f065c6ecd45f4c95ea7ac706a9d87ccaceb7faf",
        "lib/esm/regular/jsonrepair.js": "9b7d7367a763931855d1c962e998529f06c6e80a4a056dccb8ebdb96e1d68a1d",
        "lib/esm/utils/JSONRepairError.js": "760bbdf77243afe6da53aad48520423c2b3da2e15838ca89cb118e87067ef130",
        "lib/esm/utils/stringUtils.js": "d5e1065bc473e1c06c9ae2c70dae048175fe8b96c7749b00c267fe29f5c322c3",
    },
}


def encoded(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def frame(raw: bytes, private=False) -> bytes:
    return encoded({"schema": "archeaxis.openmaic-slide-reply/v1", "include_private": private,
                    "reply_utf8_base64": base64.b64encode(raw).decode("ascii")})


def example():
    return {"elements": [{"type": "text", "left": 60, "top": 50, "width": 880, "height": 76, "rotate": 0,
                           "content": "<p>合成文字 😀</p>", "defaultFontName": "", "defaultColor": ""},
                          {"type": "text", "id": "given_2", "left": 60, "top": 150, "width": 880,
                           "height": 130, "rotate": 0, "content": "第二项", "defaultFontName": "Arial"}],
            "background": {"type": "solid", "color": "#ffffff"}, "remark": "合成说明"}


def decode_blob(value):
    raw = base64.b64decode(value["utf8_base64"], validate=True)
    assert value["bytes"] == len(raw) and value["sha256"] == digest(raw)
    return raw


@pytest.fixture
def stage(tmp_path_factory):
    target = tmp_path_factory.mktemp("slide-reply") / "h"
    for package, members in FILES.items():
        for name, expected in members.items():
            raw = read_bytes((SERVICE / package).joinpath(*name.split("/")))
            assert digest(raw) == expected
            write_new((target / package).joinpath(*name.split("/")), raw)
    source = read_bytes(WORKER)
    assert digest(source) == WORKER_SHA256
    write_new(target / WORKER.name, source)
    return target


def run(stage, raw, *, private=False):
    code, result, output, stderr = raw_call(stage / WORKER.name, frame(raw, private))
    assert code == 0 and len(stderr) <= 8192
    return result, output


def test_original_member_manifests_and_licenses():
    for package, members in FILES.items():
        manifest_name = "SOURCE.json" if package == NPM else "ORIGINALS.json"
        manifest = json.loads(read_bytes(SERVICE / package / manifest_name))
        for name, expected in members.items():
            assert digest(read_bytes((SERVICE / package).joinpath(*name.split("/")))) == expected
            if name != manifest_name:
                declared = manifest["files"][name]["sha256"] if package == NPM else manifest["originals"][name]
                assert declared == expected
    assert json.loads(read_bytes(SERVICE / GEN / "package.json"))["license"] == "MIT"
    assert json.loads(read_bytes(SERVICE / DSL / "package.json"))["license"] == "MIT"
    assert json.loads(read_bytes(SERVICE / NPM / "package.json"))["license"] == "ISC"


@requires_node
def test_exact_reply_calls_original_parser_and_normalizer_without_assigning_ids(stage):
    raw = json.dumps(example(), ensure_ascii=False, indent=2).encode("utf-8")
    public, public_bytes = run(stage, raw)
    assert public["status"] == "CANDIDATE" and public["private"] is None
    assert "合成文字".encode() not in public_bytes
    result, _ = run(stage, raw, private=True)
    assert result["status"] == "CANDIDATE" and result["reason"] == "EXACT_TEXT_ELEMENTS_ONLY"
    assert result["scope"] == "CALLER_SUPPLIED_UNVERIFIED" and result["model_call"] == "NOT_INVOKED"
    assert result["full_scene_generation"] == "NOT_PERFORMED" and result["core_authorization"] == "NOT_ESTABLISHED"
    assert result["rendering"] == "NOT_PERFORMED" and result["sanitization"] == "NOT_PERFORMED"
    assert result["content_trust"] == "UNTRUSTED"
    detail = result["private"]
    assert decode_blob(detail["reply"]) == raw
    assert detail["upstream_observation"]["state"] == "SERIALIZED_UPSTREAM_VALUE"
    assert json.loads(decode_blob(detail["upstream_observation"]["value"])) == example()
    expected = copy.deepcopy(example())
    expected["elements"][0]["defaultFontName"] = "Microsoft YaHei"
    expected["elements"][0]["defaultColor"] = "#333333"
    expected["elements"][1]["defaultColor"] = "#333333"
    assert json.loads(decode_blob(detail["normalized"])) == expected
    assert "id" not in expected["elements"][0] and expected["elements"][1]["id"] == "given_2"
    assert detail["semantic_changes"] == [
        {"path": "/elements/0/defaultFontName", "kind": "EMPTY_REPLACED_WITH_DEFAULT"},
        {"path": "/elements/0/defaultColor", "kind": "EMPTY_REPLACED_WITH_DEFAULT"},
        {"path": "/elements/1/defaultColor", "kind": "ABSENT_FILLED_WITH_DEFAULT"},
    ]
    assert detail["diagnostic_counts"] == {"debug": 0, "info": 0, "warn": 0, "error": 0}


@requires_node
def test_text_content_is_preserved_not_sanitized_or_rendered(stage):
    value = example()
    value["elements"][0]["content"] = '<p>inert</p><script>globalThis.SYNTHETIC_SIDE_EFFECT=1</script>'
    result, _ = run(stage, encoded(value), private=True)
    assert result["status"] == "CANDIDATE" and result["sanitization"] == "NOT_PERFORMED"
    assert result["rendering"] == "NOT_PERFORMED" and result["content_trust"] == "UNTRUSTED"
    output = json.loads(decode_blob(result["private"]["normalized"]))
    assert output["elements"][0]["content"] == value["elements"][0]["content"]


@requires_node
def test_canonical_decimal_is_not_claimed_to_be_exact_binary(stage):
    value = example()
    value["elements"][0]["width"] = 0.1
    result, _ = run(stage, encoded(value), private=True)
    assert result["status"] == "CANDIDATE"
    assert json.loads(decode_blob(result["private"]["normalized"]))["elements"][0]["width"] == 0.1


@requires_node
def test_original_parser_extracts_fenced_json_but_candidate_quarantines_it(stage):
    original = encoded(example())
    raw = b"SYNTHETIC_PRIVATE_BEFORE\n```json\n" + original + b"\n```\nSYNTHETIC_PRIVATE_AFTER"
    result, output = run(stage, raw)
    assert result["status"] == "QUARANTINED" and result["reason"] == "NONEXACT_OR_AMBIGUOUS_JSON"
    assert b"SYNTHETIC_PRIVATE" not in output and result["private"] is None
    result, _ = run(stage, raw, private=True)
    detail = result["private"]
    assert decode_blob(detail["reply"]) == raw
    assert detail["upstream_observation"]["state"] == "SERIALIZED_UPSTREAM_VALUE"
    assert json.loads(decode_blob(detail["upstream_observation"]["value"])) == example()
    assert detail["diagnostic_counts"]["debug"] >= 1 and "normalized" not in detail


@requires_node
def test_failed_upstream_diagnostics_do_not_leak_reply_to_stdout_or_stderr(stage):
    # The original parser's terminal failure passes raw first/last fragments to
    # its logger. The fixed logger must count these calls without emitting them.
    secret = b"SYNTHETIC_PRIVATE_LOG_SENTINEL"
    # jsonrepair accepts string concatenation, so use a malformed Unicode
    # escape inside a string with trailing bytes; this must not be truncated.
    raw = b'{"value":"' + secret + b'_\\uZZZZ_WITH_TRAILING_TEXT"}'
    code, result, stdout, stderr = raw_call(stage / WORKER.name, frame(raw))
    assert code == 0 and result["status"] == "QUARANTINED" and result["reason"] == "UPSTREAM_NULL"
    assert result["private"] is None and secret not in stdout and secret not in stderr
    code, result, _stdout, stderr = raw_call(stage / WORKER.name, frame(raw, True))
    assert code == 0 and secret not in stderr
    assert result["status"] == "QUARANTINED" and result["reason"] == "UPSTREAM_NULL"
    detail = result["private"]
    assert decode_blob(detail["reply"]) == raw
    assert detail["upstream_observation"]["state"] == "UPSTREAM_NULL"
    assert detail["diagnostic_counts"]["warn"] > 0 and detail["diagnostic_counts"]["error"] >= 3


@requires_node
def test_duplicate_keys_are_observed_but_never_silently_admitted(stage):
    raw = encoded(example()).replace(b'"content":"<p>', b'"content":"SYNTHETIC_FIRST","content":"<p>', 1)
    assert raw.count(b'"content"') == 3
    result, _ = run(stage, raw, private=True)
    assert result["status"] == "QUARANTINED" and result["reason"] == "NONEXACT_OR_AMBIGUOUS_JSON"
    detail = result["private"]
    assert decode_blob(detail["reply"]) == raw
    observed = json.loads(decode_blob(detail["upstream_observation"]["value"]))
    assert observed["elements"][0]["content"] == example()["elements"][0]["content"]
    assert "normalized" not in detail


@pytest.mark.parametrize("mode", ["noncanonical_number", "overflow", "truncated"])
@requires_node
def test_repair_or_inexact_numeric_input_retains_raw_but_is_quarantined(stage, mode):
    raw = encoded(example())
    if mode == "noncanonical_number": raw = raw.replace(b'"left":60', b'"left":60.0', 1)
    if mode == "overflow": raw = raw.replace(b'"left":60', b'"left":1e999', 1)
    if mode == "truncated": raw = raw[:-1]
    result, _ = run(stage, raw, private=True)
    assert result["status"] == "QUARANTINED"
    assert decode_blob(result["private"]["reply"]) == raw
    assert "normalized" not in result["private"]
    if mode == "overflow": assert result["private"]["upstream_observation"]["state"] == "UNREPRESENTABLE"


@pytest.mark.parametrize("mode", ["unknown", "image", "nonzero_rotation", "duplicate_id", "bad_geometry", "empty_elements"])
@requires_node
def test_unknown_or_unsupported_data_is_preserved_and_rejected(stage, mode):
    value = example()
    if mode == "unknown": value["SYNTHETIC_PRIVATE_FIELD"] = "do not echo"
    if mode == "image": value["elements"][0]["type"] = "image"
    if mode == "nonzero_rotation": value["elements"][0]["rotate"] = 3
    if mode == "duplicate_id": value["elements"][0]["id"] = "given_2"
    if mode == "bad_geometry": value["elements"][0]["width"] = 0
    if mode == "empty_elements": value["elements"] = []
    raw = encoded(value)
    result, output = run(stage, raw)
    assert result["status"] == "QUARANTINED" and result["reason"] == "UNSUPPORTED_SLIDE_REPLY"
    assert b"SYNTHETIC_PRIVATE_FIELD" not in output
    result, _ = run(stage, raw, private=True)
    assert decode_blob(result["private"]["reply"]) == raw and "normalized" not in result["private"]


@requires_node
def test_invalid_utf8_is_retained_only_on_private_request(stage):
    raw = b"SYNTHETIC_PRIVATE\xff"
    result, output = run(stage, raw)
    assert result["status"] == "QUARANTINED" and result["reason"] == "INVALID_REPLY_UTF8"
    assert result["private"] is None and b"SYNTHETIC_PRIVATE" not in output
    result, _ = run(stage, raw, private=True)
    assert decode_blob(result["private"]["reply"]) == raw
    assert result["private"]["upstream_observation"] == "NOT_INVOKED"


@pytest.mark.parametrize(("package", "name"), [
    (GEN, "src/json-repair.ts"), (GEN, "src/logger.ts"), (DSL, "src/normalize.ts"),
    (DSL, "src/stage.ts"), (NPM, "lib/esm/regular/jsonrepair.js"), (NPM, "SOURCE.json"),
])
@requires_node
def test_changed_original_or_dependency_is_rejected_without_echo(stage, package, name):
    target = (stage / package).joinpath(*name.split("/"))
    with open(native(target), "ab") as stream:
        stream.write(b"SYNTHETIC_TAMPER")
    result, output = run(stage, encoded(example()), private=True)
    assert result["status"] == "REJECTED" and result["reason"] == "SOURCE_IDENTITY_MISMATCH"
    assert result["private"] is None and b"SYNTHETIC_TAMPER" not in output


@requires_node
def test_invalid_outer_frame_does_not_echo_unknown_or_duplicate_fields(stage):
    raw = b'{"schema":"archeaxis.openmaic-slide-reply/v1","reply_utf8_base64":"e30=","include_private":true,"SYNTHETIC_PRIVATE":"x"}'
    code, result, output, _ = raw_call(stage / WORKER.name, raw)
    assert code == 0 and result["status"] == "REJECTED" and result["reason"] == "INVALID_REQUEST"
    assert result["private"] is None and b"SYNTHETIC_PRIVATE" not in output
    duplicate = b'{"schema":"archeaxis.openmaic-slide-reply/v1","reply_utf8_base64":"e30=","include_private":false,"include_private":true}'
    _, result, _, _ = raw_call(stage / WORKER.name, duplicate)
    assert result["status"] == "REJECTED" and result["reason"] == "INVALID_REQUEST"
    noncanonical = b'{"schema":"archeaxis.openmaic-slide-reply/v1","reply_utf8_base64":"e30","include_private":true}'
    _, result, _, _ = raw_call(stage / WORKER.name, noncanonical)
    assert result["status"] == "REJECTED" and result["reason"] == "INVALID_REQUEST"


@requires_node
def test_file_growth_during_identity_check_does_not_expand_read(stage):
    # Instrumented test-only copy: grow a staged donor after fstat, record
    # actual reads on that fd, and flag any unbounded whole-file read.
    source = read_bytes(stage / WORKER.name)
    anchor = b"    const bytes = Buffer.allocUnsafe(before.size + 1); let total = 0;"
    assert source.count(anchor) == 1
    injection = b'''    if (root === roots.gen && name === 'src/json-repair.ts') {
      fs.appendFileSync(file, Buffer.alloc(16384, 65));
      fs.writeFileSync('synthetic-growth-observed', 'yes');
      let observed = 0, calls = 0;
      const oldRead = fs.readSync.bind(fs), oldWhole = fs.readFileSync.bind(fs);
      fs.readSync = (...args) => {
        if (args[0] === fd && args[3] > before.size + 1 - observed)
          fs.writeFileSync('synthetic-read-bound-broken', 'oversized request');
        const count = oldRead(...args);
        if (args[0] === fd) {
          calls += 1; observed += count;
          fs.writeFileSync('synthetic-target-read.json', JSON.stringify({calls, bytes: observed}));
        }
        return count;
      };
      fs.readFileSync = (...args) => {
        if (args[0] === fd) fs.writeFileSync('synthetic-read-bound-broken', 'whole file read');
        return oldWhole(...args);
      };
    }
'''
    probe = stage / "synthetic-growing-source.mjs"
    write_new(probe, source.replace(anchor, injection + anchor))
    target = stage / GEN / "src/json-repair.ts"
    original_size = len(read_bytes(target))
    _, result, output, _ = raw_call(probe, frame(encoded(example()), True))
    assert result["status"] == "REJECTED" and result["reason"] == "SOURCE_IDENTITY_MISMATCH"
    assert os.path.exists(native(stage / "synthetic-growth-observed"))
    assert len(read_bytes(target)) == original_size + 16384
    observed = json.loads(read_bytes(stage / "synthetic-target-read.json"))
    assert type(observed["calls"]) is int and observed["calls"] > 0
    assert observed["bytes"] == original_size + 1
    assert not os.path.exists(native(stage / "synthetic-read-bound-broken"))
    assert b"synthetic-growth-observed" not in output


@requires_node
def test_changed_node_digest_cannot_be_mistaken_for_fixed_runtime(stage):
    source = read_bytes(stage / WORKER.name)
    expected = b"ba4e6d110e8c1592a1ecd390f6b05f3da124b13871a5be62b341a07a853c6c32"
    assert source.count(expected) == 1
    probe = stage / "synthetic-wrong-node-hash.mjs"
    write_new(probe, source.replace(expected, b"0" * 64))
    _, result, _, _ = raw_call(probe, frame(encoded(example())))
    assert result["status"] == "REJECTED" and result["reason"] == "NODE_IDENTITY_MISMATCH"
