import { resolveProductModel } from "../runtime/modelBinding";
import type { ModelLane } from "../api/generated/model-configuration-contract";
import { useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { ContextConsumptionDto, MachineTaskRowDto, MachineTasksPageDto, MachineConfigurationDto, MachineInventoryDto, MachineJournalStatusDto, MachineCancelDto } from "../api/generated/core-contract";
import { assertAiAssetDto, type AssetPacketRequest, type MachineAssetContext } from "../api/generated/ai-asset-contract";
import { sameAssetPin } from "../presentation/assetConsumption";
import { ApiError, type MachineAdmissionRefusal } from "../api/client";
import { readMachineAdmissionRefusal } from "../api/machineAdmission";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { RawReceiptButton } from "./DiagnosticConsole";
import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import type { PendingMachine } from "../presentation/coreWorkingState";

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid response");
  return value as Record<string, unknown>;
}

function canonical(value: unknown): string {
  return JSON.stringify(value, (_key, item: unknown) => item && typeof item === "object" && !Array.isArray(item)
    ? Object.fromEntries(Object.entries(item as Record<string,unknown>).sort(([a],[b]) => a<b?-1:a>b?1:0)) : item);
}

async function frozenFingerprint(entry: PendingMachine): Promise<string> {
  const body=entry.body;
  const request={knowledge_id:body.knowledge_id,question:body.question,max_tokens:body.max_tokens,timeout_s:body.timeout_s,
    context_grant:body.context_grant??null,asset_context_grant:body.asset_context_grant??null,
    client_request_id:entry.operation==="answer"?body.client_request_id??null:null,
    retest_of:entry.operation==="retest"?body.retest_of??null:null,...(body.model===undefined?{}:{model:body.model}),...(body.model_configuration===undefined?{}:{model_configuration:body.model_configuration})};
  const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(canonical({operation:entry.operation,request})));
  return Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,"0")).join("");
}

type ReviewAction = "accepted" | "rejected" | "deprecated";

