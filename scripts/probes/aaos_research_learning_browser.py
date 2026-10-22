"""Owned browser transport shim: canonical built UI reads actual candidate Core.

Only listed read operations reach Core. Remaining native shell/state surfaces are
synthetic. Credentials stay in Python; this is not Tauri/native qualification.
"""

import argparse
import functools
import hashlib
import importlib.util
import json
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--runtime-receipt", type=Path, required=True)
    parser.add_argument("--material-model-receipt", type=Path)
    args = parser.parse_args()
    dev = load("research_browser_dev", ROOT / "scripts/runtime/dev.py")
    run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
    run.relative_to(ROOT / ".project-local/runs")
    assert dev.layout(ROOT, run.name)["run"] == run
    for path in (args.build_receipt, args.runtime_receipt):
        dev.safe_path(path).relative_to(ROOT / ".project-local/runs")
    build = json.loads(args.build_receipt.read_text(encoding="utf-8"))
    runtime = json.loads(args.runtime_receipt.read_text(encoding="utf-8"))
    assert build["status"] == "PASS" and build["source_consistent"]
    assert runtime["status"] == "PASS_DECLARED_INTEGRATED_SUBSET"
    assert runtime["candidate_files_unchanged"] and runtime["independent_restore_equal"]
    material_model = None
    if args.material_model_receipt:
        model_path = dev.safe_path(args.material_model_receipt)
        model_path.relative_to(ROOT / ".project-local/runs")
        material_model = json.loads(model_path.read_text(encoding="utf-8"))
        assert material_model["status"] == "PASS_DECLARED_LOCAL_MODEL_SUBSET"
        assert material_model["candidate_files_unchanged"] and material_model["restart_equal"]
        assert len(material_model["model_calls"]) == 2
        assert material_model["candidate"] == runtime["candidate"]
        assert material_model["inputs"][0]["sha256"] == hashlib.sha256(args.runtime_receipt.read_bytes()).hexdigest()
    dist = dev.safe_path(Path(build["frontend_dist"]))
    dist.relative_to(ROOT / ".project-local/runs")
    candidate, workspace = (
        dev.safe_path(Path(runtime["candidate"])),
        dev.safe_path(Path(material_model["workspace"] if material_model else runtime["independent_workspace"])),
    )
    for p in (candidate, workspace):
        p.relative_to(ROOT / ".project-local/runs")
    office = load(
        "embed_real_browser_office", ROOT / "scripts/probes/aaos01_office_runtime_loop.py"
    )
    helper = load(
        "embed_real_browser_helper", ROOT / "scripts/probes/aaos_public_research_runtime_loop.py"
    )
    launcher = load("embed_real_browser_launcher", ROOT / "scripts/release/backend_launcher.py")
    client = load("embed_real_browser_client", ROOT / "shared/core_client.py")
    harness = load("embed_real_browser_harness", ROOT / "scripts/probes/stitch_ui_browser.py")
    # Bind this browser run to the exact candidate in the runtime receipt.
    # This step hashes host/Core/manifests, not every portable member.
    assert runtime["candidate_files_unchanged"]
    manifest = json.loads((candidate / "candidate-manifest.json").read_text(encoding="utf-8"))
    assert (
        manifest["build_receipt"]["sha256"]
        == hashlib.sha256(args.build_receipt.read_bytes()).hexdigest()
    )

    def candidate_identity():
        names = [
            "ArcheAxis.exe",
            "core/archeaxis-api.exe",
            "backend-runtime-manifest.json",
            "worker-profile.json",
            "candidate-manifest.json",
        ]
        return {name: hashlib.sha256((candidate / name).read_bytes()).hexdigest() for name in names}

    identity_before = candidate_identity()
    for name in (
        "ArcheAxis.exe",
        "core/archeaxis-api.exe",
        "worker-profile.json",
        "backend-runtime-manifest.json",
    ):
        assert identity_before[name] == manifest["files"][name]["sha256"]
    assert (
        manifest["host_sha256"] == build["host_sha256"]
        and manifest["core_sha256"] == build["core_sha256"]
    )
    out = run / "artifacts/real-research-learning-browser"
    out.mkdir(exist_ok=False)
    receipt = {
        "schema": "archeaxis.research-learning-real-browser/v1",
        "status": "RUNNING",
        "evidence_level": "INTEGRATED_REAL_CORE_WITH_SIMULATED_HOST_TRANSPORT",
        "native_host": "NOT_EXECUTED",
        "installed": "NOT_EXECUTED",
        "candidate": str(candidate),
        "built_ui": str(dist),
        "host_sha256": build["host_sha256"],
        "core_sha256": build["core_sha256"],
        "source_patch_sha256": build["source_patch_sha256"],
        "probe_source_patch_sha256": runtime.get(
            "probe_source_patch_sha256", "recorded in runtime wrapper"
        ),
        "execution_source_patch_sha256": os.environ["ARCHEAXIS_SOURCE_PATCH_SHA256"],
        "runtime_api_evidence_candidate": runtime["candidate"],
        "backend_member_reuse": "same candidate recorded by runtime input",
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "candidate_identity_scope": "host/Core/runtime-manifest/worker-profile/candidate-manifest only",
        "candidate_identity_before": identity_before,
        "real_read_calls": [],
        "simulated_operations": [],
        "console_errors": [],
        "blocked_external": [],
        "stopped": [],
        "cleanup": {},
    }
    if material_model:
        receipt["material_model_input"] = office.identity(model_path)
        receipt["model_inference"] = "NOT_EXECUTED; only previously recorded actual final answers are read"
    child = context = server = thread = None
    browser_pids = []
    base = token = None

    def checkpoint():
        (out / "receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def core_read(op, payload):
        # Finite, read-only test transport. No launch address/token reaches JS.
        p = payload or {}
        def identity(key):
            return quote(str(p[key]), safe="")
        method, body = "GET", None
        if op == "material_question_status":
            assert material_model
            method, body = "POST", p["body"]
            assert set(body) == {"request_id"}
            assert body["request_id"] is None or body["request_id"] in {
                r["request"]["request_id"] for r in material_model["model_calls"]
            }
            path = "/api/v1/material/questions/status"
        elif op in ("public_research_list", "public_research_read"):
            method, body = "POST", p["body"]
            assert (
                body["workspace_id"] == scope["workspace_id"]
                and body["restore_epoch"] == scope["restore_epoch"]
            )
            assert set(body) == (
                {"workspace_id", "restore_epoch", "request_id"}
                if op.endswith("_read")
                else {"workspace_id", "restore_epoch"}
            )
            path = "/api/v1/research/public/" + ("read" if op.endswith("_read") else "list")
        elif op == "system_version":
            path = "/api/v1/system/version"
        elif op == "documents_list":
            path = "/api/v1/documents"
        elif op == "sources_list":
            path = "/api/v1/sources"
        elif op == "source_jobs":
            path = f"/api/v1/sources/{identity('source_id')}/jobs"
        elif op == "document_get":
            path = f"/api/v1/documents/{identity('document_id')}"
        elif op == "document_version":
            path = f"/api/v1/documents/{identity('document_id')}/versions/{int(p['version'])}"
        elif op == "document_checks":
            path = f"/api/v1/documents/{identity('document_id')}/checks?version={int(p['version'])}"
        elif op == "source_original":
            path = f"/api/v1/sources/{identity('source_id')}/original"
        elif op == "knowledge_get":
            path = f"/api/v1/knowledge-items/{identity('id')}/v3"
        elif op == "knowledge_qualification":
            path = f"/api/v1/knowledge-items/{identity('id')}/qualification"
        elif op == "course_list":
            path = "/api/v1/courses"
        elif op == "learning_items":
            path = "/api/v1/learning/items"
        elif op == "learning_state":
            path = f"/api/v1/learning/items/{identity('item_key')}/state"
        elif op == "learning_history":
            path = f"/api/v1/learning/events/{identity('item_key')}"
        elif op == "assessment_get":
            path = f"/api/v1/learning/items/{identity('item_key')}/assessment"
        elif op == "document_graph":
            path = f"/api/v1/documents/{identity('document_id')}/relations"
        else:
            raise ValueError("Unexpected operation " + op)
        status, value = client.call(base, method, path, token, body, timeout=20)
        receipt["real_read_calls"].append(
            {"op": op, "payload": p, "method": method, "status": status}
        )
        checkpoint()
        return {"status": status, "body": value}

    class StaticHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    try:
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        receipt["core_pid"] = child.pid
        status, scope = client.call(base, "GET", "/api/v1/workspace/ui-state", token, timeout=20)
        assert status == 200
        receipt["working_state_scope"] = {
            key: scope[key] for key in ("workspace_id", "restore_epoch")
        }
        receipt["working_state_storage"] = "SIMULATED; only scope identity copied from actual Core"
        assert runtime["public_channels_complete"], (
            "This probe requires all three actual public channels"
        )
        public_path = dev.safe_path(Path(runtime["inputs"][0]["path"]))
        public_path.relative_to(ROOT / ".project-local/runs")
        assert office.identity(public_path) == runtime["inputs"][0]
        public = json.loads(public_path.read_text(encoding="utf-8"))
        assert public["source_consistent"] and public["candidate_consistent"]
        assert dev.safe_path(Path(public["candidate"])) == candidate
        search = next(s["body"] for s in public["steps"] if s["label"] == "public_search")
        helper.checked_channels(search)
        main_before = core_read("document_get", {"document_id": runtime["document_id"]})["body"]
        history_before = core_read("learning_history", {"item_key": runtime["item_key"]})["body"]
        model_document_before = None
        if material_model:
            model_document_before = core_read("document_get", {"document_id": material_model["document_id"]})["body"]
            assert model_document_before["version"] == 2
            for record in material_model["model_calls"]:
                assert core_read("material_question_status", {"body": {"request_id": record["request"]["request_id"]}})["body"] == record["result"]
        material_count = len(main_before["editor_json"]["attrs"]["archeaxis_research"]["materials"])
        unresolved = main_before["editor_json"]["attrs"]["archeaxis_research"]["unresolved"]
        assert unresolved[0]["text"] == "三类公开检索已完成；公开结论尚待人工核验。"
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(StaticHandler, directory=str(dist))
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_port
        receipt["server_port"] = port
        a0 = harness.load_a0()
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            chromium = a0._declared_tool(
                "ext.toolchains.playwright-chromium", "playwright-chromium"
            )
            assert chromium
            assert next(x for x in Path(chromium).parts if x.startswith("chromium-")) == next(
                x
                for x in Path(playwright.chromium.executable_path).parts
                if x.startswith("chromium-")
            )
            context = playwright.chromium.launch_persistent_context(
                str(run / "tmp/real-embed-profile"),
                executable_path=chromium,
                headless=True,
                viewport={"width": 1440, "height": 1000},
                reduced_motion="reduce",
                service_workers="block",
                accept_downloads=False,
                args=[
                    "--disable-background-networking",
                    "--disable-component-update",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
                ],
            )
            session = context.browser.new_browser_cdp_session()
            browser_pids = [
                p["id"]
                for p in session.send("SystemInfo.getProcessInfo")["processInfo"]
                if p["type"] == "browser"
            ]
            session.detach()
            assert browser_pids
            receipt["browser_pids"] = browser_pids
            context.expose_function("__embedRealRead", core_read)
            stub = a0.host_bridge_stub()
            needle = 'workspace_id:"a".repeat(32),restore_epoch:"initial"'
            assert stub.count(needle) == 1
            stub = stub.replace(
                needle,
                "workspace_id:"
                + json.dumps(scope["workspace_id"])
                + ",restore_epoch:"
                + json.dumps(scope["restore_epoch"]),
            )
            script = (
                stub
                + """
(() => {
 const previous=window.__TAURI__.core.invoke;
 const reads=new Set(['system_version','documents_list','sources_list','source_jobs','document_get','document_version','document_checks','source_original','knowledge_get','knowledge_qualification','learning_items','learning_state','learning_history','assessment_get','document_graph','course_list','public_research_list','public_research_read','material_question_status']);
 window.__embedShimCalls=[];
 window.__TAURI__.core.invoke=async(command,request)=>{
   const op=request?.request?.operation,p=request?.request?.payload??{};
   if(command==='core_command'&&reads.has(op))return window.__embedRealRead(op,p);
   if(command==='core_command'&&['document_draft','document_create','ingest_member_relations_apply','learning_review','knowledge_review','assessment_create','learning_reference','material_question','material_question_submit','material_question_cancel','model_configuration_save'].includes(op))throw new Error('READ_ONLY_BROWSER_PROBE');
   window.__embedShimCalls.push({command,operation:op});
   return previous(command,request);
 };
})();"""
            )
            context.add_init_script("if(location.protocol==='http:'){" + script + "}")

            def route_request(route):
                url = urlsplit(route.request.url)
                if url.hostname != "127.0.0.1" or url.port != port or url.scheme != "http":
                    receipt["blocked_external"].append(route.request.url)
                    route.abort("blockedbyclient")
                elif url.path.startswith("/api") or url.path.startswith("/workspace/api"):
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps(a0.api_payload(route.request.url)),
                    )
                else:
                    route.continue_()

            context.route("**/*", route_request)
            context.route_web_socket("**/*", lambda _: None)
            page = context.new_page()
            page.set_default_timeout(10000)
            page.on("pageerror", lambda e: receipt["console_errors"].append(str(e)))
            page.on(
                "console",
                lambda m: receipt["console_errors"].append(m.text) if m.type == "error" else None,
            )
            try:
                if material_model:
                    page.goto(f"http://127.0.0.1:{port}/#page=02", wait_until="networkidle")
                    if page.get_by_role("button", name="收起小栖窗口").is_visible():
                        page.get_by_role("button", name="收起小栖窗口").click()
                    page.get_by_role("button", name="打开文档 " + model_document_before["title"], exact=True).click()

                    def recover_material(keyboard=False):
                        page.locator("details.reader-material-tools > summary").click()
                        panel = page.get_by_role("region", name="固定版本材料问答", exact=True)
                        recover = panel.get_by_role("button", name="恢复本版材料的上次提问", exact=True)
                        if keyboard:
                            recover.focus()
                            page.keyboard.press("Enter")
                        else:
                            recover.click()
                        answer = material_model["model_calls"][1]
                        panel.get_by_text(answer["result"]["answer"]["answer"], exact=True).wait_for()
                        assert panel.get_by_role("textbox", name="材料问题", exact=True).input_value() == answer["request"]["question"]
                        assert panel.get_by_role("textbox", name="材料问答选区", exact=True).input_value() == model_document_before["text_projection"]
                        assert panel.get_by_role("combobox", name="材料模型通道", exact=True).input_value() == "fast"
                        assert panel.get_by_role("checkbox", name="离开此页后继续提问", exact=True).is_checked()
                        frozen = panel.get_by_role("region", name="待确认请求", exact=True)
                        frozen.get_by_text(f"《{model_document_before['title']}》，已保存文档第 2 版，当前版本全文", exact=True).wait_for()
                        frozen.get_by_text("aaos-fast-4b（快速）", exact=True).wait_for()
                        frozen.get_by_text("http://127.0.0.1:1234/v1", exact=True).wait_for()
                        panel.get_by_text("原请求历史回执已读回；没有再次推理。", exact=True).wait_for()
                        assert not panel.get_by_text(material_model["model_calls"][0]["result"]["answer"]["answer"], exact=True).count()
                        return panel

                    material_panel = recover_material()
                    material_panel.get_by_text(material_model["model_calls"][1]["result"]["answer"]["answer"], exact=True).scroll_into_view_if_needed()
                    page.screenshot(path=str(out / "actual-material-final-answer.png"))
                    # Read-only historical view must not silently rebind the current v2 request.
                    page.get_by_role("button", name="查看历史版本", exact=True).click()
                    page.get_by_role("spinbutton", name="恢复历史版本", exact=True).fill("1")
                    page.get_by_role("button", name="只读查看历史版本", exact=True).click()
                    historical = page.get_by_role("region", name="历史版本详情", exact=True)
                    historical.get_by_role("heading", name="历史版本 1", exact=True).wait_for()
                    assert material_model["model_calls"][0]["request"]["material"]["content_sha256"] != model_document_before["content_sha256"]
                    assert historical.locator("pre").first.inner_text() != model_document_before["text_projection"]
                    material_panel.get_by_text(material_model["model_calls"][1]["result"]["answer"]["answer"], exact=True).wait_for()
                    page.reload(wait_until="networkidle")
                    # Browser host working-state storage is synthetic: reopen explicitly from the actual list.
                    page.goto(f"http://127.0.0.1:{port}/#page=02", wait_until="networkidle")
                    if page.get_by_role("button", name="收起小栖窗口").is_visible():
                        page.get_by_role("button", name="收起小栖窗口").click()
                    page.get_by_role("button", name="打开文档 " + model_document_before["title"], exact=True).click()
                    material_panel = recover_material(keyboard=True)
                    page.set_viewport_size({"width": 640, "height": 480})
                    material_panel.get_by_text(material_model["model_calls"][1]["result"]["answer"]["answer"], exact=True).scroll_into_view_if_needed()
                    receipt["material_panel_geometry"] = material_panel.evaluate("n=>({width:n.clientWidth,scroll_width:n.scrollWidth})")
                    assert receipt["material_panel_geometry"]["scroll_width"] <= receipt["material_panel_geometry"]["width"] + 1
                    page.screenshot(path=str(out / "actual-material-final-answer-narrow.png"))
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    receipt["material_answer_recovered_without_inference"] = True
                    receipt["material_answer_version_binding"] = 2
                    receipt["material_recovery_keyboard"] = "Enter activates the same read-only recovery button after reload"
                page.goto(f"http://127.0.0.1:{port}/#page=05", wait_until="networkidle")
                if page.get_by_role("button", name="收起小栖窗口").is_visible():
                    page.get_by_role("button", name="收起小栖窗口").click()
                page.get_by_role("button", name="研究与个人学习贯穿 · 版本 1", exact=True).click()
                evidence = page.get_by_role("navigation", name="研究内容导航")
                evidence.get_by_role(
                    "button", name=f"证据与材料 ({material_count})", exact=True
                ).click()
                page.locator('[data-research-material="community"]').wait_for()
                page.get_by_role("complementary", name="相关资料", exact=True).get_by_role(
                    "heading", name=f"相关资料 ({material_count})", exact=True
                ).wait_for()
                for family in ("encyclopedia", "community", "research"):
                    page.locator('[data-research-material="' + family + '"]').get_by_role(
                        "button", name="读取校验原件", exact=True
                    ).click()
                    original_view = page.get_by_role(
                        "complementary", name="固定版本引用阅读", exact=True
                    )
                    original_view.get_by_role("heading", name="引用对象", exact=True).wait_for()
                    original_view.scroll_into_view_if_needed()
                    ref = next(
                        m["reference"]
                        for m in main_before["editor_json"]["attrs"]["archeaxis_research"][
                            "materials"
                        ]
                        if m["id"] == family
                    )
                    assert any(
                        c["op"] == "source_original"
                        and c["payload"]["source_id"] == ref["source_id"]
                        and c["status"] == 200
                        for c in receipt["real_read_calls"]
                    )
                page.screenshot(path=str(out / "actual-research.png"))
                panel = page.get_by_role("region", name="公开资料检索", exact=True)
                panel.get_by_role("button", name="恢复最近公开请求记录", exact=True).click()
                panel.get_by_role("button", name="回读请求 " + search["query"], exact=True).click()
                states = panel.get_by_role("list", name="本次来源状态", exact=True)
                for label in ("百科", "社区", "科研"):
                    states.get_by_text(label + "：本次检索完成", exact=True).wait_for()
                for channel in search["channels"]:
                    for hit in channel["hits"]:
                        panel.get_by_role("heading", name=hit["title"], exact=True).wait_for()
                panel.get_by_role("button", name="读取百科原始 API 原件", exact=True).click()
                raw = search["channels"][0]["raw_source"]
                assert any(
                    c["op"] == "source_original"
                    and c["payload"]["source_id"] == raw["source_id"]
                    and c["status"] == 200
                    for c in receipt["real_read_calls"]
                )
                states.scroll_into_view_if_needed()
                page.screenshot(path=str(out / "actual-three-public-channels.png"))
                receipt["public_journal_recovered_without_network_retry"] = True
                page.goto(f"http://127.0.0.1:{port}/#page=02", wait_until="networkidle")
                page.get_by_role("button", name="打开文档 研究与个人学习贯穿", exact=True).click()
                embeds = page.get_by_role("region", name="文档嵌入内容", exact=True)
                embeds.get_by_text(
                    "合成个人定义：正文甲是本例正文，表格乙是本例表格。仅验证流程。", exact=True
                ).wait_for()
                embeds.get_by_text(
                    "公开来源摘录候选；内容待人工核验，未接纳。", exact=True
                ).wait_for()
                assert embeds.get_by_role("complementary", name="固定版本嵌入阅读").count() == 2
                geometry = page.locator(".ui-reader-document").evaluate(
                    "n=>({readonly_bottom:Math.max(...[...n.querySelector('[aria-label=\"共享文档只读视图\"]').querySelectorAll('p,button,pre')].map(x=>x.getBoundingClientRect().bottom)),embed_top:n.querySelector('.ui-document-embeds').getBoundingClientRect().top})"
                )
                receipt["readonly_geometry"] = geometry
                assert geometry["readonly_bottom"] <= geometry["embed_top"] + 1, geometry
                embeds.get_by_text(
                    "公开来源摘录候选；内容待人工核验，未接纳。", exact=True
                ).scroll_into_view_if_needed()
                page.screenshot(path=str(out / "actual-reader-knowledge.png"))
                page.goto(f"http://127.0.0.1:{port}/#page=06", wait_until="networkidle")
                page.locator('[data-learning-item-key="' + runtime["item_key"] + '"]').click()
                page.get_by_role("textbox", name="本次答案", exact=True).wait_for()
                assert page.get_by_role("textbox", name="本次答案", exact=True).input_value() == ""
                page.get_by_text(
                    "请用自己的话复述本条知识，并解释其依据或适用条件；作答后再查看核对内容。",
                    exact=True,
                ).wait_for()
                assert not page.get_by_role("region", name="答案与核对内容").count()
                page.get_by_role("textbox", name="本次答案", exact=True).fill(
                    "SYNTHETIC browser draft; not a human learning outcome."
                )
                page.get_by_role("button", name="查看答案与核对内容", exact=True).click()
                radio_geometry = page.locator(
                    '.ui-learning-review input[type="radio"]'
                ).evaluate_all(
                    "nodes=>nodes.map(n=>{const r=n.getBoundingClientRect(),l=n.closest('label').getBoundingClientRect();return {width:r.width,height:r.height,label_height:l.height,left_delta:r.left-l.left}})"
                )
                receipt["radio_geometry"] = radio_geometry
                assert len(radio_geometry) == 2 and all(
                    r["width"] <= 24
                    and r["height"] <= 24
                    and r["label_height"] <= 48
                    and r["left_delta"] <= 16
                    for r in radio_geometry
                ), radio_geometry
                page.get_by_label("回答正确", exact=True).check()
                assert page.get_by_label("回答正确", exact=True).is_checked()
                page.get_by_label("回答正确", exact=True).focus()
                page.keyboard.press("ArrowDown")
                assert page.get_by_label("回答不正确", exact=True).is_checked()
                page.get_by_role(
                    "textbox", name="本次答案", exact=True
                ).scroll_into_view_if_needed()
                page.screenshot(path=str(out / "actual-learning.png"))
                page.set_viewport_size({"width": 640, "height": 480})
                page.get_by_label("回答不正确", exact=True).scroll_into_view_if_needed()
                narrow = page.locator('.ui-learning-review input[type="radio"]').evaluate_all(
                    "nodes=>nodes.map(n=>{const r=n.getBoundingClientRect(),l=n.closest('label').getBoundingClientRect();return {width:r.width,height:r.height,label_height:l.height,left_delta:r.left-l.left}})"
                )
                assert all(
                    r["width"] <= 24
                    and r["height"] <= 24
                    and 44 <= r["label_height"] <= 48
                    and r["left_delta"] <= 16
                    for r in narrow
                ), narrow
                receipt["narrow_radio_geometry"] = narrow
                page.screenshot(path=str(out / "actual-learning-narrow.png"))
                receipt["simulated_operations"] = page.evaluate("window.__embedShimCalls")
                assert any(
                    c["op"] == "learning_state"
                    and c["payload"]["item_key"] == runtime["item_key"]
                    and c["status"] == 200
                    for c in receipt["real_read_calls"]
                )
                assert {
                    c["payload"]["id"]
                    for c in receipt["real_read_calls"]
                    if c["op"] == "knowledge_get" and c["status"] == 200
                } >= {runtime["personal_knowledge_id"], runtime["pending_public_knowledge_id"]}
                assert not receipt["console_errors"] and not receipt["blocked_external"]
            except Exception:
                page.screenshot(path=str(out / "failure.png"))
                (out / "failure.txt").write_text(
                    page.locator("body").inner_text()[:18000], encoding="utf-8"
                )
                receipt["simulated_operations"] = page.evaluate("window.__embedShimCalls")
                raise
            finally:
                context.close()
                context = None
        assert (
            core_read("document_get", {"document_id": runtime["document_id"]})["body"]
            == main_before
        )
        assert (
            core_read("learning_history", {"item_key": runtime["item_key"]})["body"]
            == history_before
        )
        receipt["learning_history_unchanged"] = True
        if material_model:
            assert core_read("document_get", {"document_id": material_model["document_id"]})["body"] == model_document_before
            for record in material_model["model_calls"]:
                assert core_read("material_question_status", {"body": {"request_id": record["request"]["request_id"]}})["body"] == record["result"]
            receipt["model_material_and_answers_unchanged"] = True
        receipt["status"] = "PASS"
    except Exception as e:
        receipt.update(status="FAIL", error=f"{type(e).__name__}: {e}")
    finally:
        if context:
            try:
                context.close()
            except Exception as e:
                receipt["cleanup"]["context_close_observation"] = str(e)
        if server:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            receipt["cleanup"]["server_closed"] = not thread.is_alive() and not harness.port_open(
                receipt["server_port"]
            )
        if child:
            try:
                helper.stop_owned(child, launcher, receipt["stopped"])
            except Exception as e:
                receipt.update(status="FAIL", cleanup_error=str(e))
        receipt["cleanup"]["browser"] = [
            {"pid": p, "exited": not harness.pid_running(p)} for p in browser_pids
        ]
        if (
            any(not p["exited"] for p in receipt["cleanup"]["browser"])
            or receipt["cleanup"].get("server_closed") is False
        ):
            receipt["status"] = "FAIL"
        try:
            receipt["candidate_identity_after"] = candidate_identity()
            assert receipt["candidate_identity_after"] == identity_before
            receipt["candidate_identity_unchanged"] = True
        except Exception as e:
            receipt.update(status="FAIL", candidate_identity_unchanged=False, identity_error=str(e))
        checkpoint()
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "real_reads": len(receipt["real_read_calls"]),
                "receipt": str(out / "receipt.json"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
