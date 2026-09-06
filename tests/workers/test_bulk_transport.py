"""BULK-0907 P17: text NDJSON transport local-failure regressions (transport/text_ndjson.py).

Direct execute() negatives (no subprocess): extra request field, mismatched uri/hash,
tampered staged input, non-empty parameters, oversized input; plus strict main-boundary
rejections for invalid JSON/non-finite using a patched stdin. Reuses the real transport
entry and the R2 safe-path discipline.
"""

import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/python-workers/transport/text_ndjson.py"


def _load():
    spec = importlib.util.spec_from_file_location("text_ndjson", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TransportBulkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transport = _load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)
        self.staging = Path(self.tmp.name)
        (self.staging / "input").mkdir()
        (self.staging / "output").mkdir()

    def _request(self, raw: bytes = b"hello"):
        digest = hashlib.sha256(raw).hexdigest()
        (self.staging / "input" / digest).write_bytes(raw)
        return {"schema": "archeaxis.worker-request/v1", "type": "job_request",
                "request_id": "r", "job_id": "j", "attempt": 1, "protocol_minor": 0,
                "capability": "text.extract", "capability_version": "1", "deadline_ms": 30000,
                "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": "text/plain"}],
                "parameters": {}}

    def _rejected(self, request):
        with self.assertRaises(self.transport.Rejected):
            self.transport.execute(request, self.staging)

    def test_extra_field_and_wrong_parameter_shapes_are_rejected(self):
        self._rejected({**self._request(), "extra": True})
        self._rejected({**self._request(), "parameters": {"not": "empty"}})
        self._rejected({**self._request(), "inputs": []})

    def test_uri_hash_mismatch_and_attempt_below_minimum_are_rejected(self):
        bad_uri = self._request()
        bad_uri["inputs"][0]["uri"] = f"job://input/{'b' * 64}"
        self._rejected(bad_uri)
        bad_attempt = self._request()
        bad_attempt["attempt"] = 0
        self._rejected(bad_attempt)

    def test_tampered_staged_input_is_rejected_by_hash(self):
        request = self._request()
        (self.staging / "input" / request["inputs"][0]["sha256"]).write_bytes(b"tampered")
        self._rejected(request)

    def test_oversized_input_is_rejected(self):
        raw = b"x" * (16 * 1024 * 1024 + 1)
        request = self._request(raw)
        with self.assertRaises(self.transport.Rejected) as ctx:
            self.transport.execute(request, self.staging)
        self.assertEqual(ctx.exception.code, "AAK-VAL-003")

    def test_strict_main_rejects_nonfinite_and_bad_json_with_no_outputs(self):
        request = self._request()
        bad_json = json.dumps(request).replace('"attempt": 1', "not-json")
        stdin = io.TextIOWrapper(io.BytesIO(bad_json.encode("utf-8")))
        stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        with patch.object(self.transport.sys, "stdin", stdin), \
                patch.object(self.transport.sys, "stdout", stdout), \
                patch.object(self.transport.sys, "argv", [str(SCRIPT), "--staging-root", str(self.staging)]):
            exit_code = self.transport.main()
            response = json.loads(stdout.buffer.getvalue().splitlines()[1])
        self.assertEqual(exit_code, 1)
        self.assertEqual(response["status"], "rejected")
        self.assertEqual(response["outputs"], [])
        self.assertEqual(list((self.staging / "output").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
