"""Stitch production-page browser matrix on an isolated SYNTHETIC bridge.

Run only after the root writer accepts the Stitch shell. Reuses the registered
Playwright/Chromium and a0 fixtures; never installs tools or contacts real Core.
Browser evidence does not establish native-host, Green or Owner acceptance.
"""
from __future__ import annotations

import argparse
import faulthandler
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import traceback
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[2]


def load_a0():
    # This script's production location is scripts/probes; imported helpers stay
    # in scripts, not in an unrelated private tool/profile directory.
    from scripts import a0_browser_smoke
    return a0_browser_smoke


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_identity() -> dict:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "frontend/src"],
        cwd=ROOT, text=True, encoding="utf-8").splitlines()
    files = {}
    for name in sorted(set(paths)):
        path = ROOT / name
        if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
            raise RuntimeError("UI source reparse point: " + name)
        if path.is_file():
            files[name] = sha(path)
    return {"head": head, "ui_files": files,
            "ui_tree_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
            "qualification": "dirty-worktree-browser-candidate-not-exact-SHA-CI"}


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def port_open(port: int) -> bool:
    with socket.socket() as listener:
        listener.settimeout(.25)
        return listener.connect_ex(("127.0.0.1", port)) == 0


def pid_running(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, pid)  # query only; never os.kill(pid, 0) on Windows
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


MENU_FOR_PAGE = {
    "01": "视图", "02": "知识", "03": "知识", "04": "视图", "05": "研究",
    "06": "学习", "07": "学习", "08": "学习", "09": "学习", "10": "学习",
    "11": "学习", "12": "学习", "13": "AI 与模型", "14": "AI 与模型",
    "15": "工具", "16": "工具", "17": "工具", "18": "工具", "19": "AI 与模型",
    "20": "知识", "21": "视图", "22": "AI 与模型",
}
DOCK_PAGES = {"工作台": "01", "知识": "02", "学习": "06", "研究专题": "05"}
WRITE_OPERATIONS = {"document_create", "document_draft"}


def page_registry() -> dict[str, str]:
    source = (ROOT / "frontend/src/presentation/uiPages.ts").read_text(encoding="utf-8")
    result = dict(re.findall(r'page\("(\d\d)",\s*"([^"]+)"', source))
    expected = {f"{n:02d}" for n in range(1, 23)}
    if set(result) != expected or set(MENU_FOR_PAGE) != expected:
        raise RuntimeError("production page registry is not the declared 22-page matrix")
    return result


def synthetic_research(a0) -> str:
    value = {"schema": "archeaxis.research/v1", "question": "SYNTHETIC：材料如何支持作者结论？",
             "materials": [
                 {"id": "probe_material_a", "note": "SYNTHETIC 原件材料", "reference": {
                     "kind": "source", "source_id": a0.A0_SOURCE["source_id"], "sha256": a0.A0_SOURCE["sha256"]}},
                 {"id": "probe_material_b", "note": "SYNTHETIC 固定版本材料", "reference": {
                     "kind": "document", "document_id": "a0_target_1", "version": 1}}],
             "hypotheses": [], "methods": [], "experiments": [], "counterevidence": [],
             "unresolved": [], "conclusions": []}
    editor = {"type": "doc", "attrs": {"archeaxis_research": value}, "content": []}
    doc = {"document_id": "doc_stitch_research_probe", "title": "SYNTHETIC · Stitch 研究导航样本", "version": 1,
           "source_id": None, "source_revision": None, "text_projection": value["question"], "blocks": [],
           "editor_json": editor, "content_sha256": hashlib.sha256(json.dumps(editor).encode()).hexdigest()}
    return a0.host_bridge_stub(stateful_documents=True) + "\n" + """
(() => {
  const previous = window.__TAURI__.core.invoke;
  const research = __RESEARCH__;
  window.__STITCH_PROBE_CALLS__ = [];
  window.__TAURI__.core.invoke = async (command, request) => {
    const operation = request?.request?.operation;
    const payload = request?.request?.payload ?? {};
    if (command === 'core_command') {
      window.__STITCH_PROBE_CALLS__.push({operation,payload:structuredClone(payload)});
      if (['document_get','document_version'].includes(operation) && payload.document_id === research.document_id)
        return {status:200,body:structuredClone(research)};
      if (['document_create','document_draft'].includes(operation))
        return {status:503,body:{error:'SYNTHETIC_PROBE_DOES_NOT_SAVE'}};
      if (operation === 'source_original' && window.__STITCH_DELAY_ORIGINAL__) {
        const answer = await previous(command,request);
        await new Promise(resolve => { window.__STITCH_RELEASE_ORIGINAL__=resolve; });
        window.__STITCH_RELEASE_ORIGINAL__=null;
        return answer;
      }
      if (operation === 'documents_list') {
        const answer = await previous(command,request);
        const {document_id,source_id,source_revision,title,version,content_sha256}=research;
        answer.body.documents.push({document_id,source_id,source_revision,title,version,content_sha256});answer.body.snapshot_count += 1;
        return answer;
      }
    }
    return previous(command,request);
  };
})();
""".replace("__RESEARCH__", json.dumps(doc, ensure_ascii=False))


