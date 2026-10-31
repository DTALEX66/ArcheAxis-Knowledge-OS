"""Formal worker-route regressions using synthetic files and real stdio processes.

These verify declared canvas facts and complete text projection, not a vault
migration, attachment import, plugin execution or rendered canvas acceptance.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CANVAS = ROOT / "services/python-workers/document/worker_canvas.py"
TEXT = ROOT / "services/python-workers/transport/text_ndjson.py"


class CanvasReferenceRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["ARCHEAXIS_RUN_ROOT"])
        self.addCleanup(self.tmp.cleanup)
        self.staging = Path(self.tmp.name)
        (self.staging / "input").mkdir()
        (self.staging / "output").mkdir()
        self.protocol = Draft202012Validator(json.loads(
            (ROOT / "packages/contracts/v1/worker-protocol.schema.json").read_text(encoding="utf-8")))
        self.loss_schema = Draft202012Validator(json.loads(
            (ROOT / "packages/contracts/v1/loss-receipt.schema.json").read_text(encoding="utf-8")))

    def invoke(self, raw: bytes, *, capability="canvas.structure", media="application/json"):
        digest = hashlib.sha256(raw).hexdigest()
        source = self.staging / "input" / digest
        source.write_bytes(raw)
        request = {
            "schema": "archeaxis.worker-request/v1", "type": "job_request",
            "request_id": "synthetic-request", "job_id": "synthetic-job", "attempt": 1,
            "protocol_minor": 0, "capability": capability, "capability_version": "1",
            "deadline_ms": 30000,
            "inputs": [{"uri": f"job://input/{digest}", "sha256": digest, "media_type": media}],
            "parameters": {},
        }
        script = CANVAS if capability == "canvas.structure" else TEXT
        process = subprocess.run(
            [sys.executable, "-B", "-S", str(script), "--staging-root", str(self.staging)],
            input=json.dumps(request) + "\n", capture_output=True, text=True, encoding="utf-8",
            check=False, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertEqual(len(process.stdout.splitlines()), 2, process.stdout)
        hello, response = map(json.loads, process.stdout.splitlines())
        self.protocol.validate(hello)
        self.protocol.validate(response)
        self.assertEqual(hello["capabilities"], [capability])
        self.assertEqual(response["status"], "succeeded", response)
        self.assertEqual(source.read_bytes(), raw, "the worker must not rewrite original bytes")
        artifacts = {}
        for output in response["outputs"]:
            data = (self.staging / "output" / output["sha256"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), output["sha256"])
            self.assertEqual(len(data), output["byte_length"])
            self.assertEqual(output["authority_effect"], "candidate_or_measurement_only")
            artifacts[output["kind"]] = data
        self.assertEqual(set(artifacts), {"text", "document_structure", "loss_report"})
        self.loss_schema.validate(json.loads(artifacts["loss_report"]))
        return digest, artifacts

    def test_real_canvas_route_keeps_source_facts_without_following_references(self):
        payload = {
            "nodes": [
                {"id": "group", "type": "group", "label": "材料组", "background": "missing/bg.png",
                 "backgroundStyle": "repeat", "x": 0, "y": 0, "width": 800, "height": 400},
                {"id": "file", "type": "file", "file": "../../unselected/研究.md", "subpath": "#结果",
                 "x": 20, "y": 30, "width": 100, "height": 100, "plugin:custom": {"mode": "保留"}},
                {"id": "link", "type": "link", "url": "https://example.invalid/unselected",
                 "x": 40, "y": 50, "width": 100, "height": 100},
                {"id": "text", "type": "text", "text": "正文\n[[研究#结果]]", "x": 60, "y": 70,
                 "width": 200, "height": 100},
            ],
            "edges": [{"id": "e", "fromNode": "file", "toNode": "text", "label": "依据",
                       "fromSide": "right", "toSide": "left", "plugin:edge": [1, 2]}],
            "plugin:root": {"layout": "retained"},
        }
        raw = b"\xef\xbb\xbf" + json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        digest, artifacts = self.invoke(raw)
        receipt = json.loads(artifacts["loss_report"])
        facts = receipt["params"]["worker_output"]
        self.assertEqual(receipt["params"]["source"], {
            "format": "json-canvas", "spec_reference": "1.0", "sha256": digest, "byte_length": len(raw)})
        self.assertEqual(artifacts["text"].decode("utf-8"), payload["nodes"][3]["text"])
        self.assertEqual(facts["edges"], payload["edges"])
        self.assertEqual(facts["node_attributes"][:3], payload["nodes"][:3])
        self.assertEqual(facts["canvas_attributes"], {"plugin:root": payload["plugin:root"]})
        self.assertEqual(facts["references"][0]["subpath"], "#结果")
        self.assertEqual(facts["references"][0]["file"], "../../unselected/研究.md")
        self.assertTrue(all(item["resolution"] == "NOT_EXECUTED" for item in facts["references"]))
        self.assertEqual(receipt["params"]["reference_resolution"], "NOT_EXECUTED")
        self.assertTrue(any("not opened" in loss for loss in receipt["losses"]))

    def test_real_canvas_route_accepts_optional_empty_arrays(self):
        _, artifacts = self.invoke(b"{}")
        self.assertEqual(artifacts["text"], b"")
        self.assertEqual(json.loads(artifacts["document_structure"]), [])
        receipt = json.loads(artifacts["loss_report"])
        self.assertEqual((receipt["covered"], receipt["total"], receipt["coverage"]), (0, 0, 1.0))

    def test_large_canvas_text_is_complete_and_not_duplicated_in_metadata(self):
        text = "正文 研究\n" * 10000 + "FINAL_CANVAS_MARKER_末尾"
        raw = json.dumps({"nodes": [{"id": "long", "type": "text", "text": text}]}).encode("utf-8")
        _, artifacts = self.invoke(raw)
        self.assertEqual(artifacts["text"].decode("utf-8"), text)
        receipt = json.loads(artifacts["loss_report"])
        self.assertEqual(receipt["params"]["worker_output"]["node_attributes"],
                         [{"id": "long", "type": "text"}])
        anchor = receipt["params"]["worker_structure"][0]
        self.assertEqual((anchor["char_start"], anchor["char_end"]), (0, len(text)))
        lines = json.loads(artifacts["document_structure"])
        self.assertEqual(len(lines), 5000)
        self.assertEqual(lines[-1]["char_end"], len("正文 研究\n" * 5000))
        self.assertEqual((receipt["covered"], receipt["total"]), (5000, 10001))
        self.assertAlmostEqual(receipt["coverage"], 5000 / 10001)
        self.assertIn("line anchors capped at 5000", receipt["losses"])
        self.assertIn("line anchors capped at 5000", receipt["loss_note"])

    def test_formal_markdown_route_preserves_large_body_and_reports_anchor_cap(self):
        text = "---\ntitle: 合成笔记\n---\n" + "保留正文与来源 [[另一笔记#章节]]\n" * 6000 + "FINAL_MARKDOWN_MARKER_末尾"
        _, artifacts = self.invoke(text.encode("utf-8"), capability="text.extract", media="text/markdown")
        self.assertEqual(artifacts["text"].decode("utf-8"), text)
        receipt = json.loads(artifacts["loss_report"])
        self.assertEqual(receipt["covered"], 5000)
        self.assertEqual(receipt["total"], len(text.splitlines(keepends=True)))
        self.assertLess(receipt["coverage"], 1.0)
        self.assertIn("line anchors capped at 5000", receipt["losses"])
        self.assertGreater(len(text), 10000)


if __name__ == "__main__":
    unittest.main()
