"""显式合成工作区的原生材料/陪伴旅程；仅可信 UI 发起写入和模型调用。"""
from __future__ import annotations

import hashlib
import json
import uuid


def literal(value):
    # XPath 1.0 string literal, including authored titles containing both quote types.
    if "'" not in value:
        return "'" + value + "'"
    return "concat(" + ',"\'",'.join("'" + part + "'" for part in value.split("'")) + ")"


def node(scope):
    return "document.evaluate(" + json.dumps(scope) + ",document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue"


def install_observer(js, questions, include_cancel=False):
    js("""if(window.__aaosMC)throw Error('Observer already installed');
const original=window.__TAURI__,invoke=original.core.invoke,includeCancel=""" + json.dumps(include_cancel) + """,questions=""" + json.dumps(questions) + """;
const proof={rows:[],overflow:false};window.__aaosMC={original,proof};
const observed=async function(command,args,...rest){
 const op=args?.request?.operation,body=args?.request?.payload?.body;
 const cancellation=includeCancel&&['material_question_cancel','conversation_cancel'].includes(op);
 const tracked=command==='core_command'&&(['material_question','conversation_request'].includes(op)||cancellation);
 let row;if(tracked){row={operation:op,preview:body?.preview===true,request_id:body?.request_id??null,session_id:body?.session_id??null,own:body?.question===questions[op],completed:false};
 if(cancellation)row.own=proof.rows.some(r=>r.own&&r.request_id===body?.request_id&&r.session_id===(body?.session_id??null));
 if(proof.rows.length>=128)proof.overflow=true;else proof.rows.push(row);
 if(row.own)row.request=JSON.parse(JSON.stringify(body));}
 try{const value=await Reflect.apply(invoke,original.core,[command,args,...rest]);
 if(row){row.status=value.status;if(row.own&&row.preview&&value.status===200)row.preview_response=JSON.parse(JSON.stringify(value.body));
 if(row.own&&!row.preview){const body=value.body;row.terminal_response=body&&typeof body==='object'?Object.fromEntries(
 ['schema','request_id','session_id','task_id','outcome','state','reason_code','plan_sha256','cancel_requested','provider_stop_state'].filter(k=>Object.hasOwn(body,k)).map(k=>[k,body[k]])):null;}}return value;
 }catch(error){if(row)row.error='BRIDGE_REJECTED';throw error;}finally{if(row)row.completed=true;}
};window.__TAURI__={...original,core:{...original.core,invoke:observed}};
if(window.__TAURI__.core.invoke!==observed)throw Error('Observer installation refused');""")


def proof(js):
    value = js("return window.__aaosMC.proof")
    assert not value["overflow"], "Observer overflow; no truncated PASS"
    return value


def remove_observer(js):
    try:
        return proof(js)
    finally:
        js("window.__TAURI__=window.__aaosMC.original;delete window.__aaosMC;")


def assert_bound_receipt(receipt, preview, resolved, purpose):
    """以原冻结身份校验终态，拒绝空回答、其他模型/版本和伪成功。"""
    assert receipt["request_id"] == preview["plan"]["request"]["request_id"]
    assert receipt["plan"] == preview["plan"] and receipt["plan_sha256"] == preview["plan_sha256"]
    request = receipt["plan"]["request"]
    assert request["model_configuration"] == resolved
    profile = resolved["profile"]
    assert resolved["purpose"] == purpose and resolved["lane"] == "deep"
    assert request["model"] == profile["model"] and request["max_tokens"] == profile["max_tokens"]
    assert request["timeout_s"] == profile["timeout_s"] and profile["credential_ref"] is None
    assert receipt["authority"] == "candidate" and receipt["grants_knowledge_acceptance"] is False
    if purpose == "material":
        assert receipt["schema"] == "archeaxis.material-answer/v1" and receipt["outcome"] == "succeeded", receipt.get("reason_code")
    else:
        assert receipt["schema"] == "archeaxis.conversation-receipt/v1" and receipt["state"] == "completed", receipt.get("reason_code")
        assert receipt["session_id"] == request["session_id"]
    answer = receipt["answer"]
    assert isinstance(answer.get("answer"), str) and answer["answer"].strip(), "Empty final answer"
    for key in ("model", "endpoint", "protocol"):
        assert answer[key] == profile[key], "Actual model destination mismatch: " + key
    assert answer["requested_model"] == answer["observed_model"] == profile["model"], "Observed model mismatch"
    assert answer["finish_reason"] == "stop" and answer["truncated"] is False and answer["answer_source"] == "content", "Final answer not fully qualified"
    if purpose == "material":
        assert receipt["answer_sha256"] == hashlib.sha256(answer["answer"].encode()).hexdigest()


