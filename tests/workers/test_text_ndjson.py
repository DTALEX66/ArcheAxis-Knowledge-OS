"""Real-process text NDJSON and staging-boundary regression tests."""

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/python-workers/transport/text_ndjson.py"
SCHEMA_NAMES = ["archeaxis.text/v1", "archeaxis.document-structure/v1", "archeaxis.loss-receipt/v1"]


class TextNdjsonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)
        self.staging = Path(self.tmp.name)
        (self.staging / "input").mkdir()
        (self.staging / "output").mkdir()
        schema = json.loads((ROOT / "packages/contracts/v1/worker-protocol.schema.json").read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema)

    def request(self, raw=b"first\r\nsecond\n"):
        digest = hashlib.sha256(raw).hexdigest()
        (self.staging / "input" / digest).write_bytes(raw)
        return {"schema": "archeaxis.worker-request/v1", "type": "job_request",
                "request_id": "request-1", "job_id": "job-1", "attempt": 1, "protocol_minor": 0,
                "capability": "text.extract", "capability_version": "1", "deadline_ms": 30000,
                "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": "text/plain"}],
                "parameters": {}}

    def invoke(self, request, *, ascii_stdio=False):
        self.assertTrue(SCRIPT.is_file(), "text NDJSON transport is not implemented")
        line = request if isinstance(request, str) else json.dumps(request)
        # -S proves the production wrapper needs no installed site-packages.
        command = [sys.executable, "-B", "-S", str(SCRIPT), "--staging-root", str(self.staging)]
        # Pass a child-only environment override; never mutate global settings.
        child_env = dict(os.environ, PYTHONIOENCODING="ascii") if ascii_stdio else None
        result = subprocess.run(command, input=line + "\n", capture_output=True,
                                text=True, encoding="utf-8", timeout=30, check=False,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=child_env)
        self.assertEqual(len(result.stdout.splitlines()), 2, result.stdout + result.stderr)
        hello, response = map(json.loads, result.stdout.splitlines())
        self.validator.validate(hello)
        self.validator.validate(response)
        self.assertEqual(hello["capabilities"], ["text.extract"])
        self.assertEqual(hello["schemas"], SCHEMA_NAMES)
        return result, response

    def assert_rejected(self, request):
        _, response = self.invoke(request)
        self.assertEqual(response["status"], "rejected")
        self.assertEqual(response["outputs"], [])
        self.assertFalse(response["error"]["retryable"])
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_real_process_preserves_three_independent_outputs_and_content_hashes(self):
        raw = b"\xef\xbb\xbf" + b"x\r" * 5001
        request = self.request(raw)
        process, response = self.invoke(request)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        self.assertEqual({o["kind"] for o in response["outputs"]}, {"text", "document_structure", "loss_report"})
        payloads = {}
        for output in response["outputs"]:
            self.assertEqual(output["authority_effect"], "candidate_or_measurement_only")
            self.assertEqual(output["uri"], f"job://output/{output['sha256']}")
            data = (self.staging / "output" / output["sha256"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), output["sha256"])
            self.assertEqual(len(data), output["byte_length"])
            payloads[output["kind"]] = data
        self.assertEqual(payloads["text"], b"x\r" * 5001)
        self.assertEqual(len(json.loads(payloads["document_structure"])), 5000)
        loss = json.loads(payloads["loss_report"])
        self.assertEqual((loss["covered"], loss["total"]), (5000, 5001))
        self.assertEqual(len(loss["losses"]), 2)
        # Identical requests reuse verified content-addressed artifacts.
        _, replay = self.invoke(request)
        self.assertEqual(response["outputs"], replay["outputs"])

    def test_real_process_works_from_portable_green_worker_layout(self):
        portable = self.staging / "candidate"
        script = portable / "workers" / "transport" / "text_ndjson.py"
        script.parent.mkdir(parents=True)
        shutil.copy2(SCRIPT, script)
        worker = portable / "workers" / "document" / "worker_text.py"
        worker.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "services/python-workers/document/worker_text.py", worker)

        request = self.request(b"portable candidate\n")
        result = subprocess.run(
            [sys.executable, "-B", "-S", str(script), "--staging-root", str(self.staging)],
            input=json.dumps(request) + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        hello, response = map(json.loads, result.stdout.splitlines())
        self.validator.validate(hello)
        self.validator.validate(response)
        self.assertEqual(response["status"], "succeeded")

    def test_unknown_capability_versions_attempt_and_parameters_are_rejected(self):
        request = self.request()
        for field, value in [("capability", "shell.execute"), ("capability_version", "2"),
                             ("schema", "archeaxis.worker-request/v2"), ("protocol_minor", 1),
                             ("attempt", 0), ("attempt", True), ("attempt", 1.5),
                             ("deadline_ms", 0), ("parameters", {"destination": "outside"})]:
            with self.subTest(field=field, value=value):
                self.assert_rejected({**request, field: value})
        for invalid in ({**request, "extra": True}, {**request, "inputs": {}},
                        {**request, "parameters": []}, {**request, "request_id": 1},
                        {**request, "inputs": [{**request["inputs"][0], "path": "outside"}]}):
            self.assert_rejected(invalid)

    def test_path_injection_mismatched_uri_and_changed_input_hash_are_rejected(self):
        request = self.request()
        for uri in ("job://input/../../secret", "file:///E:/secret", "job://input/" + "b" * 64):
            with self.subTest(uri=uri):
                invalid = {**request, "inputs": [{**request["inputs"][0], "uri": uri}]}
                self.assert_rejected(invalid)
        (self.staging / "input" / request["inputs"][0]["sha256"]).write_bytes(b"tampered")
        self.assert_rejected(request)

    def test_duplicate_keys_nonfinite_and_oversized_lines_are_rejected(self):
        request = self.request()
        line = json.dumps(request)
        for malformed in (line.replace('"attempt": 1', '"attempt": 1, "attempt": 2'),
                          line.replace('"deadline_ms": 30000', '"deadline_ms": NaN'),
                          line.replace('"deadline_ms": 30000', '"deadline_ms": Infinity'),
                          "x" * (1024 * 1024 + 1)):
            with self.subTest(prefix=malformed[:40]):
                self.assert_rejected(malformed)

    def test_hardlinked_input_is_rejected(self):
        request = self.request()
        os.link(self.staging / "input" / request["inputs"][0]["sha256"], self.staging / "alias")
        self.assert_rejected(request)

    def test_symlink_or_junction_input_directory_is_rejected(self):
        target = self.staging / "linked-input"
        (self.staging / "input").rename(target)
        link = self.staging / "input"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=False,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.assertEqual(result.returncode, 0, result.stderr)
        # Write only to the known regular target when preparing the fixture.
        raw = b"safe fixture"
        digest = hashlib.sha256(raw).hexdigest()
        (target / digest).write_bytes(raw)
        request = {"schema": "archeaxis.worker-request/v1", "type": "job_request", "request_id": "r", "job_id": "j",
                   "attempt": 1, "protocol_minor": 0, "capability": "text.extract", "capability_version": "1",
                   "deadline_ms": 30000, "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": "text/plain"}], "parameters": {}}
        self.assert_rejected(request)

    def test_decode_failure_has_no_success_outputs(self):
        _, response = self.invoke(self.request(b"\xff\xfe\x01"))
        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["outputs"], [])
        self.assertIsNotNone(response["error"])
        self.assertEqual(response["error"]["code"], "AAK-WORKER-003")
        self.assertFalse(response["error"]["retryable"])

    def test_error_catalog_classifies_validation_version_size_media_and_hash(self):
        request = self.request()
        asset = request["inputs"][0]
        cases = [
            ({**request, "attempt": 0}, "AAK-VAL-001"),
            ({**request, "type": "wrong"}, "AAK-VAL-001"),
            ({**request, "capability": "unknown"}, "AAK-VAL-001"),
            ({**request, "inputs": [{**asset, "uri": "job://input/../private"}]}, "AAK-VAL-001"),
            ({**request, "inputs": [{**asset, "media_type": "application/unknown"}]}, "AAK-VAL-002"),
            ({**request, "schema": "archeaxis.worker-request/v2"}, "AAK-PROTO-001"),
            ({**request, "capability_version": "2"}, "AAK-PROTO-001"),
            ({**request, "protocol_minor": 1}, "AAK-PROTO-001"),
            ("x" * (1024 * 1024 + 1), "AAK-VAL-003"),
            ("not json", "AAK-VAL-001"),
        ]
        for invalid, code in cases:
            with self.subTest(code=code, request=str(invalid)[:120]):
                _, response = self.invoke(invalid)
                self.assertEqual(response["error"]["code"], code)
                self.assertFalse(response["error"]["retryable"])
                self.assertEqual(response["outputs"], [])
        source = self.staging / "input" / asset["sha256"]
        for raw, code in ((b"changed", "AAK-HASH-001"),
                          (b"x" * (16 * 1024 * 1024 + 1), "AAK-VAL-003")):
            with self.subTest(file_error=code):
                source.write_bytes(raw)
                _, response = self.invoke(request)
                self.assertEqual(response["error"]["code"], code)
                self.assertFalse(response["error"]["retryable"])
                self.assertEqual(response["outputs"], [])

    def test_existing_output_collision_and_hardlink_are_not_overwritten(self):
        raw = b"existing object must be immutable"
        request = self.request(raw)
        path = self.staging / "output" / hashlib.sha256(raw).hexdigest()
        path.write_bytes(b"wrong bytes")
        _, response = self.invoke(request)
        self.assertEqual(response["status"], "rejected")
        self.assertEqual(response["outputs"], [])
        self.assertEqual(path.read_bytes(), b"wrong bytes")
        self.assertEqual(response["error"]["code"], "AAK-HASH-001")
        path.write_bytes(raw)
        os.link(path, self.staging / "output-alias")
        _, response = self.invoke(request)
        self.assertEqual(response["status"], "rejected")
        self.assertEqual(response["outputs"], [])
        self.assertEqual(path.read_bytes(), raw)

    def test_media_input_budget_is_real_and_does_not_expand_text_or_probe(self):
        spec = importlib.util.spec_from_file_location("media_budget_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw = b"x" * (26 * 1024 * 1024)
        request = self.request(raw)
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        with self.assertRaises(module.Rejected):
            module.read_regular(source)
        for capability, media_type in [("media.transcribe", "audio/mpeg"), ("media.video", "video/mp4")]:
            media = {**request, "capability": capability, "inputs": [{**request["inputs"][0], "media_type": media_type}]}
            with patch.object(module, "_run_route", return_value={"text": "SIMULATED budget fixture", "structure": [], "loss_receipt": {}}):
                response = module.execute(media, self.staging)
            self.assertEqual(len(response[0]), 3)
        for capability in ["text.extract", "media.probe", "image.ocr", "unknown"]:
            self.assertEqual(module.input_byte_limit(capability), 16 * 1024 * 1024)
        self.assertEqual(module.MAX_LINE_BYTES, 1024 * 1024)

    def test_over_media_budget_is_rejected_before_read_or_worker(self):
        spec = importlib.util.spec_from_file_location("media_budget_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        request = self.request()
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        with source.open("wb") as handle:
            handle.truncate(64 * 1024 * 1024 + 1)
        media = {**request, "capability": "media.transcribe", "inputs": [{**request["inputs"][0], "media_type": "audio/mpeg"}]}
        with patch.object(module, "_run_route") as worker:
            with self.assertRaises(module.Rejected) as caught:
                module.execute(media, self.staging)
        self.assertEqual(caught.exception.code, "AAK-VAL-003")
        worker.assert_not_called()

    def test_relative_deadline_is_checked_before_parser_and_produces_no_outputs(self):
        request = self.request()
        self.assertTrue(SCRIPT.is_file(), "text NDJSON transport is not implemented")
        spec = importlib.util.spec_from_file_location("text_ndjson", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module.time, "monotonic", side_effect=[0.0, 31.0]):
            with self.assertRaises(TimeoutError):
                module.execute(request, self.staging)
        self.assertEqual(list((self.staging / "output").iterdir()), [])
        # Exercise the real main boundary with a controlled monotonic clock.
        stdin = io.TextIOWrapper(io.BytesIO((json.dumps(request) + "\n").encode("utf-8")))
        stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        with patch.object(module.time, "monotonic", side_effect=[0.0, 31.0]), \
                patch.object(module.sys, "stdin", stdin), patch.object(module.sys, "stdout", stdout), \
                patch.object(module.sys, "argv", [str(SCRIPT), "--staging-root", str(self.staging)]):
            exit_code = module.main()
            response = json.loads(stdout.buffer.getvalue().splitlines()[1])
        self.validator.validate(response)
        self.assertEqual(exit_code, 1)
        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["error"]["code"], "AAK-WORKER-002")
        self.assertTrue(response["error"]["retryable"])
        self.assertEqual(response["outputs"], [])

    def test_utf8_response_ids_work_with_ascii_child_stdio(self):
        request = self.request("中文原文 😀\r\n".encode("utf-8"))
        request.update(request_id="请求😀", job_id="任务🚀")
        result, response = self.invoke(request, ascii_stdio=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((response["request_id"], response["job_id"]), ("请求😀", "任务🚀"))
        self.assertEqual(response["status"], "succeeded")

    def test_mathematical_json_integers_are_normalized_and_bounded(self):
        request = self.request()
        line = json.dumps(request).replace('"attempt": 1', '"attempt": 2e0').replace(
            '"protocol_minor": 0', '"protocol_minor": 0.0').replace('"deadline_ms": 30000', '"deadline_ms": 30000.0')
        _, response = self.invoke(line)
        self.assertEqual(response["status"], "succeeded", response)
        self.assertEqual(response["attempt"], 2)
        self.assertIs(type(response["attempt"]), int)
        for field in ("attempt", "deadline_ms", "protocol_minor"):
            for value in (True, 9007199254740992, 1.5):
                with self.subTest(field=field, value=value):
                    _, invalid = self.invoke({**request, field: value})
                    self.assertEqual(invalid["status"], "rejected")
                    self.assertEqual(invalid["outputs"], [])


    def test_decode_and_anchor_matrix_has_independent_expectations(self):
        # DS04: table-driven decode/anchor cases with hand-written expectations
        # (never copy output back as the expectation). Raw bytes -> expected
        # decoded text (UTF-8), preserving line endings and combining/emoji.
        # Expected anchor ranges are Unicode character offsets into the projected
        # text, not UTF-8 byte offsets; they are written by hand, not derived from
        # the production algorithm.
        expected_ranges = {
            "ascii": [(0, 5)],
            "chinese": [(0, 2)],
            "nfd_combining_preserved": [(0, 3)],
            "astral_emoji": [(0, 1)],
            "utf8_bom_stripped": [(0, 2)],
            "utf16le_bom": [(0, 2)],
            "crlf_and_lone_cr_preserved": [(0, 3), (3, 5), (5, 7)],
            "empty_file": [],
            "gbk_fallback": [(0, 2)],
            "invalid_bytes_replaced": [(0, 3)],
        }
        # b"\x81\xff\x81" survives UTF-8/GBK/cp1252 and lands in UTF-8 replace:
        # three U+FFFD replacement characters.
        expected_invalid_text = b"\xef\xbf\xbd" * 3
        cases = [
            # (name, raw, expected_text_utf8, expected_decode, expect_empty_note)
            ("ascii", b"plain", b"plain", "utf-8", False),
            ("chinese", "\u4e2d\u6587".encode("utf-8"), "\u4e2d\u6587".encode("utf-8"), "utf-8", False),
            ("nfd_combining_preserved", b"e\xcc\x81a", b"e\xcc\x81a", "utf-8", False),
            ("astral_emoji", "\U0001f600".encode("utf-8"), "\U0001f600".encode("utf-8"), "utf-8", False),
            ("utf8_bom_stripped", b"\xef\xbb\xbfhi", b"hi", "utf-8-sig", False),
            ("utf16le_bom", b"\xff\xfe" + "AB".encode("utf-16-le"), b"AB", "utf-16", False),
            ("crlf_and_lone_cr_preserved", b"a\r\nb\rc\n", b"a\r\nb\rc\n", "utf-8", False),
            ("empty_file", b"", b"", "utf-8", True),
            ("gbk_fallback", "\u4e2d\u6587".encode("gbk"), "\u4e2d\u6587".encode("utf-8"), "gbk", False),
            ("invalid_bytes_replaced", b"\x81\xff\x81", expected_invalid_text, "utf-8-replace", False),
        ]
        for name, raw, expected_text, expected_decode, empty_note in cases:
            with self.subTest(name=name):
                request = self.request(raw)
                process, response = self.invoke(request)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(response["status"], "succeeded", response)
                payloads = {}
                for output in response["outputs"]:
                    payloads[output["kind"]] = (self.staging / "output" / output["sha256"]).read_bytes()
                # Precise text bytes: the replacement-decoding branch is asserted
                # as exact bytes, not just "non-empty and differs from raw".
                self.assertEqual(payloads["text"], expected_text, name)
                loss = json.loads(payloads["loss_report"])
                self.assertEqual(loss["params"]["decode"], expected_decode, name)
                if empty_note:
                    self.assertEqual(loss["total"], 0)
                    self.assertIn("no lines to anchor", loss["loss_note"])
                else:
                    # anchor coverage equals splitlines count; no silent line loss
                    self.assertEqual(loss["covered"], loss["total"])
                    self.assertEqual(loss["coverage"], 1.0)
                if name == "invalid_bytes_replaced":
                    # The receipt must name U+FFFD replacement, not a silent fallback.
                    self.assertEqual(loss["losses"], ["undecodable bytes replaced with U+FFFD"])
                    self.assertIn("U+FFFD", loss["loss_note"])
                # Independent anchor expectations: hand-written character ranges,
                # generated in the same line order the worker projects.
                expected_structure = [
                    {"kind": "line", "path": [f"line-{i}"], "char_start": start, "char_end": end}
                    for i, (start, end) in enumerate(expected_ranges[name], start=1)
                ]
                structure = json.loads(payloads["document_structure"])
                self.assertEqual(structure, expected_structure, name)
                for idx, (anchor, (start, end)) in enumerate(zip(structure, expected_ranges[name], strict=True), start=1):
                    self.assertEqual(anchor["kind"], "line", name)
                    self.assertEqual(anchor["path"], [f"line-{idx}"], name)
                    self.assertEqual(anchor["char_start"], start, name)
                    self.assertEqual(anchor["char_end"], end, name)
                if expected_ranges[name]:
                    # Negative control: shifting one char_end must fail, proving the
                    # assertion does not merely mirror the production algorithm.
                    corrupted = [dict(anchor, char_end=anchor["char_end"] + 1) for anchor in expected_structure]
                    self.assertNotEqual(structure, corrupted, name)


    def test_subtitle_view_cannot_replace_the_verified_input(self):
        spec = importlib.util.spec_from_file_location("subtitle_view_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = b"1\n00:00:00,000 --> 00:00:01,000\nSYNTHETIC original A\n\n"
        other = b"1\n00:00:00,000 --> 00:00:01,000\nSYNTHETIC different B\n\n"
        request = self.request(original)
        request["capability"] = "subtitles.structure"
        request["inputs"][0]["media_type"] = "application/x-subrip"
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        view = source.with_name(source.name + ".srt")
        view.write_bytes(other)
        try:
            outputs, _, _ = module.execute(request, self.staging)
        except module.Rejected as exc:
            self.assertEqual(exc.code, "AAK-HASH-001")
        else:
            text = next(output for output in outputs if output["kind"] == "text")
            observed = (self.staging / "output" / text["sha256"]).read_bytes()
            self.fail(f"accepted a different subtitle view and produced {observed!r}")
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(view.read_bytes(), other)
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_video_media_type_normalization_reaches_the_same_route(self):
        from types import SimpleNamespace

        spec = importlib.util.spec_from_file_location("video_media_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw = b"SYNTHETIC video input; no decoder or model is invoked"
        request = self.request(raw)
        request["capability"] = "media.video"
        seen = []

        def synthetic_extract(path, *_args, **_kwargs):
            seen.append((Path(path).suffix, Path(path).read_bytes()))
            return {"text": "SYNTHETIC video result", "structure": [],
                    "loss_receipt": {}, "audio_wav": None, "frames": []}

        fake_worker = SimpleNamespace(extract_job=synthetic_extract)
        fake_spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _worker: None))
        with patch.object(module.importlib.util, "spec_from_file_location", return_value=fake_spec), \
                patch.object(module.importlib.util, "module_from_spec", return_value=fake_worker):
            for media_type in ("VIDEO/MP4", "video/mp4; codecs=avc1", " Video/Mp4 ; codecs=avc1 "):
                with self.subTest(media_type=media_type):
                    request["inputs"][0]["media_type"] = media_type
                    outputs, _, _ = module.execute(request, self.staging, self.staging)
                    self.assertEqual({item["kind"] for item in outputs},
                                     {"text", "document_structure", "loss_report"})
        self.assertEqual(seen, [(".mp4", raw)] * 3)

    def test_subtitle_view_creation_and_identical_reuse_preserve_bytes(self):
        spec = importlib.util.spec_from_file_location("subtitle_valid_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for existing in (False, True):
            with self.subTest(existing=existing):
                label = "existing" if existing else "new"
                raw = f"1\n00:00:00,000 --> 00:00:01,000\nSYNTHETIC {label}\n\n".encode()
                request = self.request(raw)
                request["capability"] = "subtitles.structure"
                request["inputs"][0]["media_type"] = "application/x-subrip"
                source = self.staging / "input" / request["inputs"][0]["sha256"]
                view = source.with_name(source.name + ".srt")
                if existing:
                    view.write_bytes(raw)
                    before = view.stat()
                outputs, _, _ = module.execute(request, self.staging)
                text = next(output for output in outputs if output["kind"] == "text")
                self.assertEqual((self.staging / "output" / text["sha256"]).read_bytes(),
                                 f"SYNTHETIC {label}\n".encode())
                self.assertEqual(source.read_bytes(), raw)
                self.assertEqual(view.read_bytes(), raw)
                if existing:
                    after = view.stat()
                    self.assertEqual((after.st_dev, after.st_ino, after.st_mtime_ns),
                                     (before.st_dev, before.st_ino, before.st_mtime_ns))

    def test_subtitle_view_changed_during_parser_is_rejected(self):
        spec = importlib.util.spec_from_file_location("subtitle_changed_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = b"1\n00:00:00,000 --> 00:00:01,000\nSYNTHETIC original\n\n"
        request = self.request(original)
        request["capability"] = "subtitles.structure"
        request["inputs"][0]["media_type"] = "application/x-subrip"
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        view = source.with_name(source.name + ".srt")
        adapt = module._as_route_contract

        def change_after_parser(result, capability):
            view.write_bytes(b"SYNTHETIC changed after parser")
            return adapt(result, capability)

        with patch.object(module, "_as_route_contract", side_effect=change_after_parser):
            with self.assertRaises(module.Rejected) as caught:
                module.execute(request, self.staging)
        self.assertEqual(caught.exception.code, "AAK-HASH-001")
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_subtitle_view_replaced_with_identical_bytes_is_rejected(self):
        spec = importlib.util.spec_from_file_location("subtitle_replaced_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw = b"1\n00:00:00,000 --> 00:00:01,000\nSYNTHETIC original\n\n"
        request = self.request(raw)
        request["capability"] = "subtitles.structure"
        request["inputs"][0]["media_type"] = "application/x-subrip"
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        view = source.with_name(source.name + ".srt")
        replacement = self.staging / "synthetic-replacement.srt"
        adapt = module._as_route_contract

        def replace_after_parser(result, capability):
            before = view.stat()
            replacement.write_bytes(raw)
            os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
            new = replacement.stat()
            if (before.st_dev, before.st_ino) == (new.st_dev, new.st_ino):
                self.skipTest("filesystem does not distinguish replacement file identities")
            os.replace(replacement, view)
            return adapt(result, capability)

        with patch.object(module, "_as_route_contract", side_effect=replace_after_parser):
            with self.assertRaises(module.Rejected) as caught:
                module.execute(request, self.staging)
        self.assertEqual(caught.exception.code, "AAK-HASH-001")
        self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(view.read_bytes(), raw)
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_oversized_subtitle_view_is_not_overwritten(self):
        spec = importlib.util.spec_from_file_location("subtitle_limit_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = b"1\n00:00:00,000 --> 00:00:01,000\nSYNTHETIC\n\n"
        request = self.request(original)
        request["capability"] = "subtitles.structure"
        request["inputs"][0]["media_type"] = "application/x-subrip"
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        view = source.with_name(source.name + ".srt")
        oversized = b"x" * 129
        view.write_bytes(oversized)
        with patch.object(module, "MAX_INPUT_BYTES", 128):
            with self.assertRaises(module.Rejected) as caught:
                module.execute(request, self.staging)
        self.assertEqual(caught.exception.code, "AAK-VAL-003")
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(view.read_bytes(), oversized)
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_hard_linked_subtitle_view_is_rejected_without_overwrite(self):
        spec = importlib.util.spec_from_file_location("subtitle_hardlink_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw = b"1\n00:00:00,000 --> 00:00:01,000\nSYNTHETIC\n\n"
        request = self.request(raw)
        request["capability"] = "subtitles.structure"
        request["inputs"][0]["media_type"] = "application/x-subrip"
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        view = source.with_name(source.name + ".srt")
        target = self.staging / "hardlink-target.srt"
        target.write_bytes(raw)
        try:
            os.link(target, view)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"hard links unavailable: {type(exc).__name__}")
        with self.assertRaises(module.Rejected):
            module.execute(request, self.staging)
        self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(target.read_bytes(), raw)
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_symlinked_subtitle_view_is_rejected_without_overwrite(self):
        spec = importlib.util.spec_from_file_location("subtitle_symlink_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw = b"1\n00:00:00,000 --> 00:00:01,000\nSYNTHETIC\n\n"
        request = self.request(raw)
        request["capability"] = "subtitles.structure"
        request["inputs"][0]["media_type"] = "application/x-subrip"
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        view = source.with_name(source.name + ".srt")
        target = self.staging / "symlink-target.srt"
        target.write_bytes(raw)
        try:
            view.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symbolic links unavailable: {type(exc).__name__}")
        with self.assertRaises(module.Rejected):
            module.execute(request, self.staging)
        self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(target.read_bytes(), raw)
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_all_suffix_route_branches_recheck_the_view_after_worker(self):
        from types import SimpleNamespace

        spec = importlib.util.spec_from_file_location("all_view_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cases = [
            ("image.ocr", "image/png", ".png", {}),
            ("media.video", "video/mp4", ".mp4", {}),
            ("media.transcribe", "audio/wav", ".wav", {}),
            ("media.transcribe", "audio/wav", ".wav", {"split": True}),
            ("office.structure", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx", {}),
            ("office.structure", "application/vnd.ms-excel", ".xls", {}),
            ("subtitles.structure", "application/x-subrip", ".srt", {}),
            ("image.caption", "image/png", ".png", {}),
        ]
        for index, (capability, media_type, suffix, parameters) in enumerate(cases):
            with self.subTest(capability=capability, media_type=media_type, parameters=parameters):
                raw = f"SYNTHETIC route {index}".encode()
                request = self.request(raw)
                request["capability"] = capability
                request["inputs"][0]["media_type"] = media_type
                request["parameters"] = parameters
                source = self.staging / "input" / request["inputs"][0]["sha256"]
                view = source.with_name(source.name + suffix)
                seen = []

                def synthetic_extract(path, *_args, **_kwargs):
                    seen.append((Path(path).suffix, Path(path).read_bytes()))
                    Path(path).write_bytes(b"SYNTHETIC changed view")
                    return {"text": "SYNTHETIC result", "structure": [], "loss_receipt": {},
                            "audio_wav": None, "frames": []}

                fake_worker = SimpleNamespace(extract=synthetic_extract, extract_job=synthetic_extract,
                                              extract_split=synthetic_extract)
                fake_spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _worker: None))
                with patch.object(module.importlib.util, "spec_from_file_location", return_value=fake_spec), \
                        patch.object(module.importlib.util, "module_from_spec", return_value=fake_worker), \
                        patch.object(module, "_ocr_language", return_value="synthetic"), \
                        patch.object(module, "_ocr_tessdata", return_value=None), \
                        patch.object(module, "_declared_tool_path", return_value=Path("synthetic-ffmpeg")), \
                        patch.dict(os.environ, {"ARCHEAXIS_ASR_MODEL_DIR": "", "ARCHEAXIS_ASR_LANG": "auto",
                                                "ARCHEAXIS_ASR_DEVICE": "cpu"}):
                    with self.assertRaises(module.Rejected) as caught:
                        module.execute(request, self.staging, self.staging)
                self.assertEqual(caught.exception.code, "AAK-HASH-001")
                self.assertEqual(seen, [(suffix, raw)])
                self.assertEqual(source.read_bytes(), raw)
                self.assertEqual(view.read_bytes(), b"SYNTHETIC changed view")
                self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_video_unsupported_media_type_still_rejects_before_route(self):
        spec = importlib.util.spec_from_file_location("video_invalid_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        request = self.request(b"SYNTHETIC video input")
        request["capability"] = "media.video"
        request["inputs"][0]["media_type"] = "application/json; charset=utf-8"
        with patch.object(module, "_run_route") as worker:
            with self.assertRaises(module.Rejected) as caught:
                module.execute(request, self.staging, self.staging)
        self.assertEqual(caught.exception.code, "AAK-VAL-002")
        worker.assert_not_called()
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_transcribe_missing_suffix_mapping_rejects_before_worker(self):
        from types import SimpleNamespace
        from unittest.mock import Mock

        spec = importlib.util.spec_from_file_location("audio_missing_suffix_transport", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw = b"SYNTHETIC audio; no model or decoder is invoked"
        request = self.request(raw)
        request["capability"] = "media.transcribe"
        request["inputs"][0]["media_type"] = "audio/wav"
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        fake_worker = SimpleNamespace(extract=Mock(return_value={"text": "SYNTHETIC", "structure": [],
                                                                 "loss_receipt": {}}))
        fake_spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _worker: None))
        # Model a future accepted MIME whose suffix mapping is accidentally omitted.
        with patch.dict(module._AUDIO_SUFFIX, {}, clear=True), \
                patch.object(module.importlib.util, "spec_from_file_location", return_value=fake_spec), \
                patch.object(module.importlib.util, "module_from_spec", return_value=fake_worker):
            with self.assertRaises(module.Rejected) as caught:
                module.execute(request, self.staging)
        self.assertEqual(caught.exception.code, "AAK-VAL-002")
        fake_worker.extract.assert_not_called()
        self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_text_plain_explicit_windows_1252_overrides_undeclared_gbk_fallback(self):
        raw = b"\xc4\xe3"
        request = self.request(raw)

        def projected_text(response):
            output = next(item for item in response["outputs"] if item["kind"] == "text")
            return (self.staging / "output" / output["sha256"]).read_bytes()

        process, undeclared = self.invoke(request)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(undeclared["status"], "succeeded")
        self.assertEqual(projected_text(undeclared), "\u4f60".encode("utf-8"))
        loss = next(item for item in undeclared["outputs"] if item["kind"] == "loss_report")
        receipt = json.loads((self.staging / "output" / loss["sha256"]).read_bytes())
        self.assertEqual(receipt["params"]["decode"], "gbk")

        declared = {**request, "inputs": [{**request["inputs"][0],
                                          "media_type": "text/plain; charset=windows-1252"}]}
        process, response = self.invoke(declared)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        self.assertEqual(projected_text(response), "\u00c4\u00e3".encode("utf-8"))
        loss = next(item for item in response["outputs"] if item["kind"] == "loss_report")
        receipt = json.loads((self.staging / "output" / loss["sha256"]).read_bytes())
        self.assertEqual(receipt["params"]["declared_charset"], "windows-1252")
        self.assertEqual(receipt["params"]["decode"], "cp1252")
        self.assertEqual(receipt["params"]["charset_source"], "explicit_parameter")
        self.assertEqual(receipt["losses"], [])
        self.assertIn("decoded using the declared charset and projected as UTF-8", receipt["loss_note"])
        self.assertIn("the worker did not overwrite the input file", receipt["loss_note"])
        source = self.staging / "input" / request["inputs"][0]["sha256"]
        self.assertEqual(source.read_bytes(), raw)

    def test_text_plain_undeclared_bom_ambiguity_and_ordinary_bom_receipts(self):
        cases = [
            (b"\xff\xfe\x00\x00A\x00", "\x00A", "utf-16", "UTF-32LE BOM"),
            (b"\x00\x00\xfe\xff\x00\x00\x00A", "\x00\x00\u00fe\u00ff\x00\x00\x00A", "cp1252", "UTF-32BE BOM"),
            (b"\xff\xfeA\x00", "A", "utf-16", None),
            (b"\xfe\xff\x00A", "A", "utf-16", None),
            (b"\xef\xbb\xbfA", "A", "utf-8-sig", None),
        ]
        for raw, expected, codec, ambiguous_as in cases:
            with self.subTest(raw=raw):
                request = self.request(raw)
                process, response = self.invoke(request)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(response["status"], "succeeded")
                text = next(item for item in response["outputs"] if item["kind"] == "text")
                self.assertEqual((self.staging / "output" / text["sha256"]).read_bytes(), expected.encode("utf-8"))
                loss = next(item for item in response["outputs"] if item["kind"] == "loss_report")
                receipt = json.loads((self.staging / "output" / loss["sha256"]).read_bytes())
                self.assertEqual(receipt["params"]["decode"], codec)
                self.assertNotIn("declared_charset", receipt["params"])
                if ambiguous_as:
                    self.assertIn("ambiguous prefix", receipt["loss_note"])
                    self.assertIn(ambiguous_as, receipt["loss_note"])
                    self.assertIn("without a declared charset the intended encoding is uncertain", receipt["loss_note"])
                    self.assertIn("the existing fallback was applied", receipt["loss_note"])
                else:
                    self.assertNotIn("ambiguous prefix", receipt["loss_note"])
                self.assertEqual((self.staging / "input" / request["inputs"][0]["sha256"]).read_bytes(), raw)

    def test_text_plain_declared_charset_aliases_and_matching_bom(self):
        cases = [
            ("Text/Plain ; Charset=\"UtF8\"", "\u4e2d\u6587".encode(), "\u4e2d\u6587", "UtF8", "utf-8"),
            ("text/plain; format=\"x;y\"; CHARSET=\"CP936\"", b"\xc4\xe3", "\u4f60", "CP936", "gbk"),
            ('text/plain; note="quoted\\\"; charset=gbk"; charset=windows-1252',
             b"\xc4\xe3", "\u00c4\u00e3", "windows-1252", "cp1252"),
            ('text/plain; \tX-unknown_1* \t= "quoted\\\"; charset=gbk" \t; \tCHARSET\t=\t"windows-1252"\t',
             b"\xc4\xe3", "\u00c4\u00e3", "windows-1252", "cp1252"),
            ("text/plain; charset=UTF-16LE", b"\xff\xfeA\x00", "A", "UTF-16LE", "utf-16"),
            ("text/plain; charset=utf-16le", b"A\x00", "A", "utf-16le", "utf-16-le"),
            ("text/plain; charset=utf-16be", b"\x00A", "A", "utf-16be", "utf-16-be"),
            ("text/plain; charset=utf-16be", b"\x00\x00\xfe\xff\x00A", "\x00\ufeffA", "utf-16be", "utf-16-be"),
            ("text/plain; charset=utf-16le", b"\xff\xfe\x00\x00A\x00", "\x00A", "utf-16le", "utf-16"),
            ("text/plain; charset=utf-16", b"\xff\xfe\x00\x00A\x00", "\x00A", "utf-16", "utf-16"),
            ("text/plain; charset=utf-8", b"\xef\xbb\xbfhello", "hello", "utf-8", "utf-8-sig"),
            ("text/plain; charset=US-ASCII", b"plain", "plain", "US-ASCII", "ascii"),
        ]
        for media_type, raw, expected, declaration, codec in cases:
            with self.subTest(media_type=media_type):
                request = self.request(raw)
                request["inputs"][0]["media_type"] = media_type
                process, response = self.invoke(request)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(response["status"], "succeeded")
                text = next(item for item in response["outputs"] if item["kind"] == "text")
                self.assertEqual((self.staging / "output" / text["sha256"]).read_bytes(), expected.encode())
                loss = next(item for item in response["outputs"] if item["kind"] == "loss_report")
                receipt = json.loads((self.staging / "output" / loss["sha256"]).read_bytes())
                self.assertEqual(receipt["params"]["declared_charset"], declaration)
                self.assertEqual(receipt["params"]["decode"], codec)
                self.assertEqual(receipt["params"]["charset_source"], "explicit_parameter")
                if raw.startswith(b"\xff\xfe\x00\x00"):
                    self.assertIn("ambiguous", receipt["loss_note"])
                    self.assertIn("UTF-16LE BOM followed by NUL", receipt["loss_note"])
                    self.assertIn("UTF-32LE BOM", receipt["loss_note"])
                if raw.startswith(b"\x00\x00\xfe\xff"):
                    self.assertIn("ambiguous", receipt["loss_note"])
                    self.assertIn("UTF-32BE BOM", receipt["loss_note"])
                self.assertEqual((self.staging / "input" / request["inputs"][0]["sha256"]).read_bytes(), raw)

    def test_text_plain_bad_charset_or_bom_is_rejected_without_output(self):
        cases = [
            ("text/plain; charset=x-not-supported", b"hello"),
            ("text/plain; charset=utf-8; CHARSET=utf-8", b"hello"),
            ("text/plain; charset=utf-8; charset=gbk", b"hello"),
            ("text/plain; charset=", b"hello"),
            ("text/plain; charset", b"hello"),
            ("text/plain; charset=utf-8 extra", b"hello"),
            ("text/plain; charset=\"utf-8", b"hello"),
            ("text/plain; charset*=utf-8''utf-8", b"hello"),
            ("text/plain; charset*0=utf-8", b"hello"),
            ("text/plain; charset*1=utf-8", b"hello"),
            ("text/plain; charset*0*=utf-8''utf; charset*2*=-8", b"hello"),
            ("text/plain; charset*0=utf; charset*0=-8", b"hello"),
            ("text/plain; charset=windows-1252; CHARSET*1=x", b"hello"),
            ("text/plain; charset\x01=windows-1252", b"\xc4\xe3"),
            ("text/plain; charset\x7f=windows-1252", b"\xc4\xe3"),
            ("text/plain; charset/garbage=windows-1252", b"\xc4\xe3"),
            ("text/plain; char\u017fet=windows-1252", b"\xc4\xe3"),
            ("text/plain; charset\u00a0=windows-1252", b"\xc4\xe3"),
            ("text/plain; \u00a0charset=windows-1252", b"\xc4\xe3"),
            ('text/plain; x="invalid\x1fvalue"; charset=windows-1252', b"\xc4\xe3"),
            ('text/plain; x="invalid\x7fvalue"; charset=windows-1252', b"\xc4\xe3"),
            ("text/plain; =invalid; charset=windows-1252", b"\xc4\xe3"),
            ("text/plain\n", b"hello"),
            ('text/plain; x="unterminated; charset=windows-1252', b"\xc4\xe3"),
            ('text/plain; x=broken"; charset=windows-1252', b"\xc4\xe3"),
            ('text/plain; x="dangling\\', b"hello"),
            ('text/plain; x=broken\\; charset=windows-1252', b"\xc4\xe3"),
            ('text/plain; x="ok"junk; charset=windows-1252', b"\xc4\xe3"),
            ('text/plain; x=broken"ok"; charset=windows-1252', b"\xc4\xe3"),
            ("text/plain; charset=utf-8\r\nX-Injected: yes", b"hello"),
            ("text/plain; charset=utf-8", b"\xff"),
            ("text/plain; charset=windows-1252", b"\x81"),
            ("text/plain; charset=utf-16le", b"\x00"),
            ("text/plain; charset=utf-16", b"A\x00"),
            ("text/plain; charset=utf-16", b"\x00A"),
            ("text/plain; charset=utf-8", b"\xff\xfeA\x00"),
            ("text/plain; charset=utf-16be", b"\xff\xfeA\x00"),
            ("text/plain; charset=utf-16le", b"\xfe\xff\x00A"),
        ]
        for media_type, raw in cases:
            with self.subTest(media_type=media_type, raw=raw):
                request = self.request(raw)
                request["inputs"][0]["media_type"] = media_type
                process, response = self.invoke(request)
                self.assertEqual(process.returncode, 1)
                self.assertEqual(response["status"], "rejected")
                self.assertEqual(response["error"]["code"], "AAK-VAL-002")
                self.assertEqual(response["outputs"], [])
                self.assertEqual((self.staging / "input" / request["inputs"][0]["sha256"]).read_bytes(), raw)
                self.assertEqual(list((self.staging / "output").iterdir()), [])

    def test_quoted_other_parameter_is_not_a_charset_declaration(self):
        raw = b"\xc4\xe3"
        for media_type in (
            'text/plain; x="charset=windows-1252; charset*0=gbk"',
            'text/plain; x="escaped\\\"; charset=windows-1252"',
        ):
            with self.subTest(media_type=media_type):
                request = self.request(raw)
                request["inputs"][0]["media_type"] = media_type
                process, response = self.invoke(request)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(response["status"], "succeeded")
                text = next(item for item in response["outputs"] if item["kind"] == "text")
                self.assertEqual((self.staging / "output" / text["sha256"]).read_bytes(), "\u4f60".encode())
                loss = next(item for item in response["outputs"] if item["kind"] == "loss_report")
                receipt = json.loads((self.staging / "output" / loss["sha256"]).read_bytes())
                self.assertEqual(receipt["params"]["decode"], "gbk")
                self.assertNotIn("declared_charset", receipt["params"])
                self.assertEqual((self.staging / "input" / request["inputs"][0]["sha256"]).read_bytes(), raw)

    def test_charset_parameters_do_not_change_other_text_formats(self):
        raw = b"\xc4\xe3"
        request = self.request(raw)
        request["inputs"][0]["media_type"] = "text/csv; charset=windows-1252"
        process, response = self.invoke(request)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(response["status"], "succeeded")
        text = next(item for item in response["outputs"] if item["kind"] == "text")
        self.assertEqual((self.staging / "output" / text["sha256"]).read_bytes(), "\u4f60".encode())
        loss = next(item for item in response["outputs"] if item["kind"] == "loss_report")
        receipt = json.loads((self.staging / "output" / loss["sha256"]).read_bytes())
        self.assertEqual(receipt["params"]["decode"], "gbk")
        self.assertNotIn("declared_charset", receipt["params"])
        self.assertEqual((self.staging / "input" / request["inputs"][0]["sha256"]).read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
