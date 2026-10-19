"""Synthetic contract negatives for the candidate native journey (no host launch)."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("handoff_probe", Path(__file__).resolve().parents[1] / "scripts/probes/aaos01_handoff_native_loop.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class HandoffNativeProbeTests(unittest.TestCase):
    def setUp(self):
        self.workspace = {"workspace_id": "a" * 32, "restore_epoch": "initial"}
        self.document = {"document_id": "owned-synthetic", "version": 3, "content_sha256": "b" * 64}
        self.selected = probe.proposal(self.workspace, self.document)
        self.identity = {
            "reference": self.selected["payload"]["source"]["reference"],
            "producer": self.selected["producer"], "reference_state": "CURRENT",
            "scope": "LOCAL_HUMAN_READ_ONLY", "source_authentication": "UNVERIFIED",
            "selection_qualification": "UNVERIFIED", "grants_execution": False,
            "grants_knowledge_acceptance": False,
            "proposal_sha256": hashlib.sha256(b"archeaxis.project-handoff/v1\x00" + json.dumps(
                self.selected, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
        }

    def test_explicit_version_is_pinned(self):
        self.assertEqual(self.selected["payload"]["source"]["reference"], self.document)
        self.assertEqual(self.selected["producer"], {"namespace":"archeaxis", **self.workspace})
        self.assertEqual(self.selected["expires_at_ms"] - self.selected["created_at_ms"], 30_000)

    def test_core_bridge_allowlist_rejects_write_and_probe_bypass(self):
        calls = []
        def bridge(operation, payload):
            calls.append((operation, payload)); return {"ok": True}
        for operation in ("document_create", "document_draft", "project_handoff_preview", "project_handoff_snapshot"):
            with self.assertRaises(AssertionError):
                probe.core_read(bridge, operation)
        self.assertEqual(calls, [])
        self.assertEqual(probe.core_read(bridge, "document_get", {"document_id":"owned-synthetic"}), {"ok":True})

    def test_diagnostic_identity_rejects_other_version_or_workspace_or_body_leak(self):
        probe.assert_snapshot_identity(self.identity, self.selected)
        cases = [
            {**self.identity, "reference": {**self.identity["reference"], "version": 4}},
            {**self.identity, "producer": {**self.identity["producer"], "workspace_id":"0"*32}},
            {**self.identity, "editor_json": {"type":"doc"}},
            {**self.identity, "grants_execution": True},
            {**self.identity, "proposal_sha256": "c" * 64},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(AssertionError):
                probe.assert_snapshot_identity(case, self.selected)


if __name__ == "__main__":
    unittest.main()