# Independent scrolling is a supported layout behavior. Only centers currently
# exposed through every clipping ancestor are hit-tested; offscreen controls in
# scrollers remain reported as not currently exposed, not falsely failed.
GEOMETRY = r"""() => {
 const root=document.scrollingElement;
 const visible=n=>{
  if(!n.getClientRects().length||getComputedStyle(n).visibility==='hidden')return false;
  for(let a=n.parentElement;a;a=a.parentElement)
   if(a.tagName==='DETAILS'&&!a.open&&!a.querySelector(':scope > summary')?.contains(n))return false;
  return true;
 };
 const describe=n=>({tag:n.tagName,label:n.getAttribute('aria-label')||n.textContent.trim().slice(0,100),cls:typeof n.className==='string'?n.className:''});
 let skipped=0;const targets=[],occluded=[];
 for(const n of document.querySelectorAll('button,summary,input,select,textarea,[role=button]')) {
  if(!visible(n)||n.disabled||n.closest('[inert]'))continue;
  const r=n.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;
  let exposed=r.width>0&&r.height>0&&x>=0&&x<innerWidth&&y>=0&&y<innerHeight;
  for(let a=n.parentElement;exposed&&a;a=a.parentElement){
   const s=getComputedStyle(a),b=a.getBoundingClientRect();
   const left=b.left+a.clientLeft,top=b.top+a.clientTop;
   if(/auto|scroll|hidden|clip/.test(s.overflowX)&&(x<left||x>=left+a.clientWidth))exposed=false;
   if(/auto|scroll|hidden|clip/.test(s.overflowY)&&(y<top||y>=top+a.clientHeight))exposed=false;
  }
  if(!exposed){skipped++;continue;}
  const hit=document.elementFromPoint(x,y),good=!!hit&&(hit===n||n.contains(hit));
  const record={...describe(n),scope:n.closest('.stitch-workspace-menu,.stitch-workspace-dock,.stitch-companion-window')?.className||'business',x:+x.toFixed(1),y:+y.toFixed(1),width:+r.width.toFixed(1),height:+r.height.toFixed(1),hit:hit?describe(hit):null};
  targets.push(record);if(!good)occluded.push(record);
 }
 const containers=[...document.querySelectorAll('.app-center,.space-view,.research-editor,.public-research-panel,.stitch-workspace-menu,.stitch-workspace-dock')].filter(visible).map(n=>({
  cls:n.className,width:n.clientWidth,scrollWidth:n.scrollWidth,overflowX:getComputedStyle(n).overflowX,
  horizontalScrollManaged:/auto|scroll/.test(getComputedStyle(n).overflowX)}));
 const images=[...document.images].filter(visible).filter(n=>n.complete&&!n.naturalWidth).map(n=>n.getAttribute('src'));
 return {viewport:[innerWidth,innerHeight],root:{width:root.clientWidth,scrollWidth:root.scrollWidth},containers,
   targets,occluded,independentScrollNotExposed:skipped,brokenImages:images};
}"""