def assert_calls(value, expected):
    assert not value["overflow"]
    rows = value["rows"]
    assert len(rows) == len(expected), "Unexpected UI inference operation count"
    for row, (op, preview) in zip(rows, expected):
        assert row["operation"] == op and row["preview"] is preview and row["own"]
        assert row["completed"] and row["status"] == 200 and not row.get("error")


def wait_execution(js, wait, stage, purpose, preview):
    """读取实际 UI 调用的终态；HTTP200中的失败不能退化成等成功文案超时。"""
    operation = "material_question" if purpose == "material" else "conversation_request"
    request = preview["plan"]["request"]
    match = {"operation": operation, "request_id": request["request_id"]}
    if purpose == "companion":
        match["session_id"] = request["session_id"]
    wait("const key=" + json.dumps(match) + ";return window.__aaosMC.proof.rows.some(r=>r.own&&!r.preview&&r.completed&&Object.entries(key).every(([k,v])=>r[k]===v))", seconds=150)
    rows = [row for row in proof(js)["rows"] if row["own"] and not row["preview"] and all(row.get(k) == v for k, v in match.items())]
    assert len(rows) == 1, "Duplicate or missing original execution observation"
    row = rows[0]
    response = row.get("terminal_response")
    stage.setdefault("execution_results", {})[purpose] = {"http_status": row.get("status"), "bridge_error": row.get("error"), "response": response}
    assert row.get("status") == 200 and not row.get("error"), f"{purpose} execution transport failure: {row.get('status')} {row.get('error')} {response}"
    assert isinstance(response, dict), "Missing original execution response metadata"
    assert response.get("request_id") == request["request_id"] and response.get("plan_sha256") == preview["plan_sha256"], "Execution response identity/plan mismatch"
    if purpose == "companion":
        assert response.get("session_id") == request["session_id"], "Execution response session mismatch"
    terminal = response.get("outcome" if purpose == "material" else "state")
    success = "succeeded" if purpose == "material" else "completed"
    assert response.get("schema") == ("archeaxis.material-answer/v1" if purpose == "material" else "archeaxis.conversation-receipt/v1"), "Execution response schema mismatch"
    assert terminal == success, f"{purpose} execution {terminal}: {response.get('reason_code', 'UNKNOWN')}"
    return response


def open_material(ui, wait, document):
    ui.page("02")
    scope = "//section[@aria-label='知识库文档视图' and not(ancestor-or-self::*[@hidden])]"
    ui.click_revealed_selector(scope + "//nav[@aria-label='已保存文档']//button[@aria-label=" + literal("打开文档 " + document["title"]) + "]")
    ui.page("20")
    wait("return [...document.querySelectorAll('.reader-material-tools')].some(n=>n.getClientRects().length>0)")
    details = "//details[contains(@class,'reader-material-tools') and not(ancestor-or-self::*[@hidden])]"
    if not ui.js("return " + node(details) + "?.open"):
        ui.click_revealed_selector(details + "/summary")
    return "//section[@aria-label='固定版本材料问答' and not(ancestor-or-self::*[@hidden])]"


def select_lane(ui, scope, label):
    selector = scope + "//label[contains(.," + literal(label) + ")]/select"
    ui.reveal_selector(selector)
    ui.click_selector(selector + "/option[@value='deep']")


def visible_answer(wait, scope, text):
    wait("const n=" + node(scope) + ";return !!n&&[...n.querySelectorAll('p')].some(p=>p.getClientRects().length>0&&p.textContent===" + json.dumps(text) + ")")


