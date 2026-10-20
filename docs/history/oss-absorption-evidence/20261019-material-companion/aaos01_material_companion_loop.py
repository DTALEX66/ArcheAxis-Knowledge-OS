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


def install_observer(js, questions):
    js("""if(window.__aaosMC)throw Error('Observer already installed');
const original=window.__TAURI__,invoke=original.core.invoke,questions=""" + json.dumps(questions) + """;
const proof={rows:[],overflow:false};window.__aaosMC={original,proof};
const observed=async function(command,args,...rest){
 const op=args?.request?.operation,body=args?.request?.payload?.body;
 const tracked=command==='core_command'&&['material_question','conversation_request'].includes(op);
 let row;if(tracked){row={operation:op,preview:body?.preview===true,request_id:body?.request_id??null,session_id:body?.session_id??null,own:body?.question===questions[op],completed:false};
 if(proof.rows.length>=128)proof.overflow=true;else proof.rows.push(row);
 if(row.own)row.request=JSON.parse(JSON.stringify(body));}
 try{const value=await Reflect.apply(invoke,original.core,[command,args,...rest]);
 if(row){row.status=value.status;if(row.own&&row.preview&&value.status===200)row.preview_response=JSON.parse(JSON.stringify(value.body));}return value;
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
        wait("return " + node(scope) + ".textContent.includes('回执与历史已读回；回答仍需你判断。')", seconds=150)
        expected.append(("conversation_request", False)); assert_calls(proof(js), expected)
        assert proof(js)["rows"][-1]["request"] == {**request, "preview": False, "confirmed_plan_sha256": preview["plan_sha256"]}
        stage["receipts"] = read_receipts(read, stage)
        for purpose in ("material", "companion"):
            assert_bound_receipt(stage["receipts"][purpose], stage[purpose + "_preview"], stage["resolved"][purpose], purpose)
        visible_answer(wait, scope, stage["receipts"]["companion"]["answer"]["answer"])
        screenshot("material-companion-completed.png")
        scope = open_material(ui, wait, document)
        visible_answer(wait, scope, stage["receipts"]["material"]["answer"]["answer"])
        screenshot("material-completed.png")
        stage["status"] = "PASS_REAL_MODEL_SYNTHETIC_MATERIAL_NOT_QUALITY_QUALIFICATION"
    finally:
        stage["observed_calls"] = remove_observer(js)


def reopen(ui, read, js, wait, screenshot, document, stage, phase):
    install_observer(js, stage["questions"])
    try:
        scope = open_material(ui, wait, document)
        ui.click_revealed("恢复最近同版本材料请求", scope)
        wait("return " + node(scope) + ".textContent.includes('原请求历史回执已读回；没有再次推理。')")
        visible_answer(wait, scope, stage["receipts"]["material"]["answer"]["answer"])
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
        visible_answer(wait, scope, stage["receipts"]["companion"]["answer"]["answer"])
        assert read_receipts(read, stage) == stage["receipts"], "Persisted original results changed across reopen"
        screenshot("companion-" + phase + ".png")
        assert_calls(proof(js), [])
        stage[phase] = {"status": "PASS", "original_receipts_unchanged": True, "observed_after_attach_ui_execution_calls": 0, "startup_execution_calls": "UNVERIFIED"}
    finally:
        stage[phase + "_observation"] = remove_observer(js)