class Probe:
    def __init__(self, artifacts: Path):
        self.artifacts = artifacts
        self.report = {"schema": "archeaxis.stitch-browser/v1", "status": "NOT_EXECUTED",
                       "evidence_level": "SYNTHETIC", "native_host": "NOT_EXECUTED", "real_core": "NOT_EXECUTED",
                       "owner_acceptance": "NOT_EXECUTED", "cases": [], "failures": [], "console_errors": [],
                       "blocked_external_requests": [], "api_requests": [], "cleanup": {}, "processes": []}
        self.case = "startup"

    def fail(self, operation: str, error) -> None:
        self.report["failures"].append({"case": self.case, "operation": operation, "error": str(error)})

    def step(self, operation, callback):
        try:
            return callback()
        except Exception as error:
            self.fail(operation, error)
            return None

    def screenshot(self, page, name: str):
        target = self.artifacts / (re.sub(r"[^a-zA-Z0-9_-]", "_", name) + ".png")
        self.step("screenshot", lambda: page.screenshot(path=str(target), full_page=False, timeout=5000))
        return str(target)

    def checkpoint(self):
        write_json(self.artifacts / "stitch-browser-progress.json", self.report)


def assert_page(page, expected: str) -> None:
    page.wait_for_function("id=>document.querySelector('[data-current-page-id]')?.dataset.currentPageId===id", arg=expected)
    assert page.locator(f'.cabin-shell[data-cabin-page="{expected}"]').count() == 1


def navigate_menu(page, page_id: str, labels: dict) -> None:
    menu = page.locator(".stitch-workspace-menu details").filter(
        has=page.locator("summary", has_text=re.compile("^" + re.escape(MENU_FOR_PAGE[page_id]) + "$")))
    menu.locator("summary").click(timeout=4000)
    menu.locator(".stitch-menu-popover").get_by_role("button", name=labels[page_id], exact=True).click(timeout=4000)
    assert_page(page, page_id)
    assert not menu.evaluate("n=>n.open"), "application menu remained open after navigation"


def launchpad_navigation(page) -> dict:
    before = page.evaluate("location.hash")
    trigger = page.locator("#stitch-launchpad-toggle")
    trigger.click(timeout=4000)
    dialog = page.get_by_role("dialog", name="全部能力", exact=True)
    dialog.get_by_role("textbox", name="搜索能力", exact=True).fill("导入")
    dialog.get_by_role("button", name=re.compile("^导入导出与互通 ")).click(timeout=4000)
    assert_page(page, "16")
    dialog.wait_for(state="hidden", timeout=4000)
    trigger.click(timeout=4000)
    dialog.wait_for(state="visible", timeout=4000)
    page.keyboard.press("Escape")
    dialog.wait_for(state="hidden", timeout=4000)
    assert trigger.evaluate("n=>n===document.activeElement"), "launchpad Esc lost opener focus"
    assert_page(page, "16")
    return {"status": "PASS", "from": before, "search_page": "16", "escape_kept_route": True, "focus_returned": True}


def theme_select(page, theme: str, a0) -> None:
    page.get_by_role("button", name="界面与工具设置", exact=True).click()
    dialog = page.get_by_role("dialog", name="界面与工具", exact=True)
    dialog.get_by_role("combobox", name="界面主题", exact=True).select_option(theme)
    dialog.get_by_role("button", name="关闭工具", exact=True).click()
    assert page.evaluate("document.documentElement.dataset.aaosTheme") == theme


def measure(page) -> dict:
    # Always return the full evidence before deciding whether any finding fails.
    return page.evaluate(GEOMETRY)


def audit_measurement(probe: Probe, result: dict) -> None:
    if result["root"]["scrollWidth"] > result["root"]["width"] + 1:
        probe.fail("document-horizontal-overflow", result["root"])
    if result["occluded"]:
        probe.fail("exposed-control-hit-targets", result["occluded"])
    if result["brokenImages"]:
        probe.fail("broken-images", result["brokenImages"])
    # Independent scrollers are retained in containers for inspection; their
    # scrollWidth is intentionally not asserted against document-root width.