def show_answer(ui, wait, scope, text):
    visible_answer(wait, scope, text)
    # 截图前将实际回答带入视口，不能把滚动区外的 DOM 当作视觉证据。
    ui.reveal_selector(scope + "//p[.=" + literal(text) + "]")


def recover_material(ui, wait, scope, text):
    # 切页会卸载组件；沿产品既有只读恢复入口找回原回执，不再确认执行。
    ui.click_revealed("恢复最近同版本材料请求", scope)
    wait("return " + node(scope) + ".textContent.includes('原请求历史回执已读回；没有再次推理。')")
    show_answer(ui, wait, scope, text)


def read_receipts(read, stage):
    material = read("material_question_status", {"body": {"request_id": stage["material_preview"]["plan"]["request"]["request_id"]}})
    request = stage["companion_preview"]["plan"]["request"]
    companion = read("conversation_status", {"body": {"session_id": request["session_id"], "request_id": request["request_id"]}})
    history = read("conversation_history", {"body": {"session_id": request["session_id"], "after_sequence": 0, "limit": 64}})
    assert history["session_id"] == request["session_id"] and history["last_sequence"] == 2
    assert [(e["kind"], e["sequence"], e["request_id"]) for e in history["events"]] == [("accepted", 1, request["request_id"]), ("completed", 2, request["request_id"])]
    assert history["events"][1]["data"] == companion and len(history["requests"]) == 1
    assert history["requests"][0]["receipt"] == companion
    return {"material": material, "companion": companion, "history": history}


def run(ui, read, js, wait, screenshot, document, saved, stage):
    nonce = uuid.uuid4().hex[:12]
    questions = {"material_question": "合成材料 " + nonce + "：请用一句中文概括所选材料的主题。", "conversation_request": "合成陪伴 " + nonce + "：请用一句中文建议今天如何复习知识。"}
    for purpose in ("material", "companion"):
        assert saved["resolved"][purpose]["profile"]["credential_ref"] is None
    stage.update(status="IN_PROGRESS", questions=questions, document=document, resolved={p: saved["resolved"][p] for p in ("material", "companion")}, startup_execution_calls="UNVERIFIED")
    install_observer(js, questions)
    expected = []
    try:
        scope = open_material(ui, wait, document)
        select_lane(ui, scope, "材料模型通道")
        area = scope + "//label[contains(.,'材料问答选区')]/textarea"
        ui.keys(area, "\ue009a\ue000")
        wait("return " + node(scope) + ".textContent.includes('已选文本：')")
        ui.type("材料问题", questions["material_question"], scope=scope)
        ui.type("提问用途", "隔离合成材料原生验证", scope=scope)
        ui.click_revealed("预览材料提问", scope)
        wait("return !!" + node(scope) + ".querySelector('[aria-label=\"待确认请求\"]')")
        expected.append(("material_question", True)); assert_calls(proof(js), expected)
        preview = proof(js)["rows"][-1]["preview_response"]; stage["material_preview"] = preview
        request = preview["plan"]["request"]
        assert request["material"] == {"kind": "document", "document_id": document["document_id"], "version": document["version"], "content_sha256": document["content_sha256"], "block_id": None}
        selection = request["selection"]; assert selection and selection["start_utf16"] == 0
        raw = document["text_projection"].encode("utf-16-le")
        assert selection["end_utf16"] == len(raw) // 2 and selection["quote_sha256"] == hashlib.sha256(raw.decode("utf-16-le").encode()).hexdigest()
        assert request["model_configuration"] == stage["resolved"]["material"]
        ui.click_revealed("确认并提问或读回同一请求", scope)
        wait_execution(js, wait, stage, "material", preview)
        wait("return " + node(scope) + ".textContent.includes('回答已记录，仍是待判断的模型候选。')", seconds=150)
        expected.append(("material_question", False)); assert_calls(proof(js), expected)
        assert proof(js)["rows"][-1]["request"] == {**request, "preview": False, "confirmed_plan_sha256": preview["plan_sha256"]}
        ui.page("14")
        scope = "//section[@aria-label='正式陪伴会话' and not(ancestor-or-self::*[@hidden])]"
        ui.click_revealed("新建陪伴会话", scope)
        wait("return " + node(scope) + ".textContent.includes('当前会话：')")
        select_lane(ui, scope, "会话模型通道")
        ui.type("会话问题", questions["conversation_request"], "textarea", scope)
        ui.click_revealed("预览会话请求", scope)
        wait("return !!" + node(scope) + ".querySelector('[aria-label=\"待确认请求\"]')")
        expected.append(("conversation_request", True)); assert_calls(proof(js), expected)
        preview = proof(js)["rows"][-1]["preview_response"]; stage["companion_preview"] = preview
        request = preview["plan"]["request"]
        assert request["material"] is None and request["model_configuration"] == stage["resolved"]["companion"]
        ui.click_revealed("确认执行同一会话请求", scope)
        wait_execution(js, wait, stage, "companion", preview)
        wait("return " + node(scope) + ".textContent.includes('回执与历史已读回；回答仍需你判断。')", seconds=150)
        expected.append(("conversation_request", False)); assert_calls(proof(js), expected)
        assert proof(js)["rows"][-1]["request"] == {**request, "preview": False, "confirmed_plan_sha256": preview["plan_sha256"]}
        stage["receipts"] = read_receipts(read, stage)
        for purpose in ("material", "companion"):
            assert_bound_receipt(stage["receipts"][purpose], stage[purpose + "_preview"], stage["resolved"][purpose], purpose)
        show_answer(ui, wait, scope, stage["receipts"]["companion"]["answer"]["answer"])
        screenshot("material-companion-completed.png")
        scope = open_material(ui, wait, document)
        recover_material(ui, wait, scope, stage["receipts"]["material"]["answer"]["answer"])
        assert read_receipts(read, stage) == stage["receipts"], "Original receipts changed during navigation recovery"
        assert_calls(proof(js), expected)
        stage["same_process_recovery"] = {"status": "PASS", "original_receipts_unchanged": True, "additional_observed_ui_execution_calls": 0}
        screenshot("material-completed.png")
        stage["status"] = "PASS_REAL_MODEL_SYNTHETIC_MATERIAL_NOT_QUALITY_QUALIFICATION"
    finally:
        stage["observed_calls"] = remove_observer(js)


