"""R6 A12 desktop route manifest and source-boundary tests."""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.contracts.desktop_routes_v1 import DesktopRouteManifestV1


ROOT = Path(__file__).resolve().parents[1]


def test_route_manifest_covers_required_shell_surfaces():
    payload = json.loads((ROOT / "config/desktop/routes-v1.json").read_text(encoding="utf-8"))
    manifest = DesktopRouteManifestV1.model_validate(payload)
    assert {route.page_id for route in manifest.routes} == {
        "knowledge", "source_reader", "learning", "jobs", "machine_growth", "settings", "recovery"
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


def _core_route_shapes() -> set[str]:
    """Normalised route shapes Core actually declares (params collapsed)."""
    api = (ROOT / "crates/archeaxis-api/src/lib.rs").read_text(encoding="utf-8")
    shapes = set()
    for raw in re.findall(r'\.route\(\s*"(/api/v1/[^"]+)"', api):
        shapes.add(re.sub(r":[A-Za-z_][A-Za-z0-9_]*", "{}", raw))
    return shapes


def test_every_declared_core_endpoint_exists_in_the_router():
    """A manifest route must name a Core route that really exists.

    The manifest is the shell's declared read surface. This test exists because
    `/api/v1/machine/assets` was declared while no such Core route existed
    (R6-EXECUTION.md already recorded that mismatch), so the manifest promised a
    projection the canonical writer never served.
    """
    manifest = json.loads((ROOT / "config/desktop/routes-v1.json").read_text(encoding="utf-8"))
    shapes = _core_route_shapes()
    assert shapes, "no Core routes parsed; the parser or the router shape changed"

    missing = []
    for route in manifest["routes"]:
        declared = re.sub(r"\{[^}]+\}", "{}", route["core_endpoint"])
        if declared not in shapes:
            missing.append((route["page_id"], route["core_endpoint"]))
    assert missing == [], f"manifest declares endpoints Core does not serve: {missing}"


def test_machine_growth_uses_the_real_machine_read_route():
    """The machine page reads a persisted machine task, not a phantom asset list."""
    manifest = json.loads((ROOT / "config/desktop/routes-v1.json").read_text(encoding="utf-8"))
    route = next(r for r in manifest["routes"] if r["page_id"] == "machine_growth")
    assert route["core_endpoint"] == "/api/v1/machine/tasks/{task_id}"
    assert route["read_only"] is True
    # And the desktop really calls it.
    shell = (ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs").read_text(encoding="utf-8")
    assert "/api/v1/machine/tasks/" in shell
    assert "machine-growth" in shell


def test_unavailable_domains_are_not_declared_as_core_readiness_routes():
    manifest = json.loads((ROOT / "config/desktop/routes-v1.json").read_text(encoding="utf-8"))
    page_ids = {route["page_id"] for route in manifest["routes"]}
    assert page_ids.isdisjoint({"research", "plugins", "models"})

    api = (ROOT / "crates/archeaxis-api/src/lib.rs").read_text(encoding="utf-8")
    assert '"/api/v1/research' not in api
    assert '"/api/v1/plugins' not in api
    assert '"/api/v1/models' not in api


def test_unavailable_domain_navigation_handlers_do_not_call_core():
    shell = (ROOT / "apps/ArcheAxis.Desktop/MainWindow.axaml.cs").read_text(encoding="utf-8")
    for handler, next_marker in (
        ("private void OnResearchClick", "private void OnOriginalEditorClick"),
        ("private void OnPluginsClick", "private void OnModelsClick"),
        ("private void OnModelsClick", "private void OnSettingsClick"),
    ):
        region = shell.split(handler, 1)[1].split(next_marker, 1)[0]
        assert "SetSection(" in region
        assert "HttpMethod" not in region
        assert "SendAsync(" not in region


def test_import_timeout_is_scoped_without_weakening_core_transport():
    supervisor = (ROOT / "apps/ArcheAxis.Desktop/CoreSupervisor.cs").read_text(encoding="utf-8")
    assert 'Timeout = TimeSpan.FromSeconds(5)' in supervisor
    assert 'Timeout = TimeSpan.FromSeconds(60)' in supervisor
    assert '!machine && method == HttpMethod.Post && path == "/api/v1/imports"' in supervisor
    assert '? ImportHttp : Http;' in supervisor
    assert 'await client.SendAsync(request, ct)' in supervisor
    assert supervisor.count('UseProxy = false, AllowAutoRedirect = false') == 2
    assert 'Core origin mismatch' in supervisor
    assert 'response.RequestMessage?.Headers.Remove("x-archeaxis-launch-token")' in supervisor