def focus_dialog(page, trigger_name: str, dialog_name: str) -> dict:
    trigger = page.get_by_role("button", name=trigger_name, exact=True).filter(visible=True)
    assert trigger.count() == 1, f"visible trigger {trigger_name}: {trigger.count()}"
    dialog = page.get_by_role("dialog", name=dialog_name, exact=True)
    try:
        trigger.click(timeout=4000)
        dialog.wait_for(state="visible", timeout=4000)
        assert dialog.evaluate("n=>n.contains(document.activeElement)"), "dialog autofocus escaped"
        page.keyboard.press("Shift+Tab")
        assert dialog.evaluate("n=>n.contains(document.activeElement)"), "dialog focus escaped on reverse Tab"
        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden", timeout=4000)
        page.wait_for_timeout(100)
        assert trigger.evaluate("n=>n===document.activeElement"), "Esc did not restore opener focus"
        return {"status": "PASS", "autofocus": True, "reverse_tab_trapped": True, "escape_focus_restored": True}
    finally:
        if dialog.is_visible():
            page.keyboard.press("Escape")
            dialog.wait_for(state="hidden", timeout=4000)


def companion_interactions(page, probe: Probe) -> dict:
    toggle = page.locator("#stitch-companion-toggle")
    panel = page.locator("#stitch-companion-window")
    if panel.is_visible():
        panel.get_by_role("button", name="收起小栖窗口").click(timeout=4000)
    toggle.click(timeout=4000)
    panel.wait_for(state="visible", timeout=4000)
    assert panel.evaluate("n=>n===document.activeElement||n.contains(document.activeElement)"), "companion focus did not enter"
    mover = panel.get_by_role("button", name="移动小栖窗口")
    mover.focus()
    before = panel.bounding_box()
    mover.press("ArrowLeft");mover.press("ArrowUp")
    after = panel.bounding_box()
    assert before and after and (before["x"] != after["x"] or before["y"] != after["y"]), "keyboard movement did not move companion"
    assert after["x"] >= -1 and after["y"] >= -1, after
    viewport = page.viewport_size
    assert after["x"] + after["width"] <= viewport["width"] + 1 and after["y"] + after["height"] <= viewport["height"] + 1, after
    # Real pointer extremes exercise the previous titlebar/menu regression.
    point = mover.bounding_box()
    page.mouse.move(point["x"] + 12, point["y"] + 12)
    page.mouse.down();page.mouse.move(point["x"] + 12, 0)
    page.wait_for_function("Math.abs(document.querySelector('#stitch-companion-window').getBoundingClientRect().y-48)<=1")
    upper = panel.bounding_box()
    assert upper and abs(upper["y"] - 48) <= 1, upper
    page.mouse.move(point["x"] + 12, viewport["height"])
    page.mouse.up()
    page.wait_for_function("()=>{const r=document.querySelector('#stitch-companion-window').getBoundingClientRect();return r.bottom<=innerHeight-63}")
    lower = panel.bounding_box()
    assert lower and lower["y"] + lower["height"] <= viewport["height"] - 63, lower
    close = panel.get_by_role("button", name="收起小栖窗口")
    assert close.evaluate("n=>{const r=n.getBoundingClientRect();const h=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return h===n||n.contains(h)}"), "companion close button is occluded"
    geometry = page.evaluate(GEOMETRY)
    blocked_chrome = [row for row in geometry["occluded"] if row["scope"] != "business"]
    assert not blocked_chrome, {"companion_occludes_global_chrome": blocked_chrome}
    screenshot = probe.screenshot(page, probe.case + "-companion-open")
    page.keyboard.press("Escape")
    panel.wait_for(state="hidden")
    assert toggle.evaluate("n=>n===document.activeElement"), "companion Esc did not restore toggle"
    toggle.click(timeout=4000);panel.get_by_role("button", name="收起小栖窗口").click(timeout=4000)
    assert toggle.evaluate("n=>n===document.activeElement"), "companion close did not restore toggle"
    return {"status": "PASS", "before": before, "keyboard_position": after, "close_hit": True,
            "global_chrome_hit_targets": True, "escape_and_close_focus": True, "screenshot": screenshot,
            "business_controls_beneath_nonmodal_window": [row for row in geometry["occluded"] if row["scope"] == "business"]}


def companion_probe(page, probe: Probe) -> dict:
    try:
        return companion_interactions(page, probe)
    finally:
        panel = page.locator("#stitch-companion-window")
        if panel.is_visible():
            panel.get_by_role("button", name="收起小栖窗口").click(timeout=4000)


