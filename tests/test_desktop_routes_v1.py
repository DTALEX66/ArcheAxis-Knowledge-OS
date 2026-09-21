"""R6 A12 desktop route manifest and source-boundary tests."""
from __future__ import annotations

import json
from pathlib import Path

from app.contracts.desktop_routes_v1 import DesktopRouteManifestV1


ROOT = Path(__file__).resolve().parents[1]


def test_route_manifest_covers_required_shell_surfaces():
    payload = json.loads((ROOT / "config/desktop/routes-v1.json").read_text(encoding="utf-8"))
    manifest = DesktopRouteManifestV1.model_validate(payload)
    assert {route.page_id for route in manifest.routes} == {
        "knowledge", "source_reader", "learning", "jobs", "machine_assets", "settings", "recovery"
    }
    assert manifest.canonical_writer == "archeaxis-core-rust-sqlite"


def test_shell_source_mentions_core_routes_and_machine_authority():
    shell = (ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs").read_text(encoding="utf-8")
    assert "/api/v1/learning/items" in shell
    assert "/api/v1/jobs" in shell
    assert "/api/v1/imports" in shell
    supervisor = (ROOT / "apps/ArcheAxis.Desktop/CoreSupervisor.cs").read_text(encoding="utf-8")
    assert "archeaxis.desktop-launch/v2" in supervisor
    assert "workspace_db" in supervisor


def test_source_reader_manifest_matches_current_core_projection_route():
    payload = json.loads((ROOT / "config/desktop/routes-v1.json").read_text(encoding="utf-8"))
    route = next(route for route in payload["routes"] if route["page_id"] == "source_reader")
    assert route["core_endpoint"] == "/api/v1/sources/{source_id}/members"
    assert route["read_only"] is True


def test_knowledge_manifest_matches_current_core_v3_route():
    payload = json.loads((ROOT / "config/desktop/routes-v1.json").read_text(encoding="utf-8"))
    route = next(route for route in payload["routes"] if route["page_id"] == "knowledge")
    assert route["core_endpoint"] == "/api/v1/knowledge-items/{knowledge_id}/v3"
    assert route["read_only"] is True


def test_recovery_manifest_matches_the_current_read_only_boundary_surface():
    payload = json.loads((ROOT / "config/desktop/routes-v1.json").read_text(encoding="utf-8"))
    route = next(route for route in payload["routes"] if route["page_id"] == "recovery")
    assert route["core_endpoint"] == "/api/v1/system/version"
    assert route["read_only"] is True


def test_versioned_schema_is_present_and_binds_canonical_writer():
    schema = json.loads((ROOT / "packages/contracts/v1/desktop-routes.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "archeaxis.desktop-routes/v1"
    assert schema["properties"]["canonical_writer"]["const"] == "archeaxis-core-rust-sqlite"
