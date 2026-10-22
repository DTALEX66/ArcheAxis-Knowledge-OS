"""Targeted formal Stitch reader check with authored pinned-reference fixtures.

SYNTHETIC bridge, real browser and formal UI. No actual Core/native/install claim.
Run through runtime/dev.py; reuse the registered project browser and owned Vite.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fixture(a0):
    def document(identity, text):
        editor = {"type": "doc", "content": [{"type": "paragraph", "attrs": {"block_id": "selected"}, "content": [{"type": "text", "text": text}]}]}
        return {"document_id": identity, "version": 1, "title": identity, "source_id": None, "source_revision": None,
                "text_projection": text, "content_sha256": hashlib.sha256(json.dumps(editor).encode()).hexdigest(), "editor_json": editor,
                "blocks": [{"block_id": "selected", "kind": "paragraph", "ordinal": 0, "node_json": editor["content"][0], "text_projection": text, "codec_status": "known"}]}
    target = document("embed_target", "固定 v1 块内容，不读取 v2。")
    original_text = "SYNTHETIC 附件原文 <script>不执行</script>"
    raw = original_text.encode()
    original = {"source_id": "embed_asset", "name": "authored.txt", "media_type": "text/plain", "sha256": hashlib.sha256(raw).hexdigest(), "content_base64": base64.b64encode(raw).decode()}
    references = [
        {"kind": "document", "document_id": target["document_id"], "version": 1, "block_id": "selected"},
        {"kind": "source", "source_id": original["source_id"], "sha256": original["sha256"]},
        {"kind": "document", "document_id": "missing_embed", "version": 1},
        {"kind": "document", "document_id": target["document_id"], "version": 1},
    ]
    main = document("doc_embed_browser", "原文保留，嵌入由已保存关系读取。")
    main["title"] = "SYNTHETIC嵌入验证"
    main["editor_json"]["attrs"] = {"archeaxis_relations": {"schema": "archeaxis.relations/v1", "relations": [
        {"id": f"embed_{index}", "kind": "related", "label": f"固定嵌入 {index}", "target": reference, "presentation": "embed"}
        for index, reference in enumerate(references)
    ]}}
    main["content_sha256"] = hashlib.sha256(json.dumps(main["editor_json"]).encode()).hexdigest()
    values = {"main": main, "target": target, "original": original}
    return a0.host_bridge_stub() + "\n" + """
