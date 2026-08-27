from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def _loopback_write_request() -> object:
    from starlette.requests import Request

    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "http",
            "path": "/workspace/api/delivery/dispatch",
            "query_string": b"",
            "headers": [(b"host", b"127.0.0.1:8000")],
            "client": ("127.0.0.1", 4242),
            "server": ("127.0.0.1", 8000),
        }
    )


def test_browser_smoke_write_bypass_requires_explicit_opt_in(monkeypatch) -> None:
    """The legacy browser smoke may bypass only in its explicit test process."""
    from app.workspace.router import _require_desktop_write_request

    monkeypatch.delenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", raising=False)
    monkeypatch.delenv("COGNITIVE_DESKTOP_LAUNCH_TOKEN", raising=False)
    monkeypatch.delenv("ARCHEAXIS_BROWSER_SMOKE_WRITE_BYPASS", raising=False)
    with pytest.raises(HTTPException) as rejected:
        _require_desktop_write_request(_loopback_write_request())
    assert rejected.value.status_code == 503

    monkeypatch.setenv("ARCHEAXIS_BROWSER_SMOKE_WRITE_BYPASS", "1")
    _require_desktop_write_request(_loopback_write_request())


def test_source_archive_projection_lists_retained_originals_without_paths(tmp_path, monkeypatch) -> None:
    from app.ingestion.raw_asset import RawAssetStore
    from app.main import app
    from app.workspace import router

    database = tmp_path / "archeaxis.sqlite"
    RawAssetStore(root=tmp_path / "source_archive" / "raw-assets").store_original(
        b"immutable source bytes", "notes.md"
    )
    monkeypatch.setattr(router, "DB_PATH", database)

    response = TestClient(app).get("/workspace/api/library")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["source_name"] == "notes.md"
    assert item["size_bytes"] == len(b"immutable source bytes")
    assert item["conversion_state"] == "retained"
    assert len(item["raw_sha256"]) == 64
    assert "path" not in item


def test_source_archive_content_opens_only_by_sha256(tmp_path, monkeypatch) -> None:
    from app.ingestion.raw_asset import RawAssetStore
    from app.main import app
    from app.workspace import router

    database = tmp_path / "archeaxis.sqlite"
    record = RawAssetStore(root=tmp_path / "source_archive" / "raw-assets").store_original(
        b"immutable source bytes", "notes.md", mime_type="text/markdown"
    )
    monkeypatch.setattr(router, "DB_PATH", database)

    response = TestClient(app).get(
        f"/workspace/api/library/{record.sha256}/content"
    )

    assert response.status_code == 200
    assert response.content == b"immutable source bytes"
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "notes.md" in response.headers["content-disposition"]
    assert str(tmp_path) not in response.text


def test_source_archive_content_rejects_invalid_or_missing_digest(
    tmp_path, monkeypatch
) -> None:
    from app.main import app
    from app.workspace import router

    monkeypatch.setattr(router, "DB_PATH", tmp_path / "archeaxis.sqlite")
    client = TestClient(app)

    assert client.get("/workspace/api/library/not-a-digest/content").status_code == 422
    assert client.get(
        f"/workspace/api/library/{'a' * 64}/content"
    ).status_code == 404


def test_evidence_anchor_api_uses_cursor_pagination_without_internal_rowids(tmp_path, monkeypatch) -> None:
    from app.evidence.anchor import build_evidence_anchor, store_evidence_anchor
    from app.main import app
    from app.workspace import router

    database = tmp_path / "archeaxis.sqlite"
    for index in range(3):
        store_evidence_anchor(
            database,
            build_evidence_anchor(
                raw_sha256=f"{index:x}" * 64,
                source_revision=f"revision-{index}",
                locator={"page": index + 1},
            ),
        )
    monkeypatch.setattr(router, "DB_PATH", database)
    client = TestClient(app)

    first = client.get("/workspace/api/evidence/anchors?limit=2")

    assert first.status_code == 200, first.text
    first_page = first.json()
    assert first_page["count"] == 2
    assert [item["source_revision"] for item in first_page["items"]] == ["revision-0", "revision-1"]
    assert isinstance(first_page["next_cursor"], str)
    assert "rowid" not in first_page["next_cursor"]

    second = client.get(
        "/workspace/api/evidence/anchors",
        params={"limit": 2, "cursor": first_page["next_cursor"]},
    )
    assert second.status_code == 200, second.text
    assert [item["source_revision"] for item in second.json()["items"]] == ["revision-2"]
    assert second.json()["next_cursor"] is None
    assert client.get("/workspace/api/evidence/anchors?cursor=invalid").status_code == 422


def test_bundle_inspection_route_projects_real_governed_ledger(tmp_path, monkeypatch) -> None:
    from app.evidence.ledger import EvidenceBundleDraft, EvidenceBundleEntry, store_bundle
    from app.main import app
    from app.workspace import router
    from shared.migration_runner import MigrationOperator

    database = tmp_path / "archeaxis.sqlite"
    database.touch()
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "knowledge-governance.sqlite"
    )
    store_bundle(
        EvidenceBundleDraft(
            bundle_id="workspace-bundle", claim_id="workspace-claim",
            entries=[
                EvidenceBundleEntry(
                    entry_id="workspace-entry", relation_kind="supports", raw_sha256="a" * 64,
                    source_revision="2026-08-24T00:00:00Z", anchor={"page": 1},
                    source_lineage="publisher", source_kind="document", scope="education", rights="cc-by-4.0",
                )
            ],
        ),
        db_path=database,
    )
    monkeypatch.setattr(router, "DB_PATH", database)

    client = TestClient(app)
    response = client.get("/workspace/api/evidence/bundles/workspace-bundle/inspection")

    assert response.status_code == 200, response.text
    projection = response.json()
    assert projection["bundle_id"] == "workspace-bundle"
    assert projection["rights"] == ["cc-by-4.0"]
    assert projection["version_history"] == []

    summaries = client.get("/workspace/api/evidence/bundles?limit=10")
    assert summaries.status_code == 200, summaries.text
    summary_items = summaries.json()["items"]
    assert len(summary_items) == 1
    assert summary_items[0]["bundle_id"] == "workspace-bundle"
    assert summary_items[0]["claim_id"] == "workspace-claim"
    assert summary_items[0]["review_decision"] is None
    assert summary_items[0]["created_at"]