def reopen(ui, read, js, wait, screenshot, document, stage, phase):
    install_observer(js, stage["questions"])
    try:
        scope = open_material(ui, wait, document)
        recover_material(ui, wait, scope, stage["receipts"]["material"]["answer"]["answer"])
        screenshot("material-" + phase + ".png")
        ui.page("14")
        scope = "//section[@aria-label='正式陪伴会话' and not(ancestor-or-self::*[@hidden])]"
        sid = stage["companion_preview"]["plan"]["request"]["session_id"]
        selector = scope + "//label[contains(.,'已保存会话')]/select"
        ui.reveal_selector(selector)
        ui.click_selector(selector + "/option[@value=" + literal(sid) + "]")
        wait("return " + node(scope) + ".textContent.includes('当前会话：')")
        ui.click_revealed("重读历史", scope)
        wait("return " + node(scope) + ".textContent.includes('历史已读回；未确认的提问请继续查询。')")
        show_answer(ui, wait, scope, stage["receipts"]["companion"]["answer"]["answer"])
        assert read_receipts(read, stage) == stage["receipts"], "Persisted original results changed across reopen"
        screenshot("companion-" + phase + ".png")
        assert_calls(proof(js), [])
        stage[phase] = {"status": "PASS", "original_receipts_unchanged": True, "observed_after_attach_ui_execution_calls": 0, "startup_execution_calls": "UNVERIFIED"}
    finally:
        stage[phase + "_observation"] = remove_observer(js)