(() => {
 const previous=window.__TAURI__.core.invoke, values=__VALUES__;
 window.__EMBED_CALLS__=[];
 window.__TAURI__.core.invoke=async(command,request)=>{
  const op=request?.request?.operation,p=request?.request?.payload??{};
  if(command==='core_command'){
   window.__EMBED_CALLS__.push({op,p:structuredClone(p)});
   if(op==='documents_list'){const {document_id,source_id,source_revision,title,version,content_sha256}=values.main;return {status:200,body:{documents:[{document_id,source_id,source_revision,title,version,content_sha256}],next_cursor:null,snapshot_count:1}};}
   if(op==='document_get'&&p.document_id===values.main.document_id)return {status:200,body:structuredClone(values.main)};
   if(op==='document_version'){
    const doc=[values.main,values.target].find(doc=>doc.document_id===p.document_id&&doc.version===p.version);
    return doc?{status:200,body:structuredClone(doc)}:{status:404,body:{error:'FIXED_VERSION_UNAVAILABLE'}};
   }
   if(op==='source_original'&&p.source_id===values.original.source_id)return {status:200,body:structuredClone(values.original)};
   if(['document_draft','document_create','ingest_member_relations_apply'].includes(op))return {status:503,body:{error:'READ_ONLY_PROBE'}};
  }
  return previous(command,request);
 };
})();
""".replace("__VALUES__", json.dumps(values, ensure_ascii=False))


def main():
    run = Path(os.environ["ARCHEAXIS_RUN_ROOT"]).resolve()
    run.relative_to((ROOT / ".project-local/runs").resolve())
    harness = load("embed_browser_harness", ROOT / "scripts/probes/stitch_ui_browser.py")
    artifacts = run / "artifacts/document-embeds-browser"
    artifacts.mkdir(parents=True, exist_ok=False)
    probe = harness.Probe(artifacts)
    probe.report["schema"] = "archeaxis.document-embeds-browser/v1"
    probe.report["source_before"] = harness.source_identity()
    process = log = context = None
    browser_pids = []
    port = None
    try:
        a0 = harness.load_a0()
        process, log, origin, port = harness.start_vite(a0, run, probe)
        probe.checkpoint()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            chromium = a0._declared_tool("ext.toolchains.playwright-chromium", "playwright-chromium")
            if not chromium:
                raise RuntimeError("Registered Chromium missing; no automatic installation")
            declared = next((part for part in Path(chromium).parts if part.startswith("chromium-")), None)
            expected = next((part for part in Path(playwright.chromium.executable_path).parts if part.startswith("chromium-")), None)
            if declared is None or declared != expected:
                raise RuntimeError("Registered Chromium build mismatch")
            context = playwright.chromium.launch_persistent_context(str(run / "tmp/embed-profile"), executable_path=chromium,
                headless=True, viewport={"width": 1440, "height": 1000}, reduced_motion="reduce", service_workers="block", accept_downloads=False,
                args=["--disable-background-networking", "--disable-component-update", "--no-first-run", "--no-default-browser-check", "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1"])
            session = context.browser.new_browser_cdp_session()
            browser_pids = [row["id"] for row in session.send("SystemInfo.getProcessInfo")["processInfo"] if row["type"] == "browser"]
            session.detach()
            if not browser_pids:
                raise RuntimeError("Owned browser PID not recorded")
            probe.report["processes"] += [{"kind": "owned-chromium", "pid": pid} for pid in browser_pids]
            probe.checkpoint()
            def route_request(route):
                url = urlsplit(route.request.url)
                if url.scheme != "http" or url.hostname != "127.0.0.1" or url.port != port:
                    probe.report["blocked_external_requests"].append(route.request.url)
                    route.abort("blockedbyclient")
                elif url.path.startswith("/api") or url.path.startswith("/workspace/api"):
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(a0.api_payload(route.request.url)))
                else:
                    route.continue_()
            context.route("**/*", route_request)
            context.route_web_socket("**/*", lambda websocket: None)
            context.add_init_script("if(location.protocol==='http:'){" + fixture(a0) + "}")
            page = context.new_page()
            page.set_default_timeout(7000)
            page.on("pageerror", lambda error: probe.report["console_errors"].append(str(error)))
            page.on("console", lambda message: probe.report["console_errors"].append(message.text) if message.type == "error" else None)
            try:
                page.goto(origin + "/#page=02", wait_until="networkidle")
                if page.get_by_role("button", name="收起小栖窗口").is_visible():
                    page.get_by_role("button", name="收起小栖窗口").click()
                page.get_by_role("button", name="打开文档 SYNTHETIC嵌入验证", exact=True).click()
                embeds = page.get_by_role("region", name="文档嵌入内容", exact=True)
                embeds.get_by_text("固定 v1 块内容，不读取 v2。", exact=True).wait_for()
                embeds.get_by_text("SYNTHETIC 附件原文 <script>不执行</script>", exact=True).wait_for()
                embeds.get_by_role("alert").wait_for()
                assert embeds.get_by_role("complementary", name="固定版本嵌入阅读").count() == 3
                assert page.locator(".tiptap").inner_text() == "原文保留，嵌入由已保存关系读取。"
                geometry = page.locator(".ui-reader-document").evaluate("n=>({content_bottom:Math.max(...[...n.querySelectorAll('.document-editor > nav,.document-editor > p')].map(x=>x.getBoundingClientRect().bottom)),embed_top:n.querySelector('.ui-document-embeds').getBoundingClientRect().top,editor_height:n.querySelector('.document-editor').getBoundingClientRect().height})")
                probe.report["editor_embed_geometry"] = geometry
                assert geometry["content_bottom"] <= geometry["embed_top"] + 1 and geometry["editor_height"] >= 240, "editor controls/body collapse into embeds: " + str(geometry)
                fixed = embeds.get_by_text("固定 v1 块内容，不读取 v2。", exact=True)
                fixed.scroll_into_view_if_needed()
                assert fixed.evaluate("n=>{const r=n.getBoundingClientRect(), hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return hit===n||n.contains(hit)}")
                probe.screenshot(page, "reader-embeds-desktop")
                page.set_viewport_size({"width": 640, "height": 480})
                embeds.get_by_role("button", name="下一组嵌入").click()
                embeds.get_by_text("固定 v1 块内容，不读取 v2。", exact=True).wait_for()
                assert embeds.get_by_role("complementary", name="固定版本嵌入阅读").count() == 1
                assert page.evaluate("document.scrollingElement.scrollWidth <= innerWidth+2")
                fixed.scroll_into_view_if_needed()
                assert fixed.evaluate("n=>{const r=n.getBoundingClientRect(), hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return hit===n||n.contains(hit)}")
                probe.screenshot(page, "reader-embeds-narrow")
                probe.report["calls"] = page.evaluate("window.__EMBED_CALLS__")
                assert not any(row["op"] in {"document_draft", "document_create", "ingest_member_relations_apply"} for row in probe.report["calls"])
                assert all(row["p"].get("version") == 1 for row in probe.report["calls"] if row["op"] == "document_version")
                assert not probe.report["console_errors"] and not probe.report["blocked_external_requests"]
                probe.report["cases"] = ["formal-reader-mount", "fixed-block", "verified-source", "missing-version-no-fallback", "three-visible-budget", "explicit-pagination", "body-unchanged-no-writes", "640x480-no-page-overflow"]
            except Exception:
                probe.screenshot(page, "failure-surface")
                (artifacts / "failure-surface.txt").write_text(page.locator("body").inner_text()[:16000], encoding="utf-8")
                probe.report["calls"] = page.evaluate("window.__EMBED_CALLS__")
                raise
            context.close()
            context = None
    except Exception as error:
        probe.fail("targeted-embed-browser", error)
    finally:
        if context is not None:
            try:
                context.close()
            except Exception as error:
                # sync_playwright already closes its transport on exceptional
                # exit. Still clean Vite and verify the recorded browser PID.
                probe.report["cleanup"]["context_close_observation"] = str(error)
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except Exception:
                    process.kill()
                    process.wait(timeout=5)
            probe.report["cleanup"]["vite"] = {"pid": process.pid, "exited": process.poll() is not None}
        if log:
            log.close()
        probe.report["cleanup"]["browser"] = [{"pid": pid, "exited": not harness.pid_running(pid)} for pid in browser_pids]
        probe.report["cleanup"]["port_closed"] = port is None or not harness.port_open(port)
        probe.report["source_after"] = harness.source_identity()
        probe.report["source_consistent"] = probe.report["source_before"] == probe.report["source_after"]
        if not probe.report["source_consistent"] or not probe.report["cleanup"]["port_closed"]:
            probe.fail("source-or-cleanup", "Source changed or owned port remains open")
        if any(not row["exited"] for row in probe.report["cleanup"]["browser"]):
            probe.fail("browser-cleanup", "Owned browser still running")
        probe.report["status"] = "PASS" if not probe.report["failures"] else "FAIL"
        harness.write_json(artifacts / "receipt.json", probe.report)
    print(json.dumps({"status": probe.report["status"], "evidence_level": "SYNTHETIC", "cases": len(probe.report["cases"]), "failures": probe.report["failures"], "receipt": str(artifacts / "receipt.json")}, ensure_ascii=False))
    return 0 if probe.report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