def test_tauri_origin_requires_exact_desktop_launch_token(tmp_path, monkeypatch) -> None:
    from app.main import app
    from app.workspace import router

    monkeypatch.setattr(router, "DB_PATH", tmp_path / "archeaxis.sqlite")
    monkeypatch.setenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", "test-launch-token-1234567890")
    client = TestClient(app)
    headers = {
        "Origin": "http://tauri.localhost:5173",
        "Sec-Fetch-Site": "cross-site",
        "X-ArcheAxis-Launch-Token": "wrong-token",
    }
    assert client.get("/workspace/api/diagnostics", headers=headers).status_code == 403
    headers["X-ArcheAxis-Launch-Token"] = "test-launch-token-1234567890"
    accepted = client.get("/workspace/api/diagnostics", headers=headers)
    assert accepted.status_code == 200
    assert accepted.headers["access-control-allow-origin"] == "http://tauri.localhost:5173"


def test_external_dev_origin_requires_flag_and_exact_launch_token(tmp_path, monkeypatch) -> None:
    from app.main import app
    from app.workspace import router

    monkeypatch.setattr(router, "DB_PATH", tmp_path / "archeaxis.sqlite")
    monkeypatch.setenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", "test-launch-token-1234567890")
    headers = {
        "Origin": "http://127.0.0.1:5173",
        "Sec-Fetch-Site": "same-site",
        "X-ArcheAxis-Launch-Token": "test-launch-token-1234567890",
    }
    client = TestClient(app)

    assert client.get("/workspace/api/diagnostics", headers=headers).status_code == 403
    monkeypatch.setenv("ARCHEAXIS_EXTERNAL_DEV", "1")
    headers["X-ArcheAxis-Launch-Token"] = "wrong-token"
    assert client.get("/workspace/api/diagnostics", headers=headers).status_code == 403
    headers["X-ArcheAxis-Launch-Token"] = "test-launch-token-1234567890"
    accepted = client.get("/workspace/api/diagnostics", headers=headers)
    assert accepted.status_code == 200
    assert accepted.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_desktop_write_rejects_missing_token_scope_or_idempotency_key(tmp_path, monkeypatch) -> None:
    """A React-backed write needs all three desktop intent proofs."""
    from app.main import app
    from app.workspace import router

    monkeypatch.setenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", "test-launch-token-1234567890")
    monkeypatch.setenv("ARCHEAXIS_DESKTOP_WRITE_SCOPES", "workspace:write")
    monkeypatch.setattr(router, "_backup_root", lambda: tmp_path / "backups")
    monkeypatch.setattr(router, "resolve_runtime_path", lambda _name: tmp_path / "data")
    client = TestClient(app)

    assert client.post("/workspace/api/backup/create", json={"name": "release"}).status_code == 403
    assert client.post(
        "/workspace/api/backup/create",
        headers={"X-ArcheAxis-Launch-Token": "test-launch-token-1234567890"},
        json={"name": "release"},
    ).status_code == 403
    assert client.post(
        "/workspace/api/backup/create",
        headers={
            "X-ArcheAxis-Launch-Token": "test-launch-token-1234567890",
            "X-ArcheAxis-Scopes": "workspace:write",
        },
        json={"name": "release"},
    ).status_code == 422
    assert client.post(
        "/workspace/api/backup/create",
        headers={
            "X-ArcheAxis-Launch-Token": "test-launch-token-1234567890",
            "X-ArcheAxis-Scopes": "workspace:write admin",
            "Idempotency-Key": "workspace-backup-regression-extra-scope",
        },
        json={"name": "release"},
    ).status_code == 403
    accepted = client.post(
        "/workspace/api/backup/create",
        headers={
            "X-ArcheAxis-Launch-Token": "test-launch-token-1234567890",
            "X-ArcheAxis-Scopes": "workspace:write",
            "Idempotency-Key": "workspace-backup-regression-1",
        },
        json={"name": "release"},
    )
    assert accepted.status_code == 200, accepted.text


def test_desktop_learning_write_requires_the_same_token_scope_and_idempotency_proofs(
    monkeypatch,
) -> None:
    from app.main import app

    monkeypatch.setenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", "test-launch-token-1234567890")
    monkeypatch.setenv("ARCHEAXIS_DESKTOP_WRITE_SCOPES", "workspace:write")
    client = TestClient(app)
    payload = {
        "record_id": "teach-back-1",
        "concept": "BKT",
        "restatement": "BKT models learned knowledge as a changing probability.",
        "reference": "BKT models a learner's knowledge probability over time.",
        "key_terms": ["knowledge", "probability"],
    }

    assert client.post("/api/v1/learning/teach-back", json=payload).status_code == 403
    accepted = client.post(
        "/api/v1/learning/teach-back",
        headers={
            "X-ArcheAxis-Launch-Token": "test-launch-token-1234567890",
            "X-ArcheAxis-Scopes": "workspace:write",
            "Idempotency-Key": "workspace-learning-teach-back-1",
        },
        json=payload,
    )
    assert accepted.status_code == 200, accepted.text


