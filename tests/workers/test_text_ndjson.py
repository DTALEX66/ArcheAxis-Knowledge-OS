"""Real-process text NDJSON and staging-boundary regression tests."""

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
