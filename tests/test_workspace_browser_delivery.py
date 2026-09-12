"""Real Chromium Workspace delivery slice: upload -> dispatch -> reload readback.

Run with the project-data wrapper so the isolated runtime stays under .project-local/.
"""
from __future__ import annotations

import time

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
        fixture.write_text("Chromium delivery evidence fixture.", encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(BASE, wait_until="networkidle")
            page.get_by_role("button", name="导入资料").first.click()
            page.set_input_files("#intake-file", str(fixture))
            page.get_by_role("button", name="导入文件").click()
            page.locator("#intake-result").wait_for(state="visible")
            page.wait_for_function("""() => document.querySelector('#intake-result')?.innerText !== '处理中…'""")
            intake_text = page.locator("#intake-result").inner_text()
            assert "处理完成" in intake_text, intake_text
            page.get_by_role("button", name="关闭").click()

            page.goto(f"{BASE}#runtime", wait_until="networkidle")
            delivery = page.locator("#delivery-center")
            delivery.get_by_role("button", name="投递下一条").click()
            page.wait_for_function(
                """() => document.querySelector('#delivery-center')?.innerText.includes('Receipt recorded：1')"""
            )
            assert "Outbox pending：0" in delivery.inner_text()
            assert "Receipt recorded：1" in delivery.inner_text()

            page.reload(wait_until="networkidle")
            page.wait_for_function(
                """() => document.querySelector('#delivery-center')?.innerText.includes('Receipt recorded：1')"""
            )
            assert "Outbox pending：0" in delivery.inner_text()
            print(f"BROWSER_DELIVERY_PASS data={DATA_DIR}")
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