def test_desktop_delivery_controls_require_the_shared_write_intent(monkeypatch) -> None:
    from app.main import app

    monkeypatch.setenv("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", "test-launch-token-1234567890")
    monkeypatch.setenv("ARCHEAXIS_DESKTOP_WRITE_SCOPES", "workspace:write")
    client = TestClient(app)
    assert client.post("/workspace/api/delivery/dispatch").status_code == 403
    assert client.post("/workspace/api/delivery/retry").status_code == 403
    headers = {
        "X-ArcheAxis-Launch-Token": "test-launch-token-1234567890",
        "X-ArcheAxis-Scopes": "workspace:write",
        "Idempotency-Key": "workspace-delivery-control-1",
    }
    assert client.post("/workspace/api/delivery/dispatch", headers=headers).status_code == 200
    assert client.post("/workspace/api/delivery/retry", headers=headers).status_code == 200


def test_all_react_learning_write_routes_require_desktop_write_intent() -> None:
    """Keep future Learning writes from bypassing the shared desktop boundary."""
    from app.api.learning import router as learning_router
    from app.workspace.router import _require_desktop_write_request

    protected_paths = {
        "/api/v1/learning/teach-back",
        "/api/v1/learning/distill",
        "/api/v1/learning/trajectory",
        "/api/v1/learning/tick",
        "/api/v1/learning/learning-path",
        "/api/v1/learning/review-outcome",
    }
    routes = {
        route.path: route
        for route in learning_router.routes
        if "POST" in getattr(route, "methods", set())
    }
    assert set(routes) == protected_paths
    for route in routes.values():
        assert any(
            dependency.dependency is _require_desktop_write_request
            for dependency in route.dependencies
        )


def test_local_workspace_page_and_safe_diagnostics_are_available() -> None:
    from app.main import app

    client = TestClient(app)

    page = client.get("/workspace")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert page.headers["content-security-policy"] == (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; img-src 'self' data:; font-src 'self' data:; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )
    assert page.headers["x-content-type-options"] == "nosniff"
    assert page.headers["referrer-policy"] == "no-referrer"
    assert page.headers["x-frame-options"] == "DENY"
    assert "星环知识平台" in page.text
    assert "ArcheAxis Knowledge" in page.text
    assert "元枢·观心" not in page.text
    assert "archeaxis-workspace" not in page.text
    assert "API key" not in page.text
    assert 'id="intake-url-form"' in page.text
    assert 'id="intake-file-form"' in page.text
    assert "command_id" not in page.text
    assert "fonts.googleapis.com" not in page.text
    assert "onclick=" not in page.text
    for fabricated_claim in (
        "536 tests passed",
        "PostgreSQL 适配层",
        "Qdrant 兼容层",
        "本地服务全部可达",
        "队列 5 / 并发 2",
        "生成 ArcheAxis 原型",
    ):
        assert fabricated_claim not in page.text
    assert "尚未接入真实数据" in page.text

    stylesheet = client.get("/workspace/assets/styles.css")
    assert stylesheet.status_code == 200
    assert stylesheet.headers["content-type"].startswith("text/css")
    assert stylesheet.headers["x-content-type-options"] == "nosniff"
    assert "--accent:#C8A972" in stylesheet.text
    assert "fonts.googleapis.com" not in stylesheet.text
    application = client.get("/workspace/assets/app.js")
    assert application.status_code == 200
    assert "javascript" in application.headers["content-type"]
    assert application.headers["x-content-type-options"] == "nosniff"
    assert "Command Palette" not in application.text

    diagnostics = client.get("/workspace/api/diagnostics")
    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["schema_version"] == "v1"
    assert "database_path" not in diagnostics.text
    assert "backup_path" not in diagnostics.text


def test_workspace_static_assets_are_allowlisted_and_local_only(monkeypatch) -> None:
    from app.main import app
    from shared.config import config

    client = TestClient(app)
    for path in (
        "/workspace/assets/README.md",
        "/workspace/assets/generate.py",
        "/workspace/assets/unknown.js",
        "/workspace/assets/%2e%2e/%2e%2e/pyproject.toml",
    ):
        assert client.get(path).status_code in {404, 422}

    assert TestClient(app, base_url="http://192.168.1.10").get("/workspace").status_code == 403
    assert client.post(
        "/workspace/api/intake/url",
        headers={"Origin": "https://evil.example"},
        json={"url": "https://example.com"},
    ).status_code == 403
    assert client.post(
        "/workspace/api/intake/url",
        headers={"Sec-Fetch-Site": "cross-site"},
        json={"url": "https://example.com"},
    ).status_code == 403

    monkeypatch.setitem(config._data["auth"], "enabled", True)
    assert client.get("/workspace").status_code == 200


def test_workspace_runtime_assets_are_packaged() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert (root / "app/workspace/ui/index.html").is_file()
    assert (root / "app/workspace/ui/assets/styles.css").is_file()
    assert (root / "app/workspace/ui/assets/app.js").is_file()
    assert (root / "app/workspace/ui/assets/pdf-loader.mjs").is_file()
    assert (root / "app/workspace/ui/assets/pdf.mjs").is_file()
    assert (root / "app/workspace/ui/assets/pdf.worker.mjs").is_file()
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert '"app.workspace" = ["ui/*.html", "ui/assets/*.css", "ui/assets/*.js", "ui/assets/*.mjs", "ui/assets/licenses/*.txt"]' in pyproject


def test_workspace_pdf_runtime_disables_eval_and_document_scripting() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    page = (root / "app/workspace/ui/index.html").read_text(encoding="utf-8")
    loader = (root / "app/workspace/ui/assets/pdf-loader.mjs").read_text(encoding="utf-8")
    application = (root / "app/workspace/ui/assets/app.js").read_text(encoding="utf-8")
    router_source = (root / "app/workspace/router.py").read_text(encoding="utf-8")

    assert 'type="module"' in page
    assert 'src="/workspace/assets/pdf-loader.mjs"' in page
    assert 'pdf.mjs' in loader
    assert 'await import("/workspace/assets/app.js")' in loader
    assert 'pdf.worker.mjs' in application
    assert "isEvalSupported: false" in application
    assert "enableScripting: false" in application
    assert '"pdf-loader.mjs"' in router_source
    assert '"pdf.mjs"' in router_source
    assert '"pdf.worker.mjs"' in router_source


