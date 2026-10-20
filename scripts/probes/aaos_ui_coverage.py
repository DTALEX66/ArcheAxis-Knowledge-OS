"""Rendered production-page coverage; synthetic host, never installed acceptance.

Uses the existing A0 bridge and process lifecycle. No product API or external
network is contacted. Unknown fixture operations deliberately fail with 501.
The report retains all axe violations/incomplete results and navigation failures.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import time
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from scripts import a0_browser_smoke as a0
from playwright.sync_api import sync_playwright


PARENTS = {"03": "02", "07": "06", "08": "06", "09": "06", "10": "06",
           "11": "06", "12": "06", "14": "13", "16": "15", "18": "17",
           "20": "19", "21": "06", "22": "13"}


def console_gestures(page, output: Path, theme: str) -> list[dict]:
    """Actual pointer/keyboard input against each internal edge; no native DPI claim."""
    console = page.locator(".console-window")
    assert console.get_attribute("data-console-mode") == "floating"
    observations = []
    for edge, dx, dy in [("n", 0, 24), ("ne", -24, 24), ("e", -24, 0),
                          ("se", -24, -24), ("s", 0, -24), ("sw", 24, -24),
                          ("w", 24, 0), ("nw", 24, 24)]:
        before = console.bounding_box()
        handle = page.locator(f'[data-console-edge="{edge}"]') if edge != "se" else page.get_by_role("button", name="调整主控台大小", exact=True)
        box = handle.bounding_box()
        assert box is not None, f"missing visible resize handle {edge}"
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        hit = handle.evaluate("node => {const r=node.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===node;}")
        assert hit, f"resize handle {edge} is covered"
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + dx, y + dy, steps=5)
        # Pointer dispatch may precede React's animation-frame commit.
        page.wait_for_function("""before => {const r=document.querySelector('.console-window').getBoundingClientRect();
          return r.x!==before.x||r.y!==before.y||r.width!==before.width||r.height!==before.height;}""", arg=before)
        after = console.bounding_box()
        assert after != before, f"resize handle {edge} did not adjust the console"
        if "w" in edge:
            assert abs(after["x"] + after["width"] - before["x"] - before["width"]) < 1
        if "n" in edge:
            assert abs(after["y"] + after["height"] - before["y"] - before["height"]) < 1
        assert after["width"] >= 640 and after["height"] >= 480
        page.keyboard.press("Escape")
        page.mouse.up()
        page.wait_for_function("""before => {const r=document.querySelector('.console-window').getBoundingClientRect();
          return r.x===before.x&&r.y===before.y&&r.width===before.width&&r.height===before.height;}""", arg=before)
        restored = console.bounding_box()
        assert restored == before, (edge, before, restored)
        observations.append({"edge": edge, "before": before, "after": after, "cancelled": restored})
    page.screenshot(path=str(output / f"console-edges-{theme}.png"))
    return observations


def navigate(page, page_id: str, capability_id: str | None = None) -> None:
    if page_id == "18":
        navigate(page, "17")
        page.get_by_role("tab", name="目录与搜索", exact=True).click()
        entries = page.locator('.capability-center-list button[data-entry-id]')
        target = entries.first if capability_id is None else page.locator(f'.capability-center-list button[data-entry-id="{capability_id}"]')
        target.scroll_into_view_if_needed()
        target.click()
        page.get_by_role("tabpanel", name="能力详情", exact=True).wait_for()
        return

    def surface():
        drawer = page.get_by_role("dialog", name="产品导航", exact=True)
        if drawer.is_visible():
            return drawer
        trigger = page.get_by_role("button", name="打开产品导航", exact=True)
        if trigger.is_visible():
            trigger.click()
            drawer = page.get_by_role("dialog", name="产品导航", exact=True)
            drawer.wait_for()
            return drawer
        return page.locator(".navigation-sidebar")

    nav = surface()
    target = nav.locator(f'[data-page-id="{page_id}"]')
    if not target.is_visible():
        nav.locator(f'[data-page-id="{PARENTS[page_id]}"]').click()
        nav = surface()
    nav.locator(f'[data-page-id="{page_id}"]').click()
    page.wait_for_function("id => location.hash === '#page=' + id", arg=page_id)
    page.locator(".space-view:visible").wait_for()
    page.wait_for_function("() => document.fonts.status === 'loaded'")
    page.wait_for_timeout(200)


def dock_interactions(page, output: Path, theme: str) -> dict:
    """Visible input against existing tabs and the real changing dock rectangle."""
    page.set_viewport_size({"width": 1600, "height": 1000})
    navigate(page, "03")
    navigate(page, "17")
    navigate(page, "03")
    workspace = page.get_by_role("region", name="自由布局工作区", exact=True)
    workspace.locator(".dock-layout-options > summary").click()

    def observe(label):
        page.wait_for_timeout(350)
        path = output / f"dock-{label}-{theme}.png"
        page.screenshot(path=str(path))
        return {"screenshot": str(path), "viewport": page.viewport_size,
                "surface": workspace.locator(".dock-surface").bounding_box(),
                "groups": workspace.locator(".dv-groupview").evaluate_all("nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {width:r.width,height:r.height,x:r.x,y:r.y,tabs:[...n.querySelectorAll('[role=tab]')].map(t=>t.getAttribute('aria-label'))};})"),
                "tabs": workspace.get_by_role("tab").all_text_contents()}

    result = {"theme": theme, "before": observe("before")}
    workspace.get_by_role("button", name="左右分栏", exact=True).click()
    result["horizontal"] = observe("horizontal")
    workspace.get_by_role("button", name="上下分栏", exact=True).click()
    result["vertical"] = observe("vertical")
    workspace.get_by_role("button", name="左右分栏", exact=True).click()
    page.set_viewport_size({"width": 640, "height": 480})
    result["narrow"] = observe("narrow")
    workspace.get_by_role("tab", name="阅读与编辑", exact=True).click()
    page.get_by_role("region", name="阅读与编辑文档视图", exact=True).wait_for()
    result["reader_tab_reachable"] = True
    page.set_viewport_size({"width": 1600, "height": 1000})
    result["restored"] = observe("restored")
    horizontal, vertical = result["horizontal"]["groups"], result["vertical"]["groups"]
    result["axes_verified"] = (len(horizontal) == len(vertical) == 2 and
        abs(horizontal[0]["y"] - horizontal[1]["y"]) < 2 and abs(horizontal[0]["x"] - horizontal[1]["x"]) > 100 and
        abs(vertical[0]["x"] - vertical[1]["x"]) < 2 and abs(vertical[0]["y"] - vertical[1]["y"]) > 100)
    result["status"] = "PASS" if (len(result["horizontal"]["groups"]) == 2 and
        len(result["vertical"]["groups"]) == 2 and len(result["narrow"]["groups"]) == 1 and
        len(result["restored"]["groups"]) == 2 and result["axes_verified"]) else "FAIL"
    # Entry-state coverage below is intentionally separate from the multi-panel
    # gesture journey. Reset using the visible product control, retaining hosts.
    (output / f"dock-journey-{theme}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    workspace.get_by_role("button", name="重置视图布局", exact=True).click()
    workspace.locator(".dock-layout-options > summary").click()
    return result


def template_requirements(page, output: Path, case_id: str) -> dict:
    """Exercise the actual template disclosure, diagnostic channel and capability route."""
    page.get_by_role("tab", name="学科模板", exact=True).click()
    launcher = page.get_by_role("region", name="学科模板工作区", exact=True)
    launcher.get_by_role("combobox", name="模板", exact=True).select_option("T2")
    panel = page.get_by_role("region", name="模板能力需求", exact=True)
    panel.get_by_text("本轮已读取 0 条能力运行状态。", exact=False).wait_for()
    text = panel.inner_text()
    assert not re.search(r"Core|worker|CAP-|稳定 ID|html\.structure|NOT_RUN", text), text
    table = panel.get_by_role("table")
    assert table.get_by_role("row", name=re.compile("网页结构读取")).inner_text().count("当前应用未接入此处理服务") == 1
    assert "只有需求说明，尚未接入实际处理" in table.get_by_role("row", name=re.compile("本地内容检索")).inner_text()
    details_button = table.get_by_role("button", name="查看网页结构读取的能力详情", exact=True)
    details_button.scroll_into_view_if_needed()
    control = a0.visible_control_box(details_button)
    assert control["reachable"] and abs(control["height"] - control["rawHeight"]) <= 1, control
    screenshot = output / f"template-requirements-{case_id}.png"
    page.screenshot(path=str(screenshot))
    trigger = panel.get_by_role("button", name="查看诊断详情：模板能力登记与运行状态", exact=True)
    trigger.scroll_into_view_if_needed()
    trigger.click()
    dialog = page.get_by_role("dialog", name="运行诊断", exact=True)
    raw = json.loads(dialog.locator("pre").inner_text())
    assert raw["template"]["id"] == "T2" and len(raw["requirements"]) == 7
    html = next(row for row in raw["requirements"] if row["declared"] == "html.structure")
    assert html["capability_id"] == "CAP-0020" and html["availability"] == "runtime_absent"
    assert raw["read"] == {"state": "read", "rows": []}
    page.keyboard.press("Escape")
    dialog.wait_for(state="hidden")
    assert trigger.evaluate("node => document.activeElement === node"), "diagnostic close lost focus"
    details_button.click()
    page.wait_for_function("() => location.hash === '#capability/CAP-0020'")
    detail = page.get_by_role("article", name="能力详情", exact=True)
    assert "Office文档结构读取" in detail.inner_text()
    detail.get_by_role("button", name="到资料库打开学科模板", exact=True).click()
    page.locator(".space-view:visible").get_by_role("heading", name="资料库", exact=True).wait_for()
    navigate(page, "15")
    page.get_by_role("tab", name="学科模板", exact=True).click()
    launcher = page.get_by_role("region", name="学科模板工作区", exact=True)
    launcher.get_by_role("combobox", name="模板", exact=True).select_option("T2")
    return {"status": "PASS", "text": text, "raw": raw,
            "capability_route": "CAP-0020", "diagnostic_focus_restored": True,
            "details_button": control, "screenshot": str(screenshot)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--axe-source", type=Path, required=True)
    parser.add_argument("--themes", nargs="+", choices=a0.AAOS_THEME_IDS, default=["cosmic"])
    parser.add_argument("--pages", nargs="+")
    parser.add_argument("--sizes", nargs="+", default=["1600x1000", "640x480"])
    parser.add_argument("--state", choices=["baseline", "read-failure"], default="baseline")
    parser.add_argument("--console-gestures", action="store_true")
    parser.add_argument("--dock-interactions", action="store_true")
    parser.add_argument("--capability-details", action="store_true")
    parser.add_argument("--template-requirements", action="store_true")
    args = parser.parse_args()
    if args.template_requirements and args.pages and "15" not in args.pages:
        parser.error("--template-requirements requires production page 15")
    root = Path(os.environ["ARCHEAXIS_RUN_ROOT"])
    output = root / "artifacts" / "ui-coverage"
    output.mkdir(parents=True, exist_ok=False)
    axe_source = args.axe_source.read_text(encoding="utf-8")
    registry = (a0.ROOT / "frontend/src/presentation/uiPages.ts").read_text(encoding="utf-8")
    roles = re.findall(r'page\("(\d{2})", "([^"]+)"', registry)
    assert len(roles) == 22, "production semantic-page registry changed; review coverage"
    if args.pages:
        assert set(args.pages) <= {id_ for id_, _ in roles}
        roles = [(id_, label) for id_, label in roles if id_ in args.pages]
    sizes = [tuple(map(int, size.split("x"))) for size in args.sizes]
    report = {"schema": "archeaxis/ui-coverage/v1", "evidence": "SYNTHETIC",
              "source": a0.source_revision(), "started_at": datetime.now(timezone.utc).isoformat(),
              "state": args.state, "axe_sha256": sha256(axe_source.encode()).hexdigest(),
              "probe_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "production page entry states; no model, persistence, installed or Owner acceptance",
              "cases": [], "errors": [], "external_requests": []}
    a0.RUNTIME.mkdir(parents=True, exist_ok=True)
    process, log = a0.start_vite(a0.RUNTIME / "ui-coverage-vite.log")
    report["service"] = {"pid": process.pid, "url": a0.URL}
    try:
        with sync_playwright() as p:
            executable = a0._declared_tool("ext.toolchains.playwright-chromium", "playwright-chromium")
            if os.name == "nt" and not executable:
                raise RuntimeError("declared Chromium missing; no automatic install")
            browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
            report["browser"] = browser.version
            for width, height in sizes:
                for theme in args.themes:
                    context = browser.new_context(viewport={"width": width, "height": height},
                                                  device_scale_factor=1, reduced_motion="reduce")
                    faults = {"documents_list": 503, "sources_list": 503} if args.state == "read-failure" else {}
                    bridge = a0.host_bridge_stub(failing_operations=faults, stateful_documents=True)
                    bridge = bridge.replace('bodies[operation] ?? {}', 'bodies[operation] ?? {error:"UNIMPLEMENTED_UI_FIXTURE",operation}')
                    bridge = bridge.replace('return { status: 200, body: bodies[operation]',
                                            'return { status: bodies[operation] ? 200 : 501, body: bodies[operation]')
                    # axe's temporary frames must not initialize a second host or
                    # run document hashes in an insecure about:blank context.
                    context.add_init_script(f"if(window.top===window && location.origin==={json.dumps(a0.URL)}){{{bridge}}}")
                    page = context.new_page()
                    page.set_default_timeout(8000)
                    # Match the existing A0 cold-navigation budget; interactions
                    # still use 8s and all geometry/hit assertions remain strict.
                    page.set_default_navigation_timeout(30000)
                    page.on("pageerror", lambda error: report["errors"].append(error.stack))

                    def route(request):
                        parsed = urlsplit(request.request.url)
                        if parsed.netloc != urlsplit(a0.URL).netloc:
                            report["external_requests"].append(request.request.url)
                            request.abort()
                        elif parsed.path.startswith((a0.API_PREFIX + "/", a0.WORKSPACE_PREFIX + a0.API_PREFIX + "/")):
                            request.fulfill(status=200, content_type="application/json",
                                            body=json.dumps(a0.api_payload(request.request.url)))
                        else:
                            request.continue_()

                    page.route("**/*", route)
                    try:
                        page.goto(a0.URL, wait_until="networkidle")
                        page.locator(".space-view:visible").wait_for()
                        a0.select_ui_theme(page, theme)
                        if args.dock_interactions:
                            report.setdefault("dock_interactions", []).append(dock_interactions(page, output, theme))
                        if args.console_gestures:
                            report.setdefault("console_gestures", []).append({"theme": theme, "viewport": [width, height],
                                "observations": console_gestures(page, output, theme)})
                        cases = [(page_id, label, None) for page_id, label in roles]
                        if args.capability_details:
                            navigate(page, "17")
                            entries = page.locator('.capability-center-list button[data-entry-id]').evaluate_all("nodes=>nodes.map(n=>({id:n.dataset.entryId,label:n.querySelector('b').innerText}))")
                            assert entries and len({entry["id"] for entry in entries}) == len(entries)
                            cases = [(page_id, label, None) for page_id, label in roles if page_id != "18"]
                            cases += [("18", entry["label"], entry["id"]) for entry in entries]
                        for page_id, label, capability_id in cases:
                            case = {"page_id": page_id, "label": label, "theme": theme,
                                    "viewport": [width, height], "dpr": 1}
                            report["cases"].append(case)
                            if capability_id:
                                case["capability_id"] = capability_id
                            try:
                                started = time.perf_counter()
                                navigate(page, page_id, capability_id)
                                case["navigation_ms"] = round((time.perf_counter() - started) * 1000, 2)
                                if args.template_requirements and page_id == "15":
                                    case["template_requirements"] = template_requirements(page, output, f"{theme}-{width}x{height}")
                                if page_id == "18":
                                    heading = page.get_by_role("article", name="能力详情", exact=True).locator(":scope > h3")
                                    case["detail_heading"] = a0.visible_control_box(heading)
                                    assert case["detail_heading"]["reachable"] and abs(case["detail_heading"]["height"] - case["detail_heading"]["rawHeight"]) <= 1, case["detail_heading"]
                                case["controls"] = a0.check_business_controls(page)
                                case["dock_tabs"] = page.locator('.dock-surface [role="tab"]').evaluate_all("""tabs => tabs
                                  .filter(n=>n.getClientRects().length && getComputedStyle(n).visibility==='visible')
                                  .map(n=>({text:n.innerText,font:parseFloat(getComputedStyle(n).fontSize),
                                    color:getComputedStyle(n).color,background:getComputedStyle(n).backgroundColor}))""")
                                assert all(tab["font"] >= 14 for tab in case["dock_tabs"]), case["dock_tabs"]
                                case["observed"] = page.locator(".space-view:visible").evaluate("""node => ({
                                  text:node.innerText.slice(0,12000),
                                  headings:[...node.querySelectorAll('h1,h2,h3')].map(n=>n.innerText),
                                  notices:[...node.querySelectorAll('[role=alert],[role=status]')].map(n=>n.innerText),
                                  font:getComputedStyle(node).fontFamily,
                                  overflow:document.documentElement.scrollWidth>innerWidth+1})""")
                                assert not case["observed"]["overflow"], "document horizontal overflow"
                                assert case["observed"]["text"].strip(), "empty production page"
                                page.add_script_tag(content=axe_source)
                                case["axe"] = page.evaluate("""async () => {
                                  const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}});
                                  const compact=items=>items.map(({id,impact,description,nodes})=>({id,impact,description,
                                    nodes:nodes.map(({target,html,failureSummary})=>({target,html,failureSummary}))}));
                                  return {version:r.testEngine.version,violations:compact(r.violations),
                                    incomplete:compact(r.incomplete),passes:r.passes.map(x=>x.id)};
                                }""")
                                case["status"] = "FAIL" if case["axe"]["violations"] else "PASS_AUTOMATED_ONLY"
                            except Exception as error:
                                case.update(status="FAIL", error=str(error))
                                case["surface_snapshot"] = page.locator(".space-view:visible").aria_snapshot()
                            shot = output / f"page-{page_id}{'-' + capability_id if capability_id else ''}-{theme}-{width}x{height}.png"
                            page.screenshot(path=str(shot))
                            case["screenshot"] = str(shot.relative_to(root))
                            (output / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                            print(json.dumps({k: case[k] for k in ("page_id", "theme", "viewport", "status")}, ensure_ascii=False), flush=True)
                    finally:
                        context.close()
            browser.close()
    except Exception as error:
        report["errors"].append(str(error))
        raise
    finally:
        a0.stop_vite(process, log)
        with socket.socket() as check:
            report["service"].update(exit_code=process.poll(), port_closed=check.connect_ex(("127.0.0.1", a0.PORT)) != 0)
        report["ended_at"] = datetime.now(timezone.utc).isoformat()
        report["status"] = "FAIL" if (report["errors"] or report["external_requests"] or
                                        any(c["status"] == "FAIL" for c in report.get("dock_interactions", [])) or
                                        any(c["status"] == "FAIL" for c in report["cases"])) else "PASS_AUTOMATED_ONLY"
        (output / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report={output / 'coverage.json'} status={report['status']}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
