"""UI Contract v2 keeps the product flow user-facing and authority-safe."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/product/UI_CONTRACT_V2.json"


def test_ui_contract_v2_defines_the_complete_learning_golden_flow() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "archeaxis/ui-contract/v2"
    # SUP-022 makes the Tauri 2 + React/TypeScript/Vite host the formal shell; the contract
    # used to name the Avalonia donor as the production entry, which is why a reader could not
    # tell from the machine-readable authority which shell the product actually starts.
    assert payload["productShell"]["base"] == "ArcheAxis Tauri 2 + React/TypeScript/Vite"
    assert payload["productShell"]["mode"] == "formal-desktop-shell"
    assert payload["productShell"]["productionEntrypoint"] == "src-tauri/tauri.conf.json"
    assert payload["productShell"]["reactUiEntry"] == "frontend/src/app/App.tsx"
    assert payload["productShell"]["authorityDecision"] == "SUP-022"
    assert (
        payload["productShell"]["donorShell"]["role"] == "frozen-behavior-and-component-donor"
    )
    assert (
        payload["productShell"]["donorShell"]["path"]
        == "apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj"
    )
    assert (
        payload["productShell"]["recoveryEntry"]["identifier"]
        == "com.archeaxis.workspace.recovery"
    )
    # A declared entry that is not on disk is a stale claim, not a contract.
    for declared in (
        payload["productShell"]["productionEntrypoint"],
        payload["productShell"]["reactUiEntry"],
        payload["productShell"]["donorShell"]["path"],
        payload["productShell"]["recoveryEntry"]["path"],
    ):
        assert (ROOT / declared).exists(), f"declared entry missing: {declared}"
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