def test_workspace_page_router_reacts_to_browser_hash_changes() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    application = (root / "app/workspace/ui/assets/app.js").read_text(encoding="utf-8")

    assert "addEventListener('hashchange'" in application
    assert "openPage(location.hash.slice(1)||'overview')" in application
    assert "const productRoutes=new Set" in application
    assert "document.getElementById(`page-${page}`)" in application
    assert "querySelector(`#page-${page}`)" not in application


def test_workspace_frontend_status_and_intake_fail_closed() -> None:
    from pathlib import Path

    application = (
        Path(__file__).resolve().parents[1] / "app/workspace/ui/assets/app.js"
    ).read_text(encoding="utf-8")

    assert "function validateStatus(payload)" in application
    assert "function renderStatusUnavailable()" in application
    assert "capabilities.textContent=''" in application
    assert "result.textContent='处理中…'" in application
    assert "无法连接本地服务，请重试" in application
    assert "payload.engine||'自动'" not in application
    assert "payload.char_count||0" not in application
    assert "payload.format||payload.source_type||'网页'" not in application


def test_workspace_click_dispatch_does_not_treat_body_theme_as_a_button() -> None:
    from pathlib import Path

    application = (
        Path(__file__).resolve().parents[1] / "app/workspace/ui/assets/app.js"
    ).read_text(encoding="utf-8")

    assert "event.target.closest('button[data-theme]')" in application
    assert "event.target.closest('[data-theme]')" not in application


def test_workspace_diagnostics_ui_uses_the_safe_diagnostics_api() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    page = (root / "app/workspace/ui/index.html").read_text(encoding="utf-8")
    application = (root / "app/workspace/ui/assets/app.js").read_text(encoding="utf-8")

    assert 'id="diagnostics-summary"' in page
    assert "'/workspace/api/status'" in application
    assert "'/workspace/api/diagnostics'" not in application
    assert "本地状态读取失败" in application


def test_workspace_job_center_does_not_render_fake_execution_progress() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    page = (root / "app/workspace/ui/index.html").read_text(encoding="utf-8")
    application = (root / "app/workspace/ui/assets/app.js").read_text(encoding="utf-8")

    assert 'class="job collapsed"' not in page
    assert "原型任务" not in page
    assert "job-toggle" not in application
    assert "当前阶段" in page


def test_workspace_evidence_lifecycle_page_is_wired_in_ui() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    page = (root / "app/workspace/ui/index.html").read_text(encoding="utf-8")
    application = (root / "app/workspace/ui/assets/app.js").read_text(encoding="utf-8")

    assert 'id="page-evidence"' in page
    assert "'evidence'" in application
    assert "lifecycle" in page.lower() or "证据" in page
    assert "validateLifecycle" in application
    assert "renderLifecycle" in application
    assert "refreshLifecycle" in application
    assert "renderLifecycleUnavailable" in application
    assert "'/workspace/api/lifecycle'" in application
    assert "permission" in application and "execution" in application
    assert "evaluation" in application and "lesson" in application
    assert "command_id" not in page
    assert "package_id" not in page


def test_workspace_lifecycle_frontend_fail_closed_and_schema_validation() -> None:
    from pathlib import Path

    application = (
        Path(__file__).resolve().parents[1] / "app/workspace/ui/assets/app.js"
    ).read_text(encoding="utf-8")

    assert "function validateLifecycle(payload)" in application
    assert "function renderLifecycle(payload)" in application
    assert "function renderLifecycleUnavailable()" in application
    assert "lifecycle-refresh" in application
    assert "本地生命周期读取失败" in application


def test_workspace_lifecycle_ui_navigation_wires_evidence_page() -> None:
    from pathlib import Path

    application = (
        Path(__file__).resolve().parents[1] / "app/workspace/ui/assets/app.js"
    ).read_text(encoding="utf-8")

    assert "page==='evidence'" in application or "'evidence'" in application
    assert "lifecycle" in application


