"""Opt-in native UI qualification of bounded exchange and task-role presentation.

Only read operations use the formal bridge. Import writes require trusted file
selection and the rendered user confirmation. Materials are synthetic fixtures.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import time
import uuid
from pathlib import Path

ROLE_OBSERVATION = """const visible=n=>!!n&&n.getClientRects().length>0&&
 !n.closest('[hidden],[aria-hidden="true"],[inert]')&&
 Array.from((function*(x){for(;x;x=x.parentElement)yield x;})(n)).every(x=>{
  const s=getComputedStyle(x);return s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse';});
const roles=[...document.querySelectorAll('[aria-label="模型与工具职责"]')].filter(visible);
return roles.length===1?roles[0].innerText:null;"""

IMPORT_SAVED_OBSERVATION = """const panel=document.querySelector('[aria-label="有界文档便携包"]');
return [...(panel?.querySelectorAll('[role="status"]')??[])].some(n=>
 n.innerText.includes('已保存为新文档；尚未加入知识库'));"""


def qualify_task_roles(ui, js, wait):
    # The current catalog presents roles in the selected capability's details.
    ui.page("17", confirm_navigation=True)
    ui.click("目录与搜索", "//*[@role='tablist' and @aria-label='能力目录视图']")
    ui.type("查找能力", "")
    ui.click("全部", "//*[@aria-label='能力分类']")
    ui.click_selector("(//section[@aria-label='能力列表']//button[@data-entry-id])[1]")
    wait("return (function(){" + ROLE_OBSERVATION + "})()!==null")
    roles = js(ROLE_OBSERVATION)
    for text in ("本地资料转换", "日常对话与学习", "联网研究与核验", "最终采用由用户决定"):
        assert text in roles, "Missing current task-role presentation"


def run(*, ui, read, bridge, js, wait, restart, work, report, download_control=None):
    evidence = report.setdefault("closure_features", {"status": "IN_PROGRESS"})
    qualify_task_roles(ui, js, wait)
    evidence["roles"] = "REAL_RENDERED_CURRENT_NATIVE_UI"

    before = read("documents_list")
    candidates = [row for row in before["documents"] if row.get("source_id")]
    assert candidates, "Bound ordinary fixture document missing"
    package = copy.deepcopy(bridge("document_package_export", {"document_id": candidates[0]["document_id"]}))
    assert package["schema"] == "archeaxis.document-package/v1"
    nonce = uuid.uuid4().hex
    title = "合成便携媒体闭环 " + nonce
    # Author an external synthetic package, retaining actual exported originals
    # while adding a PNG and an unknown editor node. This is input, not success.
    image = (Path(__file__).absolute().parents[2] / "tests/fixtures/golden/golden-screenshot-ocr.png").read_bytes()
    media_sha = hashlib.sha256(image).hexdigest()
    media_id = "synthetic_portable_media_" + nonce
    editor = package["document"]["editor_json"]
    attrs = editor.setdefault("attrs", {})
    assert "archeaxis_expression" not in attrs, "Fixture must not overwrite expression content"
    attrs["future_portable_attribute"] = {"preserved": [1, "中文", True]}
    attrs["archeaxis_expression"] = {
        "schema": "archeaxis.expression/v1",
        "nodes": [{"id": "portable_pic", "type": "media", "text": "合成媒体", "x": 0, "y": 0,
                   "width": 32, "height": 32,
                   "media": {"source_id": media_id, "sha256": media_sha, "media_type": "image/png"}}],
        "edges": [],
    }
    editor.setdefault("content", []).append({"type": "future_portable_widget", "attrs": {"opaque": ["保留", 42]}})
    package["document"]["title"] = title
    package["document"]["content_sha256"] = hashlib.sha256(
        json.dumps(editor, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    package["objects"].append({"source_id": media_id, "sha256": media_sha,
                               "original_name": "synthetic-portable.png", "bytes": list(image)})
    fixture = work / ("closure-portable-" + nonce + ".json")
    fixture.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
    count = before["snapshot_count"]

    def import_file():
        ui.page("16", confirm_navigation=True)
        ui.click("文档导出", "//nav[@aria-label='导入导出区域']")
        selector = '[aria-label="有界文档便携包"] input[type="file"]'
        element = ui.find(selector, "css selector")
        ui.command(element, "value", {"text": str(fixture.absolute())})
        ui.evidence.append({"action": "trusted_portable_file_selection", "synthetic_fixture": str(fixture)})
        wait("return document.querySelector('[aria-label=\"有界文档便携包\"]')?.innerText.includes('待保存：')")
        wait("return [...document.querySelector('[aria-label=\"有界文档便携包\"]').querySelectorAll('button')].some(b => b.textContent === '确认保存为新普通文档' && !b.disabled)")
        ui.click("确认保存为新普通文档", "//section[@aria-label='有界文档便携包']")
        wait(IMPORT_SAVED_OBSERVATION)

    import_file()
    rows = read("documents_list")
    assert rows["snapshot_count"] == count + 1, "Import created an unexpected document count"
    imported = [row for row in rows["documents"] if row["title"] == title]
    assert len(imported) == 1
    document_id = imported[0]["document_id"]
    saved = read("document_get", {"document_id": document_id})
    expected = copy.deepcopy(editor)
    nodes = saved["editor_json"]["attrs"]["archeaxis_expression"]["nodes"]
    expected["attrs"]["archeaxis_expression"]["nodes"][0]["media"]["source_id"] = nodes[0]["media"]["source_id"]
    # Core assigns stable block identities to new top-level editor nodes. The
    # externally authored unknown widget has none yet; preserve every supplied
    # field and require its newly assigned identity to survive export/restart.
    widget = saved["editor_json"]["content"][-1]
    assert widget["type"] == "future_portable_widget"
    block_id = widget["attrs"].get("block_id")
    assert isinstance(block_id, str) and block_id, "Core block identity missing"
    expected["content"][-1]["attrs"]["block_id"] = block_id
    assert saved["editor_json"] == expected, "Unknown nodes or original structure lost"
    original = read("source_original", {"source_id": nodes[0]["media"]["source_id"]})
    assert original["sha256"] == media_sha and base64.b64decode(original["content_base64"]) == image
    exported = bridge("document_package_export", {"document_id": document_id})
    assert exported["document"] == saved
    assert any(obj["sha256"] == media_sha and bytes(obj["bytes"]) == image for obj in exported["objects"])
    evidence.update(import_status="TRUSTED_UI_CONFIRMATION_PASS", media_cas="FORMAL_CORE_BYTES_AND_HASH_PASS",
                    unknown_nodes="PASS", source_bound_originals="PASS", admission="NOT_EXECUTED",
                    document_id=document_id, source_id=nodes[0]["media"]["source_id"], media_sha256=media_sha,
                    downloaded_file_readback="NOT_EXECUTED; export route only, no browser disk claim")
    restart()
    assert read("document_get", {"document_id": document_id}) == saved
    assert read("source_original", {"source_id": nodes[0]["media"]["source_id"]}) == original
    import_file()
    assert read("documents_list")["snapshot_count"] == count + 1, "Repeated file selection duplicated a document"
    assert read("document_get", {"document_id": document_id}) == saved
    if download_control is not None:
        directory = work / "closure-downloads"
        download_control(directory)
        wait("return [...document.querySelector('[aria-label=\"有界文档便携包\"]').querySelectorAll('button')].some(b => b.textContent === '下载文档与媒体便携包' && !b.disabled)")
        ui.click("下载文档与媒体便携包", "//section[@aria-label='有界文档便携包']")
        downloaded = directory / f"{document_id}-v{saved['version']}.aak-document.json"
        deadline = time.monotonic() + 30
        while not downloaded.is_file() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert downloaded.is_file(), "Owned WebView download did not land in isolated directory"
        raw = downloaded.read_bytes()
        assert json.loads(raw) == exported, "Downloaded package differs from formal export"
        assert not list(directory.glob("*.crdownload")), "Download remains incomplete"
        fixture = downloaded
        import_file()
        rows = read("documents_list")
        assert rows["snapshot_count"] == count + 2, "Downloaded package must create exactly one new ordinary document"
        copies = [row for row in rows["documents"] if row["title"] == title and row["document_id"] != document_id]
        assert len(copies) == 1
        copy_id = copies[0]["document_id"]
        copied = read("document_get", {"document_id": copy_id})
        copied_media = copied["editor_json"]["attrs"]["archeaxis_expression"]["nodes"][0]["media"]["source_id"]
        expected_copy = copy.deepcopy(saved["editor_json"])
        expected_copy["attrs"]["archeaxis_expression"]["nodes"][0]["media"]["source_id"] = copied_media
        assert copied["editor_json"] == expected_copy, "Downloaded file reimport lost structure or unknown nodes"
        copied_original = read("source_original", {"source_id": copied_media})
        assert copied_original["sha256"] == media_sha and base64.b64decode(copied_original["content_base64"]) == image
        restart()
        assert read("document_get", {"document_id": copy_id}) == copied
        assert read("source_original", {"source_id": copied_media}) == copied_original
        import_file()
        assert read("documents_list")["snapshot_count"] == count + 2, "Repeated downloaded package created a duplicate"
        evidence.update(downloaded_file_readback="REAL_OWNED_WEBVIEW_FILE_PASS", downloaded_file_sha256=hashlib.sha256(raw).hexdigest(),
                        downloaded_file_reimport="TRUSTED_UI_PASS", downloaded_file_cold_restart="PASS",
                        downloaded_file_repeat="IDEMPOTENT_PASS")
    evidence.update(cold_restart="PASS", repeated_ui_import="IDEMPOTENT_PASS", status="PASS",
                    qualification="REAL_CURRENT_NATIVE_UI_AND_CORE_SYNTHETIC_MATERIAL; not Owner acceptance")
