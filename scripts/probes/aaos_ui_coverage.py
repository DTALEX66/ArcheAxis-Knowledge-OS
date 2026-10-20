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


def navigate(page, page_id: str) -> None:
    if page_id == "18":
        navigate(page, "17")
        page.locator('.capability-center-list button[data-entry-id]').first.click()
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
    page.locator(".space-view").wait_for()
    page.wait_for_function("() => document.fonts.status === 'loaded'")
    page.wait_for_timeout(200)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--axe-source", type=Path, required=True)
    parser.add_argument("--themes", nargs="+", choices=a0.AAOS_THEME_IDS, default=["cosmic"])
    parser.add_argument("--pages", nargs="+")
    parser.add_argument("--sizes", nargs="+", default=["1600x1000", "640x480"])
    parser.add_argument("--state", choices=["baseline", "read-failure"], default="baseline")
    parser.add_argument("--console-gestures", action="store_true")
    args = parser.parse_args()
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
                        page.locator(".space-view").wait_for()
                        a0.select_ui_theme(page, theme)
                        if args.console_gestures:
                            report.setdefault("console_gestures", []).append({"theme": theme, "viewport": [width, height],
                                "observations": console_gestures(page, output, theme)})
                        for page_id, label in roles:
                            case = {"page_id": page_id, "label": label, "theme": theme,
                                    "viewport": [width, height], "dpr": 1}
                            report["cases"].append(case)
                            try:
                                started = time.perf_counter()
                                navigate(page, page_id)
                                case["navigation_ms"] = round((time.perf_counter() - started) * 1000, 2)
                                case["controls"] = a0.check_business_controls(page)
                                case["dock_tabs"] = page.locator('.dock-surface [role="tab"]').evaluate_all("""tabs => tabs
                                  .filter(n=>n.getClientRects().length && getComputedStyle(n).visibility==='visible')
                                  .map(n=>({text:n.innerText,font:parseFloat(getComputedStyle(n).fontSize),
                                    color:getComputedStyle(n).color,background:getComputedStyle(n).backgroundColor}))""")
                                assert all(tab["font"] >= 14 for tab in case["dock_tabs"]), case["dock_tabs"]
                                case["observed"] = page.locator(".space-view").evaluate("""node => ({
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
                            shot = output / f"page-{page_id}-{theme}-{width}x{height}.png"
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
                                        any(c["status"] == "FAIL" for c in report["cases"])) else "PASS_AUTOMATED_ONLY"
        (output / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report={output / 'coverage.json'} status={report['status']}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