def research_focus(page) -> dict:
    page.locator("details.research-document-tools > summary").click(timeout=4000)
    page.get_by_role("button", name="SYNTHETIC · Stitch 研究导航样本 · 版本 1", exact=True).click(timeout=4000)
    expand = page.get_by_role("button", name="展开检查器", exact=True)
    if expand.is_visible():
        expand.click(timeout=4000)
    sidebar = page.get_by_role("complementary", name="相关资料", exact=True)
    sidebar.get_by_role("heading", name="相关资料 (2)", exact=True).wait_for()
    writes = lambda: page.evaluate("ops=>window.__STITCH_PROBE_CALLS__.filter(c=>ops.includes(c.operation))", list(WRITE_OPERATIONS))
    before = writes()
    sidebar.get_by_role("button", name="定位相关材料 2", exact=True).click(timeout=4000)
    assert page.evaluate("document.activeElement?.dataset.researchMaterial") == "probe_material_b"
    nav = page.get_by_role("navigation", name="研究内容导航")
    nav.get_by_role("button", name="研究笔记 (0)", exact=True).click(timeout=4000)
    assert page.evaluate("document.activeElement?.dataset.researchPane") == "notes"
    assert writes() == before, "research focus performed authored document writes"
    return {"status": "PASS", "bound_materials": 2, "write_call_count_before": len(before), "write_call_count_after": len(writes())}


def research_original_no_focus_steal(page) -> dict:
    page.evaluate("window.__STITCH_DELAY_ORIGINAL__=true")
    try:
        nav = page.get_by_role("navigation", name="研究内容导航")
        nav.get_by_role("button", name="证据对比 (2)", exact=True).click(timeout=4000)
        page.locator('[data-research-material="probe_material_a"]').get_by_role("button", name="材料 1", exact=False).first.click(timeout=4000)
        page.get_by_role("button", name="摘录材料 1原文", exact=True).click(timeout=4000)
        page.wait_for_function("()=>typeof window.__STITCH_RELEASE_ORIGINAL__==='function'")
        nav.get_by_role("button", name="概览", exact=True).click(timeout=4000)
        question = page.get_by_role("textbox", name="研究问题", exact=True)
        question.focus();question.press("ArrowRight")
        before = page.locator(".app-center").evaluate("n=>({top:n.scrollTop,left:n.scrollLeft})")
        page.evaluate("window.__STITCH_RELEASE_ORIGINAL__()")
        page.get_by_role("region", name="已读取并核对指纹的原件", exact=True).wait_for(state="attached")
        page.wait_for_timeout(100)
        assert question.evaluate("n=>n===document.activeElement"), "late original read stole current editing focus"
        after = page.locator(".app-center").evaluate("n=>({top:n.scrollTop,left:n.scrollLeft})")
        assert after == before, {"error": "late original read scrolled away from current editing", "before": before, "after": after}
        return {"status": "PASS", "focus_preserved": True, "scroll_before": before, "scroll_after": after}
    finally:
        page.evaluate("window.__STITCH_DELAY_ORIGINAL__=false;window.__STITCH_RELEASE_ORIGINAL__?.()")


