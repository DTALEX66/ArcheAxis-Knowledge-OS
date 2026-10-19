"""Explicit BE06 candidate UI journey with synthetic memory and owned downloads."""

from __future__ import annotations

import hashlib
import json
import time


def run(*, ui, bridge, js, wait, restart, download_control, work, screenshot, report):
    scope = "//section[@aria-label='角色档案与获准记忆']"
    report.update(status="IN_PROGRESS", evidence_level="REAL_NATIVE_UI_CORE_SYNTHETIC_INPUT",
                  owner_acceptance=False, model_call="NOT_EXECUTED", installation="NOT_QUALIFIED")
    operations = []

    def observe():
        # Observe operation names only; never replace a result or read credentials.
        js("""const original=window.__TAURI__,invoke=original.core.invoke;
window.__memoryProbeOriginal=original;window.__memoryProbeOps=[];
const observed=async function(command,args){const value=await invoke(command,args);
if(command==='core_command')window.__memoryProbeOps.push({operation:args.request.operation,
command:args.request.operation==='character_memory_apply'?args.request.payload?.body?.command?.operation:null,status:value.status});
return value;};window.__TAURI__={...original,core:{...original.core,invoke:observed}};
if(window.__TAURI__.core.invoke!==observed)throw new Error('Memory observer refused');""")

    def collect():
        operations.extend(js("return window.__memoryProbeOps"))
        js("window.__TAURI__=window.__memoryProbeOriginal;delete window.__memoryProbeOriginal;delete window.__memoryProbeOps;")

    def read():
        profile = bridge("character_memory_get")
        assert profile["schema"] == "archeaxis.character-memory/v1"
        return profile

    def ready():
        wait("return !!document.querySelector('[aria-label=\"工作草稿状态\"][data-working-state=\"ready\"]')")
        ui.page("14")
        wait("const panel=document.querySelector('[aria-label=\"角色档案与获准记忆\"]');return !!panel && !panel.closest('[hidden]') && !!panel.getClientRects().length && panel.innerText.includes('当前存储 v')")

    def saved(revision):
        wait("return document.querySelector('[aria-label=\"角色档案与获准记忆\"]').innerText.includes('当前存储 v" + str(revision) + " ·')")
        value = read()
        assert value["revision"] == revision
        return value

    def remember(text):
        ui.type("记忆内容", text, "textarea", scope=scope)
        ui.type("记忆来源", "synthetic explicit human fixture", scope=scope)
        ui.click("保存并核对这条记忆", scope)

    def reopen(expected):
        collect()
        restart()
        observe()
        ready()
        assert read() == expected
        report.setdefault("cold_reopens", []).append({"revision":expected["revision"],"memories":len(expected["memories"]),"same_workspace_epoch_profile":True})

    observe()
    ready()
    initial = read()
    assert initial["revision"] == 0 and initial["memories"] == [] and not initial["enabled"]
    ui.type("角色偏好", "synthetic calm stepwise style", "textarea", scope=scope)
    ui.type("学习目标", "synthetic evidence-reading goal", "textarea", scope=scope)
    ui.click("保存并核对档案", scope)
    profile = saved(1)
    assert profile["preferences"] == "synthetic calm stepwise style"
    assert profile["learning_goals"] == "synthetic evidence-reading goal"
    remember("synthetic first approved memory")
    profile = saved(2)
    first = profile["memories"][0]["id"]
    row_scope = scope + "//article[@aria-label='获准记忆 " + first + "']"
    ui.click("纠正此条", row_scope)
    ui.type("记忆内容", "synthetic corrected approved memory", "textarea", scope=scope)
    ui.click("保存并核对纠正", scope)
    profile = saved(3)
    assert profile["memories"][0] == {"id":first,"text":"synthetic corrected approved memory","provenance":"synthetic explicit human fixture"}
    remember("synthetic second approved memory")
    profile = saved(4)
    second = profile["memories"][1]["id"]
    assert second != first
    ui.click("明确启用陪伴记忆", scope)
    profile = saved(5)
    assert profile["enabled"] is True
    context = bridge("character_memory_context")
    assert context["approved_memories"] == profile["memories"]
    assert context["knowledge_admitted"] is False and context["grants"] == []
    reopen(profile)
    screenshot("memory-after-cold-reopen.png")

    directory = work / "memory-download"
    download_control(directory)
    ui.click("导出当前记忆 JSON", scope)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        files = list(directory.glob("archeaxis-memory-v5*.json"))
        if len(files) == 1:
            try:
                exported = json.loads(files[0].read_bytes())
                break
            except (OSError, ValueError):
                pass
        time.sleep(.1)
    else:
        raise TimeoutError("Owned native memory JSON download unavailable")
    assert exported == {"schema":"archeaxis.memory-export/v1","profile":profile,"contains_personal_memory":True,"network_performed":False}
    report["download"] = {"path":str(files[0]),"bytes":files[0].stat().st_size,"sha256":hashlib.sha256(files[0].read_bytes()).hexdigest(),"exact_profile":True}

    ui.click("停用陪伴记忆", scope)
    profile = saved(6)
    assert not profile["enabled"]
    context = bridge("character_memory_context")
    assert context["approved_memories"] == [] and context["grants"] == []
    assert context["knowledge_admitted"] is False
    ui.click("审阅遗忘此条", row_scope)
    ui.click("取消遗忘", "//*[@role='alertdialog']")
    assert read() == profile
    report["cancel_forget_unchanged"] = True
    ui.click("审阅遗忘此条", row_scope)
    ui.click("确认遗忘", "//*[@role='alertdialog']")
    profile = saved(7)
    assert [row["id"] for row in profile["memories"]] == [second]
    ui.click("审阅遗忘全部记忆", scope)
    ui.click("确认遗忘", "//*[@role='alertdialog']")
    profile = saved(8)
    assert profile["memories"] == []
    assert profile["preferences"] == "synthetic calm stepwise style"
    reopen(profile)
    screenshot("memory-after-forget-cold-reopen.png")
    collect()
    writes = [row for row in operations if row["operation"] == "character_memory_apply"]
    assert [row["command"] for row in writes] == ["profile","remember","correct","remember","enable","disable","forget","forget_all"]
    assert all(row["status"] == 200 for row in writes)
    assert not any(row["operation"] in {"machine_answer","machine_retest","material_question","conversation_request","job_execute","job_enqueue","document_check_execute"} for row in operations)
    report.update(status="PASS",engineering_status="PASS",operations=operations,
                  final_profile=profile,manual_memory_commands=8,
                  historical_chat_and_backups="UNCHANGED_PER_CORE_RECEIPT; not secure erasure",
                  limitations=["Synthetic memory only; no Owner acceptance","Candidate run without installer qualification","No real model response or memory quality qualification"])
