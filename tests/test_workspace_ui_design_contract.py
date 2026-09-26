"""Legacy React/Tauri recovery contracts and formal-shell authority guards."""
from __future__ import annotations

from pathlib import Path
import json

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/workspace/router.py"


def test_formal_product_shell_is_avalonia_and_web_shell_is_legacy() -> None:
    contract = json.loads((ROOT / "config/product/UI_CONTRACT_V2.json").read_text(encoding="utf-8"))

    assert contract["productShell"]["base"] == "ArcheAxis C#/Avalonia"
    assert contract["productShell"]["mode"] == "formal-desktop-shell"
    assert contract["productShell"]["productionEntrypoint"] == "apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj"
    assert contract["productShell"]["webCompatibilityRole"] == "legacy-recovery-and-behavior-reference"


def test_loopback_workspace_no_longer_exposes_or_packages_a_second_product_ui() -> None:
    response = TestClient(app).get("/workspace", follow_redirects=False)
    router = ROUTER.read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert response.status_code == 410
    assert response.json()["canonical_surface"] == "desktop"
    assert not (ROOT / "app/workspace/ui").exists()
    assert "def workspace_asset(" not in router
    assert '"app.workspace" = ["ui/' not in pyproject


def test_legacy_knowledge_dashboard_does_not_redirect_to_a_retired_loopback_ui() -> None:
    response = TestClient(app).get("/kb/", follow_redirects=False)

    assert response.status_code == 410


def test_legacy_tauri_recovery_surface_remains_covered_by_compatibility_ci() -> None:
    frontend = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    tauri = (ROOT / "src-tauri/src/main.rs").read_text(encoding="utf-8")
    desktop_lib = (ROOT / "desktop/src-tauri/src/lib.rs").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "星环知识平台" in frontend
    assert "ArcheAxis Knowledge" in frontend
    assert '.title("星环知识")' in desktop_lib
    assert "Enforce OSUI design and Chinese-first frontend contracts" in workflow
    assert "npm test -- --run" in workflow


def test_tauri_creates_recovery_webview_before_blocking_backend_startup() -> None:
    source = (ROOT / "src-tauri/src/main.rs").read_text(encoding="utf-8")
    setup = source[source.index(".setup(move |app|"):source.index(".on_window_event")]

    assert setup.index("WebviewWindowBuilder::new") < setup.index("std::thread::spawn")
    assert setup.index("std::thread::spawn") < setup.index("BackendProcess::launch")


def test_canonical_library_uses_the_validated_pdf_endpoint_and_sandbox() -> None:
    library = (ROOT / "frontend/src/spaces/LibrarySpace.tsx").read_text(encoding="utf-8")
    client = (ROOT / "frontend/src/api/workspace.ts").read_text(encoding="utf-8")

    assert "downloadPdfAsset(asset.raw_sha256)" in library
    assert 'sandbox=""' in library
    assert "/workspace/api/pdf/sha256:" in client
    assert "/workspace/api/library/${encodeURIComponent(rawSha256)}/content" in client