def test_workspace_status_returns_only_real_aggregate_state(monkeypatch, tmp_path) -> None:
    from datetime import datetime

    from app.main import app
    from app.workspace import router, service
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(router, "DB_PATH", database)
    monkeypatch.setattr(
        service,
        "convert_url",
        lambda _url: ("# Truthful workspace status\nVerified local content.", "test"),
    )
    service.intake_url(url="https://example.com/truth", db_path=database)

    response = TestClient(app).get("/workspace/api/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "v1"
    assert datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00")).tzinfo is not None
    assert payload["components"] == {
        "api": "available",
        "database": "available",
        "worker": "available",
        "outbox_dispatcher": "lease_fenced",
        "server_sent_events": "not_connected",
    }
    assert payload["migrations"]
    assert set(payload["migrations"]) <= {
        "applied",
        "pending",
        "failed",
        "rolled_back",
        "unavailable",
    }
    assert payload["counts"]["research"] == {"candidate": 1}
    assert payload["counts"]["jobs"] == {"succeeded": 1}
    assert payload["counts"]["outbox"] == {"pending": 1}
    assert payload["capabilities"]["asynchronous_worker"] == "available"
    assert payload["capabilities"]["interactive_job_center"] == "available"
    assert "database_path" not in response.text
    assert "backup_path" not in response.text
    assert '"job_id"' not in response.text
    assert '"package_id"' not in response.text
    assert '"command_id"' not in response.text

    def unavailable_status(_operator):
        raise RuntimeError("live migration probe requires a checkpoint")

    monkeypatch.setattr(MigrationOperator, "status", unavailable_status)
    unavailable = TestClient(app).get("/workspace/api/status")
    assert unavailable.status_code == 200
    assert unavailable.json()["migrations"] == {"unavailable": 1}
    assert unavailable.json()["components"]["database"] == "available"


def test_workspace_mutations_use_local_principal_without_api_credentials(monkeypatch) -> None:
    from app.main import app
    from app.workspace import router

    received: dict[str, object] = {}

    def promote(**kwargs):
        received.update(kwargs)
        return {"status": "candidate"}

    monkeypatch.setattr(router.service, "promote_research", promote)
    payload = {"command_id": "cmd-local", "package_id": "pkg-local", "rationale": "reviewed"}
    response = TestClient(app).post(
        "/workspace/api/commands/promote-research",
        json=payload,
    )

    assert response.status_code == 200
    assert received["reviewer_id"] == "local-workspace"
    assert TestClient(app).post(
        "/workspace/api/commands/promote-research",
        json={**payload, "reviewer_id": "forged"},
    ).status_code == 422


def test_workspace_intake_accepts_web_sources_and_uploaded_text(monkeypatch, tmp_path) -> None:
    from app.main import app
    from app.workspace import router
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(router, "DB_PATH", database)
    monkeypatch.setattr(
        router.service,
        "intake_url",
        lambda *, url, db_path: {
            "source_type": "web",
            "source": url,
            "content": "# extracted",
            "engine": "test",
            "requires_human_review": True,
            "source_count": 1,
            "claim_count": 1,
            "evidence_count": 1,
        },
    )
    client = TestClient(app)

    webpage = client.post("/workspace/api/intake/url", json={"url": "https://example.com/article"})
    assert webpage.status_code == 200
    assert webpage.json()["source_type"] == "web"

    uploaded = client.post(
        "/workspace/api/intake/upload",
        files={"file": ("notes.txt", b"local intake content", "text/plain")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["source_type"] == "file"
    assert uploaded.json()["file_name"] == "notes.txt"
    assert "local intake content" in uploaded.json()["content_preview"]
    assert uploaded.json()["requires_human_review"] is True
    assert not {"package_id", "job_id", "command_id", "status"} & uploaded.json().keys()

    import sqlite3

    from app.facades.research import get_research_package

    with sqlite3.connect(database) as connection:
        package_id = connection.execute("SELECT id FROM research_packages_v1").fetchone()[0]
    package = get_research_package(str(package_id), db_path=database)
    assert package.package.status == "candidate"
    assert package.sources[0].content == "local intake content"


def test_workspace_web_intake_persists_a_minimal_candidate_research_package(
    monkeypatch, tmp_path,
) -> None:
    from app.facades.research import get_research_package
    from app.workspace import service
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(service, "convert_url", lambda url: ("# Grounded article\nBody.", "safe-http-test"))

    result = service.intake_url(url="https://example.com/article", db_path=database)

    assert result == {
        "source_type": "web",
        "source": "https://example.com/article",
        "package_id": result["package_id"],
        "job_id": result["job_id"],
        "status": "candidate",
        "requires_human_review": True,
        "source_count": 1,
        "claim_count": 1,
        "evidence_count": 1,
    }
    package = get_research_package(result["package_id"], db_path=database)
    assert package.canonical_url == "https://example.com/article"
    assert package.sources[0].source_locator == "https://example.com/article"
    assert package.sources[0].content == "# Grounded article\nBody."

    import sqlite3
    from contextlib import closing

    with closing(sqlite3.connect(database)) as second_connection:
        job = second_connection.execute(
            "SELECT command_id, aggregate_id, state FROM workspace_jobs_v1"
        ).fetchone()
        outbox = second_connection.execute(
            "SELECT event_type, state FROM workspace_outbox_v1"
        ).fetchone()
        receipt = second_connection.execute(
            "SELECT command_id, job_id FROM workspace_command_receipts_v1"
        ).fetchone()
    assert job is not None
    assert job[1:] == (result["package_id"], "succeeded")
    assert outbox == ("intake.research.succeeded", "pending")
    assert receipt is not None
    assert receipt[0] == job[0]


def test_workspace_http_job_readback_reloads_package_and_rejects_tampering(
    monkeypatch, tmp_path,
) -> None:
    import json
    import sqlite3

    from fastapi.testclient import TestClient

    from app.main import app
    from app.workspace import router, service
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(router, "DB_PATH", database)
    monkeypatch.setattr(service, "convert_url", lambda url: ("# Job readback\nBody.", "test"))

    payload = service.intake_url(
        url="https://example.com/job-readback",
        db_path=database,
    )

    loaded = TestClient(app).get(f"/workspace/api/jobs/{payload['job_id']}")
    assert loaded.status_code == 200
    assert loaded.json() | {"updated_at": "ignored"} == {
        "job_id": payload["job_id"],
        "state": "succeeded",
        "event_type": "intake.research.succeeded",
        "outbox_state": "pending",
        "package_id": payload["package_id"],
        "package_status": "candidate",
        "source_count": 1,
        "updated_at": "ignored",
    }

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        job = connection.execute(
            "SELECT command_id, state, payload_json, correlation_id, causation_id "
            "FROM workspace_jobs_v1 WHERE job_id=?",
            (payload["job_id"],),
        ).fetchone()
        outbox = connection.execute(
            "SELECT event_id, state, payload_json FROM workspace_outbox_v1 WHERE job_id=?",
            (payload["job_id"],),
        ).fetchone()
        receipt = connection.execute(
            "SELECT command_type, request_fingerprint, result_json "
            "FROM workspace_command_receipts_v1 WHERE job_id=?",
            (payload["job_id"],),
        ).fetchone()
    assert job is not None and outbox is not None and receipt is not None
    extra_result = {**json.loads(receipt["result_json"]), "unexpected": True}
    mutations = [
        ("workspace_jobs_v1", "state", "queued", job["state"]),
        ("workspace_jobs_v1", "correlation_id", "tampered", job["correlation_id"]),
        ("workspace_jobs_v1", "causation_id", "tampered", job["causation_id"]),
        ("workspace_outbox_v1", "state", "leased", outbox["state"]),
        ("workspace_outbox_v1", "payload_json", "{}", outbox["payload_json"]),
        (
            "workspace_command_receipts_v1",
            "command_id",
            "tampered-command-id",
            job["command_id"],
        ),
        (
            "workspace_command_receipts_v1",
            "command_type",
            "tampered.command",
            receipt["command_type"],
        ),
        (
            "workspace_command_receipts_v1",
            "request_fingerprint",
            "0" * 64,
            receipt["request_fingerprint"],
        ),
        (
            "workspace_command_receipts_v1",
            "result_json",
            json.dumps(extra_result, separators=(",", ":"), sort_keys=True),
            receipt["result_json"],
        ),
        ("workspace_command_receipts_v1", "result_json", "[]", receipt["result_json"]),
    ]
    for table, column, tampered_value, original_value in mutations:
        with sqlite3.connect(database) as connection:
            connection.execute(
                f"UPDATE {table} SET {column}=? WHERE job_id=?",
                (tampered_value, payload["job_id"]),
            )
            connection.commit()
        tampered = TestClient(app).get(f"/workspace/api/jobs/{payload['job_id']}")
        assert tampered.status_code == 409, (table, column, tampered.text)
        with sqlite3.connect(database) as connection:
            connection.execute(
                f"UPDATE {table} SET {column}=? WHERE job_id=?",
                (original_value, payload["job_id"]),
            )
            connection.commit()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE workspace_jobs_v1 SET job_id='job_tampered' WHERE job_id=?",
            (payload["job_id"],),
        )
        connection.commit()
    tampered_job_id = TestClient(app).get(f"/workspace/api/jobs/{payload['job_id']}")
    assert tampered_job_id.status_code == 409
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE workspace_jobs_v1 SET job_id=? WHERE job_id='job_tampered'",
            (payload["job_id"],),
        )
        connection.commit()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE workspace_outbox_v1 SET job_id='job_tampered' WHERE event_id=?",
            (outbox["event_id"],),
        )
        connection.commit()
    misbound_outbox = TestClient(app).get(f"/workspace/api/jobs/{payload['job_id']}")
    assert misbound_outbox.status_code == 409
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE workspace_outbox_v1 SET job_id=? WHERE event_id=?",
            (payload["job_id"], outbox["event_id"]),
        )
        connection.commit()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE workspace_command_receipts_v1 SET job_id='job_tampered' WHERE command_id=?",
            (job["command_id"],),
        )
        connection.commit()
    misbound_receipt = TestClient(app).get(f"/workspace/api/jobs/{payload['job_id']}")
    assert misbound_receipt.status_code == 409


