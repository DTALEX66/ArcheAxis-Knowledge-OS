"""A windowed transcription request is accepted, and nothing else gains a parameter channel.

The Core can only send one bounded unit of work per job, so the transport has to carry a window —
but widening `parameters` for every route would turn a closed protocol into a free-form one. These
tests pin both halves: the window rides `media.transcribe` and reaches the worker as a one-window
plan, and every other capability still refuses a non-empty parameter object.
"""

import importlib.util
import hashlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSPORT = ROOT / "services/python-workers/transport/text_ndjson.py"

FIXTURE = '''
"""Fixture worker: records each call to the path named by AAOS_WINDOW_FIXTURE_LOG."""
import json
import os


def _record(kind, payload):
    path = os.environ.get("AAOS_WINDOW_FIXTURE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps({"kind": kind, **payload}, ensure_ascii=False) + "\\n")


def extract(path, model_path=None, language="auto", device="cpu"):
    _record("extract", {"path": path})
    return {"engine": "fixture", "engine_version": "1", "text": "unwindowed", "language": "en",
            "language_probability": 1.0, "duration_ms": 1000, "cues": [], "raw_cues": [],
            "alignment_issues": [], "alignment_status": "unlocated", "processing_status": "complete",
            "processing_error": None,
            "loss_receipt": {"engine": "fixture", "engine_version": "1", "params": {}, "loss_note": "fixture"}}


def extract_windowed(path, model_path=None, language="auto", device="cpu", plan=None, ffmpeg=None, staging=None):
    _record("extract_windowed", {"path": path, "plan": plan, "ffmpeg": ffmpeg, "staging": staging})
    return {"engine": "fixture", "engine_version": "1", "text": "windowed", "language": "en",
            "language_probability": 1.0, "duration_ms": 3000, "cues": [{"start_ms": 2000, "end_ms": 2500, "text": "w"}],
            "raw_cues": [{"start_ms": 2000, "end_ms": 2500, "text": "w"}], "alignment_issues": [],
            "alignment_status": "complete", "processing_status": "complete", "processing_error": None,
            "loss_receipt": {"engine": "fixture", "engine_version": "1", "params": {}, "loss_note": "fixture"},
            "windows": {"status": "complete", "windows_expected": 1, "windows_present": 1,
                        "windows_missing": [], "windows_resumed": [], "note": "fixture"}}
'''


def load_transport():
    spec = importlib.util.spec_from_file_location("window_transport", TRANSPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WindowParameterTests(unittest.TestCase):
    def setUp(self):
        self.transport = load_transport()
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)
        self.staging = Path(self.tmp.name)
        (self.staging / "input").mkdir()
        self.fixture = self.staging / "fixture_worker.py"
        self.fixture.write_text(FIXTURE, encoding="utf-8")
        self.original = dict(self.transport.ROUTES["media.transcribe"])
        self.transport.ROUTES["media.transcribe"]["worker"] = str(self.fixture)
        self.addCleanup(lambda: self.transport.ROUTES.__setitem__("media.transcribe", self.original))

    def request(self, parameters, capability="media.transcribe", media_type="audio/mpeg"):
        raw = b"pretend audio"
        digest = hashlib.sha256(raw).hexdigest()
        (self.staging / "input" / digest).write_bytes(raw)
        return {"schema": "archeaxis.worker-request/v1", "type": "job_request", "request_id": "r1",
                "job_id": "j1", "attempt": 1, "protocol_minor": 0, "capability": capability,
                "capability_version": "1", "deadline_ms": 30000,
                "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": media_type}],
                "parameters": parameters}

    def window(self, **overrides):
        window = {"index": 2, "start_ms": 280_000, "end_ms": 420_000}
        window.update(overrides)
        return {"window": window, "ffmpeg": "ffmpeg.exe", "staging": str(self.staging / "windows")}

    def test_a_window_reaches_the_worker_as_a_single_window_plan(self):
        parameters = self.window()
        log = self.staging / "calls.jsonl"
        os.environ["AAOS_WINDOW_FIXTURE_LOG"] = str(log)
        self.addCleanup(lambda: os.environ.pop("AAOS_WINDOW_FIXTURE_LOG", None))
        outputs, _measurements, _losses = self.transport.execute(self.request(parameters), self.staging)
        # Reaching this line at all is the contract check: the windowed envelope had to satisfy the
        # canonical artifact pipeline (text, document structure and loss receipt) to get here.
        self.assertEqual({output["kind"] for output in outputs}, {"text", "document_structure", "loss_report"})
        recorded = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(recorded), 1)
        call = recorded[0]
        self.assertEqual(call["kind"], "extract_windowed")
        self.assertEqual(call["plan"]["windows_total"], 1)
        self.assertEqual(call["plan"]["windows"][0], {"index": 2, "start_ms": 280_000, "end_ms": 420_000,
                                                      "audio_ms": 140_000, "estimated_ms": 140_000})
        self.assertEqual(call["ffmpeg"], "ffmpeg.exe")
        self.assertEqual(call["staging"], parameters["staging"])

    def test_another_capability_still_refuses_any_parameter(self):
        with self.assertRaises(self.transport.Rejected):
            self.transport.execute(self.request({"window": {"index": 0, "start_ms": 0, "end_ms": 1}}, capability="text.extract"),
                                   self.staging)

    def test_a_malformed_window_is_refused_with_a_reason(self):
        for broken in (self.window(window={"index": 0, "start_ms": 10, "end_ms": 10}),
                       {"window": {"index": 0, "start_ms": 0, "end_ms": 10}},
                       {"ffmpeg": "ffmpeg.exe"},
                       {**self.window(), "extra": 1}):
            with self.subTest(broken=broken):
                with self.assertRaises(self.transport.Rejected):
                    self.transport.execute(self.request(broken), self.staging)


def load_fixture(path: Path):  # pragma: no cover - kept for manual probing
    spec = importlib.util.spec_from_file_location("fixture_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
