"""Rendered production-page coverage; synthetic host, never installed acceptance.

Uses the existing A0 bridge and process lifecycle. No product API or external
network is contacted. Unknown fixture operations deliberately fail with 501.
The report retains all axe violations/incomplete results and navigation failures.
"""
from __future__ import annotations

import argparse
import base64
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
from playwright.sync_api import expect, sync_playwright


PARENTS = {"03": "02", "04": "02", "05": "02", "07": "06", "08": "06", "09": "06", "10": "06",
           "11": "06", "12": "06", "14": "13", "16": "15", "18": "17",
           "20": "19", "21": "06", "22": "13"}


def axe_report(page, source: str) -> dict:
    if not page.evaluate("() => typeof window.axe === 'object'"):
        page.add_script_tag(content=source)
    return page.evaluate("""async () => {
      const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']}});
      const compact=items=>items.map(({id,impact,description,nodes})=>({id,impact,description,
        nodes:nodes.map(({target,html,failureSummary})=>({target,html,failureSummary}))}));
      return {version:r.testEngine.version,violations:compact(r.violations),
        incomplete:compact(r.incomplete),passes:r.passes.map(x=>x.id)};
    }""")


def quick_menu_tab(page) -> dict:
    """Keep native Tab order usable while the menu's opacity is still opening."""
    menu = page.locator(".stitch-menus > details").filter(
        has=page.locator("summary").get_by_text("文件", exact=True))
    trigger = menu.locator("summary")
    target = menu.locator('button[data-page-id="16"]')
    original_page = page.locator(".cabin-shell").get_attribute("data-cabin-page")
    original_motion = page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    observations = []
    # Recording event identities must not force style/layout between click and Tab.
    page.evaluate("""() => {
      const trace = {events: []};
      trace.record = event => {
        if (event.type === 'keydown' && event.key !== 'Tab') return;
        trace.events.push({type:event.type,key:event.key??null,time:performance.now(),trusted:event.isTrusted});
      };
      window.__aaosQuickMenuTab = trace;
      document.addEventListener('click', trace.record, true);
      document.addEventListener('keydown', trace.record, true);
    }""")
    try:
        for motion in ("no-preference", "reduce"):
            page.emulate_media(reduced_motion=motion)
            page.keyboard.press("Escape")
            expect(menu).not_to_have_attribute("open", "")
            trigger.scroll_into_view_if_needed()
            trigger.focus()
            bounds = trigger.bounding_box()
            assert bounds, "File menu trigger is not rendered"
            page.evaluate("window.__aaosQuickMenuTab.events = []")
            page.mouse.click(bounds["x"] + bounds["width"] / 2, bounds["y"] + bounds["height"] / 2)
            # No visibility polling, computed style, layout read or delay here:
            # the old content-visibility transition skipped all four menu buttons.
            for _ in range(3):
                page.keyboard.press("Tab")
            observed = page.evaluate("""() => ({events:window.__aaosQuickMenuTab.events,
              active:{tag:document.activeElement?.tagName,page:document.activeElement?.dataset.pageId??null,
                text:document.activeElement?.textContent?.trim()},
              page:document.querySelector('.cabin-shell')?.dataset.cabinPage})""")
            clicks = [event for event in observed["events"] if event["type"] == "click"]
            tabs = [event for event in observed["events"] if event["type"] == "keydown"]
            assert len(clicks) == 1 and len(tabs) == 3 and all(event["trusted"] for event in clicks + tabs), observed
            observed.update(motion=motion, click_to_first_tab_ms=tabs[0]["time"] - clicks[0]["time"],
                            click_to_last_tab_ms=tabs[-1]["time"] - clicks[0]["time"])
            observations.append(observed)
            assert target.evaluate("node => node === document.activeElement"), observed
            assert observed["page"] == original_page, ("Tab activated a page", observed)
            page.keyboard.press("Escape")
            assert trigger.evaluate("node => node === document.activeElement"), "menu Escape lost its trigger"
            assert not menu.evaluate("node => node.open"), "menu Escape did not close File"
        return {"status": "PASS", "page_unchanged": original_page,
                "escape_restores_focus": True, "observations": observations}
    finally:
        page.keyboard.press("Escape")
        page.emulate_media(reduced_motion="reduce" if original_motion else "no-preference")
        page.evaluate("""() => {
          const trace=window.__aaosQuickMenuTab;
          document.removeEventListener('click',trace.record,true);
          document.removeEventListener('keydown',trace.record,true);
          delete window.__aaosQuickMenuTab;
        }""")


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
    trigger = panel.get_by_role("button", name="状态与诊断：模板能力登记与运行状态", exact=True)
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