def test_workspace_intake_rolls_back_research_job_and_outbox_together(
    monkeypatch, tmp_path,
) -> None:
    import sqlite3
    from contextlib import closing

    import pytest

    from app.workspace import service
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(service, "convert_url", lambda url: ("# Atomic article\nBody.", "test"))
    original = service.record_completed_command

    def fail_after_job_write(connection, **kwargs):
        original(connection, **kwargs)
        raise RuntimeError("injected outbox transaction failure")

    monkeypatch.setattr(service, "record_completed_command", fail_after_job_write)

    with pytest.raises(RuntimeError, match="injected outbox transaction failure"):
        service.intake_url(url="https://example.com/atomic", db_path=database)

    with closing(sqlite3.connect(database)) as connection:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "research_packages_v1",
                "workspace_jobs_v1",
                "workspace_outbox_v1",
                "workspace_command_receipts_v1",
            )
        }
    assert counts == {table: 0 for table in counts}


def test_workspace_upload_failure_removes_new_file_and_replay_reuses_content_path(
    monkeypatch, tmp_path,
) -> None:
    import pytest

    from app.workspace import service
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )
    original = service.record_completed_command

    def fail_after_job_write(connection, **kwargs):
        original(connection, **kwargs)
        raise RuntimeError("injected upload transaction failure")

    monkeypatch.setattr(service, "record_completed_command", fail_after_job_write)
    with pytest.raises(RuntimeError, match="injected upload transaction failure"):
        service.intake_upload(
            file_name="atomic.txt", content=b"Atomic upload", db_path=database
        )
    upload_dir = database.parent / "intake_uploads"
    assert list(upload_dir.iterdir()) == []
    raw_dir = database.parent / "source_archive" / "raw-assets"
    raw_files = [path for path in raw_dir.iterdir() if path.is_file()]
    assert len(raw_files) == 1
    assert raw_files[0].read_bytes() == b"Atomic upload"
    assert list((raw_dir / "_failures").glob("*.json"))

    monkeypatch.setattr(service, "record_completed_command", original)
    first = service.intake_upload(
        file_name="atomic.txt", content=b"Atomic upload", db_path=database
    )
    replay = service.intake_upload(
        file_name="atomic.txt", content=b"Atomic upload", db_path=database
    )
    assert replay["package_id"] == first["package_id"]
    assert first["raw_sha256"] == replay["raw_sha256"]
    assert len(list(upload_dir.iterdir())) == 1


def test_concurrent_same_upload_keeps_successful_content_when_peer_fails(
    monkeypatch, tmp_path,
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock

    from app.workspace import service
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )
    original = service.record_completed_command
    calls = 0
    lock = Lock()

    def fail_one_request(connection, **kwargs):
        nonlocal calls
        original(connection, **kwargs)
        with lock:
            calls += 1
            should_fail = calls == 1
        if should_fail:
            raise RuntimeError("injected concurrent upload failure")

    monkeypatch.setattr(service, "record_completed_command", fail_one_request)

    def upload_once():
        return service.intake_upload(
            file_name="same.txt",
            content=b"Concurrent atomic upload",
            db_path=database,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(upload_once) for _ in range(2)]
    outcomes = []
    for future in futures:
        try:
            outcomes.append(("ok", future.result()))
        except RuntimeError as exc:
            outcomes.append(("error", str(exc)))
    assert sorted(item[0] for item in outcomes) == ["error", "ok"]
    upload_dir = database.parent / "intake_uploads"
    stored = [path for path in upload_dir.iterdir() if not path.name.startswith(".upload-")]
    assert len(stored) == 1
    assert stored[0].read_bytes() == b"Concurrent atomic upload"
    assert not list(upload_dir.glob(".upload-*"))


