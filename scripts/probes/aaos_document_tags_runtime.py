"""Actual Core + built 02/03 tag consumer on an independent authored restore.

Browser business transport is read-only; host/layout/lease presentation is simulated.
This is not an external Obsidian application, native IPC, installed or Owner qualification.
"""

from __future__ import annotations

import argparse
import base64
import functools
import json
import os
import re
import subprocess
import threading
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit

import aaos01_office_runtime_loop as office
import aaos_public_research_runtime_loop as helper
from aaos_research_learning_runtime import require, sha

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--input-receipt", type=Path, required=True)
    args = parser.parse_args()
    dev = office.load("tags_dev", ROOT / "scripts/runtime/dev.py")
    run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
    paths = dev.layout(ROOT, run.name)
    require(paths["run"] == run, "Foreign run")

    def owned(path):
        path = dev.safe_path(path)
        path.relative_to(paths["dev"] / "runs")
        return path

    candidate, build_path, input_path = map(
        owned, [args.candidate, args.build_receipt, args.input_receipt]
    )
    manifest = json.loads((candidate / "candidate-manifest.json").read_text(encoding="utf-8"))
    build = json.loads(build_path.read_text(encoding="utf-8"))
    prior = json.loads(input_path.read_text(encoding="utf-8"))
    require(build["status"] == "PASS" and build["source_consistent"], "Unqualified build")
    require(manifest["build_receipt"]["sha256"] == sha(build_path.read_bytes()), "Wrong candidate")
    require(
        prior["status"] == "PASS_AUTHORED_DISCOVERY_SUBSET" and prior["independent_restore_equal"],
        "Unqualified authored input",
    )
    require(all(s["wait_reaped"] for s in prior["stopped"]), "Input process still live")
    names = [
        "ArcheAxis.exe",
        "core/archeaxis-api.exe",
        "backend-runtime-manifest.json",
        "worker-profile.json",
        "candidate-manifest.json",
    ]
    before = {name: office.identity(candidate / name) for name in names}
    require(before["core/archeaxis-api.exe"]["sha256"] == build["core_sha256"], "Core mismatch")
    for name in names[:-1]:
        require(
            before[name]["sha256"] == manifest["files"][name]["sha256"], "Candidate member changed"
        )
    output = paths["artifacts"] / "document-tags-runtime.json"
    require(not output.exists(), "Use a new run ID")
    receipt = {
        "schema": "archeaxis.document-tags-runtime/v1",
        "status": "RUNNING",
        "candidate": str(candidate),
        "candidate_identity": before,
        "build_receipt": office.identity(build_path),
        "input": office.identity(input_path),
        "execution": "ACTUAL_CORE_HTTP_SQLITE_WITH_SIMULATED_BROWSER_HOST",
        "materials": "SYNTHETIC_AUTHORED",
        "steps": [],
        "browser_calls": [],
        "stopped": [],
        "cleanup": {},
        "screenshots": [],
        "limits": [
            "No actual external application or software-version roundtrip qualification",
            "Browser host/layout/lease simulated; no native/installed/Green/Owner/CI acceptance",
            "Rich-text Markdown export context may be lossy; manifest preserves editor",
            "Only authored notes and existing baseline objects; not the whole compatibility inventory",
        ],
    }
    launcher = office.load("tags_launcher", ROOT / "scripts/release/backend_launcher.py")
    client = office.load("tags_client", ROOT / "shared/core_client.py")
    harness = office.load("tags_browser_harness", ROOT / "scripts/probes/stitch_ui_browser.py")
    child = context = server = thread = None
    base = token = None
    browser_pids = []

    def checkpoint():
        output.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )

    def call(method, path, body=None, expected=200):
        status, value = client.call(base, method, path, token, body, timeout=45)
        receipt["steps"].append({"method": method, "path": path, "status": status})
        checkpoint()
        require(status == expected, f"{method} {path}: {status}, expected {expected}")
        return value

    def stop():
        nonlocal child
        helper.stop_owned(child, launcher, receipt["stopped"])
        child = None
        checkpoint()

    def restore(backup, target):
        target.mkdir(exist_ok=False)
        result = subprocess.run(
            [
                str(candidate / "core/archeaxis-api.exe"),
                "--maintenance-restore",
                str(target / "workspace.sqlite"),
                str(backup),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        require(result.returncode == 0 and json.loads(result.stdout)["verified"], "Restore failed")
        return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}

    def editor(text):
        return {
            "type": "doc",
            "attrs": {"archeaxis_markup": "markdown", "foreign": {"keep": True}},
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"block_id": "tags_body"},
                    "content": [{"type": "text", "text": text}],
                }
            ],
        }

    def browser_read(op, payload):
        p = payload or {}
        def identity(key):
            return quote(str(p[key]), safe="")
        if op == "system_version":
            path = "/api/v1/system/version"
        elif op == "sources_list":
            path = "/api/v1/sources"
        elif op == "documents_list":
            path = "/api/v1/documents" + (
                "?cursor=" + identity("cursor") if p.get("cursor") else ""
            )
        elif op == "document_get":
            path = "/api/v1/documents/" + identity("document_id")
        elif op == "document_version":
            path = f"/api/v1/documents/{identity('document_id')}/versions/{int(p['version'])}"
        elif op == "document_checks":
            path = f"/api/v1/documents/{identity('document_id')}/checks?version={int(p['version'])}"
        elif op == "source_original":
            path = f"/api/v1/sources/{identity('source_id')}/original"
        elif op == "source_get":
            path = "/api/v1/sources/" + identity("source_id")
        elif op == "source_jobs":
            path = f"/api/v1/sources/{identity('source_id')}/jobs"
        elif op == "document_graph":
            path = f"/api/v1/documents/{identity('document_id')}/relations"
        elif op == "anchors_list":
            path = "/api/v1/anchors?source_id=" + identity("source_id")
        else:
            raise ValueError("Unexpected read " + op)
        value = call("GET", path)
        receipt["browser_calls"].append({"operation": op, "method": "GET", "status": 200})
        return {"status": 200, "body": value}

    class StaticHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    try:
        workspace = paths["artifacts"] / "tag-workspace"
        backup = owned(Path(prior["workspace"]) / "backups" / prior["backup"]["filename"])
        require(sha(backup.read_bytes()) == prior["backup"]["sha256"], "Input backup changed")
        receipt["input_restore"] = restore(backup, workspace)
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        baseline_paths = [
            f"/api/v1/documents/{prior['baseline_document_id']}",
            f"/api/v1/documents/{prior['document_id']}",
            f"/api/v1/learning/events/{prior['baseline_item_key']}",
        ]
        baseline = {p: call("GET", p) for p in baseline_paths}
        text = "---\ntags: [Read/Next, 中文, '🧠/练习']\nscore: 2\ndone: false\ncomment: '#not_a_tag'\n---\n\n#READ/next #Learn #1984\n`#code` \\#escaped https://example.org/#fragment [[#Wiki]]\n\n```md\n#fenced\n```"
        imported = call(
            "POST",
            "/api/v1/imports",
            {"name": "标签业务验证.md", "content_base64": base64.b64encode(text.encode()).decode()},
            202,
        )
        document = call(
            "POST",
            "/api/v1/documents",
            {
                "title": "标签业务验证",
                "create_request_id": uuid.uuid4().hex,
                "source_id": imported["source_id"],
                "source_revision": imported["sha256"],
                "editor_json": editor(text),
            },
            201,
        )
        route = "/api/v1/documents/" + document["document_id"]
        require(
            [t["key"] for t in document["tags"]] == ["read/next", "中文", "🧠/练习", "learn"],
            "Wrong parsed tags",
        )
        require(
            document["properties"]["done"] is False
            and document["properties"]["score"] == 2
            and document["metadata_status"] == "COMPLETE",
            "Wrong properties",
        )
        original = call("GET", f"/api/v1/sources/{imported['source_id']}/original")
        require(base64.b64decode(original["content_base64"]) == text.encode(), "Original changed")
        sibling = call(
            "POST",
            "/api/v1/documents",
            {"title": "同标签的第二篇", "editor_json": editor("#read\n\n同一个核心标签导航")},
            201,
        )
        listing = call("GET", "/api/v1/documents")
        summary = next(
            d for d in listing["documents"] if d["document_id"] == document["document_id"]
        )
        require(
            summary["tags"] == document["tags"]
            and summary["version"] == 1
            and summary["content_sha256"] == document["content_sha256"],
            "Summary version mismatch",
        )
        require(
            "properties" not in summary
            and "text_projection" not in summary
            and "editor_json" not in summary,
            "Summary leaked body",
        )
        for kind in ["markdown", "obsidian"]:
            exported = call("GET", route + "/export?format=" + kind)
            markdown = exported["files"][0]["content"]
            require(markdown.startswith(text), "Export hid original frontmatter")
            export_manifest = json.loads(exported["files"][1]["content"])
            require(
                export_manifest["document"]["tags"] == document["tags"]
                and export_manifest["document"]["properties"] == document["properties"],
                "Export metadata changed",
            )
            require(
                any(
                    loss["code"] == "metadata_projection_limits" for loss in export_manifest["loss"]
                ),
                "Missing export limits",
            )
            receipt.setdefault("exports", []).append(
                {
                    "format": kind,
                    "markdown_sha256": sha(markdown.encode()),
                    "manifest_sha256": sha(exported["files"][1]["content"].encode()),
                    "original_frontmatter_first": True,
                }
            )
        package = call("GET", route + "/package")
        receipt.update(
            document=document, sibling=sibling, workspace=str(workspace), baseline=baseline
        )
        dist = owned(Path(build["frontend_dist"]))
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(StaticHandler, directory=str(dist))
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_port
        receipt["server_port"] = port
        a0 = harness.load_a0()
        from playwright.sync_api import expect, sync_playwright

        with sync_playwright() as playwright:
            chromium = a0._declared_tool(
                "ext.toolchains.playwright-chromium", "playwright-chromium"
            )
            require(bool(chromium), "Declared browser missing")
            require(
                next(p for p in Path(chromium).parts if p.startswith("chromium-"))
                == next(
                    p
                    for p in Path(playwright.chromium.executable_path).parts
                    if p.startswith("chromium-")
                ),
                "Browser version mismatch",
            )
            context = playwright.chromium.launch_persistent_context(
                str(paths["tmp"] / "tag-browser-profile"),
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
            context.expose_function("__tagRead", browser_read)
            reads = [
                "system_version",
                "sources_list",
                "documents_list",
                "document_get",
                "document_version",
                "document_checks",
                "source_original",
                "source_get",
                "source_jobs",
                "document_graph",
                "anchors_list",
            ]
            script = (
                a0.host_bridge_stub()
                + """\n(() => {const previous=window.__TAURI__.core.invoke;window.__tagShimCalls=[];window.__TAURI__.core.invoke=async(command,request)=>{const op=request?.request?.operation,p=request?.request?.payload??{};
if(command==='core_command'&&READS.includes(op))return window.__tagRead(op,p);
if(command==='core_command'&&['document_draft','document_create','source_import','job_execute','knowledge_review'].includes(op))throw new Error('READ_ONLY_BROWSER_PROBE');
window.__tagShimCalls.push({command,operation:op});return previous(command,request);};})();""".replace(
                    "READS", json.dumps(reads)
                )
            )
            context.add_init_script("if(location.protocol==='http:'){" + script + "}")
            blocked = []
            errors = []

            def route_request(route):
                url = urlsplit(route.request.url)
                if url.hostname != "127.0.0.1" or url.port != port or url.scheme != "http":
                    blocked.append(route.request.url)
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
            page.on("pageerror", lambda e: errors.append(str(e)))
            try:
                url = f"http://127.0.0.1:{port}/#page=02"
                page.goto(url, wait_until="networkidle")
                if page.get_by_role("button", name="收起小栖窗口").is_visible():
                    page.get_by_role("button", name="收起小栖窗口").click()
                tags = page.get_by_role("region", name="已保存标签导航", exact=True)
                tags.get_by_role("combobox", name="标签排序方式", exact=True).select_option("count")
                parent_tag = tags.get_by_role("button", name=re.compile(r"^筛选标签 read，2篇已加载文档$", re.I))
                expect(parent_tag).to_be_visible()
                require(parent_tag.get_attribute("aria-pressed") == "false", "Sorting applied a filter")
                labels = tags.locator("button[aria-pressed]").evaluate_all("nodes=>nodes.map(n=>n.getAttribute('aria-label'))")
                require(labels[0].casefold() == "筛选标签 read，2篇已加载文档", "Distinct-document frequency did not sort first")
                tags.get_by_role("combobox", name="标签显示方式", exact=True).select_option("tree")
                branch = tags.get_by_role("button", name=re.compile(r"^收起 read 的下级标签$", re.I))
                branch.focus()
                page.keyboard.press("Enter")
                expect(tags.get_by_role("button", name="筛选标签 Read/Next，1篇已加载文档", exact=True)).to_have_count(0)
                tags.get_by_role("button", name=re.compile(r"^展开 read 的下级标签$", re.I)).click()
                expect(tags.get_by_role("button", name="筛选标签 Read/Next，1篇已加载文档", exact=True)).to_be_visible()
                tags.scroll_into_view_if_needed()
                page.screenshot(path=str(paths["artifacts"] / "tags-navigation-tree.png"))
                receipt["screenshots"].append("tags-navigation-tree.png")
                page.set_viewport_size({"width": 640, "height": 480})
                tags.get_by_role("combobox", name="标签显示方式", exact=True).scroll_into_view_if_needed()
                navigation_bounds = tags.evaluate("n=>({client:n.clientWidth,scroll:n.scrollWidth})")
                require(navigation_bounds["scroll"] <= navigation_bounds["client"] + 2, "Narrow tag navigation overflow")
                page.screenshot(path=str(paths["artifacts"] / "tags-navigation-narrow.png"))
                receipt["screenshots"].append("tags-navigation-narrow.png")
                tags.get_by_role("combobox", name="标签显示方式", exact=True).select_option("flat")
                expect(tags.get_by_role("button", name="筛选标签 Read/Next，1篇已加载文档", exact=True)).to_be_visible()
                page.set_viewport_size({"width": 1440, "height": 1000})
                receipt["tag_navigation"] = {"sort": "distinct_loaded_document_count", "tree_flat": True, "collapse_keyboard": "Enter", "narrow_bounds": navigation_bounds, "metadata_writes": False}
                search = page.get_by_role("searchbox", name="按标签筛选，包含下级标签")
                search.fill("#READ")
                expect(
                    page.get_by_role("button", name="打开文档 同标签的第二篇", exact=True)
                ).to_be_visible()
                page.get_by_role("button", name="打开文档 标签业务验证", exact=True).click()
                panel = page.get_by_role("region", name="已保存标签与属性").first
                expect(
                    panel.get_by_role("button", name="查看标签 Read/Next 的文档", exact=True)
                ).to_be_visible()
                panel.get_by_text("保存版属性（4项）", exact=True).click()
                expect(panel.get_by_text("false", exact=True)).to_be_visible()
                panel.get_by_role("button", name="查看标签 Read/Next 的文档", exact=True).focus()
                page.keyboard.press("Enter")
                expect(page.get_by_role("region", name="标签关联文档")).to_be_visible()
                page.screenshot(path=str(paths["artifacts"] / "tags-reader.png"))
                receipt["screenshots"].append("tags-reader.png")
                page.set_viewport_size({"width": 640, "height": 480})
                panel.get_by_role("heading").scroll_into_view_if_needed()
                bounds = panel.evaluate("(e)=>({client:e.clientWidth,scroll:e.scrollWidth})")
                require(bounds["scroll"] <= bounds["client"] + 2, "Narrow metadata overflow")
                tag_bounds = panel.get_by_role(
                    "button", name="查看标签 Read/Next 的文档", exact=True
                ).bounding_box()
                require(
                    tag_bounds and tag_bounds["y"] >= 0
                    and tag_bounds["y"] + tag_bounds["height"] <= 480,
                    "Narrow tag not in viewport",
                )
                page.screenshot(path=str(paths["artifacts"] / "tags-narrow.png"))
                receipt["screenshots"].append("tags-narrow.png")
                receipt["narrow_bounds"] = bounds
                receipt["narrow_tag_bounds"] = tag_bounds
                updated_text = text.replace(
                    "tags: [Read/Next, 中文, '🧠/练习']", "tags: [Updated/中文]"
                ).replace("#READ/next #Learn #1984", "#Updated/中文")
                updated = call(
                    "PUT",
                    route + "/draft",
                    {"expected_version": 1, "editor_json": editor(updated_text)},
                )
                require(
                    updated["tags"] == [{"name": "Updated/中文", "key": "updated/中文"}],
                    "Saved tags did not update",
                )
                page.set_viewport_size({"width": 1440, "height": 1000})
                page.goto(url, wait_until="networkidle")
                # Same hash navigation preserves the mounted list; consume the normal refresh action.
                page.get_by_role("button", name="刷新资料列表", exact=True).click()
                expect(
                    page.get_by_role("button", name="筛选标签 Updated/中文，1篇已加载文档", exact=True)
                ).to_be_visible()
                page.get_by_role("searchbox", name="按标签筛选，包含下级标签").fill("updated")
                expect(
                    page.get_by_role("button", name="打开文档 同标签的第二篇", exact=True)
                ).to_have_count(0)
                page.get_by_role("button", name="打开文档 标签业务验证", exact=True).click()
                expect(
                    page.get_by_role("button", name="查看标签 Updated/中文 的文档", exact=True)
                ).to_be_visible()
                page.get_by_role("button", name="版本", exact=True).click()
                page.get_by_role("spinbutton", name="恢复历史版本").fill("1")
                page.get_by_role("button", name="只读查看历史版本", exact=True).click()
                history = page.get_by_role("region", name="历史版本详情")
                expect(
                    history.get_by_role("button", name="查看标签 Read/Next 的文档", exact=True)
                ).to_be_visible()
                page.screenshot(path=str(paths["artifacts"] / "tags-history.png"))
                receipt["screenshots"].append("tags-history.png")
                receipt.update(
                    browser_host_operations=page.evaluate("window.__tagShimCalls"),
                    browser_errors=errors,
                    blocked_external=blocked,
                )
                require(not errors and not blocked, "Browser errors or unexpected network")
            except Exception:
                page.screenshot(path=str(paths["artifacts"] / "failure.png"))
                (paths["artifacts"] / "failure.txt").write_text(
                    page.locator("body").inner_text()[:16000], encoding="utf-8", newline="\n"
                )
                try:
                    context.close()
                except Exception as error:
                    receipt["cleanup"]["context_error"] = str(error)
                finally:
                    context = None
                raise
            context.close()
            context = None
        copied = call(
            "POST",
            "/api/v1/document-packages/import",
            {"request_id": "authored-tag-transfer", "package": package},
            201,
        )["document"]
        require(
            copied["tags"] == document["tags"]
            and copied["properties"] == document["properties"]
            and copied["editor_json"] == document["editor_json"],
            "Portable metadata changed",
        )
        receipt["portable_document"] = copied
        current = call("GET", route)
        require(current == updated, "Browser changed saved draft")
        require(call("GET", route + "/versions/1") == document, "History changed")
        for path, value in baseline.items():
            require(call("GET", path) == value, "Baseline changed")
        stop()
        child, base, token, _ = helper.hidden_start(office, candidate, workspace, launcher)
        require(
            call("GET", route) == current and call("GET", route + "/versions/1") == document,
            "Restart changed metadata",
        )
        saved_backup = call("POST", "/api/v1/workspace/backups", {}, 201)
        require(saved_backup["verified"], "Backup unverified")
        backup_file = owned(workspace / "backups" / saved_backup["filename"])
        require(sha(backup_file.read_bytes()) == saved_backup["sha256"], "Backup changed")
        stop()
        restored = paths["artifacts"] / "independent-tag-restore"
        receipt["output_restore"] = restore(backup_file, restored)
        child, base, token, _ = helper.hidden_start(office, candidate, restored, launcher)
        for path, value in {**baseline, route: current, route + "/versions/1": document}.items():
            require(call("GET", path) == value, "Independent restore changed object")
        receipt.update(
            status="PASS_AUTHORED_TAG_CONSUMER",
            current_document=current,
            backup=saved_backup,
            independent_restore_equal=True,
            restart_equal=True,
            baseline_preserved=True,
            independent_workspace=str(restored),
        )
    except Exception as error:
        receipt.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    finally:
        if context:
            try:
                context.close()
            except Exception as error:
                receipt["cleanup"]["context_error"] = str(error)
        if server:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            receipt["cleanup"]["server_closed"] = not thread.is_alive() and not harness.port_open(
                receipt["server_port"]
            )
        if child:
            try:
                stop()
            except Exception as error:
                receipt.update(status="FAIL", cleanup_error=str(error))
        receipt["cleanup"]["browser"] = [
            {"pid": pid, "exited": not harness.pid_running(pid)} for pid in browser_pids
        ]
        if (
            any(not p["exited"] for p in receipt["cleanup"]["browser"])
            or receipt["cleanup"].get("server_closed") is False
        ):
            receipt["status"] = "FAIL"
        receipt["candidate_unchanged"] = {
            name: office.identity(candidate / name) for name in names
        } == before
        if not receipt["candidate_unchanged"]:
            receipt["status"] = "FAIL"
        checkpoint()
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "calls": len(receipt["steps"]),
                "browser_reads": len(receipt["browser_calls"]),
                "receipt": str(output),
            },
            ensure_ascii=False,
        )
    )
    return 0 if receipt["status"] == "PASS_AUTHORED_TAG_CONSUMER" else 1


if __name__ == "__main__":
    raise SystemExit(main())