def research_fixture() -> dict:
    """Public synthetic input only; never read a user's research or original files."""
    raw = "第一段😀\r\n第二段保留原件；长中文引文用于核对阅读、换行和定位。".encode()
    revision = sha256(raw).hexdigest()
    quote = "第一段😀\r\n"
    position = json.dumps({"type": "text", "start": 0, "end": len(quote.encode())}, separators=(",", ":"))
    reference = {"kind": "source", "source_id": "ui_research_source", "sha256": revision}
    citation = {"schema": "archeaxis.research-citation/v1", "anchor_id": "ui_research_anchor",
                "source_sha256": revision, "anchor_position_sha256": sha256(position.encode()).hexdigest(),
                "quote": quote, "quote_sha256": sha256(quote.encode()).hexdigest(), "read_snapshot_sha256": revision}
    research = {"schema": "archeaxis.research/v1", "question": "比较资料中的支持、反对与未解决问题",
                "materials": [{"id": "ui_material", "note": "合成材料：保留中文、表情和原始换行；不作为真实研究依据。",
                               "reference": reference, "citation": citation}],
                "hypotheses": [], "methods": [], "experiments": [], "counterevidence": [], "conclusions": [], "unresolved": []}
    editor = {"type": "doc", "attrs": {"archeaxis_research": research}, "content": []}
    doc = {"document_id": "ui_research_document", "title": "研究引文排版样例", "version": 1,
           "source_id": None, "source_revision": None, "content_sha256": sha256(json.dumps(editor).encode()).hexdigest(),
           "editor_json": editor, "text_projection": research["question"], "blocks": []}
    return {"document": doc, "source": {"source_id": reference["source_id"], "source_revision": revision,
            "sha256": revision, "original_name": "中文原件排版样例.txt", "imported_at": "2026-10-20T00:00:00Z"},
            "original": {"source_id": reference["source_id"], "name": "中文原件排版样例.txt", "sha256": revision,
                         "media_type": "text/plain", "content_base64": base64.b64encode(raw).decode()},
            "reference": reference, "citation": citation, "byte_length": len(raw),
            "resolution": {"source_id": reference["source_id"], "anchor_id": citation["anchor_id"], "status": "CURRENT",
                           "source_revision": revision, "current_source_revision": revision, "position": position,
                           "scope": "locator_provenance_only", "reason": "SYNTHETIC_MATCH"},
            "knowledge_items": [{"knowledge_id": f"ui_knowledge_{n}", "head": "同名合成材料", "status": "candidate", "active": False} for n in (1, 2)]}


def research_fixture_bridge(fixture: dict) -> str:
    # Extend the existing isolated bridge only for named fixture objects. Unknown calls retain 501.
    return """(() => {
      const fixture=__FIXTURE__, original=window.__TAURI__.core.invoke;
      window.__TAURI__.core.invoke=async(command,args)=>{
        const request=args?.request, op=request?.operation, payload=request?.payload??{};
        if(command!=="core_command") return original(command,args);
        if(op==="documents_list"||op==="sources_list") {
          const response=await original(command,args); if(response.status!==200)return response;
          const body=structuredClone(response.body);
          if(op==="documents_list") {
            const {editor_json,blocks,text_projection,...summary}=fixture.document;
            body.documents=[summary,...body.documents];body.snapshot_count++;
          }
          else body.sources=[fixture.source,...body.sources];
          return {status:200,body};
        }
        if((op==="document_get"||op==="document_version")&&payload.document_id===fixture.document.document_id)
          return op==="document_version"&&payload.version!==1?{status:404,body:{error:"FIXTURE_VERSION_NOT_FOUND"}}:{status:200,body:structuredClone(fixture.document)};
        if(op==="document_draft"&&payload.document_id===fixture.document.document_id)
          return {status:409,body:{error:"READ_ONLY_UI_FIXTURE"}};
        if(op==="source_original"&&payload.source_id===fixture.source.source_id)
          return {status:200,body:structuredClone(fixture.original)};
        if(op==="source_jobs"&&payload.source_id===fixture.source.source_id)
          return {status:200,body:{source_id:fixture.source.source_id,jobs:[],jobs_capped:false}};
        if(op==="anchor_resolve"&&payload.source_id===fixture.source.source_id&&payload.anchor_id===fixture.citation.anchor_id)
          return {status:200,body:structuredClone(fixture.resolution)};
        if(op==="search"&&["对照样例","无匹配样例","服务错误样例","迟到样例"].includes(payload.q)) {
          if(payload.q==="服务错误样例")return {status:503,body:{error:"SYNTHETIC_SEARCH_FAILURE"}};
          if(payload.q==="迟到样例")await new Promise(resolve=>setTimeout(resolve,250));
          const items=payload.q==="无匹配样例"?[]:structuredClone(fixture.knowledge_items);
          return {status:200,body:{items,transforms:[],count:items.length,transform_count:0,documents:[],document_count:0}};
        }
        return original(command,args);
      };
    })();""".replace("__FIXTURE__", json.dumps(fixture, ensure_ascii=False))


