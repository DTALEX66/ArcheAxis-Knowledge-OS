"""Real Chromium regression gate for the local Workspace truth boundary."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import Page, Route, sync_playwright
from runtime_http_smoke import running_core

WORKSPACE_ROOT = "/" + "workspace"
STATUS_PATTERN = f"**{WORKSPACE_ROOT}/api/status"
INTAKE_PATTERN = f"**{WORKSPACE_ROOT}/api/intake/url"
RESEARCH_PATTERN = f"**{WORKSPACE_ROOT}/api/research"


def _partial_status(route: Route) -> None:
    route.fulfill(status=200, content_type="application/json", body='{"schema_version":"v1"}')


def _network_failure(route: Route) -> None:
    route.abort("connectionfailed")


def _intake_success(route: Route) -> None:
    route.fulfill(
        status=200,
        content_type="application/json",
        body=(
            '{"source_type":"web","source_count":1,"claim_count":2,'
            '"evidence_count":3,"requires_human_review":true}'
        ),
    )


def _partial_intake_success(route: Route) -> None:
    route.fulfill(status=200, content_type="application/json", body="{}")


def _research_queue(route: Route) -> None:
    route.fulfill(status=200, content_type="application/json", body=(
        '{"schema_version":"v1","items":[{"source":"https://example.com/review",'
        '"claim_count":2,"evidence_count":3,"verification":"unverified",'
        '"created_at":"2026-07-23T00:00:00Z"}]}'
    ))


def exercise_workspace(page: Page, base_url: str) -> None:
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    page.goto(f"{base_url}/workspace#overview]", wait_until="networkidle")
    assert page.url.endswith("#unavailable")
    assert page.get_by_role("heading", name="功能尚未接入").is_visible()

    page.evaluate("location.hash = '#projects'")
    page.get_by_role("heading", name="项目").wait_for()
    page.evaluate("location.hash = '#overview]'")
    page.get_by_role("heading", name="功能尚未接入").wait_for()

    page.goto(f"{base_url}/workspace#overview", wait_until="networkidle")
    assert page.locator("body").get_attribute("data-theme") == "violet-core"
    assert page.get_by_role("complementary", name="一级模块").is_visible()
    assert page.get_by_role("complementary", name="认知检查器").is_visible()
    assert page.get_by_role("region", name="活动坞").is_visible()
    assert page.get_by_role("button", name="折叠认知检查器").is_visible()
    page.get_by_role("button", name="折叠认知检查器").click()
    assert page.evaluate("document.body.classList.contains('inspector-collapsed')")
    page.get_by_role("button", name="展开认知检查器").click()
    assert not page.evaluate("document.body.classList.contains('inspector-collapsed')")
    page.get_by_role("button", name="折叠活动坞").click()
    assert page.evaluate("document.body.classList.contains('dock-collapsed')")
    page.get_by_role("button", name="展开活动坞").click()
    assert not page.evaluate("document.body.classList.contains('dock-collapsed')")
    page.get_by_role("button", name="智体").click()
    page.get_by_role("heading", name="Agent管理").wait_for()
    assert "尚未接入真实数据" in page.locator("#page-unavailable").inner_text()
    page.locator('.rail-item[title="观心"]').click()
    page.get_by_role("heading", name="观心总览").wait_for()
    page.get_by_text("异步Worker", exact=True).wait_for()
    assert "尚未实现" in page.locator("#capability-summary").inner_text()

    page.route(STATUS_PATTERN, _partial_status)
    page.goto(f"{base_url}/workspace#diagnostics", wait_until="networkidle")
    page.get_by_role("button", name="刷新").click()
    page.get_by_text("系统状态", exact=True).wait_for()
    assert "本地状态读取失败" in page.locator("#diagnostics-summary").inner_text()
    assert "能力状态" in page.locator("#capability-summary").inner_text()
    assert "异步Worker" not in page.locator("#capability-summary").inner_text()
    page.unroute(STATUS_PATTERN, _partial_status)

    page.goto(f"{base_url}/workspace#overview", wait_until="networkidle")
    intake_button = page.get_by_role("button", name="导入资料")
    intake_button.click()
    dialog = page.get_by_role("dialog", name="导入资料")
    assert dialog.get_attribute("aria-modal") == "true"
    assert page.evaluate("document.activeElement?.id") == "intake-url"
    page.keyboard.press("Escape")
    assert page.evaluate("document.activeElement?.dataset.action") == "intake"
    intake_button.click()
    page.get_by_label("网页地址").fill("https://example.com/offline")
    page.route(INTAKE_PATTERN, _network_failure)
    page.get_by_role("button", name="导入网页或GitHub仓库").click()
    page.get_by_text("无法连接本地服务，请重试", exact=False).wait_for()
    assert "处理中" not in page.locator("#intake-result").inner_text()
    assert console_errors and all("ERR_CONNECTION_FAILED" in error for error in console_errors)
    console_errors.clear()
    page.unroute(INTAKE_PATTERN, _network_failure)

    page.get_by_label("网页地址").fill("https://example.com/truth")
    page.route(INTAKE_PATTERN, _intake_success)
    page.get_by_role("button", name="导入网页或GitHub仓库").click()
    page.locator("#intake-result").filter(has_text="下一步：等待人工复核").wait_for()
    result = page.locator("#intake-result").inner_text()
    assert "来源记录：1" in result
    assert "候选要点：2" in result
    assert "证据记录：3" in result
    assert "引擎：自动" not in result
    assert "内容长度：0" not in result
    assert all(identifier not in result for identifier in ("package_id", "job_id", "command_id"))
    page.unroute(INTAKE_PATTERN, _intake_success)

    page.get_by_label("网页地址").fill("https://example.com/partial")
    page.route(INTAKE_PATTERN, _partial_intake_success)
    page.get_by_role("button", name="导入网页或GitHub仓库").click()
    page.locator("#intake-result").filter(has_text="处理失败").wait_for()
    assert "处理完成" not in page.locator("#intake-result").inner_text()
    page.unroute(INTAKE_PATTERN, _partial_intake_success)

    page.route(RESEARCH_PATTERN, _research_queue)
    page.goto(f"{base_url}/workspace#research", wait_until="networkidle")
    page.get_by_role("heading", name="察微研究").wait_for()
    page.get_by_text("https://example.com/review", exact=True).wait_for()
    assert page.get_by_role("button", name="批准进入知识候选").is_visible()
    page.unroute(RESEARCH_PATTERN, _research_queue)

    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(f"{base_url}/workspace#overview", wait_until="networkidle")
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{base_url}/workspace#overview", wait_until="networkidle")
    assert page.get_by_role("heading", name="观心总览").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")

    assert not page_errors, page_errors
    assert not console_errors, console_errors


def exercise_real_delivery(page: Page, base_url: str, data_dir: str) -> None:
    """Prove real upload → SQLite outbox → dispatch → receipt → UI reread."""
    source_path = Path(data_dir) / "browser-delivery.txt"
    source_path.write_text("Real Chromium delivery readback", encoding="utf-8")
    try:
        page.keyboard.press("Escape")
        page.goto(f"{base_url}/workspace#overview", wait_until="networkidle")
        page.get_by_role("button", name="导入资料").click()
        page.set_input_files("#intake-file", str(source_path))
        page.get_by_role("button", name="导入文件").click()
        intake_result = page.locator("#intake-result")
        intake_result.wait_for()
        page.wait_for_function(
            "() => !document.querySelector('#intake-result')?.textContent.includes('处理中')"
        )
        if "处理完成" not in intake_result.inner_text():
            raise AssertionError(f"real upload failed: {intake_result.inner_text()}")
        page.keyboard.press("Escape")

        page.evaluate("location.hash = '#runtime'")
        page.get_by_role("heading", name="知行任务执行").wait_for()
        delivery = page.locator("#delivery-center")
        delivery.get_by_text("Outbox pending：1", exact=False).wait_for()
        delivery_text = delivery.inner_text()
        assert "Receipt missing：1" in delivery_text
        assert "状态：succeeded · 投递：pending" in page.locator("#job-center").inner_text()
        assert all(
            identifier not in delivery_text
            for identifier in ("package_id", "job_id", "command_id", "event_internal")
        )

        page.get_by_role("button", name="投递下一条").click()
        delivery.get_by_text("Receipt recorded：1", exact=False).wait_for()
        delivery_text = delivery.inner_text()
        assert "投递器：on_demand" in delivery_text
        assert "Outbox pending：0" in delivery_text
        assert "Receipt missing：0" in delivery_text
        assert "Outbox：delivered" in delivery_text
        assert "Receipt：recorded" in delivery_text

        page.reload(wait_until="networkidle")
        page.get_by_role("heading", name="知行任务执行").wait_for()
        delivery_text = page.locator("#delivery-center").inner_text()
        assert "Outbox pending：0" in delivery_text
        assert "Receipt recorded：1" in delivery_text
        assert "Receipt missing：0" in delivery_text
    finally:
        source_path.unlink(missing_ok=True)


def main() -> int:
    data_dir = os.environ.get("COGNITIVE_DATA_DIR", "").strip()
    if not data_dir:
        raise RuntimeError("COGNITIVE_DATA_DIR must point to an isolated browser-smoke directory")
    subprocess.run(
        [sys.executable, "-m", "app.runtime_entrypoint", "migrate"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    with running_core() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            exercise_workspace(page, base_url)
            delivery_page = browser.new_page(viewport={"width": 1440, "height": 1000})
            try:
                exercise_real_delivery(delivery_page, base_url, data_dir)
            finally:
                delivery_page.close()
        finally:
            browser.close()
    print("A0 Chromium browser smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
