import { useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { ContextConsumptionDto, MachineTaskRowDto, MachineTasksPageDto } from "../api/generated/core-contract";
import { assertAiAssetDto, type AssetPacketRequest, type MachineAssetContext } from "../api/generated/ai-asset-contract";
import { sameAssetPin } from "../presentation/assetConsumption";
import { ApiError } from "../api/client";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { RawReceiptButton } from "./DiagnosticConsole";

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid response");
  return value as Record<string, unknown>;
}

function canonical(value: unknown): string {
  return JSON.stringify(value, (_key, item: unknown) => item && typeof item === "object" && !Array.isArray(item)
    ? Object.fromEntries(Object.entries(item as Record<string,unknown>).sort(([a],[b]) => a.localeCompare(b))) : item);
}

type ReviewAction = "accepted" | "rejected" | "deprecated";

export function MachineAnswerPanel({ knowledgeId, contextGrant, retestContextGrant, scoped = false, assetContextGrant, retestAssetContextGrant, assetScoped=false, retestAssetScoped=false, onTask, onCandidate }: {
  knowledgeId: string; contextGrant?: ContextConsumptionDto; retestContextGrant?: ContextConsumptionDto;
  scoped?: boolean; assetContextGrant?:AssetPacketRequest; retestAssetContextGrant?:AssetPacketRequest; assetScoped?:boolean; retestAssetScoped?:boolean; onTask?: (id: string) => void; onCandidate?: (id: string) => void;
}) {
  const answerScoped=scoped||assetScoped||!!assetContextGrant;
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Record<string, unknown> | null>(null);
  const [task, setTask] = useState<unknown>(null);
  const [corrected, setCorrected] = useState("");
  const [note, setNote] = useState("");
  const [correctionAuthor, setCorrectionAuthor] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [correction, setCorrection] = useState<Record<string, unknown> | null>(null);
  const [candidate, setCandidate] = useState<Record<string, unknown> | null>(null);
  const [retest, setRetest] = useState<Record<string, unknown> | null>(null);
  const [retestTask, setRetestTask] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const alive = useRef(true);
  const epoch = useRef(0);
  const [history, setHistory] = useState<MachineTaskRowDto[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const [withheld, setWithheld] = useState(false);
  const frozenAnswer = useRef<Record<string, unknown> | null>(null);
  const frozenRetest = useRef<Record<string, unknown> | null>(null);
  const dirtyOwner = useId(); const savedReview = useRef("");
  const requestLive = (generation: number) => alive.current && epoch.current === generation;

  useEffect(() => {
    alive.current = true; epoch.current += 1;
    frozenAnswer.current = null; frozenRetest.current = null; savedReview.current = "";
    setAnswer(null); setTask(null); setCorrection(null); setCandidate(null); setRetest(null); setRetestTask(null);
    setQuestion(""); setCorrected(""); setNote(""); setReviewNote(""); setReviewer(""); setCorrectionAuthor("");
    setHistory([]); setCursor(null); setBusy(false); setUncertain(false); setWithheld(false); setMessage("");
    return () => { alive.current = false; epoch.current += 1; window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:dirtyOwner,dirty:false}})); };
  }, [knowledgeId]);
  function downstreamDirty() {
    return corrected.trim() !== String(correction?.corrected_answer ?? "") || note.trim() !== String(correction?.error_note ?? "")
      || correctionAuthor.trim() !== String(correction?.reviewer ?? "")
      || canonical([reviewer.trim(),reviewNote.trim()]) !== (savedReview.current || canonical([String(correction?.reviewer ?? ""),""]));
  }
  useEffect(() => {
    const dirty = busy || uncertain || !!frozenRetest.current || question.trim() !== String(answer?.question ?? "") || downstreamDirty();
    window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:dirtyOwner,dirty}}));
  },[busy,uncertain,question,corrected,note,correctionAuthor,reviewer,reviewNote,answer,correction,dirtyOwner]);

  function validateAnswer(value: Record<string, unknown>, id: string, expectedQuestion?: string) {
    const body = record(value.answer);
    if (value.schema !== "archeaxis.machine-answer/v1" || value.knowledge_id !== id
      || typeof value.answer_id !== "string" || !value.answer_id || typeof value.question !== "string"
      || !value.question.trim() || (expectedQuestion !== undefined && value.question !== expectedQuestion)
      || typeof body.answer !== "string" || !body.answer.trim() || typeof body.model !== "string" || !body.model
      || value.authority !== "candidate") throw new Error("answer identity mismatch");
  }

  function validateTask(proof: Record<string, unknown>, response: Record<string, unknown>, scope: string, taskId: string) {
    const stored = record(JSON.parse(String(proof.conditions)));
    if (proof.task_id !== taskId || proof.scope !== scope || proof.outcome !== "unmeasured"
      || proof.model_version !== record(response.answer).model || typeof proof.knowledge_version !== "string"
      || !proof.knowledge_version.startsWith(String(response.knowledge_id) + "@")
      || stored.schema !== response.schema || stored.answer_id !== response.answer_id
      || stored.knowledge_id !== response.knowledge_id || stored.question !== response.question
      || canonical(stored.answer) !== canonical(response.answer)
      || stored.authority !== "candidate" || (record(response.request??{}).asset_context!==undefined && canonical(stored.request)!==canonical(response.request))) throw new Error("task identity mismatch");
    if (scope === "runtime.retest" && (proof.retest_of !== response.retest_of
      || stored.retest_task_id !== response.retest_task_id || stored.retest_of !== response.retest_of
      || canonical(stored.request) !== canonical(response.request) || (record(response.execution_request??{}).asset_context!==undefined&&canonical(stored.execution_request)!==canonical(response.execution_request)))) throw new Error("retest binding mismatch");
    return stored;
  }

  function validateAssetContext(value:unknown,expected:AssetPacketRequest){const actual=assertAiAssetDto<MachineAssetContext>("MachineAssetContext",value);if(!sameAssetPin(actual.asset,expected.asset)||!sameAssetPin(actual.grant,expected.grant)||actual.consumer!==expected.consumer||actual.operation!==expected.operation)throw new Error("asset consumption receipt mismatch");}
  async function validateFrozenAnswer(response:Record<string,unknown>,request:Record<string,unknown>){
    validateAnswer(response,String(request.knowledge_id),String(request.question));
    if(request.client_request_id!==undefined||request.asset_context_grant!==undefined){
      if(typeof request.client_request_id!=="string")throw new Error("missing frozen answer request identity");
      const expected=(await documentRequestIdentity(request.client_request_id)).replace("doc_req_","answer_req_");
      const proof=record(response.request);
      if(response.answer_id!==expected||response.client_request_id!==request.client_request_id
        ||proof.schema!=="archeaxis.machine-answer-request/v1"||proof.knowledge_id!==request.knowledge_id
        ||proof.question!==request.question||proof.max_tokens!==request.max_tokens||proof.timeout_s!==request.timeout_s
        ||typeof proof.context_sha256!=="string"||!/^[a-f0-9]{64}$/.test(proof.context_sha256)
        ||canonical(proof.context_grant)!==canonical(request.context_grant))throw new Error("frozen answer identity mismatch");
      if(request.asset_context_grant!==undefined){
        if(canonical(proof.asset_context_grant)!==canonical(request.asset_context_grant)
          ||proof.asset_client_request_id!==request.client_request_id
          ||typeof proof.knowledge_context_sha256!=="string"||!/^[a-f0-9]{64}$/.test(proof.knowledge_context_sha256))throw new Error("frozen asset request mismatch");
        validateAssetContext(proof.asset_context,assertAiAssetDto<AssetPacketRequest>("AssetPacketRequest",request.asset_context_grant));
      }else if(proof.asset_context_grant!==undefined||proof.asset_context!==undefined)throw new Error("unexpected asset request");
    }
  }
  async function readHistory(more = false) {
    if (busy) return;
    const generation = epoch.current; setBusy(true);
    try {
      const page = await coreCommand<MachineTasksPageDto>("machine_tasks_list", {limit:20, ...(more && cursor ? {cursor} : {})});
      if (!Array.isArray(page.items) || (page.next_cursor !== null && typeof page.next_cursor !== "string")
        || (more && page.next_cursor !== null && page.next_cursor === cursor)) throw new Error("invalid history page");
      if (requestLive(generation)) { setHistory(previous => more ? [...previous, ...page.items.filter(row => !previous.some(p => p.task_id === row.task_id))] : page.items); setCursor(page.next_cursor); setMessage("仅读取既有任务；不会自动再次调用模型。"); }
    } catch { if (requestLive(generation)) setMessage("历史读取失败；当前内容保留，执行状态 UNKNOWN。"); }
    finally { if (requestLive(generation)) setBusy(false); }
  }

  async function restoreHistory(row: MachineTaskRowDto) {
    if (busy) return;
    const frozenMatch = frozenAnswer.current && (()=>{try {const doc=record(JSON.parse(row.conditions));return doc.client_request_id===frozenAnswer.current!.client_request_id && doc.question===question.trim();}catch{return false;}})();
    if (downstreamDirty() || frozenRetest.current || (question.trim() !== String(answer?.question ?? "") && !frozenMatch)) {
      setMessage("当前回答、纠正或审核草稿未保存；历史读取不会覆盖输入，请先提交或核对当前请求。"); return;
    }
    const generation = ++epoch.current; setBusy(true);
    try {
      const proof = record(await coreCommand("machine_task_get", {task_id:row.task_id}));
      if (proof.task_id !== row.task_id || proof.scope !== row.scope || proof.conditions !== row.conditions) throw new Error("history identity changed");
      const doc = record(JSON.parse(String(proof.conditions)));
      const evaluation = row.scope === "runtime.evaluation.failed" ? doc : row.scope === "runtime.retest" ? record(record(doc.prior).conditions) : null;
      const original = evaluation ?? doc;
      validateAnswer(original, knowledgeId);
      if(frozenAnswer.current)await validateFrozenAnswer(original,frozenAnswer.current);
      if(record(original.request??{}).asset_context!==undefined)assertAiAssetDto<MachineAssetContext>("MachineAssetContext",record(original.request).asset_context);
      if(row.scope==="runtime.retest"&&record(doc.execution_request??{}).asset_context!==undefined)assertAiAssetDto<MachineAssetContext>("MachineAssetContext",record(doc.execution_request).asset_context);
      const originalTask = record(await coreCommand("machine_task_get", {task_id:original.answer_id}));
      validateTask(originalTask, original, "runtime.answer", String(original.answer_id));
      let correctionValue: Record<string,unknown> | null = null;
      let candidateValue: Record<string,unknown> | null = null;
      if (evaluation) {
        correctionValue = record(evaluation.correction);
        if (correctionValue.answer_id !== original.answer_id || correctionValue.corrects_knowledge_id !== knowledgeId
          || correctionValue.question !== original.question || correctionValue.machine_answer !== record(original.answer).answer
          || typeof correctionValue.corrected_answer !== "string" || typeof correctionValue.correction_candidate_id !== "string"
          || correctionValue.failed_task_id !== `evaluation_${String(original.answer_id)}`) throw new Error("correction history mismatch");
        const failed = record(await coreCommand("machine_task_get", {task_id:correctionValue.failed_task_id}));
        if (failed.scope !== "runtime.evaluation.failed" || failed.outcome !== "failed"
          || canonical(record(JSON.parse(String(failed.conditions))).correction) !== canonical(correctionValue)) throw new Error("evaluation readback mismatch");
        candidateValue = await readCandidate(correctionValue.correction_candidate_id);
        if (candidateValue.body !== correctionValue.corrected_answer) throw new Error("candidate history mismatch");
      }
      if (row.scope === "runtime.retest") validateTask(proof, doc, "runtime.retest", row.task_id);
      else if (row.scope !== "runtime.answer" && row.scope !== "runtime.evaluation.failed") throw new Error("not a learning history task");
      if (!requestLive(generation)) return;
      setAnswer(original); setTask(originalTask); setQuestion(String(original.question));
      setCorrection(correctionValue); setCandidate(candidateValue);
      if (candidateValue) onCandidate?.(String(candidateValue.knowledge_id));
      setCorrectionAuthor(correctionValue ? String(correctionValue.reviewer) : "");
      setReviewer(correctionValue ? String(correctionValue.reviewer) : ""); setReviewNote(""); savedReview.current="";
      setCorrected(correctionValue ? String(correctionValue.corrected_answer) : ""); setNote(correctionValue ? String(correctionValue.error_note) : "");
      setRetest(row.scope === "runtime.retest" ? doc : null); setRetestTask(row.scope === "runtime.retest" ? proof : null);
      frozenAnswer.current=null; setUncertain(false); onTask?.(String(original.answer_id)); setMessage("已从 Core 恢复固定回答与既有回执；历史记录不代表当前可消费资格或复测通过。");
    } catch { if (requestLive(generation)) {setUncertain(true); setMessage("历史身份或读回未确认，状态 UNKNOWN；不会自动重跑推理。");} }
    finally { if (requestLive(generation)) setBusy(false); }
  }

  async function readCandidate(id: string) {
    const value = record(await coreCommand("knowledge_get", { id }));
    if (value.knowledge_id !== id || typeof value.body !== "string" || typeof value.version !== "string" || !value.version
      || !["candidate", "accepted", "rejected", "deprecated"].includes(String(value.status))) {
      throw new Error("invalid correction candidate");
    }
    return value;
  }

  async function ask() {
    const generation = epoch.current;
    if (!question.trim() || busy || (uncertain && !frozenAnswer.current) || (answerScoped && !contextGrant && !frozenAnswer.current) || (assetScoped && !assetContextGrant && !frozenAnswer.current)) return;
    if (answer && (downstreamDirty() || frozenRetest.current)) {setMessage("纠正或审核草稿尚未确认，请先保存和核对后再发起新回答。");return;}
    const request = frozenAnswer.current ?? Object.freeze({knowledge_id:knowledgeId,question:question.trim(),max_tokens:2048,timeout_s:120,
      ...(contextGrant ? {context_grant:structuredClone(contextGrant)} : {}), ...(assetContextGrant ? {asset_context_grant:{...structuredClone(assetContextGrant),request_id:`assetanswer_${crypto.randomUUID()}`,consumer:"local-machine",operation:"answer"}} : {}), ...(answerScoped ? {client_request_id:`machine_${crypto.randomUUID()}`} : {})});
    if (answerScoped) frozenAnswer.current = request;
    setBusy(true); setAnswer(null); setTask(null); setCorrection(null); setCandidate(null); setRetest(null); setRetestTask(null);
    setCorrected(""); setNote(""); setReviewNote(""); setMessage("正在执行本地机器回答，等待真实回执…");
    try {
      const response = record(await coreCommand("machine_answer", { body: request }));
      await validateFrozenAnswer(response,request);
      const proof = record(await coreCommand("machine_task_get", { task_id: response.answer_id }));
      validateTask(proof, response, "runtime.answer", String(response.answer_id));
      if (requestLive(generation)) { frozenAnswer.current = null; setUncertain(false); setAnswer(response); setTask(proof); onTask?.(String(response.answer_id)); setMessage("本地回答已持久化读回；可能为同请求的历史重放。它仍是候选，不是已接受知识或能力评分。"); }
    } catch (reason) {
      if (requestLive(generation)) {
        if (reason instanceof ApiError && reason.execution) {frozenAnswer.current=null;setUncertain(true);setWithheld(true);setMessage(reason.execution.audit_status === "RECORDED" ? `推理已执行，答案未发布；脱敏审计 ${reason.execution.audit_task_id} 已保存。请核对授权与审计，不自动重跑。` : "推理已执行，答案未发布；持久化审计未确认。请保留草稿并检查 Core，不自动重跑。");}
        else if (reason instanceof ApiError && [400,403,404,422].includes(reason.status)) {frozenAnswer.current=null;setUncertain(false);setMessage("Core 明确拒绝此回答请求；请核对当前知识、用途或授权，原输入保留。");}
        else {setUncertain(true); setMessage("回答未完成或持久化读回未确认，状态 UNKNOWN。请读取历史核对；不会自动再次推理。");}
      }
    } finally { if (requestLive(generation)) setBusy(false); }
  }

  async function correct() {
    const generation = epoch.current;
    if (!answer || busy || !corrected.trim() || !note.trim() || !correctionAuthor.trim()) return;
    setBusy(true);
    try {
      const receipt = record(await coreCommand("machine_correction", { body: {
        answer_id: answer.answer_id, knowledge_id: knowledgeId, question: answer.question,
        machine_answer: record(answer.answer).answer, corrected_answer: corrected.trim(),
        error_note: note.trim(), reviewer: correctionAuthor.trim(),
      } }));
      if (receipt.answer_id !== answer.answer_id || receipt.status !== "candidate" || receipt.authority !== "candidate"
        || receipt.corrects_knowledge_id !== knowledgeId || receipt.question !== answer.question
        || receipt.machine_answer !== record(answer.answer).answer || receipt.corrected_answer !== corrected.trim()
        || receipt.error_note !== note.trim() || receipt.reviewer !== correctionAuthor.trim()
        || typeof receipt.correction_candidate_id !== "string" || typeof receipt.failed_task_id !== "string") throw new Error("invalid correction receipt");
      if (!requestLive(generation)) return;
      setCorrection(receipt);
      const value = await readCandidate(receipt.correction_candidate_id);
      if (value.body !== receipt.corrected_answer || value.status !== "candidate") throw new Error("candidate readback does not match correction receipt");
      if (requestLive(generation)) { setCandidate(value); onCandidate?.(String(value.knowledge_id)); setReviewer(correctionAuthor.trim()); setMessage("纠正已保存为候选；审核尚未发生，候选正文、来源范围和机器回答可供对照。"); }
    } catch {
      if (requestLive(generation)) setMessage("纠正已提交或候选读回未确认。请保留填写内容并读取 Core 回执核对状态。");
    } finally { if (requestLive(generation)) setBusy(false); }
  }

  async function reviewCorrection(action: ReviewAction) {
    const generation = epoch.current;
    if (!candidate || busy || !reviewer.trim() || !reviewNote.trim()) return;
    setBusy(true);
    try {
      const id = String(candidate.knowledge_id);
      const receipt = record(await coreCommand("knowledge_review", { id, body: {
        action, reviewer: reviewer.trim(), note: reviewNote.trim(), expected_version: candidate.version,
      } }));
      if (receipt.knowledge_id !== id || typeof receipt.version !== "string") throw new Error("review identity mismatch");
      const latest = await readCandidate(id);
      if (latest.status !== action || latest.version !== receipt.version || latest.body !== candidate.body) throw new Error("review status readback mismatch");
      if (requestLive(generation)) {
        savedReview.current=canonical([reviewer.trim(),reviewNote.trim()]);
        setCandidate(latest);
        onCandidate?.(String(latest.knowledge_id));
        setMessage(action === "accepted" ? "Core 已接受此纠正知识。独立复测尚未执行，不能据此宣称机器改进。"
          : action === "rejected" ? "Core 已拒绝此纠正候选；机器回答和审核记录仍保留。"
          : "Core 已将此纠正标记为弃用；候选、来源和复测证据仍保留。" );
      }
    } catch {
      if (requestLive(generation)) setMessage("纠正审核未完成，可能版本已变化。保留审核备注并重新读取候选后再决定。");
    } finally { if (requestLive(generation)) setBusy(false); }
  }

  async function reloadCandidate() {
    const generation = epoch.current;
    const id = candidate?.knowledge_id ?? correction?.correction_candidate_id;
    if (typeof id !== "string" || busy) return;
    setBusy(true);
    try {
      const value = await readCandidate(id);
      if (correction && value.body !== correction.corrected_answer) throw new Error("candidate receipt mismatch");
      if (requestLive(generation)) { setCandidate(value); onCandidate?.(String(value.knowledge_id)); setMessage("已重新读取 Core 当前候选与版本。"); }
    }
    catch { if (requestLive(generation)) setMessage("候选重新读取失败；当前对照仍保留，审核操作已暂停。"); }
    finally { if (requestLive(generation)) setBusy(false); }
  }

  async function runIndependentRetest() {
    const generation = epoch.current;
    if (!answer || !correction || !candidate || candidate.status !== "accepted" || retest || busy || ((scoped||retestAssetScoped||!!retestAssetContextGrant||record(answer.request??{}).asset_context!==undefined) && !retestContextGrant && !frozenRetest.current) || ((retestAssetScoped || record(answer.request??{}).asset_context!==undefined) && !retestAssetContextGrant && !frozenRetest.current)) return;
    const failedTaskId = correction.failed_task_id;
    const candidateId = String(candidate.knowledge_id);
    const originalQuestion = String(answer.question);
    const request = frozenRetest.current ?? { retest_of: failedTaskId, knowledge_id: candidateId, question: originalQuestion, max_tokens: 2048, timeout_s: 120, ...(retestContextGrant ? {context_grant:structuredClone(retestContextGrant)} : {}), ...(retestAssetContextGrant ? {asset_context_grant:{...structuredClone(retestAssetContextGrant),request_id:`assetretest_${crypto.randomUUID()}`,consumer:"local-machine",operation:"retest"}} : {}) };
    frozenRetest.current=request;
    setBusy(true); setMessage("正在以已审核纠正知识重答原问题；Core 回执与任务读回确认前不显示为完成…");
    try {
      const response = record(await coreCommand("machine_retest", { body: request }));
      const machine = record(response.answer);
      if (response.schema !== "archeaxis.machine-retest/v1" || response.retest_of !== failedTaskId
        || response.knowledge_id !== candidateId || response.question !== originalQuestion
        || response.authority !== "candidate" || typeof response.retest_task_id !== "string"
        || typeof machine.answer !== "string" || !machine.answer.trim()) throw new Error("invalid retest receipt");
      if (canonical(response.request) !== canonical({retest_of:request.retest_of,knowledge_id:request.knowledge_id,question:request.question,max_tokens:request.max_tokens,...(request.context_grant ? {context_grant:request.context_grant} : {}),...(request.asset_context_grant ? {asset_context_grant:request.asset_context_grant} : {})})) throw new Error("retest request mismatch");
      if(request.asset_context_grant){const execution=record(response.execution_request);if(execution.schema!=="archeaxis.machine-retest-execution/v1"||execution.timeout_s!==request.timeout_s||canonical(execution.request)!==canonical(response.request)||typeof execution.context_sha256!=="string"||!/^[a-f0-9]{64}$/.test(execution.context_sha256)||typeof execution.knowledge_context_sha256!=="string"||!/^[a-f0-9]{64}$/.test(execution.knowledge_context_sha256))throw new Error("retest execution budget or context mismatch");validateAssetContext(execution.asset_context,assertAiAssetDto<AssetPacketRequest>("AssetPacketRequest",request.asset_context_grant));}
      const proof = record(await coreCommand("machine_task_get", { task_id: response.retest_task_id }));
      validateTask(proof, response, "runtime.retest", String(response.retest_task_id));
      if (requestLive(generation)) {
        setRetest(response); setRetestTask(proof);
        frozenRetest.current=null;
        onTask?.(String(response.retest_task_id));
        setMessage("Core 独立复测回执与持久化任务读回一致；复测结果仍是未测评候选，请真人对照两次回答。没有自动判定改进。");
      }
    } catch (reason) {
      if (requestLive(generation)) {
        if (reason instanceof ApiError && reason.execution) {frozenRetest.current=null;setUncertain(true);setWithheld(true);setMessage(reason.execution.audit_status === "RECORDED" ? `复测推理已执行，答案未发布；脱敏审计 ${reason.execution.audit_task_id} 已保存，不自动重跑。` : "复测推理已执行，答案未发布；审计持久化未确认，不自动重跑。");}
        else if (reason instanceof ApiError && [400,403,404,422].includes(reason.status)) {frozenRetest.current=null;setMessage("Core 明确拒绝复测请求；原回答与纠正仍保留，请核对当前授权。");}
        else setMessage("复测未完成或持久化读回未确认。保留纠正与原失败回执；重试保持同一冻结请求，不能据此宣称完成。");
      }
    } finally { if (requestLive(generation)) setBusy(false); }
  }

  return <section aria-label="知识到机器回答" className="ui-machine-answer">
    {withheld ? <button disabled={busy} onClick={()=>{setWithheld(false);setUncertain(false);setMessage("已结束此未发布请求，问题与纠正草稿保留。再次执行将是新的明确操作，请先核对授权。");}}>结束已执行但未发布的请求，保留草稿</button> : null}
    <h4>既有机器学习回执</h4>
    <button disabled={busy} onClick={() => void readHistory()}>读取机器学习历史</button>
    <ul aria-label="既有机器学习任务">{history.filter(row => ["runtime.answer","runtime.evaluation.failed","runtime.retest"].includes(row.scope)).map(row => <li key={row.task_id}><span>{row.task_id} · {row.scope} · {row.outcome}</span><button disabled={busy} onClick={() => void restoreHistory(row)}>读取此任务旅程 {row.task_id}</button></li>)}</ul>
    {cursor ? <button disabled={busy} onClick={() => void readHistory(true)}>读取更多任务</button> : null}
    {uncertain ? <p>执行状态 UNKNOWN；先核对既有历史，避免重复调用。</p> : null}
    <h4>基于当前知识的本地回答</h4>
    <label>实际问题 <textarea value={question} disabled={busy} onChange={event => setQuestion(event.target.value)} /></label>
    {answerScoped && !contextGrant ? <p>请先选择已保存、允许回答的上下文授权。</p> : null}
    <button disabled={busy || (uncertain && !frozenAnswer.current) || !question.trim() || (answerScoped && !contextGrant && !frozenAnswer.current) || (assetScoped && !assetContextGrant && !frozenAnswer.current)} onClick={() => void ask()}>{frozenAnswer.current ? "重试同一回答请求" : "执行本地机器回答"}</button>
    {assetScoped&&!assetContextGrant?<p>选中的资产授权已失效或未确认；新执行暂停，原历史保留。</p>:null}
    {message ? <p role="status">{message}</p> : null}
    {answer ? <>
      <h4>机器回答候选</h4><pre aria-label="真实机器回答">{String(record(answer.answer).answer)}</pre>
      <p>机器回答未被接受为知识。保存错误纠正不会自行改变已接受知识，也不会证明机器改进。</p>
      <RawReceiptButton label="持久化任务与模型回执" payload={task} />
      <p>若你实际发现错误，可记录具体更正；没有错误无需提交。</p>
      <label>正确答案 <textarea value={corrected} disabled={busy} onChange={event => setCorrected(event.target.value)} /></label>
      <label>具体错误依据 <textarea value={note} disabled={busy} onChange={event => setNote(event.target.value)} /></label>
      <label>纠正提交者 <input value={correctionAuthor} disabled={busy} onChange={event => setCorrectionAuthor(event.target.value)} /></label>
      <button disabled={busy || !corrected.trim() || !note.trim() || !correctionAuthor.trim()} onClick={() => void correct()}>记录使用者纠正候选</button>
      {correction ? <>
        <h4>纠正对照与范围</h4>
        <dl><div><dt>纠正候选 ID</dt><dd>{String(correction.correction_candidate_id)}</dd></div>
          <div><dt>绑定知识</dt><dd>{String(correction.corrects_knowledge_id)}</dd></div>
          <div><dt>纠正候选修订</dt><dd>{candidate ? String(candidate.version) : "Core 候选读回未确认"}</dd></div>
          <div><dt>本题</dt><dd>{String(correction.question)}</dd></div>
          <div><dt>原机器回答</dt><dd>{String(correction.machine_answer)}</dd></div>
          <div><dt>使用者纠正</dt><dd>{String(correction.corrected_answer)}</dd></div>
          <div><dt>Core 候选正文读回</dt><dd>{candidate ? String(candidate.body) : "未确认；审核操作不可用"}</dd></div>
          <div><dt>错误依据</dt><dd>{String(correction.error_note)}</dd></div>
          <div><dt>状态</dt><dd>{candidate ? String(candidate.status) : "候选读回未确认"}</dd></div>
        </dl>
        <RawReceiptButton label="机器纠正候选回执" payload={correction} />
        {!candidate ? <button disabled={busy} onClick={() => void reloadCandidate()}>重新读取纠正候选</button> : null}
      </> : null}
      {candidate ? <section aria-label="纠正候选审核">
        <h4>真人审核与决定</h4>
        <label>审核者 <input value={reviewer} disabled={busy} onChange={event => setReviewer(event.target.value)} /></label>
        <label>审核依据 <textarea value={reviewNote} disabled={busy} onChange={event => setReviewNote(event.target.value)} /></label>
        <button disabled={busy || candidate.status !== "candidate" || !reviewer.trim() || !reviewNote.trim()} onClick={() => void reviewCorrection("accepted")}>接受纠正知识</button>
        <button disabled={busy || candidate.status !== "candidate" || !reviewer.trim() || !reviewNote.trim()} onClick={() => void reviewCorrection("rejected")}>拒绝纠正候选</button>
        <button disabled={busy} onClick={() => void reloadCandidate()}>重新读取审核版本</button>
        <button disabled={busy || candidate.status !== "accepted" || !reviewer.trim() || !reviewNote.trim()} onClick={() => void reviewCorrection("deprecated")}>撤回已接受纠正（标记为弃用）</button>
        {candidate.status === "accepted" ? <>
          <p>已审核知识可用于重答原问题。Core 会校验先前失败任务和知识修订 lineage；接受知识本身不等同复测通过。</p>
          {scoped && !retestContextGrant ? <p>请先为已接受的纠正知识保存并选择独立复测授权。</p> : null}
          <button disabled={busy || withheld || Boolean(retest) || ((scoped||retestAssetScoped||!!retestAssetContextGrant||record(answer.request??{}).asset_context!==undefined) && !retestContextGrant && !frozenRetest.current) || ((retestAssetScoped || record(answer.request??{}).asset_context!==undefined) && !retestAssetContextGrant && !frozenRetest.current)} onClick={() => void runIndependentRetest()}>{retest ? "独立复测已记录" : frozenRetest.current ? "重试同一冻结复测请求" : "以已接受纠正知识运行独立复测"}</button>
        </> : null}
          {retest ? <section aria-label="独立复测结果对照">
            <h4>独立复测结果对照</h4>
            <dl><div><dt>复测任务</dt><dd>{String(retest.retest_task_id)}</dd></div><div><dt>绑定失败任务</dt><dd>{String(retest.retest_of)}</dd></div><div><dt>作答知识 ID</dt><dd>{String(retest.knowledge_id)}</dd></div><div><dt>候选审核读回版本</dt><dd>{String(candidate.version)}</dd></div><div><dt>评价状态</dt><dd>未测评；等待真人比较</dd></div></dl>
            <h5>原机器回答（失败样本）</h5><pre>{String(record(answer.answer).answer)}</pre>
            <h5>纠正后复测回答（候选）</h5><pre aria-label="独立复测机器回答">{String(record(retest.answer).answer)}</pre>
            <p>Core 仅记录独立复测及其失败任务绑定，不自动推断纠正有效；真人比较结果尚未记录。</p>
            <RawReceiptButton label="复测任务持久化回执" payload={retestTask} />
            <RawReceiptButton label="机器复测回执" payload={retest} />
          </section> : null}
      </section> : null}
    </> : null}
  </section>;
}