def research_citations(page, output: Path, case_id: str, fixture: dict, axe_source: str) -> dict:
    def dismiss_diagnostic(dialog, trigger):
        # Visible portal text can precede Radix's focus/effect setup. Assert the
        # real keyboard target before sending one Escape; never force focus or
        # repeat the key to hide a failed dismiss/focus-return interaction.
        expect(dialog.get_by_role("button", name="关闭运行诊断", exact=True)).to_be_focused(timeout=8000)
        page.keyboard.press("Escape")
        dialog.wait_for(state="hidden")
        expect(trigger).to_be_focused(timeout=8000)

    page.get_by_role("button", name="研究引文排版样例 · 版本 1", exact=True).click()
    region = page.get_by_role("region", name="研究编辑区", exact=True)
    quote = region.get_by_role("complementary", name="已保存版本的引文快照", exact=True)
    quote.wait_for()
    assert quote.locator("blockquote").text_content() == fixture["citation"]["quote"]
    assert not re.search(r"ui_research_source|ui_research_anchor|[a-f0-9]{64}|expected_version|GraphRAG", region.inner_text())
    trigger = quote.get_by_role("button", name="状态与诊断：研究引文原始记录", exact=True)
    trigger.click()
    dialog = page.get_by_role("dialog", name="运行诊断", exact=True)
    assert json.loads(dialog.locator("pre").inner_text()) == {"reference": fixture["reference"], "citation": fixture["citation"]}
    dismiss_diagnostic(dialog, trigger)
    quote.get_by_role("button", name="重新核验引文定位", exact=True).click()
    page.get_by_text("引文定位仍有效；仅核对定位，不表示内容已证实。", exact=True).wait_for()
    replay_trigger = quote.get_by_role("button", name="状态与诊断：引文定位核验记录", exact=True)
    replay_trigger.click()
    resolution = json.loads(dialog.locator("pre").first.inner_text())
    assert resolution["result"] == fixture["resolution"] and resolution["outcome"] == "read", resolution
    assert resolution["citation"] == fixture["citation"] and resolution["reference"] == fixture["reference"]
    dismiss_diagnostic(dialog, replay_trigger)
    region.get_by_role("button", name="摘录材料 1原文", exact=True).click()
    original = region.get_by_role("region", name="已读取并核对指纹的原件", exact=True)
    original.wait_for()
    source_trigger = original.get_by_role("button", name="状态与诊断：研究原件读取记录", exact=True)
    source_trigger.click()
    record = json.loads(dialog.locator("pre").first.inner_text())
    assert record == {"reference": fixture["reference"], "name": fixture["original"]["name"],
                      "sha256": fixture["source"]["sha256"], "byte_length": fixture["byte_length"]}
    dismiss_diagnostic(dialog, source_trigger)
    region.get_by_role("button", name="添加材料或待整理说明", exact=True).click()
    picker = page.get_by_role("dialog", name="选择研究引用", exact=True)
    search = picker.get_by_role("button", name="检索本地知识", exact=True)
    query = picker.get_by_role("textbox", name="研究本地知识检索", exact=True)
    query.fill("对照样例")
    search.click()
    picker.get_by_text("本地检索完成：2 项结果。", exact=True).wait_for()
    assert "ui_knowledge_" not in picker.inner_text()
    result_trigger = picker.get_by_role("button", name="状态与诊断：本地知识结果 2", exact=True)
    result_trigger.click()
    assert json.loads(dialog.locator("pre").first.inner_text()) == fixture["knowledge_items"][1]
    dismiss_diagnostic(dialog, result_trigger)
    picker.get_by_role("button", name="选择本地知识结果 2 · 同名合成材料", exact=True).click()
    picker.get_by_text("将绑定 同名合成材料 · 固定知识版本", exact=True).wait_for()
    picker_axe = axe_report(page, axe_source)
    page.screenshot(path=str(output / f"research-picker-{case_id}.png"))
    query.fill("无匹配样例")
    search.click()
    picker.get_by_text("本地检索完成：0 项结果。", exact=True).wait_for()
    query.fill("服务错误样例")
    search.click()
    picker.get_by_role("alert").get_by_text("本地检索失败，是否存在结果仍未知；可重新检索。", exact=True).wait_for()
    assert picker.get_by_text("本地检索完成：0 项结果。", exact=True).count() == 0
    error_axe = axe_report(page, axe_source)
    page.screenshot(path=str(output / f"research-picker-error-{case_id}.png"))
    query.fill("迟到样例")
    search.click()
    query.fill("输入已更新")
    picker.get_by_text("以下是上次关键词“迟到样例”的结果；输入已变化，请重新检索。", exact=True).wait_for()
    expect(picker.get_by_role("button", name="选择本地知识结果 2 · 同名合成材料", exact=True)).to_be_disabled()
    expect(picker.get_by_role("button", name="添加所选引用", exact=True)).to_be_disabled()
    picker.get_by_role("button", name="取消引用选择", exact=True).click()
    picker.wait_for(state="hidden")
    trigger.scroll_into_view_if_needed()
    control = a0.visible_control_box(trigger)
    assert control["reachable"] and abs(control["height"] - control["rawHeight"]) <= 1, control
    reference_spacing = quote.locator("..").locator(":scope > ul > li").first.evaluate("""row=>{
      const label=row.querySelector('span').getBoundingClientRect(),button=row.querySelector('button').getBoundingClientRect();
      const sameLine=button.top<label.bottom && button.bottom>label.top;
      return {same_line:sameLine,gap:sameLine?button.left-label.right:button.top-label.bottom};
    }""")
    assert reference_spacing["gap"] >= 7.5, reference_spacing
    screenshot = output / f"research-citation-{case_id}.png"
    page.screenshot(path=str(screenshot))
    return {"status": "PASS", "quote_exact": True, "diagnostic_focus_restored": True,
            "original_byte_length": fixture["byte_length"], "control": control,
            "reference_spacing": reference_spacing, "screenshot": str(screenshot),
            "resolution_record_exact": True, "query_states": ["read", "empty", "failed", "stale"],
            "picker_axe": picker_axe, "error_axe": error_axe}


