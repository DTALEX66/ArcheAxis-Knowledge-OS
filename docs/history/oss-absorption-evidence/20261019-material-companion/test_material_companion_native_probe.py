"""SIMULATED negative qualification checks; no host/model/database is started."""
import copy
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("material_companion_probe_contract", ROOT / "scripts/probes/aaos01_material_companion_loop.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def fixture(purpose):
    profile = {"model": "synthetic-selected", "endpoint": "http://127.0.0.1:1234/v1", "protocol": "openai", "max_tokens": 1024, "timeout_s": 120, "credential_ref": None}
    resolved = {"purpose": purpose, "lane": "deep", "profile": profile, "configuration_revision": 1, "workspace_id": "synthetic-owned", "restore_epoch": "initial"}
    request = {"request_id": "original", "session_id": "original-session", "model_configuration": resolved, "model": profile["model"], "max_tokens": 1024, "timeout_s": 120}
    preview = {"plan": {"request": request}, "plan_sha256": "a" * 64}
    receipt = {**preview, "request_id": "original", "session_id": "original-session", "schema": "archeaxis.material-answer/v1" if purpose == "material" else "archeaxis.conversation-receipt/v1", "outcome": "succeeded", "state": "completed", "authority": "candidate", "grants_knowledge_acceptance": False, "answer": {**profile, "answer": "SYNTHETIC final answer", "requested_model": profile["model"], "observed_model": profile["model"], "finish_reason": "stop", "truncated": False, "answer_source": "content"}, "answer_sha256": hashlib.sha256(b"SYNTHETIC final answer").hexdigest()}
    return receipt, preview, resolved


@pytest.mark.parametrize("purpose", ["material", "companion"])
def test_receipt_rejects_wrong_identity_binding_destination_empty_or_nonterminal(purpose):
    receipt, preview, resolved = fixture(purpose)
    probe.assert_bound_receipt(receipt, preview, resolved, purpose)
    mutations = [lambda r: r.update(request_id="other"), lambda r: r.update(plan_sha256="b" * 64), lambda r: r.update(authority="accepted"), lambda r: r.update(grants_knowledge_acceptance=True), lambda r: r["answer"].update(answer="  "), lambda r: r["answer"].update(model="different"), lambda r: r["answer"].update(endpoint="https://external.invalid"), lambda r: r["plan"]["request"]["model_configuration"].update(configuration_revision=2), lambda r: r.update(outcome="failed", state="cancelled"), lambda r: r["answer"].update(observed_model="other"), lambda r: r["answer"].update(finish_reason="length"), lambda r: r["answer"].update(truncated=True), lambda r: r["answer"].update(answer_source="reasoning_content")]
    for mutate in mutations:
        bad = copy.deepcopy(receipt); mutate(bad)
        with pytest.raises(AssertionError):
            probe.assert_bound_receipt(bad, preview, resolved, purpose)


def test_call_counter_rejects_duplicate_pending_wrong_origin_or_overflow():
    row = {"operation": "conversation_request", "preview": False, "own": True, "completed": True, "status": 200}
    expected = [("conversation_request", False)]
    probe.assert_calls({"rows": [row], "overflow": False}, expected)
    for bad in [{"rows": [row, row], "overflow": False}, {"rows": [row], "overflow": True}, *({"rows": [{**row, **change}], "overflow": False} for change in [{"preview": True}, {"own": False}, {"completed": False}, {"status": 503}, {"error": "BRIDGE_REJECTED"}])]:
        with pytest.raises(AssertionError):
            probe.assert_calls(bad, expected)
    with pytest.raises(AssertionError):
        probe.assert_calls({"rows": [row], "overflow": False}, [])


def test_cli_refuses_material_companion_without_saved_actual_model_before_launch():
    value = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/probes/aaos01_tauri_webdriver_loop.py"), "--host", str(ROOT / ".project-local/never-launched.exe"), "--grouped-material-companion-loop"], capture_output=True, text=True, encoding="utf-8")
    assert value.returncode == 2 and "material/companion requires" in value.stderr