def test_workspace_github_intake_persists_a_candidate_research_package(tmp_path) -> None:
    from app.facades.research import get_research_package
    from app.workspace import service
    from shared.migration_runner import MigrationOperator
    from tests.test_phase4_research_github import _transport
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )

    result = service.intake_url(
        url="https://github.com/octo/loop-os",
        db_path=database,
        fetcher=_transport(),
    )

    assert result["source_type"] == "github_repository"
    assert result["status"] == "candidate"
    assert result["requires_human_review"] is True
    package = get_research_package(result["package_id"], db_path=database)
    assert package.package.package_id == result["package_id"]
    assert package.package.status == "candidate"


def test_workspace_http_flow_promotes_persisted_research_and_derives_mastery(
    monkeypatch, tmp_path,
) -> None:
    import sqlite3

    from app.facades.research import research_github_repository
    from app.main import app
    from app.workspace import router
    from shared.config import config
    from tests.test_phase4_research_github import _transport
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    monkeypatch.setattr(router, "DB_PATH", database)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    monkeypatch.setitem(config._data["auth"], "enabled", False)
    client = TestClient(app)

    promoted = client.post(
        "/workspace/api/commands/promote-research",
        json={"command_id": "promote-1", "package_id": graph.package.package_id, "rationale": "grounded"},
    )
    assert promoted.status_code == 200
    conflicting_promotion = client.post(
        "/workspace/api/commands/promote-research",
        json={
            "command_id": "promote-1",
            "package_id": graph.package.package_id,
            "rationale": "changed rationale",
        },
    )
    assert conflicting_promotion.status_code == 409

    claim_id = next(item for item in promoted.json()["unit_ids"] if "claim" in item)
    learning = client.post(
        "/workspace/api/commands/start-learning",
        json={"command_id": "learning-1", "unit_id": claim_id, "rationale": "practice"},
    )
    assert learning.status_code == 200
    assert learning.json()["status"] == "approved"
    assert learning.json()["card_ids"]
    artifact_id = learning.json()["artifact_id"]
    conflicting_learning = client.post(
        "/workspace/api/commands/start-learning",
        json={"command_id": "learning-1", "unit_id": claim_id, "rationale": "changed rationale"},
    )
    assert conflicting_learning.status_code == 409

    for index in range(3):
        practice = client.post(
            "/workspace/api/commands/record-practice",
            json={"command_id": f"practice-{index}", "artifact_id": artifact_id, "quality": 5},
        )
    assert practice.status_code == 200
    assert practice.json()["mastered"] is True
    assert practice.json()["machine_candidate_id"]
    conflicting_practice = client.post(
        "/workspace/api/commands/record-practice",
        json={"command_id": "practice-0", "artifact_id": artifact_id, "quality": 0},
    )
    assert conflicting_practice.status_code == 409
    with sqlite3.connect(database) as connection:
        counts_before_wildcards = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "kb_reviews",
                "mastery_signals_v1",
                "machine_knowledge_candidates_v1",
            )
        )
    wildcard_artifacts = (
        "*",
        artifact_id[:-1] + "?",
        artifact_id[:-1] + f"[{artifact_id[-1]}]",
    )
    for wildcard_artifact in wildcard_artifacts:
        wildcard_replay = client.post(
            "/workspace/api/commands/record-practice",
            json={
                "command_id": "practice-0",
                "artifact_id": wildcard_artifact,
                "quality": 5,
            },
        )
        assert wildcard_replay.status_code == 409
    with sqlite3.connect(database) as connection:
        counts_after_wildcards = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "kb_reviews",
                "mastery_signals_v1",
                "machine_knowledge_candidates_v1",
            )
        )
    assert counts_after_wildcards == counts_before_wildcards
    case = client.get(f"/workspace/api/cases/{artifact_id}")
    assert case.status_code == 200
    assert any(event["event_type"] == "machine_knowledge_candidate_created" for event in case.json()["events"])


def test_workspace_learning_creation_and_approval_roll_back_together(
    monkeypatch, tmp_path,
) -> None:
    import sqlite3

    from app.facades.research import research_github_repository
    from app.knowledge import closed_loop
    from app.main import app
    from app.workspace import router
    from shared.config import config
    from tests.test_phase4_research_github import _transport
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    monkeypatch.setattr(router, "DB_PATH", database)
    monkeypatch.setitem(config._data["auth"], "enabled", False)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )
    client = TestClient(app)
    promoted = client.post(
        "/workspace/api/commands/promote-research",
        json={
            "command_id": "atomic-learning-promotion",
            "package_id": graph.package.package_id,
            "rationale": "grounded",
        },
    )
    assert promoted.status_code == 200
    claim_id = next(item for item in promoted.json()["unit_ids"] if "claim" in item)

    def fail_after_artifact_write(connection, *args, **kwargs):
        assert connection.execute(
            "SELECT COUNT(*) FROM knowledge_candidate_learning_artifacts_v1"
        ).fetchone()[0] == 1
        raise RuntimeError("injected learning approval failure")

    monkeypatch.setattr(
        closed_loop, "approve_artifact_cards_on_connection", fail_after_artifact_write
    )
    failed = client.post(
        "/workspace/api/commands/start-learning",
        json={
            "command_id": "atomic-learning",
            "unit_id": claim_id,
            "rationale": "must roll back",
        },
    )
    assert failed.status_code == 409
    with sqlite3.connect(database) as connection:
        counts = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "knowledge_candidate_learning_artifacts_v1",
                "learning_approval_events_v1",
                "kb_cards",
            )
        )
    assert counts == (0, 0, 0)