def start_vite(a0, run: Path, probe: Probe):
    node = a0._declared_node()
    vite = ROOT / "frontend/node_modules/vite/bin/vite.js"
    if not node or not vite.is_file():
        raise RuntimeError("registered Node/Vite unavailable; no installation permitted")
    port = free_port()
    config = run / "tmp/stitch-browser-vite.config.mjs"
    canonical = (ROOT / "frontend/vite.config.ts").as_posix()
    config.write_text("import canonical from " + json.dumps(canonical) + ";\nexport default env=>{const c=canonical(env);return {...c,server:{...c.server,host:'127.0.0.1',port:"
                      + str(port) + ",strictPort:true,hmr:false,proxy:{}}}};\n", encoding="utf-8")
    log = (probe.artifacts / "vite.log").open("wb")
    command = [node, str(vite), "--config", str(config), "--host", "127.0.0.1", "--port", str(port), "--strictPort"]
    process = subprocess.Popen(command, cwd=ROOT / "frontend", stdout=log, stderr=subprocess.STDOUT,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    probe.report["processes"].append({"kind": "owned-vite", "pid": process.pid, "command": command, "port": port})
    origin = f"http://127.0.0.1:{port}"
    opener = build_opener(ProxyHandler({}))  # fixed self-owned loopback only
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Vite exited before readiness")
            try:
                with opener.open(origin, timeout=1) as response:
                    if response.status == 200:
                        return process, log, origin, port
            except OSError:
                time.sleep(.2)
        raise RuntimeError("Vite readiness timed out")
    except BaseException:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)
        log.close()
        probe.report["cleanup"]["vite"] = {"pid": process.pid, "exited": process.poll() is not None}
        probe.report["cleanup"]["port"] = {"port": port, "closed": not port_open(port)}
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", choices=["all", "desktop", "narrow", "research"], default="all")
    args = parser.parse_args()
    run_env = os.environ.get("ARCHEAXIS_RUN_ROOT")
    if not run_env:
        raise RuntimeError("run through scripts/runtime/dev.py with an independent --run-id")
    run = Path(run_env).resolve()
    run.relative_to((ROOT / ".project-local/runs").resolve())
    artifacts = run / "artifacts/stitch-browser"
    artifacts.mkdir(parents=True, exist_ok=False)
    probe = Probe(artifacts)
    process = log = context = None
    port = None
    browser_pids = []
    started = datetime.now(timezone.utc).isoformat()
    faulthandler.dump_traceback_later(45, repeat=True)
    try:
        shell = ROOT / "frontend/src/components/StitchWorkspaceChrome.tsx"
        app = (ROOT / "frontend/src/app/App.tsx").read_text(encoding="utf-8")
        if not shell.is_file() or "StitchWorkspaceMenu" not in app:
            raise RuntimeError("Stitch shell candidate has not been accepted; refuse to test the previous UI")
        a0 = load_a0()
        labels = page_registry()
        probe.report["requested_groups"] = args.groups
        probe.report["full_matrix_requested"] = args.groups == "all"
        probe.report["source_before"] = source_identity()
        process, log, origin, port = start_vite(a0, run, probe)
        print("[stitch-browser] own Vite ready", flush=True)
        probe.checkpoint()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            chromium = a0._declared_tool("ext.toolchains.playwright-chromium", "playwright-chromium")
            if not chromium:
                raise RuntimeError("registered Chromium missing; no automatic installation")
            declared_build = next((p for p in Path(chromium).parts if p.startswith("chromium-")), None)
            expected_build = next((p for p in Path(playwright.chromium.executable_path).parts if p.startswith("chromium-")), None)
            if declared_build is None or declared_build != expected_build:
                raise RuntimeError("registered Chromium build differs from installed Playwright")
            profile = run / "tmp/stitch-browser-profile"
            print("[stitch-browser] launching owned Chromium", flush=True)
            context = playwright.chromium.launch_persistent_context(
                str(profile), executable_path=chromium, headless=True, viewport={"width": 1440, "height": 1000},
                timeout=30000,
                reduced_motion="reduce", service_workers="block", accept_downloads=False,
                args=["--disable-background-networking", "--disable-component-update", "--no-first-run", "--no-default-browser-check",
                      "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1"])
            print("[stitch-browser] owned Chromium ready", flush=True)
            probe.report["browser"] = {"version": context.browser.version if context.browser else "UNKNOWN",
                                       "executable": chromium, "profile": str(profile), "declared_build": declared_build}
            if context.browser:
                print("[stitch-browser] querying own browser PID", flush=True)
                session = context.browser.new_browser_cdp_session()
                info = session.send("SystemInfo.getProcessInfo")
                browser_pids = [row["id"] for row in info["processInfo"] if row["type"] == "browser"]
                session.detach()
                print("[stitch-browser] own browser PID recorded", flush=True)
                faulthandler.cancel_dump_traceback_later()
            if not browser_pids:
                raise RuntimeError("owned Chromium browser PID could not be recorded")
            probe.report["processes"] += [{"kind": "owned-chromium", "pid": pid} for pid in browser_pids]

            def route_request(route):
                url = urlsplit(route.request.url)
                if url.scheme not in {"http", "https"} or url.hostname != "127.0.0.1" or url.port != port:
                    probe.report["blocked_external_requests"].append({"case": probe.case, "url": route.request.url, "method": route.request.method})
                    route.abort("blockedbyclient")
                    return
                # URL route prefixes, not absolute filesystem locations.
                if url.path.startswith("/" + "api") or url.path.startswith("/" + "workspace" + "/api"):
                    probe.report["api_requests"].append({"case": probe.case, "path": url.path, "method": route.request.method})
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(a0.api_payload(route.request.url)))
                else:
                    route.continue_()

            context.route("**/*", route_request)
            # A routed socket stays mocked unless connect_to_server is called.
            # Do not synchronously close during this callback: the installed
            # Playwright runtime deadlocks while dispatching the socket event.
            context.route_web_socket("**/*", lambda websocket: None)
            context.add_init_script("if(location.protocol==='http:'){\n" + synthetic_research(a0) + "\n}")
            groups = []
            if args.groups in {"all", "desktop"}:
                groups += [("desktop-" + t, t, ("1440x1000@100", 1440, 1000, 1), list(labels)) for t in a0.AAOS_THEME_IDS]
            if args.groups in {"all", "narrow"}:
                groups += [("narrow-" + v[0], "cosmic", v, list(labels)) for v in a0.DESKTOP_MATRIX if v[1:3] in {(640, 480), (960, 540)}]
            if args.groups in {"all", "research"}:
                groups += [("research-" + v[0], "cosmic", v, ["05"]) for v in a0.DESKTOP_MATRIX]
            probe.report["planned_cases"] = sum(len(ids) for _, _, _, ids in groups)
            for group, theme, viewport, ids in groups:
                probe.case = group + "-startup"
                page = context.new_page()
                page.set_default_timeout(4500)
                page.on("pageerror", lambda error: probe.report["console_errors"].append({"case": probe.case, "kind": "pageerror", "text": str(error)}))
                page.on("console", lambda message: probe.report["console_errors"].append({"case": probe.case, "kind": "console", "text": message.text}) if message.type == "error" else None)
                page.on("dialog", lambda dialog: dialog.dismiss())
                try:
                    _, width, height, scale = viewport
                    page.set_viewport_size({"width": width, "height": height})
                    cdp = context.new_cdp_session(page)
                    cdp.send("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": scale, "mobile": False})
                    page.goto(origin + "/#page=01", wait_until="networkidle", timeout=20000)
                    page.locator(".stitch-workspace-menu").wait_for(state="visible")
                    def passive_companion_focus():
                        if width >= 1280 and height >= 700 and page.locator("#stitch-companion-window").is_visible():
                            assert not page.locator("#stitch-companion-window").evaluate("n=>n===document.activeElement||n.contains(document.activeElement)"), "automatic companion opening stole business focus"
                    probe.step("automatic-companion-no-focus-steal", passive_companion_focus)
                    theme_select(page, theme, a0)
                    interactions = {"group": group, "companion": probe.step("companion-keyboard-close", lambda: companion_probe(page, probe)),
                                    "diagnostic": probe.step("diagnostic-escape-focus", lambda: focus_dialog(page, "运行诊断", "运行诊断")),
                                    "command": probe.step("command-escape-focus", lambda: focus_dialog(page, "打开全局命令", "全局命令"))}
                    probe.report.setdefault("interaction_groups", []).append(interactions)
                    # Exercise each visible Dock entry on every size/theme group.
                    for label, target in DOCK_PAGES.items():
                        def click_dock(label=label, target=target):
                            page.get_by_role("navigation", name="工作空间快捷导航").get_by_role("button", name=label, exact=True).click(timeout=4000)
                            assert_page(page, target)
                        probe.step("dock-" + target, click_dock)
                    probe.step("launchpad-search-and-escape", lambda: launchpad_navigation(page))
                    for page_id in ids:
                        probe.case = group + "-page-" + page_id
                        case = {"id": probe.case, "page_id": page_id, "label": labels[page_id], "theme": theme,
                                "viewport": {"label": viewport[0], "width": width, "height": height, "device_scale_factor": scale},
                                "status": "NOT_EXECUTED"}
                        start_failures = len(probe.report["failures"])
                        probe.step("visible-menu-navigation", lambda: navigate_menu(page, page_id, labels))
                        try:
                            assert_page(page, page_id)
                            page.wait_for_timeout(100)
                            if page_id == "05":
                                case["research_focus"] = probe.step("research-focus-no-save", lambda: research_focus(page))
                                case["research_original_focus"] = probe.step("research-original-no-focus-steal", lambda: research_original_no_focus_steal(page))
                                if case["research_focus"] and case["research_original_focus"]:
                                    page.get_by_role("navigation", name="研究内容导航").get_by_role("button", name="证据对比 (2)", exact=True).click(timeout=4000)
                                    if width >= 1280 and height >= 700 and not page.locator("#stitch-companion-window").is_visible():
                                        page.get_by_role("button", name="小栖", exact=True).click(timeout=4000)
                            case["geometry"] = probe.step("geometry-and-hit-targets", lambda: measure(page))
                            if case["geometry"] is not None:
                                audit_measurement(probe, case["geometry"])
                            case["screenshot"] = probe.screenshot(page, probe.case)
                        except Exception as error:
                            probe.fail("case-readback", error)
                            case["screenshot"] = probe.screenshot(page, probe.case + "-failed")
                        case["status"] = "PASS" if len(probe.report["failures"]) == start_failures else "FAIL"
                        probe.report["cases"].append(case)
                        probe.checkpoint()
                    cdp.detach()
                except Exception as error:
                    probe.fail("group-startup", error)
                    probe.screenshot(page, group + "-startup-failed")
                    completed = {c["page_id"] for c in probe.report["cases"] if c["id"].startswith(group + "-page-")}
                    for page_id in ids:
                        if page_id not in completed:
                            probe.report["cases"].append({"id": group + "-page-" + page_id, "page_id": page_id,
                                                           "theme": theme, "status": "BLOCKED", "reason": str(error)})
                finally:
                    probe.step("close-owned-page", page.close)
                    probe.checkpoint()
            context.close()
            context = None
        probe.report["source_after"] = source_identity()
        if probe.report["source_before"]["ui_tree_sha256"] != probe.report["source_after"]["ui_tree_sha256"]:
            probe.fail("source-consistency", "frontend UI source changed during the matrix; rerun final candidate")
    except Exception as error:
        probe.fail("startup", error)
        probe.report["startup_traceback"] = traceback.format_exc()
    finally:
        if context is not None:
            probe.step("close-owned-browser", context.close)
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=5)
            probe.report["cleanup"]["vite"] = {"pid": process.pid, "exited": process.poll() is not None}
        if log is not None:
            log.close()
        probe.report["cleanup"]["chromium"] = [{"pid": pid, "exited": not pid_running(pid)} for pid in browser_pids]
        if port is not None:
            probe.report["cleanup"]["port"] = {"port": port, "closed": not port_open(port)}
        if any(not row["exited"] for row in probe.report["cleanup"].get("chromium", [])):
            probe.fail("cleanup", "owned Chromium process still running")
        if port is not None and port_open(port):
            probe.fail("cleanup", "owned Vite port still listening")
        if probe.report["console_errors"]:
            probe.fail("browser-errors", f"{len(probe.report['console_errors'])} console/page errors; see complete records")
        if probe.report["blocked_external_requests"]:
            probe.fail("unexpected-egress-attempt", f"{len(probe.report['blocked_external_requests'])} requests blocked before network")
        if "planned_cases" in probe.report and len(probe.report["cases"]) != probe.report["planned_cases"]:
            probe.fail("incomplete-matrix", {"planned": probe.report["planned_cases"], "recorded": len(probe.report["cases"])})
        probe.report["started_at"] = started
        faulthandler.cancel_dump_traceback_later()
        probe.report["ended_at"] = datetime.now(timezone.utc).isoformat()
        probe.report["status"] = "FAIL" if probe.report["failures"] else "PASS"
        probe.report["case_counts"] = {state: sum(c["status"] == state for c in probe.report["cases"]) for state in ["PASS", "FAIL", "BLOCKED"]}
        write_json(artifacts / "stitch-browser.json", probe.report)
        print(json.dumps({"status": probe.report["status"], "evidence_level": "SYNTHETIC", "case_counts": probe.report["case_counts"],
                          "failures": len(probe.report["failures"]), "report": str(artifacts / "stitch-browser.json")}, ensure_ascii=False))
    return 1 if probe.report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
