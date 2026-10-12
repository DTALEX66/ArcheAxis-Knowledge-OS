"""Independent installed document-conflict journey adapter.

The shared native harness must call initialize_fixture using its owned Core HTTP
human session BEFORE host launch, stop that Core normally, then run_ui using
trusted WebDriver controls. This file does not launch/install a host, write SQL,
mutate a native bridge, claim physical IME, or qualify the Owner nine-step loop.
"""
from __future__ import annotations

import copy
import json
import re
import time

ROUTE = "/api/v1/workspace/ui-state"
READS = frozenset({"ui_state_read", "document_get", "document_version", "workspace_backups"})
EDITOR = '[aria-label="版本化草稿编辑器"] [role="textbox"][aria-label="文档草稿"]'


def basis(read):
    return {key: read[key] for key in ("workspace_id", "restore_epoch", "state_revision")}


def editor(text, block):
    return {"type": "doc", "content": [{"type": "paragraph", "attrs": {"block_id": block},
            "content": [{"type": "text", "text": text}]}]}


def assert_journal(read, expected, workspace, epoch=None):
    assert read["schema"] == "archeaxis.ui-working-state/v1"
    assert read["workspace_id"] == workspace
    if epoch is not None:
        assert read["restore_epoch"] == epoch
    assert read["recovery_requires_confirmation"] is False and read["recovery_candidates"] is None
    assert read["state"]["drafts"] == expected
    assert set(read["draft_digests"]) == set(expected)
    assert all(re.fullmatch(r"[0-9a-f]{64}", digest) for digest in read["draft_digests"].values())
    assert read["state"]["pending_original"] is None
    assert not read["state"].get("pending_jobs"), "Unexpected pending business request"


def assert_document(actual, original, version, content):
    assert actual["document_id"] == original["document_id"]
    assert actual["title"] == original["title"] and actual["source_id"] is None
    assert actual["version"] == version and actual["editor_json"] == content
    assert re.fullmatch(r"[0-9a-f]{64}", actual["content_sha256"])


def initialize_fixture(http, *, owned_fresh_workspace, source_identity):
    """http(method,path,body,expected) uses real Core HTTP, not the UI bridge.

    Caller must supply the owned launcher/candidate/source receipt, normally stop
    initialization Core, and launch installed host on the SAME portable data root.
    Pure tests supply SIMULATED transports and are never execution receipts.
    """
    assert owned_fresh_workspace is True, "No authorization for an existing user workspace"
    assert source_identity["commit"] and source_identity["patch_sha256"]
    listing = http("GET", "/api/v1/documents", None, 200)
    assert listing["documents"] == [] and listing["next_cursor"] is None
    initial = http("GET", ROUTE, None, 200)
    assert_journal(initial, {}, initial["workspace_id"])
    assert initial["state"]["opened_documents"] == []
    docs = {}
    drafts = {}
    for name in ("A", "B"):
        saved = editor(f"Installed conflict {name} saved v1", f"owned-conflict-{name}")
        doc = http("POST", "/api/v1/documents", {"title": f"Installed-conflict-owned-{name}",
                   "editor_json": saved}, 201)
        assert_document(doc, doc, 1, saved)
        docs[name] = doc
        drafts[doc["document_id"]] = {"base_version": 1,
            "editor_json": editor(f"Installed independent {name} unsaved", f"owned-conflict-{name}")}
    remote = editor("Installed conflict A other saved v2", "owned-conflict-A")
    current_a = http("PUT", f"/api/v1/documents/{docs['A']['document_id']}/draft",
                     {"expected_version": 1, "editor_json": remote}, 200)
    assert_document(current_a, docs["A"], 2, remote)
    state = copy.deepcopy(initial["state"])
    state.update(drafts=drafts, opened_documents=[doc["document_id"] for doc in docs.values()],
                 active_document=docs["A"]["document_id"], page_id="19")
    journal = http("PUT", ROUTE, {**basis(initial), "state": state}, 200)
    assert_journal(journal, drafts, initial["workspace_id"], initial["restore_epoch"])
    assert journal["state"] == state
    backup = http("POST", "/api/v1/workspace/backups", {}, 201)
    assert re.fullmatch(r"[0-9a-f]{32}", backup["backup_id"])
    assert backup["filename"] == backup["backup_id"] + ".sqlite"
    assert re.fullmatch(r"[0-9a-f]{64}", backup["sha256"])
    # Legal explicit CAS discards only the owned fixture's live working state.
    # The immutable backup retains both drafts; restore UI cannot run dirty.
    clean = copy.deepcopy(initial["state"])
    clean["page_id"] = "19"
    discarded = http("PUT", ROUTE, {**basis(journal), "state": clean}, 200)
    assert discarded["state"] == clean
    confirmed = http("GET", ROUTE, None, 200)
    assert confirmed == discarded
    assert_journal(confirmed, {}, initial["workspace_id"], initial["restore_epoch"])
    for name, doc in docs.items():
        readback = http("GET", f"/api/v1/documents/{doc['document_id']}", None, 200)
        assert readback == (current_a if name == "A" else doc)
    return {"initialization": "SYNTHETIC_INITIALIZATION", "source": source_identity,
            "workspace_id": initial["workspace_id"], "initial_epoch": initial["restore_epoch"],
            "documents": docs, "current_a": current_a, "drafts": drafts,
            "backup": backup, "journal_backup_state": state, "clean_state": clean,
            "owner_acceptance": "NOT_EXECUTED", "installed_ui": "NOT_EXECUTED"}


