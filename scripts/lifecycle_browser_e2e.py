"""Real Chromium E2E test: lifecycle page renders aggregate state without IDs."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import Page, sync_playwright
from runtime_http_smoke import running_core

FORBIDDEN_INTERNAL_IDS = {"package_id", "job_id", "command_id", "unit_id", "artifact_id"}


def _seed_lifecycle_data(data_dir: Path) -> None:
    """Seed lifecycle tables AFTER migration, respecting the real schema."""
    db = data_dir / "cognitive_os.sqlite"
    now = "2026-07-26T14:00:00Z"
    with sqlite3.connect(db) as connection:
        # execution_traces: 2 traces, 1 blocked permission
        connection.execute(
            "INSERT INTO execution_traces(id, task_id, events_json, result_json, success, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                "task-lifecycle-1",
                json.dumps(
                    [
                        {
                            "result": {
                                "tool": "permission",
                                "status": "blocked",
                                "reason": "risk_threshold_exceeded",
                            }
                        },
                        {"result": {"tool": "execute", "status": "attempted"}},
                    ]
                ),
                "{}",
                0,
                now,
            ),
        )
        connection.execute(
            "INSERT INTO execution_traces(id, task_id, events_json, result_json, success, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                "task-lifecycle-2",
                json.dumps(
                    [
                        {"result": {"tool": "permission", "status": "allowed"}},
                        {"result": {"tool": "execute", "status": "completed"}},
                        {"result": {"tool": "trace", "status": "recorded"}},
                    ]
                ),
                json.dumps({"status": "completed", "output": "verified"}),
                1,
                now,
            ),
        )

        # evaluation_candidates_v1: 3 candidates, 2 approved
        connection.execute(
            "INSERT INTO evaluation_candidates_v1(id, trace_id, evaluation_json, status) "
            "VALUES (?, ?, ?, 'candidate')",
            (str(uuid4()), str(uuid4()), json.dumps({"score": 0.6})),
        )
        connection.execute(
            "INSERT INTO evaluation_candidates_v1(id, trace_id, evaluation_json, status, reviewer_id, rationale, reviewed_at) "
            "VALUES (?, ?, ?, 'approved', 'local-auditor', 'meets threshold', ?)",
            (str(uuid4()), str(uuid4()), json.dumps({"score": 0.9}), now),
        )
        connection.execute(
            "INSERT INTO evaluation_candidates_v1(id, trace_id, evaluation_json, status, reviewer_id, rationale, reviewed_at) "
            "VALUES (?, ?, ?, 'approved', 'local-auditor', 'passes review', ?)",
            (str(uuid4()), str(uuid4()), json.dumps({"score": 0.85}), now),
        )

        # machine_lessons: 1 lesson item
        connection.execute(
            "INSERT INTO machine_lessons(id, pattern, lesson_type, future_constraint, evidence_trace_id, created_at) "
            "VALUES (?, ?, 'failure', ?, ?, ?)",
            (
                str(uuid4()),
                "blocked_high_risk_access",
                "Blocked high-risk tool access requires explicit human confirmation.",
                str(uuid4()),
                now,
            ),
        )
        connection.commit()


def _verify_lifecycle_page(page: Page, base_url: str) -> None:
    """Navigate to evidence page and verify lifecycle cards render correctly."""
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: page_errors.append(str(err)))

    # Navigate to evidence/lifecycle page
    page.goto(f"{base_url}/workspace#evidence", wait_until="networkidle")
    page.get_by_role("heading", name="证据中心·生命周期").wait_for()

    # --- Permission card: shows blocked state with gate=2, blocked=1 ---
    permission_text = page.locator("#lifecycle-permission").inner_text()
    assert "权限门禁" in permission_text, f"Expected permission label, got: {permission_text}"
    assert "blocked" in permission_text or "阻断" in permission_text, (
        f"Expected blocked state, got: {permission_text}"
    )
    assert "2" in permission_text, f"Expected 2 gates, got: {permission_text}"

    # --- Execution card: 2 runs ---
    execution_text = page.locator("#lifecycle-execution").inner_text()
    assert "2" in execution_text, f"Expected 2 executions, got: {execution_text}"

    # --- Trace card: 2 traces ---
    trace_text = page.locator("#lifecycle-trace").inner_text()
    assert "2" in trace_text, f"Expected 2 traces, got: {trace_text}"

    # --- Evaluation card: 3 candidates, 2 approved ---
    evaluation_text = page.locator("#lifecycle-evaluation").inner_text()
    assert "3" in evaluation_text, f"Expected 3 evaluation candidates, got: {evaluation_text}"

    # --- Lesson card: 1 lesson item ---
    lesson_text = page.locator("#lifecycle-lesson").inner_text()
    assert "1" in lesson_text, f"Expected 1 lesson, got: {lesson_text}"

    # --- No internal IDs leaked anywhere on the page ---
    page_text = page.locator("main").inner_text()
    for identifier in FORBIDDEN_INTERNAL_IDS:
        assert identifier not in page_text, f"Internal ID '{identifier}' leaked to page"

    # Check no UUIDs leaked
    import re as _re
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    uuids = _re.findall(uuid_pattern, page_text)
    assert not uuids, f"UUID(s) leaked to page: {uuids[:3]}"

    # --- Verify the refresh button is visible and clickable ---
    refresh_button = page.get_by_role("button", name="刷新生命周期")
    assert refresh_button.is_visible()
    refresh_button.click()
    page.wait_for_timeout(500)

    # --- No JS errors during the test ---
    assert not page_errors, f"Page errors: {page_errors}"
    assert not console_errors, f"Console errors: {console_errors}"


def main() -> int:
    # Use project-local .project-local/task-runtime/tmp/ for the lifecycle test data dir
    # so cleanup doesn't fight with subprocess DB locks.
    project_root = Path(__file__).resolve().parent.parent
    runtime_root = project_root / ".project-local" / "task-runtime"
    lifecycle_tmp = runtime_root / "tmp" / "lifecycle-e2e"
    lifecycle_tmp.mkdir(parents=True, exist_ok=True)

    data_dir = lifecycle_tmp
    os.environ["ARCHEAXIS_DATA_DIR"] = str(data_dir)
    os.environ.pop("COGNITIVE_DATA_DIR", None)

    db = data_dir / "cognitive_os.sqlite"
    # Remove any leftover from a previous run
    if db.is_file():
        db.unlink()
    backup_dir = data_dir / "backups"
    if backup_dir.is_dir():
        import shutil
        shutil.rmtree(backup_dir)

    # Run migration FIRST to create the full schema
    migrate_result = subprocess.run(
        [sys.executable, "-m", "app.runtime_entrypoint", "migrate"],
        capture_output=True, text=True,
        cwd=project_root,
    )
    if migrate_result.returncode != 0:
        print(f"Migration failed:\n{migrate_result.stdout}\n{migrate_result.stderr}")
        return 1

    if not db.is_file():
        print(f"Database was not created at {db}")
        return 1

    # Seed lifecycle data into the migrated database
    _seed_lifecycle_data(data_dir)

    # Verify seed data is present
    with sqlite3.connect(db) as connection:
        trace_count = connection.execute("SELECT COUNT(*) FROM execution_traces").fetchone()[0]
        eval_count = connection.execute("SELECT COUNT(*) FROM evaluation_candidates_v1").fetchone()[0]
        lesson_count = connection.execute("SELECT COUNT(*) FROM machine_lessons").fetchone()[0]
        print(f"Seeded: {trace_count} traces, {eval_count} evaluations, {lesson_count} lessons")

    # Start the real server and exercise lifecycle page with Chromium
    with running_core() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            _verify_lifecycle_page(page, base_url)
        finally:
            browser.close()

    # Clean up lifecycle test data (running_core's process is dead by now)
    import shutil
    shutil.rmtree(lifecycle_tmp, ignore_errors=True)

    print("")
    print("✅ Lifecycle E2E browser smoke passed — aggregate state verified, no internal IDs leaked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
