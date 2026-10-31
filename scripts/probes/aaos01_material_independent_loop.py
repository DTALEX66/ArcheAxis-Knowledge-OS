"""Independent authored-material native journeys; no answer/retest prerequisite.

Only called by the explicitly opted-in native harness on its fresh owned workspace.
All writes go through trusted product UI; ``read`` is the grouped read-only bridge.
"""
import uuid


def create_document(ui, read, wait, grouped):
    """A single original note, with exact Core identity and known authored body."""
    assert read("sources_list")["sources"] == [], "Requires fresh owned sources"
    assert read("documents_list")["snapshot_count"] == 0, "Requires fresh owned documents"
    assert grouped.machine_tasks(read) == [], "Requires fresh owned task journal"
    config = read("model_configuration_get")
    assert config["revision"] == 0 and config["profiles"] == {} and config["bindings"] == [], "Requires fresh owned model configuration"
    ui.page("02")
    ui.click_revealed("新建笔记")
    wait("""return location.hash==="#page=03" && !!document.querySelector('[aria-label="文档草稿编辑器"] .tiptap')""")
    rows = grouped.poll(read, "documents_list", {}, lambda value: len(value["documents"]) == 1)["documents"]
    document = read("document_get", {"document_id": rows[0]["document_id"]})
    assert document["source_id"] is None and document["source_revision"] is None
    text = "Independent synthetic material " + uuid.uuid4().hex + ". ArcheAxis keeps a versioned local note for reading and review."
    selector = '[aria-label="文档草稿编辑器"] .tiptap'
    ui.reveal_selector("//*[@aria-label='文档草稿编辑器']//*[contains(concat(' ',normalize-space(@class),' '),' tiptap ')]")
    ui.keys(selector, "\ue009a\ue000" + text, "css selector")
    ui.click_revealed("保存草稿")
    saved = grouped.poll(read, "document_get", {"document_id": document["document_id"]}, lambda value: value["version"] > document["version"])
    assert saved["document_id"] == document["document_id"] and saved["source_id"] is None and saved["source_revision"] is None
    assert saved["text_projection"] == text, "Authored document body mismatch"
    return saved


def open_reader(ui, read, js, wait, grouped, document):
    ui.page("02")
    ui.click_revealed_selector("//nav[@aria-label='已保存文档']//button[@aria-label=" + grouped.xpath_literal("打开文档 " + document["title"]) + "]")
    return grouped.restored_reader(ui, read, js, wait, document)


def assert_cancel_bindings(stage, saved, document, material):
    assert set(stage["purposes"]) == {"material", "companion"}
    for purpose, value in stage["purposes"].items():
        preview = value["preview"]
        request = preview["plan"]["request"]
        resolved = saved["resolved"][purpose]
        assert request["model_configuration"] == resolved, "Cancellation saved binding mismatch"
        for key in ("model", "max_tokens", "timeout_s"):
            assert request[key] == resolved["profile"][key], "Cancellation profile mismatch: " + key
        expected_material = {"kind": "document", "document_id": document["document_id"], "version": document["version"], "content_sha256": document["content_sha256"], "block_id": None} if purpose == "material" else None
        assert request["material"] == expected_material, "Cancellation material identity mismatch"
        material.assert_cancelled_receipt(value["receipt"], preview, purpose)


def restore_backup(ui, read, wait, grouped):
    ui.page("19")
    prior = {row["backup_id"] for row in read("workspace_backups")["backups"]}
    ui.click_revealed("创建备份")
    backups = grouped.poll(read, "workspace_backups", {}, lambda value: len(value["backups"]) == len(prior) + 1)["backups"]
    assert len([row for row in backups if row["backup_id"] not in prior]) == 1
    ui.click_revealed("检查此备份")
    ui.click_revealed("确认恢复整个工作区")
    wait("return document.body.innerText.includes('整个工作区已恢复，并已重新打开确认')")
    wait("return [...document.querySelectorAll('button')].some(b=>b.textContent==='保留恢复候选')")
    before = read("ui_state_read")
    ui.click_revealed("保留恢复候选")
    after = grouped.poll(read, "ui_state_read", {}, lambda value: value["recovery_requires_confirmation"] is False)
    assert before["restore_epoch"] == after["restore_epoch"] and after["state"] == before["recovery_candidates"]
    return {"status": "PASS", "restore_epoch": after["restore_epoch"]}


def run(*, mode, ui, read, js, wait, restart, screenshot, grouped, material, selected_model, report):
    if mode not in ("recovery", "cancel"):
        raise ValueError("Unknown independent material/companion mode")
    report.update(schema="archeaxis.material-companion-independent-probe/v1", mode=mode,
                  engineering_status="IN_PROGRESS", status="PARTIAL", evidence_level="REAL_TAURI_WEBDRIVER_CANDIDATE_SYNTHETIC_MATERIAL",
                  owner_acceptance="NOT_EXECUTED", human_signoff=False, closed_loop_verified=False,
                  full_grouped_ai_chain="NOT_EXECUTED", startup_execution_calls="UNVERIFIED",
                  provider_stop_state="UNKNOWN", worker_started="UNVERIFIED")
    try:
        document = create_document(ui, read, wait, grouped)
        report["document"] = document
        report["reader_initial"] = grouped.restored_reader(ui, read, js, wait, document)
        grouped.save_deep_model_binding(ui, read, wait, report, selected_model, purposes=("material", "companion"))
        saved = report["saved_deep_binding"]
        if mode == "recovery":
            stage = report["material_companion"] = {}
            material.run(ui, read, js, wait, screenshot, document, saved, stage)
        else:
            stage = report["material_companion_cancellation"] = {}
            # No prior successful generation or mc.run is required for cancellation.
            material.run_cancel(ui, read, js, wait, screenshot, document, stage, grouped.poll)
            assert_cancel_bindings(stage, saved, document, material)
        tasks = grouped.machine_tasks(read)
        restart()
        grouped.read_saved_model_configuration(ui, read, wait, report, restored=False)
        assert grouped.machine_tasks(read) == tasks, "Cold reopen changed unrelated task journal"
        report["reader_cold_reopen"] = open_reader(ui, read, js, wait, grouped, document)
        if mode == "cancel":
            material.reopen_cancel(ui, read, js, wait, screenshot, document, stage)
            assert_cancel_bindings(stage, saved, document, material)
        else:
            material.reopen(ui, read, js, wait, screenshot, document, stage, "cold_reopen")
            report["workspace_restore"] = restore_backup(ui, read, wait, grouped)
            restart()
            grouped.read_saved_model_configuration(ui, read, wait, report, restored=True)
            assert grouped.machine_tasks(read) == tasks, "Backup reopen changed unrelated task journal"
            report["reader_backup_restore"] = open_reader(ui, read, js, wait, grouped, document)
            material.reopen(ui, read, js, wait, screenshot, document, stage, "backup_restore")
        assert read("document_get", {"document_id": document["document_id"]}) == document, "Original document changed"
        report["engineering_status"] = "PASS"
        report["status"] = "PASS_INDEPENDENT_RECOVERY_NOT_FULL_AI_CHAIN" if mode == "recovery" else "PASS_CORE_ADMISSION_UI_CANCEL_RECOVERY_NOT_PROVIDER_STOP"
        return report
    except Exception as error:
        report["engineering_status"] = "FAIL"
        report["failure_type"] = type(error).__name__
        raise