def public_research(page, output: Path, case_id: str) -> dict:
    panel = page.get_by_role("region", name="公开资料检索", exact=True)
    query = panel.get_by_role("textbox", name="公开检索关键词", exact=True)
    expect(query).to_have_value("")
    expect(panel.get_by_role("button", name="检索公开资料", exact=True)).to_be_disabled()
    assert "百科、社区、科研检索尚未接线" in panel.inner_text()
    query.fill("公开的间隔复习研究 2026")
    panel.get_by_role("checkbox", name="社区", exact=True).uncheck()
    keep = panel.get_by_role("button", name="把检索计划加入未决草稿", exact=True)
    keep.click()
    expect(keep).to_be_disabled()
    note = page.get_by_role("textbox", name="未决 1", exact=True)
    expect(note).to_have_value(re.compile(r"公开检索计划（未执行外部检索）\n关键词：公开的间隔复习研究 2026\n来源范围：百科、科研"))
    query.scroll_into_view_if_needed()
    page.screenshot(path=str(output / f"public-research-{case_id}.png"))
    return {"status": "PASS", "production_adapter": "NOT_CONNECTED", "query_initially_empty": True,
            "explicit_plan_in_unresolved_draft": True, "external_retrieval": "NOT_EXECUTED"}


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
    parser.add_argument("--research-citations", action="store_true")
    parser.add_argument("--public-research", action="store_true")
    args = parser.parse_args()
    if args.template_requirements and args.pages and "15" not in args.pages:
        parser.error("--template-requirements requires production page 15")
    if args.research_citations and (args.state != "baseline" or (args.pages and "05" not in args.pages)):
        parser.error("--research-citations requires baseline state and production page 05")
    if args.public_research and (args.state != "baseline" or (args.pages and "05" not in args.pages)):
        parser.error("--public-research requires baseline state and production page 05")
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
                    if args.research_citations:
                        bridge += research_fixture_bridge(research_fixture())
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
                        a0.pause_first_use_guide(page)
                        page.locator(".space-view:visible").wait_for()
                        report.setdefault("menu_quick_tab", []).append({"theme": theme, "viewport": [width, height],
                            **quick_menu_tab(page)})
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
                                if args.research_citations and page_id == "05":
                                    case["research_citations"] = research_citations(page, output, f"{theme}-{width}x{height}", research_fixture(), axe_source)
                                if args.public_research and page_id == "05":
                                    case["public_research"] = public_research(page, output, f"{theme}-{width}x{height}")
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
                                case["axe"] = axe_report(page, axe_source)
                                research = case.get("research_citations", {})
                                child_violations = research.get("picker_axe", {}).get("violations", []) + research.get("error_axe", {}).get("violations", [])
                                case["status"] = "FAIL" if case["axe"]["violations"] or child_violations else "PASS_AUTOMATED_ONLY"
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