def assert_cancelled_receipt(receipt, preview, purpose):
    request = preview["plan"]["request"]
    assert receipt["request_id"] == request["request_id"]
    assert receipt["plan"] == preview["plan"] and receipt["plan_sha256"] == preview["plan_sha256"]
    assert receipt["answer"] is None and receipt["provider_stop_state"] == "UNKNOWN"
    assert receipt["authority"] == "candidate" and receipt["grants_knowledge_acceptance"] is False
    if purpose == "material":
        assert receipt["schema"] == "archeaxis.material-answer/v1" and receipt["outcome"] == "failed"
        assert receipt["reason_code"] == "material_question_cancelled"
    else:
        assert receipt["schema"] == "archeaxis.conversation-receipt/v1" and receipt["state"] == "cancelled"
        assert receipt["session_id"] == request["session_id"] and receipt["reason_code"] == "conversation_cancelled"


def run_cancel(ui, read, js, wait, screenshot, document, stage, poll):
    """真实UI取消已准入请求；不宣称服务端推理停止或worker已实际启动。"""
    nonce = uuid.uuid4().hex[:12]
    questions = {op: "隔离取消验证 " + nonce + "：请详细分二十节说明知识整理与复习流程，每节至少两百字。" for op in ("material_question", "conversation_request")}
    stage.update(status="IN_PROGRESS", questions=questions, purposes={}, provider_stop_state="UNKNOWN", worker_started="UNVERIFIED")
    # The prior restore/refusal exercise deliberately leaves an owned synthetic
    # draft. Leave through the existing trusted confirmation, never suppress the
    # product guard or accept an unrelated private draft.
    ui.page("02", confirm_navigation=True)
    install_observer(js, questions, include_cancel=True)
    expected = []
    try:
        for purpose in ("material", "companion"):
            if purpose == "material":
                scope = open_material(ui, wait, document)
                select_lane(ui, scope, "材料模型通道")
                ui.type("材料问题", questions["material_question"], scope=scope)
                ui.type("提问用途", "自有合成材料取消验证", scope=scope)
                op, cancel_op, status_op = "material_question", "material_question_cancel", "material_question_status"
                preview_label, execute_label, cancel_label = "预览材料提问", "确认并提问或读回同一请求", "取消材料提问"
            else:
                ui.page("14")
                scope = "//section[@aria-label='正式陪伴会话' and not(ancestor-or-self::*[@hidden])]"
                ui.click_revealed("新建陪伴会话", scope)
                wait("return " + node(scope) + ".textContent.includes('当前会话：')")
                select_lane(ui, scope, "会话模型通道")
                ui.type("会话问题", questions["conversation_request"], "textarea", scope)
                op, cancel_op, status_op = "conversation_request", "conversation_cancel", "conversation_status"
                preview_label, execute_label, cancel_label = "预览会话请求", "确认执行同一会话请求", "取消会话请求"
            ui.click_revealed(preview_label, scope)
            wait("return !!" + node(scope) + ".querySelector('[aria-label=\"待确认请求\"]')")
            expected.append((op, True)); assert_calls(proof(js), expected)
            preview = proof(js)["rows"][-1]["preview_response"]
            request = preview["plan"]["request"]
            identity = {k: request[k] for k in (("request_id",) if purpose == "material" else ("session_id", "request_id"))}
            item = stage["purposes"][purpose] = {"preview": preview, "identity": identity}
            ui.click_revealed(execute_label, scope)
            # The persisted claim/status is evidence of Core admission, not of a
            # model server receiving the request. No fixed sleep implies that.
            if purpose == "companion":
                # A newly created session exists before its request journal does;
                # history stays readable during admission, while status may be 404.
                item["admitted_history"] = poll(read, "conversation_history", {"body": {"session_id": identity["session_id"], "after_sequence": 0, "limit": 64}}, lambda h: any(r.get("request_id") == identity["request_id"] for r in h["requests"]), seconds=10)
            item["admitted_status"] = poll(read, status_op, {"body": identity}, lambda r: r.get("execution_state") == "UNKNOWN", seconds=10)
            ui.click_revealed(cancel_label, scope)
            wait("return window.__aaosMC.proof.rows.some(r=>r.operation===" + json.dumps(cancel_op) + "&&r.completed)")
            row = next(r for r in proof(js)["rows"] if r["operation"] == cancel_op)
            assert row["own"] and row["status"] == 200 and row["request"] == identity
            assert row["terminal_response"]["cancel_requested"] is True
            item["cancel_ack"] = row["terminal_response"]
            wait("return window.__aaosMC.proof.rows.some(r=>r.operation===" + json.dumps(op) + "&&!r.preview&&r.completed)")
            item["receipt"] = read(status_op, {"body": identity})
            assert_cancelled_receipt(item["receipt"], preview, purpose)
            expected.extend([(op, False), (cancel_op, False)]); assert_calls(proof(js), expected)
            message = "执行失败或取消，原请求和材料保留。" if purpose == "material" else "cancelled"
            if purpose == "material":
                wait("return " + node(scope) + ".textContent.includes(" + json.dumps(message) + ")")
            else:
                wait("return !!" + node(scope) + ".querySelector('.xiaoqi-avatar[data-visible-state=\"interrupted\"]')")
                ui.click_revealed("重读历史", scope)
                history = read("conversation_history", {"body": {"session_id": identity["session_id"], "after_sequence": 0, "limit": 64}})
                assert len(history["requests"]) == 1 and [e["kind"] for e in history["events"]] == ["accepted", "cancelled"]
                assert history["requests"][0]["receipt"] == item["receipt"]
                item["history"] = history
            ui.reveal_selector(scope)
            screenshot("cancel-" + purpose + ".png")
        stage["status"] = "PASS_CORE_ADMISSION_AND_UI_CANCELLATION_NOT_PROVIDER_STOP"
    finally:
        stage["observation"] = remove_observer(js)


