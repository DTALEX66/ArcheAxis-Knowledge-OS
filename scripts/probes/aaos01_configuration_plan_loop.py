"""Opt-in BE08 read-only plans and finite product configuration on an isolated candidate."""
from __future__ import annotations


def run(*, ui, bridge, js, wait, restart, screenshot, report):
    report.update(status="IN_PROGRESS", evidence_level="REAL_NATIVE_UI_CORE_SYNTHETIC_INPUT",
                  owner_acceptance=False, model_call="NOT_EXECUTED", installation="NOT_QUALIFIED")
    operations = []

    def observe():
        # Observe identity/outcome only; delegate unchanged and never replace Core results.
        js("""const original=window.__TAURI__,invoke=original.core.invoke;
window.__planProbeOriginal=original;window.__planProbeOps=[];
const observed=async function(command,args){const value=await invoke(command,args);
if(command==='core_command')window.__planProbeOps.push({command,operation:args.request.operation,status:value.status});
if(command==='ui_host_command')window.__planProbeOps.push({command,operation:args.request.operation,outcome:value.outcome});
return value;};window.__TAURI__={...original,core:{...original.core,invoke:observed}};
if(window.__TAURI__.core.invoke!==observed)throw new Error('Plan observer refused');""")

    def collect():
        operations.extend(js("return window.__planProbeOps"))
        js("window.__TAURI__=window.__planProbeOriginal;delete window.__planProbeOriginal;delete window.__planProbeOps;")

    def ready():
        wait("return !!document.querySelector('[aria-label=\"工作草稿状态\"][data-working-state=\"ready\"]')")
        ui.page("19")
        wait("const panel=document.querySelector('[aria-label=\"配置与部署计划\"]');return !!panel && !panel.closest('[hidden]') && !!panel.getClientRects().length")

    def read_plans(expected):
        ui.click("读取配置与部署计划", "//section[@aria-label='配置与部署计划']")
        wait("return document.querySelector('[aria-label=\"配置与部署计划\"]').innerText.includes('已读取当前配置')")
        plans = bridge("configuration_plans_read")
        assert plans == expected
        assert not any(plans[key] for key in ("installer_available", "network_performed", "storage_changed", "worker_started"))
        assert plans["execution_grant"] is None
        text = js("return document.querySelector('[aria-label=\"配置与部署计划\"]').innerText")
        assert "（此值不是模型文件 hash）" in text and "文件 SHA-256：未知" in text
        assert "不可执行：缺少安装引擎" in text and "不可执行：只读取配置" in text
        assert js("return document.querySelector('[aria-label=\"配置与部署计划\"]').querySelectorAll('button').length") == 1
        return plans

    observe()
    ready()
    before = bridge("model_configuration_get")
    assert before["revision"] == 0 and before["profiles"] == {}
    assert bridge("configuration_plans_read")["plans"] == []
    scope = "//section[@aria-label='产品模型与用途绑定']"
    ui.click("读取模型配置", scope)
    ui.type("本地服务地址", "http://127.0.0.1:1234/v1", scope=scope)
    ui.type("模型名称", "synthetic-plan-model", scope=scope)
    ui.click("保存配置与用途绑定", scope)
    wait("return document.querySelector('[aria-label=\"产品模型与用途绑定\"]').innerText.includes('已保存版本 1')")
    saved = bridge("model_configuration_get")
    assert saved["revision"] == 1 and saved["profiles"]["local"]["model"] == "synthetic-plan-model"
    assert saved["bindings"] == []
    expected = bridge("configuration_plans_read")
    assert expected["configuration_revision"] == 1 and len(expected["plans"]) == 2
    assert {p["mode"] for p in expected["plans"]} == {"existing_service", "local_download"}
    for plan in expected["plans"]:
        assert plan["executable"] is False
        assert all(plan[k] is None for k in ("version", "artifact_sha256", "size_bytes"))
    assert expected["plans"][0]["source"] == "http://127.0.0.1:1234/v1" and expected["plans"][1]["source"] is None
    read_plans(expected)
    assert bridge("model_configuration_get") == saved
    screenshot("configuration-plans.png")
    collect()
    restart()
    observe()
    ready()
    assert bridge("model_configuration_get") == saved
    read_plans(expected)
    assert bridge("model_configuration_get") == saved
    screenshot("configuration-plans-cold-reopen.png")
    collect()
    writes = [r for r in operations if r["command"] == "core_command" and r["operation"] == "model_configuration_put"]
    reads = [r for r in operations if r["command"] == "ui_host_command"]
    assert len(writes) == 1 and writes[0]["status"] == 200
    assert len(reads) == 2 and all(r["operation"] == "configuration.plan.read" and r["outcome"] == "READ_OK" for r in reads)
    assert not any(r["operation"] in {"machine_answer", "machine_retest", "material_question", "conversation_request", "job_execute", "job_enqueue", "document_check_execute", "machine_inventory"} for r in operations)
    report.update(status="PASS", operations=operations, manual_configuration_writes=1,
                  formal_plan_reads=2, cold_reopens=1, current_configuration_unchanged_by_reads=True,
                  plan_count=2, configuration_sha256=expected["configuration_sha256"],
                  limitations=["Synthetic configuration only; no actual service probe or model execution", "No installer, installed Green, release or Owner acceptance qualification"])
