"""Canonical UI contracts: React/Tauri is the only product shell."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/workspace/router.py"


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


def test_tauri_surface_and_ci_share_the_ui_release_gate() -> None:
    frontend = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    tauri = (ROOT / "src-tauri/src/main.rs").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "星环知识平台（ArcheAxis Knowledge）" in frontend
    assert '.title("星环知识平台（ArcheAxis Knowledge）")' in tauri
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
