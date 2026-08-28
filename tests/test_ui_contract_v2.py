"""UI Contract v2 keeps the product flow user-facing and authority-safe."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/product/UI_CONTRACT_V2.json"


def test_ui_contract_v2_defines_the_complete_learning_golden_flow() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "archeaxis/ui-contract/v2"
    assert payload["productShell"]["base"] == "ArcheAxis React/Tauri"
    assert payload["productShell"]["mode"] == "canonical-native-shell"
    assert payload["sidecars"]["deeptutor"]["role"] == "optional-learning-engine"
    assert payload["authority"] == "ArcheAxis"
    assert [step["id"] for step in payload["goldenFlow"]] == [
        "import",
        "read",
        "anchor",
        "claim",
        "learn",
        "practice",
        "review",
        "distill",
        "recover",
    ]


def test_user_forms_do_not_expose_internal_ids_or_approval_bureaucracy() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    forbidden = {"artifact_id", "package_id", "command", "jwt", "approval_reason"}
    required_fields = {
        field
        for surface in payload["surfaces"]
        for field in surface.get("userRequiredFields", [])
    }
    assert forbidden.isdisjoint(required_fields)
    assert payload["providerConfiguration"]["insideGoldenFlow"] is False


def test_downstream_shell_cannot_emit_truth_bearing_fields() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert "verified" in payload["authorityFirewall"]["forbiddenInboundFields"]
    assert "machine_level" in payload["authorityFirewall"]["forbiddenInboundFields"]
    assert payload["authorityFirewall"]["sidecarDeletionSafe"] is True