def readonly(bridge):
    def read(operation, payload=None):
        assert operation in READS, "Installed conflict probe forbids native bridge writes"
        return bridge(operation, payload or {})
    return read


def poll(read, operation, payload, predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = read(operation, payload)
        if predicate(result):
            return result
        time.sleep(0.1)
    raise AssertionError(f"Core readback timed out: {operation}")


def assert_restart(receipt):
    assert receipt["normal_exit"] is True and receipt["exit_code"] == 0
    assert receipt["old_pid"] != receipt["new_pid"]
    assert receipt["old_session"] != receipt["new_session"]
    assert receipt["old_portable_root"] == receipt["new_portable_root"]


def run_ui(fixture, *, ui, bridge, js, wait, navigate, accept_navigation_alert, restart,
           screenshot, host_identity, verify_source):
    """Trusted ui.click/click_selector only; js/wait are DOM observations.

    navigate(page) must use WebDriver sidebar click, GET alert text + POST accept
    when the unsaved guard appears, then observe hash. accept_navigation_alert()
    does that after the actual document button click (never JS window.confirm).
    restart() performs normal whole-host exit + fresh WebDriver session on the
    same portable root. Host identity/exit/source-consistency receipts belong to
    the caller, and are prerequisites for classifying an actual run as installed.
    """
    assert host_identity.get("installed") is True
    assert host_identity.get("source") == fixture["source"], "Source baseline drift"
    read = readonly(bridge)
    a, b = (fixture["documents"][key] for key in ("A", "B"))
    before = read("ui_state_read")
    assert_journal(before, {}, fixture["workspace_id"], fixture["initial_epoch"])
    navigate("19")
    ui.click("刷新备份产物")
    backups = read("workspace_backups")["backups"]
    assert [item for item in backups if item["backup_id"] == fixture["backup"]["backup_id"]] == [fixture["backup"]]
    # Bind the real button to exactly this backup row, rather than first-match.
    filename = json.dumps(fixture["backup"]["filename"])
    row = "//section[@aria-label='一致备份']//li[strong=" + filename + "]"
    ui.click("预检此备份", row)
    ui.click("确认恢复整个工作区")
    wait("return document.body.innerText.includes('整个工作区已恢复，Core 已重启并读回')")
    candidate = read("ui_state_read")
    assert candidate["workspace_id"] == fixture["workspace_id"]
    assert candidate["restore_epoch"] != fixture["initial_epoch"]
    assert candidate["recovery_requires_confirmation"] is True
    assert candidate["recovery_candidates"] == fixture["journal_backup_state"]
    assert candidate["state"]["drafts"] == {}, "Restore candidates applied without consent"
    ui.click("保留恢复候选")
    recovered = poll(read, "ui_state_read", {}, lambda value: not value["recovery_requires_confirmation"])
    assert recovered["state"] == candidate["recovery_candidates"]
    assert_journal(recovered, fixture["drafts"], fixture["workspace_id"], candidate["restore_epoch"])
    def open_doc(doc):
        navigate("02")
        ui.click_selector('[aria-label="打开文档 ' + doc["title"] + '"]', "css selector")
        accept_navigation_alert()
        wait("return location.hash==='#page=03' && !!document.querySelector(" + json.dumps(EDITOR) + ")")
    open_doc(a)
    ui.click("保存草稿")
    wait("return !!document.querySelector('[aria-label=\"文档版本冲突恢复\"]')")
    assert read("document_get", {"document_id": a["document_id"]}) == fixture["current_a"]
    assert_journal(read("ui_state_read"), fixture["drafts"], fixture["workspace_id"], recovered["restore_epoch"])
    ui.click("读取当前版本并比较（保留草稿）")
    expected = {"原基准": a["editor_json"], "当前已保存": fixture["current_a"]["editor_json"],
                "我的草稿": fixture["drafts"][a["document_id"]]["editor_json"]}
    for label, content in expected.items():
        selector = '[aria-label="文档版本冲突恢复"] section[aria-label="' + label + '"] details pre'
        wait("return !!document.querySelector(" + json.dumps(selector) + ")")
        actual = js("return document.querySelector(" + json.dumps(selector) + ").textContent")
        assert json.loads(actual) == content, "Comparison identity/content mismatch: " + label
    screenshot("installed-document-three-way-conflict.png")
    ui.click("明确保留本稿并按已比较版本保存")
    remaining = {b["document_id"]: fixture["drafts"][b["document_id"]]}
    journal = poll(read, "ui_state_read", {}, lambda value: set(value["state"]["drafts"]) == {b["document_id"]})
    assert_journal(journal, remaining, fixture["workspace_id"], recovered["restore_epoch"])
    saved_a = read("document_get", {"document_id": a["document_id"]})
    assert_document(saved_a, a, 3, expected["我的草稿"])
    assert read("document_get", {"document_id": b["document_id"]}) == b
    for version, body in ((1, a), (2, fixture["current_a"]), (3, saved_a)):
        assert read("document_version", {"document_id": a["document_id"], "version": version}) == body
    screenshot("installed-A-saved-B-independent.png")
    restart_receipt = restart()
    assert_restart(restart_receipt)
    assert_journal(read("ui_state_read"), remaining, fixture["workspace_id"], recovered["restore_epoch"])
    assert read("document_get", {"document_id": a["document_id"]}) == saved_a
    assert read("document_get", {"document_id": b["document_id"]}) == b
    open_doc(b)
    text = js("return document.querySelector(" + json.dumps(EDITOR) + ").textContent")
    assert text == remaining[b["document_id"]]["editor_json"]["content"][0]["content"][0]["text"]
    assert_journal(read("ui_state_read"), remaining, fixture["workspace_id"], recovered["restore_epoch"])
    assert read("document_get", {"document_id": b["document_id"]}) == b
    screenshot("installed-B-restored-after-host-restart.png")
    final_source = verify_source()
    assert final_source == fixture["source"], "Source changed during installed journey"
    return {"status": "PASS", "initialization": "SYNTHETIC_INITIALIZATION",
            "installed_ui": "TRUSTED_WEBDRIVER_CONTROLS", "owner_acceptance": "NOT_EXECUTED",
            "source": fixture["source"], "host": host_identity, "saved_a": saved_a,
            "remaining_b": remaining, "restart_readback": True, "restart_receipt": restart_receipt,
            "final_source": final_source,
            "limits": ["No UI creation of the initialized drafts", "No physical IME qualification",
                       "No complete Owner nine-step qualification", "No permanent pre-merge draft archive",
                       "Permission refusal/late input require separate existing regression evidence"]}