def reopen_cancel(ui, read, js, wait, screenshot, document, stage):
    install_observer(js, stage["questions"], include_cancel=True)
    try:
        scope = open_material(ui, wait, document)
        ui.click_revealed("恢复最近同版本材料请求", scope)
        wait("return " + node(scope) + ".textContent.includes('原请求历史回执已读回；没有再次推理。')")
        # The UI must restore this cancelled request, not a prior successful
        # request for the same document/version. A separate Core read is weaker.
        request = stage["purposes"]["material"]["preview"]["plan"]["request"]
        restored = js("const s=" + node(scope) + ";return {question:s.querySelector('label:has(input) input')?.value,inputs:Array.from(s.querySelectorAll('input')).map(x=>x.value),lane:s.querySelector('select')?.value,hasAnswer:Array.from(s.querySelectorAll('p[style]')).some(x=>x.textContent.trim())}")
        assert restored["inputs"] == [request["question"], request["purpose"]] and restored["lane"] == "deep" and not restored["hasAnswer"], "UI restored a different material request"
        stage["cold_reopen_material_ui"] = restored
        for purpose, item in stage["purposes"].items():
            op = "material_question_status" if purpose == "material" else "conversation_status"
            assert read(op, {"body": item["identity"]}) == item["receipt"]
            assert_cancelled_receipt(item["receipt"], item["preview"], purpose)
        screenshot("cancel-material-cold-reopen.png")
        ui.page("14")
        scope = "//section[@aria-label='正式陪伴会话' and not(ancestor-or-self::*[@hidden])]"
        sid = stage["purposes"]["companion"]["identity"]["session_id"]
        selector = scope + "//label[contains(.,'已保存会话')]/select"
        ui.reveal_selector(selector); ui.click_selector(selector + "/option[@value=" + literal(sid) + "]")
        wait("return " + node(scope) + ".textContent.includes('当前会话：')")
        ui.click_revealed("重读历史", scope)
        wait("return !!" + node(scope) + ".querySelector('.xiaoqi-avatar[data-visible-state=\"interrupted\"]')")
        history = read("conversation_history", {"body": {"session_id": sid, "after_sequence": 0, "limit": 64}})
        assert history == stage["purposes"]["companion"]["history"]
        screenshot("cancel-companion-cold-reopen.png")
        assert_calls(proof(js), [])
        stage["cold_reopen"] = {"status": "PASS", "receipts_unchanged": True, "observed_after_attach_execution_calls": 0, "startup_execution_calls": "UNVERIFIED"}
    finally:
        stage["cold_reopen_observation"] = remove_observer(js)
