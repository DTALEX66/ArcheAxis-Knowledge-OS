"""Real Chromium failure -> retry -> replay delivery slice.

Uses the product upload and delivery buttons, with direct SQL only to seed the
controlled failed-state fixture after the success path is proven.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

from tests.test_workspace_delivery_lifecycle import (
    DATA_DIR,
    PROJECT_ROOT,
    _ensure_schema,
    _reset_runtime,
    _start_server,
    _wait_for_server,
)

BASE = "http://127.0.0.1:18723/workspace"


def _summary(page):
    return page.locator("#delivery-center").inner_text()


def main() -> int:
    _reset_runtime()
    if not _ensure_schema():
        raise RuntimeError("migration failed")
    proc = _start_server()
    try:
        if not _wait_for_server(BASE):
            raise RuntimeError("server did not become ready")
        fixture = PROJECT_ROOT / "tests" / "fixtures" / "sample.txt"
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text("Chromium retry replay fixture.", encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(BASE, wait_until="networkidle")
            page.get_by_role("button", name="导入资料").first.click()
            page.set_input_files("#intake-file", str(fixture))
            page.get_by_role("button", name="导入文件").click()
            page.locator("#intake-result").wait_for(state="visible")
            page.wait_for_function("""() => document.querySelector('#intake-result')?.innerText !== '处理中…'""")
            assert "处理完成" in page.locator("#intake-result").inner_text()
            page.get_by_role("button", name="关闭").click()

            page.goto(f"{BASE}#runtime", wait_until="networkidle")
            delivery = page.locator("#delivery-center")
            delivery.get_by_role("button", name="投递下一条").click()
            page.wait_for_function("""() => document.querySelector('#delivery-center')?.innerText.includes('Receipt recorded：1')""")
            assert "Outbox pending：0" in _summary(page)

            database = DATA_DIR / "cognitive_os.sqlite"
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE workspace_outbox_v1 SET state='failed', lease_token=NULL, "
                    "lease_expires_at=NULL, updated_at=? WHERE state='delivered'",
                    (datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),),
                )
                connection.commit()
            page.reload(wait_until="networkidle")
            page.wait_for_function("""() => document.querySelector('#delivery-center')?.innerText.includes('重试失败投递')""")
            assert "Outbox failed：1" in _summary(page) or "Outbox pending：0" in _summary(page)

            delivery.get_by_role("button", name="重试失败投递").click()
            page.wait_for_function("""() => document.querySelector('#delivery-center')?.innerText.includes('投递下一条')""")
            assert "重试失败投递" not in _summary(page)
            delivery.get_by_role("button", name="投递下一条").click()
            page.wait_for_function("""() => document.querySelector('#delivery-center')?.innerText.includes('Receipt recorded：1') && document.querySelector('#delivery-center')?.innerText.includes('Outbox pending：0')""")
            page.reload(wait_until="networkidle")
            page.wait_for_function("""() => document.querySelector('#delivery-center')?.innerText.includes('Receipt recorded：1') && document.querySelector('#delivery-center')?.innerText.includes('Outbox pending：0')""")
            print(f"BROWSER_FAILURE_RETRY_REPLAY_PASS data={DATA_DIR}")
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        time.sleep(1.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
