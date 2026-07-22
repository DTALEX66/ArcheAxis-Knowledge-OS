from __future__ import annotations


def test_workspace_job_center_exposes_only_user_readable_strictly_bound_jobs(monkeypatch, tmp_path) -> None:
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
    monkeypatch.setattr(service, "convert_url", lambda _: ("# Local candidate\nBody.", "test"))
    service.intake_url(url="https://example.com/job-center", db_path=database)

    response = TestClient(app).get("/workspace/api/jobs")

    assert response.status_code == 200
    assert response.json()["schema_version"] == "v1"
    assert response.json()["jobs"] == [
        {
            "activity": "资料导入",
            "state": "succeeded",
            "delivery_state": "pending",
            "updated_at": response.json()["jobs"][0]["updated_at"],
        }
    ]
    assert not {
        "job_id",
        "command_id",
        "package_id",
        "event_id",
        "payload",
        "lease_token",
        "correlation_id",
        "causation_id",
    } & set(response.text.split('"'))


def test_workspace_runtime_page_uses_the_real_job_center_projection() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    page = (root / "app/workspace/ui/index.html").read_text(encoding="utf-8")
    application = (root / "app/workspace/ui/assets/app.js").read_text(encoding="utf-8")

    assert 'id="page-runtime"' in page
    assert 'id="job-center"' in page
    assert "'/workspace/api/jobs'" in application
    assert "function renderJobs" in application
    assert "同步记录" in page
