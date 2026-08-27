from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "app" / "workspace" / "ui"


def test_task_cockpit_has_real_projection_contract():
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "assets" / "app.js").read_text(encoding="utf-8")

    assert 'id="task-cockpit"' in html
    assert 'id="cockpit-timeline"' in html
    assert "真实回读" in html
    assert "A2 · 真实回读" not in html
    assert "fetchJson('/workspace/api/jobs')" in js
    assert "fetchJson('/workspace/api/lifecycle')" in js
    assert "function selectTask(activity)" in js
    assert "execution.state" in js
    assert "trace.runs" in js
    assert "evaluation.candidates" in js
    assert "lesson.items" in js


def test_task_cockpit_does_not_render_internal_identifiers():
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "assets" / "app.js").read_text(encoding="utf-8")

    assert "job_id" not in html
    assert "task_id" not in html
    assert "job.job_id" not in js
    assert "task.task_id" not in js
    assert "不会显示伪进度" in html