def test_workspace_http_commands_serialize_same_id_semantic_conflicts(
    monkeypatch, tmp_path,
) -> None:
    import sqlite3
    from concurrent.futures import ThreadPoolExecutor

    from app.facades.research import research_github_repository
    from app.main import app
    from app.workspace import router
    from shared import storage
    from shared.config import config
    from shared.migration_runner import MigrationOperator
    from tests.test_phase4_research_github import _transport
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    operator = MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups")
    operator.apply("sleep-loop.sqlite")
    operator.apply("taskpack.sqlite")
    operator.apply("workspace.sqlite")
    monkeypatch.setattr(router, "DB_PATH", database)
    monkeypatch.setattr(storage, "DB_PATH", database)
    monkeypatch.setitem(config._data["auth"], "enabled", False)
    monkeypatch.setitem(config._data["rate_limit"], "enabled", False)
    graph = research_github_repository(
        "https://github.com/octo/loop-os", fetcher=_transport(), db_path=database
    )

    with TestClient(app) as client:

        def post(path: str, payload: dict[str, object]):
            return client.post(path, json=payload)

        promotion_payloads = [
            {
                "command_id": "concurrent-promote",
                "package_id": graph.package.package_id,
                "rationale": "semantic-a" if index < 4 else "semantic-b",
            }
            for index in range(8)
        ]
        with ThreadPoolExecutor(max_workers=8) as pool:
            promotions = list(
                pool.map(
                    lambda payload: post("/workspace/api/commands/promote-research", payload),
                    promotion_payloads,
                )
            )
        assert sorted(response.status_code for response in promotions) == [200] * 4 + [
            409
        ] * 4
        promotion = next(response.json() for response in promotions if response.status_code == 200)
        claim_id = next(item for item in promotion["unit_ids"] if "claim" in item)

        learning_payloads = [
            {
                "command_id": "concurrent-learning",
                "unit_id": claim_id,
                "rationale": "semantic-a" if index < 4 else "semantic-b",
            }
            for index in range(8)
        ]
        with ThreadPoolExecutor(max_workers=8) as pool:
            learnings = list(
                pool.map(
                    lambda payload: post("/workspace/api/commands/start-learning", payload),
                    learning_payloads,
                )
            )
        assert sorted(response.status_code for response in learnings) == [200] * 4 + [409] * 4
        artifact_id = next(
            response.json()["artifact_id"]
            for response in learnings
            if response.status_code == 200
        )

        practice_payloads = [
            {
                "command_id": "concurrent-practice",
                "artifact_id": artifact_id,
                "quality": 5 if index < 4 else 0,
            }
            for index in range(8)
        ]
        with ThreadPoolExecutor(max_workers=8) as pool:
            practices = list(
                pool.map(
                    lambda payload: post("/workspace/api/commands/record-practice", payload),
                    practice_payloads,
                )
            )
        assert sorted(response.status_code for response in practices) == [200] * 4 + [409] * 4
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM knowledge_candidate_governance_events_v1 "
            "WHERE approval_id='concurrent-promote'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM knowledge_candidate_learning_artifacts_v1 "
            "WHERE approval_id='concurrent-learning'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM kb_reviews WHERE id LIKE 'practice_%'"
        ).fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM mastery_signals_v1").fetchone()[0] == 1


def test_workspace_jobs_reads_live_wal_after_http_style_intake(monkeypatch, tmp_path) -> None:
    """Internal Job Center projections must read an active WAL safely."""
    import sqlite3

    from app.workspace import service
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "backups").apply(
        "workspace.sqlite"
    )
    monkeypatch.setattr(service, "convert_url", lambda _: ("# live wal\nBody.", "test"))

    intake = service.intake_url(url="https://example.com/live-wal", db_path=database)
    writer = sqlite3.connect(database, timeout=30.0)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("UPDATE workspace_jobs_v1 SET updated_at=updated_at")
    writer.commit()
    sidecars = [database.with_name(f"{database.name}{suffix}") for suffix in ("-wal", "-shm")]
    try:
        assert any(sidecar.exists() for sidecar in sidecars)
        jobs = service.workspace_jobs(db_path=database)
        assert jobs["jobs"][0]["state"] == "succeeded"
        assert jobs["jobs"][0]["delivery_state"] == "pending"
        assert intake["job_id"]
    finally:
        writer.close()


def test_workspace_capability_projection_is_honest(monkeypatch, tmp_path) -> None:
    """AXW-010B: the status endpoint must project capabilities truthfully. Any
    unimplemented capability must read not_implemented, never available, so a
    route can never claim a capability the installed runtime does not provide.
    """
    from app.main import app
    from app.workspace import router
    from shared.migration_runner import MigrationOperator
    from tests.test_phase5_mcs_closed_loop import _database

    database = _database(tmp_path)
    MigrationOperator(db_path=database, backup_dir=tmp_path / "workspace-backups").apply(
        "workspace.sqlite"
    )

    monkeypatch.setattr(router, "DB_PATH", database)

    response = TestClient(app).get("/workspace/api/status")
    assert response.status_code == 200
    caps = response.json()["capabilities"]

    # ASR has no real engine -> must stay not_implemented (never available).
    assert caps["asr_transcription"] == "not_implemented"
    assert caps["postgresql_runtime"] == "not_implemented"
    assert caps["qdrant_runtime"] == "not_implemented"
    assert caps["public_installer"] == "not_implemented"
    # Image OCR depends on an external Tesseract engine -> dependency_required.
    assert caps["image_ocr"] == "dependency_required"
    # Genuinely wired capabilities must read available.
    assert caps["asynchronous_worker"] == "available"
    assert caps["workspace_job_outbox_receipts"] == "available"
    # Every capability value must be a recognized projection token.
    allowed = {"available", "dependency_required", "not_implemented"}
    assert all(caps[k] in allowed for k in caps)