export function MachineAnswerPanel({ knowledgeId, contextGrant, retestContextGrant, scoped = false, assetContextGrant, retestAssetContextGrant, assetScoped=false, retestAssetScoped=false, onTask, onCandidate }: {
  knowledgeId: string; contextGrant?: ContextConsumptionDto; retestContextGrant?: ContextConsumptionDto;
  scoped?: boolean; assetContextGrant?:AssetPacketRequest; retestAssetContextGrant?:AssetPacketRequest; assetScoped?:boolean; retestAssetScoped?:boolean; onTask?: (id: string) => void; onCandidate?: (id: string) => void;
}) {
  const answerScoped=scoped||assetScoped||!!assetContextGrant;
  const working=useOptionalCoreWorkingState();
  const pendingAnswer=useRef<PendingMachine|null>(null);
  const pendingRetest=useRef<PendingMachine|null>(null);
  const [restoredPending,setRestoredPending]=useState(false);
  const [withheldAudit,setWithheldAudit]=useState<{taskId:string;entry:PendingMachine;failed?:true}|null>(null);
  const [selectedJournal,setSelectedJournal]=useState("");
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
  const [modelConfiguration, setModelConfiguration] = useState<MachineConfigurationDto|null>(null);
  const [inventory, setInventory] = useState<MachineInventoryDto|null>(null);
  const [inventoryBusy, setInventoryBusy] = useState(false);
  const [lane,setLane]=useState<ModelLane>("fast");
  const [selectedModel, setSelectedModel] = useState("");
  const [maxTokens, setMaxTokens] = useState<2048|4096>(2048);
  const inventoryPending = useRef(false);
  const alive = useRef(true);
  const epoch = useRef(0);
  const [history, setHistory] = useState<MachineTaskRowDto[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const [withheld, setWithheld] = useState(false);
  const [admissionRefusal,setAdmissionRefusal]=useState<MachineAdmissionRefusal|null>(null);
  const [retestFailure,setRetestFailure]=useState<{phase:string;status:number|null;code:string;reason_code?:string;diagnostics?:Record<string,unknown>}|null>(null);
  const [answerFailure,setAnswerFailure]=useState<ApiError["machineFailure"]|null>(null);
  const frozenAnswer = useRef<Record<string, unknown> | null>(null);
  const frozenRetest = useRef<Record<string, unknown> | null>(null);
  const dirtyOwner = useId(); const savedReview = useRef("");
  const requestLive = (generation: number) => alive.current && epoch.current === generation;

  useEffect(() => {
    alive.current = true; epoch.current += 1;
    frozenAnswer.current = null; frozenRetest.current = null; savedReview.current = "";
    pendingAnswer.current=null;pendingRetest.current=null;setRestoredPending(false);setWithheldAudit(null);setSelectedJournal("");
    setRetestFailure(null);
    setAnswerFailure(null);
    inventoryPending.current = false; setInventoryBusy(false); setInventory(null); setModelConfiguration(null); setSelectedModel(""); setMaxTokens(2048);
    setAnswer(null); setTask(null); setCorrection(null); setCandidate(null); setRetest(null); setRetestTask(null);
    setQuestion(""); setCorrected(""); setNote(""); setReviewNote(""); setReviewer(""); setCorrectionAuthor("");
    setHistory([]); setCursor(null); setBusy(false); setUncertain(false); setWithheld(false); setAdmissionRefusal(null); setMessage("");
    return () => { alive.current = false; epoch.current += 1; window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:dirtyOwner,dirty:false}})); };
  }, [knowledgeId]);
  useEffect(()=>{
    if(!working||working.status!=="ready"||pendingAnswer.current||pendingRetest.current)return;
    const entries=Object.values(working.state.pending_machine??{}).filter(e=>e.owner_knowledge_id===knowledgeId);
    if(entries.length>1){setUncertain(true);setRestoredPending(true);setMessage("当前知识有多条未确认机器请求；请读取历史核对，暂不启动新的推理。");return;}
    if(entries.length!==1)return;
    const entry=entries[0];
    if(entry.operation==="answer"){pendingAnswer.current=structuredClone(entry);frozenAnswer.current=Object.freeze(structuredClone(entry.body));}
    else {pendingRetest.current=structuredClone(entry);frozenRetest.current=Object.freeze(structuredClone(entry.body));}
    setQuestion(entry.body.question);setSelectedModel(entry.body.model??"");setMaxTokens(entry.body.max_tokens===4096?4096:2048);
    setUncertain(true);setRestoredPending(true);setMessage("已恢复未确认的机器请求；仅保留身份与输入。请读取历史核对，不自动推理或替换授权。");
  },[knowledgeId,working?.status,working?.state.pending_machine]);
  useEffect(()=>{
    if(!working||working.status!=="ready"||busy)return;
    const entries=Object.values(working.state.pending_machine??{}).filter(entry=>entry.owner_knowledge_id===knowledgeId);
    if(pendingAnswer.current&&!entries.some(entry=>entry.journal_id===pendingAnswer.current?.journal_id)){pendingAnswer.current=null;frozenAnswer.current=null;}
    if(pendingRetest.current&&!entries.some(entry=>entry.journal_id===pendingRetest.current?.journal_id)){pendingRetest.current=null;frozenRetest.current=null;}
    if(entries.length===1&&!pendingAnswer.current&&!pendingRetest.current&&restoredPending){
      const entry=entries[0];
      if(entry.operation==="answer"){pendingAnswer.current=structuredClone(entry);frozenAnswer.current=structuredClone(entry.body);}
      else {pendingRetest.current=structuredClone(entry);frozenRetest.current=structuredClone(entry.body);}
      setQuestion(String(entry.body.question));setSelectedModel(String(entry.body.model??""));setMaxTokens(entry.body.max_tokens===4096?4096:2048);
    }
    if(selectedJournal&&!entries.some(entry=>entry.journal_id===selectedJournal))setSelectedJournal("");
    if(entries.length===0&&restoredPending&&!withheldAudit){
      pendingAnswer.current=null;pendingRetest.current=null;frozenAnswer.current=null;frozenRetest.current=null;
      setRestoredPending(false);setUncertain(false);setWithheld(false);
      setMessage("本地知识库已确认当前知识没有待核对的机器请求；问题与纠正草稿保留。");
    }
  },[working?.status,working?.state.pending_machine,knowledgeId,busy,restoredPending,selectedJournal,withheldAudit]);
  useEffect(()=>{
    if(!withheldAudit||!working||working.status!=="ready"||working.state.pending_machine?.[withheldAudit.entry.journal_id])return;
    if(pendingAnswer.current?.journal_id===withheldAudit.entry.journal_id){pendingAnswer.current=null;frozenAnswer.current=null;}
    if(pendingRetest.current?.journal_id===withheldAudit.entry.journal_id){pendingRetest.current=null;frozenRetest.current=null;}
    setWithheldAudit(null);setWithheld(false);setUncertain(false);
    setRestoredPending(Object.values(working.state.pending_machine??{}).some(entry=>entry.owner_knowledge_id===knowledgeId));
    setMessage("本地知识库已确认待核对记录结束；历史终态与执行屏障仍保留。");
  },[withheldAudit,working?.status,working?.state.pending_machine,knowledgeId]);
  async function readInventory() {
    if (inventoryPending.current || busy || uncertain || frozenRetest.current) return;
    const generation = epoch.current;
    inventoryPending.current = true; setInventoryBusy(true); setInventory(null);
    try {
      const value = await coreCommand<MachineInventoryDto>("machine_inventory");
      if (requestLive(generation)) { setInventory(value); if(value.status!=="READ_VERIFIED"||!value.model_choices?.includes(selectedModel))setSelectedModel(""); }
    } catch {
      if (requestLive(generation)) setInventory(null);
    } finally {
      if (requestLive(generation)) { inventoryPending.current = false; setInventoryBusy(false); }
    }
  }
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
        ||canonical(proof.context_grant)!==canonical(request.context_grant??null)
        ||canonical(proof.model_configuration??null)!==canonical(request.model_configuration??null)
        ||proof.model!==request.model || (request.model!==undefined&&(record(response.answer).model!==request.model||record(response.answer).requested_model!==request.model)))throw new Error("frozen answer identity mismatch");
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
    } catch { if (requestLive(generation)) setMessage("历史读取失败；当前内容保留，执行状态尚未确认。"); }
    finally { if (requestLive(generation)) setBusy(false); }
  }

  async function restoreHistory(row: MachineTaskRowDto) {
    if (busy) return;
    if(row.scope==="runtime.execution.withheld"){await inspectWithheld(row);return;}
    const frozenMatch = frozenAnswer.current && (()=>{try {const doc=record(JSON.parse(row.conditions));return doc.client_request_id===frozenAnswer.current!.client_request_id && doc.question===question.trim();}catch{return false;}})();
    const restoredRetestMatch=frozenRetest.current&&row.scope==="runtime.retest"&&(()=>{try{const doc=record(JSON.parse(row.conditions));return doc.retest_of===frozenRetest.current!.retest_of&&doc.knowledge_id===frozenRetest.current!.knowledge_id&&doc.question===frozenRetest.current!.question;}catch{return false;}})();
    const pendingHistory=restoredPending&&(()=>{try{const doc=record(JSON.parse(row.conditions));return pendingEntries().some(entry=>
      row.scope==="runtime.retest"?entry.operation==="retest"&&entry.body.retest_of===doc.retest_of&&entry.body.knowledge_id===doc.knowledge_id
      :entry.operation==="answer"&&entry.body.client_request_id===doc.client_request_id&&entry.body.knowledge_id===doc.knowledge_id);}catch{return false;}})();
    if (downstreamDirty() || (frozenRetest.current&&!restoredRetestMatch&&!pendingHistory) || (question.trim() !== String(answer?.question ?? "") && !frozenMatch&&!restoredRetestMatch&&!pendingHistory)) {
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
      let selected:PendingMachine|null=null;
      if(row.scope==="runtime.retest"){
        const request={...record(doc.request),timeout_s:record(doc.execution_request??{}).timeout_s};
        const candidates=await Promise.all(pendingEntries().filter(entry=>entry.operation==="retest").map(async entry=>
          await frozenFingerprint(entry)===await frozenFingerprint({...entry,body:request as PendingMachine["body"]})?entry:null));
        const matches=candidates.filter((entry):entry is PendingMachine=>entry!==null);
        if(matches.length>1)throw new Error("ambiguous frozen retest history");selected=matches[0]??null;
        if(frozenRetest.current&&await frozenFingerprint({journal_id:"comparison",owner_knowledge_id:knowledgeId,operation:"retest",origin_restore_epoch:"initial",body:frozenRetest.current as PendingMachine["body"]})!==await frozenFingerprint({journal_id:"comparison",owner_knowledge_id:knowledgeId,operation:"retest",origin_restore_epoch:"initial",body:request as PendingMachine["body"]}))throw new Error("frozen retest history mismatch");
      }else{
        const matches=pendingEntries().filter(entry=>entry.operation==="answer"&&entry.body.client_request_id===original.client_request_id);
        if(matches.length>1)throw new Error("ambiguous frozen answer history");selected=matches[0]??null;
        if(selected)await validateFrozenAnswer(original,selected.body);
        else if(frozenAnswer.current)await validateFrozenAnswer(original,frozenAnswer.current);
      }
      if(pendingHistory&&!selected)throw new Error("frozen history input mismatch");
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
      if(selected&&working){if(working.status!=="ready")throw new Error("working state unconfirmed");if(working.session.getSnapshot().state.pending_machine?.[selected.journal_id])await working.session.clearMachine(selected,selected.operation==="answer"?String(original.answer_id):row.task_id);
        if(requestLive(generation)){if(pendingAnswer.current?.journal_id===selected.journal_id){pendingAnswer.current=null;frozenAnswer.current=null;}if(pendingRetest.current?.journal_id===selected.journal_id){pendingRetest.current=null;frozenRetest.current=null;}}}
      if (!requestLive(generation)) return;
      setAnswer(original); setTask(originalTask); setQuestion(String(original.question));
      setMaxTokens(record(original.request??{}).max_tokens===4096?4096:2048);
      setCorrection(correctionValue); setCandidate(candidateValue);
      if (candidateValue) onCandidate?.(String(candidateValue.knowledge_id));
      setCorrectionAuthor(correctionValue ? String(correctionValue.reviewer) : "");
      setReviewer(correctionValue ? String(correctionValue.reviewer) : ""); setReviewNote(""); savedReview.current="";
      setCorrected(correctionValue ? String(correctionValue.corrected_answer) : ""); setNote(correctionValue ? String(correctionValue.error_note) : "");
      setRetest(row.scope === "runtime.retest" ? doc : null); setRetestTask(row.scope === "runtime.retest" ? proof : null);
      const remaining=hasPendingOwner();setRestoredPending(remaining);setUncertain(remaining);if(!remaining)frozenAnswer.current=null;
      onTask?.(row.scope === "runtime.retest" ? String(row.task_id) : String(original.answer_id)); setMessage("已从本地知识库恢复固定回答与既有回执；历史记录不代表当前可消费资格或复测通过。"+(remaining?"仍有其他未确认请求，请逐条核对。":""));
    } catch { if (requestLive(generation)) {setUncertain(true); setMessage("历史身份或读回未确认，状态尚未确认；不会自动重跑推理。");} }
    finally { if (requestLive(generation)) setBusy(false); }
  }

  function pendingEntries():PendingMachine[] {
    const entries=new Map<string,PendingMachine>();
    for(const entry of [pendingAnswer.current,pendingRetest.current,...Object.values(working?.session.getSnapshot().state.pending_machine??{})]){
      if(entry&&entry.owner_knowledge_id===knowledgeId)entries.set(entry.journal_id,entry);
    }
    return Array.from(entries.values()).filter(entry=>(working?.status!=="ready"||!!working.state.pending_machine?.[entry.journal_id])&&(!selectedJournal||entry.journal_id===selectedJournal));
  }
  function hasPendingOwner():boolean {
    return Object.values(working?.session.getSnapshot().state.pending_machine??{}).some(entry=>entry.owner_knowledge_id===knowledgeId);
  }

  async function inspectWithheld(row: MachineTaskRowDto) {
    const generation=epoch.current;setBusy(true);setWithheldAudit(null);
    try {
      const proof=record(await coreCommand("machine_task_get",{task_id:row.task_id}));
      if(proof.task_id!==row.task_id||proof.scope!=="runtime.execution.withheld"||proof.conditions!==row.conditions||proof.outcome!=="failed")throw new Error("audit identity changed");
      const doc=record(JSON.parse(String(proof.conditions)));
      const candidates=pendingEntries().filter(entry=>entry.operation===doc.operation&&entry.body.knowledge_id===doc.knowledge_id);
      const entries=(await Promise.all(candidates.map(async entry=>await frozenFingerprint(entry)===doc.admission_request_sha256?entry:null))).filter((entry):entry is PendingMachine=>entry!==null);
      if(entries.length!==1)throw new Error("audit has no unique frozen request");
      const entry=entries[0];
      if(entry.owner_knowledge_id!==knowledgeId||doc.schema!=="archeaxis.machine-execution-withheld/v1"||doc.execution_state!=="EXECUTED_BUT_WITHHELD"
        ||doc.answer_published!==false||doc.authority!=="historical_execution_audit"||doc.audit_task_id!==row.task_id
        ||doc.admission_request_sha256!==await frozenFingerprint(entry)
        ||(entry.operation==="answer"&&(doc.client_request_id!==entry.body.client_request_id||doc.retest_of!==null||proof.retest_of!==null))
        ||(entry.operation==="retest"&&(doc.retest_of!==entry.body.retest_of||proof.retest_of!==entry.body.retest_of)))throw new Error("audit frozen identity mismatch");
      if(entry.operation==="retest"){
        const failed=record(await coreCommand("machine_task_get",{task_id:entry.body.retest_of}));const prior=record(JSON.parse(String(failed.conditions)));
        if(failed.task_id!==entry.body.retest_of||failed.scope!=="runtime.evaluation.failed"||prior.knowledge_id!==knowledgeId||prior.question!==entry.body.question)throw new Error("audit journey mismatch");
      }
      if(requestLive(generation)){setWithheld(true);setUncertain(true);setWithheldAudit({taskId:row.task_id,entry:structuredClone(entry)});setMessage("本地知识库脱敏终态已与冻结请求核对；可以明确结束待核对记录。历史审计与禁止重复执行的屏障继续保留。");}
    }catch{if(requestLive(generation))setMessage("扣留审计与冻结请求未确认；保留请求屏障，不结束或重跑。");}
    finally{if(requestLive(generation))setBusy(false);}
  }
  async function finishWithheld() {
    if(busy||!working||!withheldAudit)return;
    const generation=epoch.current;const audit=withheldAudit;setBusy(true);
    try {
      await working.session.clearMachine(audit.entry,audit.taskId);
      if(!requestLive(generation))return;
      if(pendingAnswer.current?.journal_id===audit.entry.journal_id){pendingAnswer.current=null;frozenAnswer.current=null;}
      if(pendingRetest.current?.journal_id===audit.entry.journal_id){pendingRetest.current=null;frozenRetest.current=null;}
      const remaining=hasPendingOwner();setWithheldAudit(null);setWithheld(false);setUncertain(remaining);setRestoredPending(remaining);
      setMessage("已确认结束待核对记录，问题与纠正草稿保留。历史终态及执行屏障仍由本地知识库保留；新的明确操作仍须满足当前授权。");
    }catch{if(requestLive(generation))setMessage("结束回执未确认；保留冻结记录，读取本地知识库工作状态核对，不重新推理。");}
    finally{if(requestLive(generation))setBusy(false);}
  }
  async function inspectFailure() {
    if(busy||!working||working.status!=="ready")return;
    const entries=pendingEntries();if(entries.length!==1){setMessage("请选择一条冻结机器请求核对。");return;}
    const entry=structuredClone(entries[0]);const server=working.session.getSnapshot().server;
    if(!server)return;
    const generation=epoch.current;setBusy(true);setWithheldAudit(null);
    try {
      const value=await coreCommand<MachineJournalStatusDto>("ui_state_machine_status",{body:{workspace_id:server.workspace_id,restore_epoch:server.restore_epoch,state_revision:server.state_revision,journal_id:entry.journal_id}});
      if(!requestLive(generation))return;
      if(value.journal_id!==entry.journal_id)throw new Error("status identity mismatch");
      if(!["FAILED","CANCELLED_LOCAL_WORKER"].includes(value.status)||!value.can_clear||typeof value.task_id!=="string"||!value.task_id||typeof value.attempt!=="number"||value.attempt<1||value.attempt>3){
        setUncertain(true);setMessage("本地知识库未确认当前请求的失败终态；保留冻结身份，不结束或重跑。");return;
      }
      setWithheld(false);setUncertain(true);setWithheldAudit({taskId:value.task_id,entry,failed:true});
      setMessage(`本地知识库已确认第 ${value.attempt} 次尝试的${value.status==="CANCELLED_LOCAL_WORKER"?"本地处理进程取消":"失败"}审计；可结束请求并保留草稿。服务端停止状态、用量与费用仍未知。`);
    }catch{if(requestLive(generation)){setUncertain(true);setMessage("失败状态读取未确认；保留冻结请求，不再次推理。");}}
    finally{if(requestLive(generation))setBusy(false);}
  }

  async function cancelMachine() {
    if(!working||working.status!=="ready")return;
    const entries=pendingEntries();if(entries.length!==1){setMessage("请选择一条冻结机器请求取消。");return;}
    const entry=structuredClone(entries[0]);const server=working.session.getSnapshot().server;
    if(!server)return;
    const generation=epoch.current;
    try {
      const value=await coreCommand<MachineCancelDto>("ui_state_cancel_machine",{body:{workspace_id:server.workspace_id,restore_epoch:server.restore_epoch,state_revision:server.state_revision,journal_id:entry.journal_id}});
      if(!requestLive(generation))return;
      if(value.journal_id!==entry.journal_id)throw new Error("cancel identity mismatch");
      setMessage(value.cancel_requested?"本地 worker 取消请求已接收；尚未确认停止。等待调用回执后核对冻结状态，模型服务停止、用量与费用仍未知。":"没有确认可取消的当前本地 worker；冻结请求保留，核对实际终态，不重新推理。");
    }catch{if(requestLive(generation))setMessage("取消回执未确认；冻结请求保留，不宣称已停止。");}
  }

  async function readCandidate(id: string) {
    const value = record(await coreCommand("knowledge_get", { id }));
    if (value.knowledge_id !== id || typeof value.body !== "string" || typeof value.version !== "string" || !value.version
      || !["candidate", "accepted", "rejected", "deprecated"].includes(String(value.status))) {
      throw new Error("invalid correction candidate");
    }
    return value;
  }

  async function configuredRequest(purpose:"answer"|"retest") {
    const frozen=await resolveProductModel(purpose,lane);
    if(!frozen)return {};
    return {model_configuration:frozen,model:frozen.profile.model,max_tokens:Math.min(maxTokens,frozen.profile.max_tokens),timeout_s:frozen.profile.timeout_s};
  }
  async function ask() {
    const generation = epoch.current;
    if(restoredPending)return;
    if (!question.trim() || busy || inventoryPending.current || uncertain || (answerScoped && !contextGrant && !frozenAnswer.current) || (assetScoped && !assetContextGrant && !frozenAnswer.current)) return;
    if (answer && (downstreamDirty() || frozenRetest.current)) {setMessage("纠正或审核草稿尚未确认，请先保存和核对后再发起新回答。");return;}
    let binding: Awaited<ReturnType<typeof configuredRequest>> = {};
    if(!frozenAnswer.current){setBusy(true);try{binding=await configuredRequest("answer");}catch{setMessage("回答用途配置未绑定或读取失败；请在设置绑定当前 FAST/DEEP 后重试。");setBusy(false);return;}if(!requestLive(generation)){setBusy(false);return;}}
    const request = frozenAnswer.current ?? Object.freeze({knowledge_id:knowledgeId,question:question.trim(),max_tokens:maxTokens,timeout_s:120,
      ...(selectedModel ? {model:selectedModel} : {}), ...(contextGrant ? {context_grant:structuredClone(contextGrant)} : {}), ...(assetContextGrant ? {asset_context_grant:{...structuredClone(assetContextGrant),request_id:`assetanswer_${crypto.randomUUID()}`,consumer:"local-machine",operation:"answer"}} : {}), client_request_id:`machine_${crypto.randomUUID()}`, ...binding});
    frozenAnswer.current = request;
    setAnswerFailure(null);
    setBusy(true); setAnswer(null); setTask(null); setCorrection(null); setCandidate(null); setRetest(null); setRetestTask(null);
    setAdmissionRefusal(null);
    setCorrected(""); setNote(""); setReviewNote(""); setMessage("正在执行本地机器回答，等待真实回执…");
    try {
      if(working){
        const entry=pendingAnswer.current??{journal_id:String(request.client_request_id),owner_knowledge_id:knowledgeId,operation:"answer" as const,origin_restore_epoch:working.server?.restore_epoch??"",body:request as PendingMachine["body"]};
        if(canonical(entry.body)!==canonical(request))throw new Error("旧冻结请求尚未清理；新输入未发送。");
        pendingAnswer.current=entry;await working.session.stageMachine(entry);
      }else if(window.__TAURI__)throw new Error("正式宿主缺少工作状态保全，尚未发送推理。");
      const response = record(await coreCommand("machine_answer", { body: request }));
      await validateFrozenAnswer(response,request);
      const proof = record(await coreCommand("machine_task_get", { task_id: response.answer_id }));
      validateTask(proof, response, "runtime.answer", String(response.answer_id));
      if(working&&pendingAnswer.current&&requestLive(generation)){await working.session.clearMachine(pendingAnswer.current,String(response.answer_id));if(requestLive(generation))pendingAnswer.current=null;}
      if (requestLive(generation)) { frozenAnswer.current = null; setUncertain(false); setAnswer(response); setTask(proof); onTask?.(String(response.answer_id)); setMessage("本地回答已持久化读回；可能为同请求的历史重放。它仍是候选，不是已接受知识或能力评分。"); }
    } catch (reason) {
      if (requestLive(generation)) {
        if(reason instanceof ApiError && reason.machineFailure)setAnswerFailure(reason.machineFailure);
        if (reason instanceof ApiError && reason.machineAdmission) {
          const refusal=await readMachineAdmissionRefusal(reason.machineAdmission,"answer",request);
          if(!requestLive(generation))return;
          setUncertain(true);setAdmissionRefusal(refusal??null);
          setMessage(refusal?"本地知识库明确拒绝此回答请求：恢复后的旧授权已隔离。本次调用未执行；同一请求的历史执行仍未验证。冻结身份与原输入保留，请核对历史并新建明确授权，不自动替换或重跑。":"授权拒绝身份未确认，状态尚未确认；保留冻结请求并核对历史。");
        }
        else if (reason instanceof ApiError && reason.execution) {frozenAnswer.current=null;setUncertain(true);setWithheld(true);setMessage(reason.execution.audit_status === "RECORDED" ? `推理已执行，答案未发布；脱敏审计 ${reason.execution.audit_task_id} 已保存。请核对授权与审计，不自动重跑。` : "推理已执行，答案未发布；持久化审计未确认。请保留草稿并检查本地知识库，不自动重跑。");}
        else if (reason instanceof ApiError && [400,403,404,422].includes(reason.status)) {setUncertain(true);setMessage("本地知识库明确拒绝此回答请求；仅说明本次拒绝，历史执行仍未确认。原冻结身份与输入保留，请读取历史核对，不自动换授权或重跑。");}
        else {setUncertain(true); setMessage("回答未完成或持久化读回未确认，状态尚未确认。" + (reason instanceof ApiError && reason.machineFailure ? reason.message : "") + "请读取历史核对；不会自动再次推理。");}
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
      if (requestLive(generation)) setMessage("纠正已提交或候选读回未确认。请保留填写内容并读取本地回执核对状态。");
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
        setMessage(action === "accepted" ? "本地知识库已接受此纠正知识。独立复测尚未执行，不能据此宣称机器改进。"
          : action === "rejected" ? "本地知识库已拒绝此纠正候选；机器回答和审核记录仍保留。"
          : "本地知识库已将此纠正标记为弃用；候选、来源和复测证据仍保留。" );
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
      if (requestLive(generation)) { setCandidate(value); onCandidate?.(String(value.knowledge_id)); setMessage("已重新读取本地知识库中的当前候选与版本。"); }
    }
    catch { if (requestLive(generation)) setMessage("候选重新读取失败；当前对照仍保留，审核操作已暂停。"); }
    finally { if (requestLive(generation)) setBusy(false); }
  }

  async function runIndependentRetest() {
    const generation = epoch.current;
    if(restoredPending||uncertain)return;
    if (!answer || !correction || !candidate || candidate.status !== "accepted" || retest || busy || ((scoped||retestAssetScoped||!!retestAssetContextGrant||record(answer.request??{}).asset_context!==undefined) && !retestContextGrant && !frozenRetest.current) || ((retestAssetScoped || record(answer.request??{}).asset_context!==undefined) && !retestAssetContextGrant && !frozenRetest.current)) return;
    const failedTaskId = correction.failed_task_id;
    const candidateId = String(candidate.knowledge_id);
    const originalQuestion = String(answer.question);
    let binding: Awaited<ReturnType<typeof configuredRequest>> = {};
    if(!frozenRetest.current){setBusy(true);try{binding=await configuredRequest("retest");}catch{setMessage("复测用途配置未绑定或读取失败；请在设置绑定当前 FAST/DEEP 后重试。");setBusy(false);return;}if(!requestLive(generation)){setBusy(false);return;}}
    const request = frozenRetest.current ?? { ...binding, retest_of: failedTaskId, knowledge_id: candidateId, question: originalQuestion, max_tokens: maxTokens, timeout_s: 120, ...(selectedModel ? {model:selectedModel} : typeof record(answer.request??{}).model === "string" ? {model:record(answer.request).model} : {}), ...(retestContextGrant ? {context_grant:structuredClone(retestContextGrant)} : {}), ...(retestAssetContextGrant ? {asset_context_grant:{...structuredClone(retestAssetContextGrant),request_id:`assetretest_${crypto.randomUUID()}`,consumer:"local-machine",operation:"retest"}} : {}), ...binding };
    frozenRetest.current=request;
    setRetestFailure(null);
    setAnswerFailure(null);
    let phase = "invoke";
    setAdmissionRefusal(null); setBusy(true); setMessage("正在以已审核纠正知识重答原问题；本地回执与任务读回确认前不显示为完成…");
    try {
      if(working){
        const entry=pendingRetest.current??{journal_id:`retest_${crypto.randomUUID()}`,owner_knowledge_id:knowledgeId,operation:"retest" as const,origin_restore_epoch:working.server?.restore_epoch??"",body:request as PendingMachine["body"]};
        if(canonical(entry.body)!==canonical(request))throw new Error("旧冻结复测尚未清理；新输入未发送。");
        pendingRetest.current=entry;await working.session.stageMachine(entry);
      }else if(window.__TAURI__)throw new Error("正式宿主缺少工作状态保全，尚未发送复测。");
      const response = record(await coreCommand("machine_retest", { body: request }));
      phase = "receipt_validation";
      const machine = record(response.answer);
      if (response.schema !== "archeaxis.machine-retest/v1" || response.retest_of !== failedTaskId
        || response.knowledge_id !== candidateId || response.question !== originalQuestion
        || response.authority !== "candidate" || typeof response.retest_task_id !== "string"
        || typeof machine.answer !== "string" || !machine.answer.trim()) throw new Error("invalid retest receipt");
      if (canonical(response.request) !== canonical({retest_of:request.retest_of,knowledge_id:request.knowledge_id,question:request.question,max_tokens:request.max_tokens,...(request.model ? {model:request.model,timeout_s:request.timeout_s} : {}),...(request.context_grant ? {context_grant:request.context_grant} : {}),...(request.asset_context_grant ? {asset_context_grant:request.asset_context_grant} : {}),...(request.model_configuration?{model_configuration:request.model_configuration}:{})}) || (request.model!==undefined&&(machine.model!==request.model||machine.requested_model!==request.model))) throw new Error("retest request mismatch");
      const execution=record(response.execution_request??{});
      if(execution.schema!=="archeaxis.machine-retest-execution/v1"||execution.timeout_s!==request.timeout_s||canonical(execution.request)!==canonical(response.request))throw new Error("retest execution envelope mismatch");
      if(request.asset_context_grant){const execution=record(response.execution_request);if(execution.schema!=="archeaxis.machine-retest-execution/v1"||execution.timeout_s!==request.timeout_s||canonical(execution.request)!==canonical(response.request)||typeof execution.context_sha256!=="string"||!/^[a-f0-9]{64}$/.test(execution.context_sha256)||typeof execution.knowledge_context_sha256!=="string"||!/^[a-f0-9]{64}$/.test(execution.knowledge_context_sha256))throw new Error("retest execution budget or context mismatch");validateAssetContext(execution.asset_context,assertAiAssetDto<AssetPacketRequest>("AssetPacketRequest",request.asset_context_grant));}
      phase = "task_readback";
      const proof = record(await coreCommand("machine_task_get", { task_id: response.retest_task_id }));
      validateTask(proof, response, "runtime.retest", String(response.retest_task_id));
      if(working&&pendingRetest.current&&requestLive(generation)){await working.session.clearMachine(pendingRetest.current,String(response.retest_task_id));if(requestLive(generation))pendingRetest.current=null;}
      if (requestLive(generation)) {
        setRetest(response); setRetestTask(proof);
        frozenRetest.current=null;
        onTask?.(String(response.retest_task_id));
        setMessage("本地独立复测回执与持久化任务读回一致；复测结果仍是未测评候选，请真人对照两次回答。没有自动判定改进。");
      }
    } catch (reason) {
      if (requestLive(generation)) {
        if (reason instanceof ApiError && reason.machineAdmission) {
          const refusal=await readMachineAdmissionRefusal(reason.machineAdmission,"retest",request);
          if(!requestLive(generation))return;
          setUncertain(true);setAdmissionRefusal(refusal??null);
          setMessage(refusal?"本地知识库明确拒绝复测请求：恢复后的旧授权已隔离。本次调用未执行；历史执行仍未验证。原冻结复测与纠正保留，不自动换授权或重跑。":"复测授权拒绝身份未确认，状态尚未确认；保留冻结请求。");
        }
        else if (reason instanceof ApiError && reason.execution) {frozenRetest.current=null;setUncertain(true);setWithheld(true);setMessage(reason.execution.audit_status === "RECORDED" ? `复测推理已执行，答案未发布；脱敏审计 ${reason.execution.audit_task_id} 已保存，不自动重跑。` : "复测推理已执行，答案未发布；审计持久化未确认，不自动重跑。");}
        else if (reason instanceof ApiError && [400,403,404,422].includes(reason.status)) {setMessage("本地知识库明确拒绝复测请求；仅说明本次拒绝，历史执行仍未确认。原冻结复测、回答与纠正保留，请读取历史核对，不自动换授权或重跑。");}
        else {setUncertain(true);setMessage("复测未完成或持久化读回未确认。" + (reason instanceof ApiError && reason.machineFailure ? reason.message : "") + "保留纠正与原失败回执；先核对终态，不再次推理。");}
        setRetestFailure({phase,status:reason instanceof ApiError ? reason.status : null,code:reason instanceof ApiError ? reason.code : "unverified",...(reason instanceof ApiError && reason.machineFailure ? {reason_code:reason.machineFailure.reason_code,...(reason.machineFailure.diagnostics?{diagnostics:reason.machineFailure.diagnostics}:{})}: {})});
        setUncertain(true);
      }
    } finally { if (requestLive(generation)) setBusy(false); }
  }

  return <section aria-label="知识到机器回答" className="ui-machine-answer" data-retest-failure={retestFailure?JSON.stringify(retestFailure):undefined}>
    {answerFailure?<RawReceiptButton label="回答失败脱敏诊断" payload={answerFailure}/>:null}
    {retestFailure?<RawReceiptButton label="复测失败脱敏诊断" payload={retestFailure}/>:null}
    {admissionRefusal?<section aria-label="恢复授权拒绝" data-context-admission-refusal={JSON.stringify(admissionRefusal)}><p>拒绝依据：恢复后的旧授权隔离。仅确认本次调用未执行；历史执行尚未核实。</p><RawReceiptButton label="恢复授权拒绝回执" payload={admissionRefusal}/></section>:null}
    {withheld ? <><p>先读取并核对已保存的扣留审计；审计未确认时保留执行屏障。</p><button disabled={busy||!withheldAudit||!working} onClick={()=>void finishWithheld()}>结束已执行但未发布的请求，保留草稿</button></> : null}
    {working&&hasPendingOwner()?<><button disabled={working.status!=="ready"} onClick={()=>void cancelMachine()}>请求取消当前本地 worker</button><button disabled={busy||working.status!=="ready"} onClick={()=>void inspectFailure()}>核对冻结机器请求的失败状态</button></>:null}
    {withheldAudit?.failed?<button disabled={busy||!working} onClick={()=>void finishWithheld()}>结束失败请求，保留草稿</button>:null}
    <h4>已保存的 AI 回答记录</h4>
    {working&&Object.values(working.state.pending_machine??{}).filter(entry=>entry.owner_knowledge_id===knowledgeId).length>1?
      <label>待核对机器请求 <select value={selectedJournal} disabled={busy||working.status!=="ready"} onChange={event=>{
        const entry=working.state.pending_machine?.[event.target.value];setSelectedJournal(event.target.value);setWithheldAudit(null);setWithheld(false);
        if(!entry||entry.owner_knowledge_id!==knowledgeId)return;
        pendingAnswer.current=entry.operation==="answer"?structuredClone(entry):null;pendingRetest.current=entry.operation==="retest"?structuredClone(entry):null;
        frozenAnswer.current=entry.operation==="answer"?Object.freeze(structuredClone(entry.body)):null;frozenRetest.current=entry.operation==="retest"?Object.freeze(structuredClone(entry.body)):null;
        setQuestion(entry.body.question);setSelectedModel(entry.body.model??"");setMaxTokens(entry.body.max_tokens===4096?4096:2048);setRestoredPending(true);setUncertain(true);
      }}><option value="">选择一条请求核对</option>{Object.values(working.state.pending_machine??{}).filter(entry=>entry.owner_knowledge_id===knowledgeId).map(entry=><option key={entry.journal_id} value={entry.journal_id}>{entry.operation==="answer"?"回答":"复测"} · {entry.body.question.slice(0,80)}</option>)}</select></label>:null}
    <button disabled={busy} onClick={() => void readHistory()}>读取机器学习历史</button>
    <ul aria-label="既有机器学习任务">{history.filter(row => ["runtime.answer","runtime.evaluation.failed","runtime.retest","runtime.execution.withheld"].includes(row.scope)).map(row => <li key={row.task_id} data-task-id={row.task_id}><span>{row.scope === "runtime.execution.withheld" ? "已执行但未发布" : row.scope === "runtime.evaluation.failed" ? "使用者纠正" : row.scope === "runtime.retest" ? "复测" : "回答"} · {row.scope === "runtime.evaluation.failed" ? "已记录" : row.outcome === "succeeded" ? "已完成" : row.outcome === "failed" ? "失败" : "未测评"} · {row.recorded_at}</span><button disabled={busy} onClick={() => void restoreHistory(row)}>查看这次任务</button></li>)}</ul>
    {cursor ? <button disabled={busy} onClick={() => void readHistory(true)}>读取更多任务</button> : null}
    {uncertain ? <p>{withheldAudit?.failed ? "本地调用失败已核对；服务停止状态仍未知。结束请求前保留冻结输入。" : "运行结果尚未确认；请先检查已保存记录，避免重复运行。"}</p> : null}
    <h4>基于当前知识的本地回答</h4>
    <button disabled={busy} onClick={()=>void coreCommand<MachineConfigurationDto>("machine_configuration").then(setModelConfiguration).catch(()=>setModelConfiguration(null))}>读取模型配置状态</button>
    <p>{modelConfiguration ? (modelConfiguration.worker_registered ? "本地回答服务已配置；模型是否已加载和能否回答仍需实际验证。" : "本地回答服务尚未配置。") : "模型配置状态未读取或读取失败。"}</p>
    <p>本地回答仅向本机服务发送已授权知识与明确填写的问题；用量和费用在服务未返回前为未知。读取配置状态不会调用模型。</p>
    <button disabled={busy || inventoryBusy || uncertain || !!frozenRetest.current} onClick={() => void readInventory()}>探测本地模型清单</button>
    <p>探测只读取本机服务清单，不发送知识或问题，不加载模型或执行推理。</p>
    <p aria-label="本地模型清单探测结果">{inventoryBusy ? "正在读取本地清单…" : !inventory ? "清单未探测或读取失败。" : inventory.status === "READ_VERIFIED" ? `清单已读取，共 ${inventory.listed_model_count} 项；声明模型${inventory.selected_model_listed ? "已列出" : "未列出"}。加载状态未知，推理尚未验证。` : inventory.status === "DISABLED" ? "本地回答能力已禁用，未探测。" : inventory.status === "BUSY" ? "模型服务入口正忙，请稍后重试。" : "清单读取未确认；模型数量与可用性未知。"}</p>
    <label>用途执行通道 <select value={lane} disabled={busy||uncertain||!!frozenRetest.current} onChange={e=>setLane(e.target.value as ModelLane)}><option value="fast">快速</option><option value="deep">深入</option></select></label>
    <label>兼容模式本地回答模型 <select value={selectedModel} disabled={busy||uncertain||!!frozenRetest.current||inventoryBusy} onChange={event=>setSelectedModel(event.target.value)}><option value="">沿用本地启动配置（模型尚未绑定）</option>{selectedModel&&(inventory?.status!=="READ_VERIFIED"||!inventory.model_choices?.includes(selectedModel))?<option value={selectedModel}>{selectedModel}（此前选择，本次清单未确认）</option>:null}{inventory?.status==="READ_VERIFIED"?inventory.model_choices?.map(model=><option key={model} value={model}>{model}（清单已列出，推理未验证）</option>):null}</select></label>
    <p>选择仅用于本次回答及复测，不修改全局配置。执行可能由本机服务加载所选模型；不会自动转云。重试保留原选择。</p>
    <label>本次输出预算 <select value={maxTokens} disabled={busy||uncertain||!!frozenRetest.current} onChange={event=>setMaxTokens(event.target.value==="4096"?4096:2048)}><option value="2048">2048 tokens</option><option value="4096">4096 tokens</option></select></label>
    <p>推理与正文可能共享输出预算；预算用尽不代表已得到答案。更高预算可能增加等待时间，本次上限 120 秒。</p>
    <label>实际问题 <textarea value={question} disabled={busy} onChange={event => setQuestion(event.target.value)} /></label>
    {answerScoped && !contextGrant ? <p>请先选择已保存、允许回答的上下文授权。</p> : null}
    <button disabled={restoredPending || busy || inventoryBusy || uncertain || !question.trim() || (answerScoped && !contextGrant && !frozenAnswer.current) || (assetScoped && !assetContextGrant && !frozenAnswer.current)} onClick={() => void ask()}>{frozenAnswer.current ? "重试同一回答请求" : "执行本地机器回答"}</button>
    {assetScoped&&!assetContextGrant?<p>选中的资产授权已失效或未确认；新执行暂停，原历史保留。</p>:null}
    {message ? <p role="status">{message}</p> : null}
    {answer ? <>
      <h4>机器回答候选</h4><pre aria-label="真实机器回答">{String(record(answer.answer).answer)}</pre>
      <dl aria-label="本次模型调用证据">
        <dt>请求模型</dt><dd>{String(record(answer.answer).requested_model ?? record(answer.answer).model ?? "未知")}</dd>
        <dt>服务返回模型</dt><dd>{typeof record(answer.answer).observed_model === "string" && record(answer.answer).observed_model ? String(record(answer.answer).observed_model) : "未知；服务未提供模型身份"}</dd>
        <dt>完成状态</dt><dd>{record(answer.answer).finish_reason === "stop" && record(answer.answer).truncated === false ? "完整返回候选答案" : record(answer.answer).truncated === true ? "答案截断" : "未知；完成状态未提供"}</dd>
        <dt>用量与费用</dt><dd>{record(answer.answer).usage_status === "REPORTED" ? `服务报告了用量；费用未知` : "未知；本次回执未提供可核实的计量"}</dd>
      </dl>
      <p>这些证据只属于本次调用，不证明服务持续可用、其他模型接通或答案正确。</p>
      <p>机器回答未被接受为知识。保存错误纠正不会自行改变已接受知识，也不会证明机器改进。</p>
      <RawReceiptButton label="任务、模型与用量详细信息" payload={{task,answer:answer.answer}} />
      <p>若你实际发现错误，可记录具体更正；没有错误无需提交。</p>
      <label>正确答案 <textarea value={corrected} disabled={busy} onChange={event => setCorrected(event.target.value)} /></label>
      <label>具体错误依据 <textarea value={note} disabled={busy} onChange={event => setNote(event.target.value)} /></label>
      <label>纠正提交者 <input value={correctionAuthor} disabled={busy} onChange={event => setCorrectionAuthor(event.target.value)} /></label>
      <button disabled={busy || !corrected.trim() || !note.trim() || !correctionAuthor.trim()} onClick={() => void correct()}>记录使用者纠正候选</button>
      {correction ? <>
        <h4>纠正对照与范围</h4>
        <p>纠正记录本身不证明原回答错误，请结合提交者与依据核验。</p>
        <dl><div><dt>纠正候选</dt><dd>已保存并关联原知识</dd></div>
          <div><dt>纠正候选修订</dt><dd>{candidate ? String(candidate.version) : "纠正候选尚未核实"}</dd></div>
          <div><dt>本题</dt><dd>{String(correction.question)}</dd></div>
          <div><dt>原机器回答</dt><dd>{String(correction.machine_answer)}</dd></div>
          <div><dt>使用者纠正</dt><dd>{String(correction.corrected_answer)}</dd></div>
          <div><dt>已保存的纠正正文</dt><dd>{candidate ? String(candidate.body) : "未确认；审核操作不可用"}</dd></div>
          <div><dt>纠正记录提交者</dt><dd>{String(correction.reviewer)}</dd></div>
          <div><dt>提交的纠正依据</dt><dd>{String(correction.error_note)}</dd></div>
          <div><dt>状态</dt><dd>{candidate ? candidate.status === "accepted" ? "已接受" : candidate.status === "rejected" ? "已拒绝" : candidate.status === "deprecated" ? "已撤回" : "待审核" : "纠正候选尚未核实"}</dd></div>
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
          <p>已审核知识可用于重答原问题。复测会再次核对原纠正记录和知识版本；接受纠正知识本身不代表复测通过。</p>
          {scoped && !retestContextGrant ? <p>请先为已接受的纠正知识保存并选择独立复测授权。</p> : null}
          <button disabled={restoredPending || busy || uncertain || withheld || Boolean(retest) || ((scoped||retestAssetScoped||!!retestAssetContextGrant||record(answer.request??{}).asset_context!==undefined) && !retestContextGrant && !frozenRetest.current) || ((retestAssetScoped || record(answer.request??{}).asset_context!==undefined) && !retestAssetContextGrant && !frozenRetest.current)} onClick={() => void runIndependentRetest()}>{retest ? "独立复测已记录" : frozenRetest.current ? "重试同一冻结复测请求" : "以已接受纠正知识运行独立复测"}</button>
        </> : null}
          {retest ? <section aria-label="独立复测结果对照">
            <h4>独立复测结果对照</h4>
            <p>这次复测关联原纠正记录，使用已审核知识第 {String(candidate.version)} 版。结果尚未由真人比较。</p>
            <h5>原机器回答（纠正前）</h5><pre>{String(record(answer.answer).answer)}</pre>
            <h5>纠正后复测回答（候选）</h5><pre aria-label="独立复测机器回答">{String(record(retest.answer).answer)}</pre>
            <p>系统仅记录独立复测及其与纠正记录的关联，不自动推断纠正有效；真人比较结果尚未记录。</p>
            <RawReceiptButton label="复测任务持久化回执" payload={retestTask} />
            <RawReceiptButton label="机器复测回执" payload={retest} />
          </section> : null}
      </section> : null}
    </> : null}
  </section>;
}
