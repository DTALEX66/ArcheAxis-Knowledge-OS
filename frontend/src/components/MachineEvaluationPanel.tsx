import { useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { CoreOperation, DocumentDto, MachineAnswerSnapshotDto, MachineDocumentsPageDto, MachineDocumentSummaryDto, MachineEvaluationDto, MachineEvaluationRequestDto, MachineJudgmentDto, MachineRubricDto, MachineRubricSnapshotDto } from "../api/generated/core-contract";
import { assertCoreDto } from "../api/generated/core-contract";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { RawReceiptButton } from "./DiagnosticConsole";

type Outcome = MachineJudgmentDto["outcome"];
type Attempt = { operation: CoreOperation; body: MachineRubricDto | MachineEvaluationRequestDto; metadata: unknown; title: string; namespace: string; expectedId?: string };
function object(v: unknown): Record<string, unknown> { if (!v || typeof v !== "object" || Array.isArray(v)) throw new Error("对象格式不符"); return v as Record<string, unknown>; }
function canonical(v: unknown): string { return JSON.stringify(v, (_k, x: unknown) => x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.entries(x as Record<string,unknown>).sort(([a],[b])=>a.localeCompare(b))) : x); }
function bytes(v: string) { return new TextEncoder().encode(v).length; }
function metadata(d: DocumentDto, key: string): unknown { return object(object(d.editor_json).attrs)[key]; }
function checkDoc(d: DocumentDto, a: Attempt) {
  if (d.document_id !== a.expectedId || d.version !== 1 || d.title !== a.title || d.source_id !== null || d.source_revision !== null
    || canonical(metadata(d,a.namespace)) !== canonical(a.metadata)) throw new Error("冻结写入身份不符");
}
function checkSnapshot(s: MachineAnswerSnapshotDto, id: string) {
  if (s.task_id !== id || s.receipt.task_id !== id || !["runtime.answer","runtime.retest"].includes(s.receipt.scope)
    || !s.original_answer.trim() || s.evaluation_authority !== "human_observation_only" || s.grants_machine_qualification !== false
    || s.grants_human_mastery !== false || s.grants_professional_truth !== false) throw new Error("机器答案快照身份不符");
}
function rubricFrom(d: DocumentDto): MachineRubricDto {
  const r = assertCoreDto<MachineRubricDto>("MachineRubricDto",metadata(d,"archeaxis_machine_rubric"));
  if (r.schema !== "archeaxis.machine-rubric/v1" || !Array.isArray(r.criteria) || !r.criteria.length || r.criteria.length > 64
    || new Set(r.criteria.map(c=>c.criterion_id)).size !== r.criteria.length || r.criteria.some(c=>!c.label?.trim() || !c.expectation?.trim())) throw new Error("不支持此历史量规，原文仍保留");
  return r;
}
const overall = (items: MachineJudgmentDto[]): Outcome => items.some(x=>x.outcome==="failed") ? "failed" : items.some(x=>x.outcome==="unmeasured") ? "unmeasured" : "passed";

/** Human observations only; the finite Core routes enforce the trusted actor. */
export function MachineEvaluationPanel({ taskId }: { taskId?: string }) {
  const owner = useId(); const alive = useRef(true); const lock = useRef(false);
  const epochs = useRef({task:0,rubric:0,history:0});
  const [busy,setBusy] = useState(false); const [message,setMessage] = useState("");
  const [taskInput,setTaskInput] = useState(""); const [snapshot,setSnapshot] = useState<MachineAnswerSnapshotDto|null>(null);
  const [rubric,setRubric] = useState<{doc:DocumentDto;body:MachineRubricDto}|null>(null);
  const [reviewer,setReviewer] = useState(""); const [basis,setBasis] = useState(""); const [judgments,setJudgments] = useState<MachineJudgmentDto[]>([]);
  const [title,setTitle] = useState(""); const [purpose,setPurpose] = useState("");
  const [criteria,setCriteria] = useState([{criterion_id:crypto.randomUUID(),label:"",expectation:""}]);
  const [rubricRows,setRubricRows] = useState<MachineDocumentSummaryDto[]>([]); const [rubricCursor,setRubricCursor] = useState<string|null>(null);
  const [evaluationRows,setEvaluationRows] = useState<MachineDocumentSummaryDto[]>([]); const [evaluationCursor,setEvaluationCursor] = useState<string|null>(null);
  const [historical,setHistorical] = useState<DocumentDto|null>(null);
  const rubricAttempt = useRef<Attempt|null>(null); const evaluationAttempt = useRef<Attempt|null>(null);
  const [,redraw] = useState(0); const [savedEvaluation,setSavedEvaluation] = useState("");
  const formSignature = canonical({task:snapshot?.task_id,rubric:rubric?.doc.document_id,version:rubric?.doc.version,reviewer,basis,judgments});
  const evaluationEdits = !!reviewer || !!basis || judgments.some(j=>!!j.basis || j.outcome!=="unmeasured");
  const evalDirty = !!evaluationAttempt.current || (evaluationEdits && formSignature!==savedEvaluation);
  const rubricDirty = !!rubricAttempt.current || !!title || !!purpose || criteria.some(c=>!!c.label || !!c.expectation);
  useEffect(()=>{alive.current=true; return ()=>{alive.current=false; epochs.current.task++; epochs.current.rubric++; epochs.current.history++;
    for(const suffix of ["rubric","evaluation"]) window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:`${owner}-${suffix}`,dirty:false}}));};},[owner]);
  useEffect(()=>{window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:`${owner}-rubric`,dirty:rubricDirty || busy && !!rubricAttempt.current}}));
    window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:`${owner}-evaluation`,dirty:evalDirty || busy && !!evaluationAttempt.current}}));},[owner,rubricDirty,evalDirty,busy]);
  // taskId is a hint only. New model receipts never replace an edited evaluation.
  function applyHint() { if(evalDirty || lock.current) {setMessage("新任务提示已保留；未保存评测不被覆盖。");return;} setTaskInput(taskId??""); }
  function begin() { if(lock.current) return false; lock.current=true;setBusy(true);return true; }
  function end() {lock.current=false;if(alive.current){setBusy(false);redraw(x=>x+1);}}
  async function loadTask() {
    if(evalDirty){setMessage("请先完成或清空本地评测；未覆盖草稿。");return;} if(!begin())return;
    const epoch=++epochs.current.task, id=taskInput;
    try {const s=await coreCommand<MachineAnswerSnapshotDto>("machine_answer_snapshot",{task_id:id});checkSnapshot(s,id);
      if(alive.current && epoch===epochs.current.task){setSnapshot(s);setReviewer("");setBasis("");setJudgments(old=>old.map(j=>({...j,outcome:"unmeasured",basis:""})));setSavedEvaluation("");setMessage("已读取持久化原答案；没有调用模型。");}}
    catch{if(alive.current)setMessage("原答案读取失败；现有内容保留，未自动执行。");} finally{end();}
  }
  async function list(kind:"rubric"|"evaluation",more=false) {
    if(!begin())return; const cursor=kind==="rubric"?rubricCursor:evaluationCursor;
    try{const page=await coreCommand<MachineDocumentsPageDto>(kind==="rubric"?"machine_rubrics_list":"machine_evaluations_list",more&&cursor?{cursor}:{});
      if(more && cursor && page.next_cursor===cursor)throw new Error("分页未推进");if(!alive.current)return;
      const update=(old:MachineDocumentSummaryDto[])=>more?[...old,...page.items.filter(row=>!old.some(p=>p.document_id===row.document_id))]:page.items;
      if(kind==="rubric"){setRubricRows(update);setRubricCursor(page.next_cursor);}else{setEvaluationRows(update);setEvaluationCursor(page.next_cursor);}
      setMessage("已读取真实登记列表；当前页不是全库完成证明。");
    }catch{if(alive.current)setMessage("登记列表读取失败；当前表单保留。");}finally{end();}
  }
  async function openRubric(row:MachineDocumentSummaryDto,version=row.version) {
    if(evalDirty){setMessage("未保存评测使用的固定量规保留；请先完成或清空本地评测。");return;}if(!begin())return;
    const epoch=++epochs.current.rubric;
    try{const doc=await coreCommand<DocumentDto>("document_version",{document_id:row.document_id,version});
      if(doc.document_id!==row.document_id || doc.version!==version || (version===row.version&&doc.content_sha256!==row.content_sha256))throw new Error("固定量规版本不符");
      const body=rubricFrom(doc);if(alive.current&&epoch===epochs.current.rubric){setRubric({doc,body});setJudgments(body.criteria.map(c=>({criterion_id:c.criterion_id,outcome:"unmeasured",basis:""})));setSavedEvaluation("");setMessage("量规已固定到所选版本与 hash；后续修改不替换它。");}}
    catch{if(alive.current)setMessage("量规读取失败或结构不支持；现有评测保留。");}finally{end();}
  }
  async function openHistory(row:MachineDocumentSummaryDto,version=row.version) {
    if(!begin())return; const epoch=++epochs.current.history;
    try{const doc=await coreCommand<DocumentDto>("document_version",{document_id:row.document_id,version});
      if(doc.document_id!==row.document_id || doc.version!==version || (version===row.version&&doc.content_sha256!==row.content_sha256))throw new Error("历史身份不符");
      const e=assertCoreDto<MachineEvaluationDto>("MachineEvaluationDto",metadata(doc,"archeaxis_machine_evaluation"));
      if(e.schema!=="archeaxis.machine-evaluation/v1")throw new Error("不支持历史结构");
      if(alive.current&&epoch===epochs.current.history){setHistorical(doc);setMessage("仅展示固定历史评测；当前未保存表单仍保留。");}}
    catch{if(alive.current)setMessage("历史读取失败或结构不支持；未替换当前表单。");}finally{end();}
  }
  async function execute(kind:"rubric"|"evaluation",readOnly=false) {
    const slot=kind==="rubric"?rubricAttempt:evaluationAttempt;if(!begin())return;
    try {
      if(!slot.current){
        if(readOnly)throw new Error("没有冻结请求");
        const request_id=crypto.randomUUID();
        if(kind==="rubric"){
          if(!title.trim()||bytes(title)>512||!purpose.trim()||bytes(purpose)>512||!criteria.length||criteria.some(c=>!c.label.trim()||bytes(c.label)>512||!c.expectation.trim()||bytes(c.expectation)>4096))throw new Error("量规需完整准则与有限依据");
          const body:MachineRubricDto={schema:"archeaxis.machine-rubric/v1",request_id,title,purpose,criteria:structuredClone(criteria),sources:[]};
          slot.current={operation:"machine_rubric_create",body,metadata:body,title,namespace:"archeaxis_machine_rubric"};
        }else{
          if(!snapshot||!rubric||!reviewer.trim()||bytes(reviewer)>128||!basis.trim()||bytes(basis)>16384||judgments.some(j=>!j.basis.trim()||bytes(j.basis)>4096))throw new Error("需原答案、固定量规、逐项人工依据及署名");
          const pinned:MachineRubricSnapshotDto={document_id:rubric.doc.document_id,version:rubric.doc.version,content_sha256:rubric.doc.content_sha256};
          const body:MachineEvaluationRequestDto={request_id,task_id:snapshot.task_id,rubric:pinned,reviewer,basis,judgments:structuredClone(judgments),outcome:overall(judgments)};
          const e:MachineEvaluationDto={...body,schema:"archeaxis.machine-evaluation/v1",knowledge_id:snapshot.knowledge_id,original_answer_sha256:snapshot.original_answer_sha256,task_receipt_sha256:snapshot.task_receipt_sha256};
          slot.current={operation:"machine_evaluation_create",body,metadata:e,title:"人工机器评测",namespace:"archeaxis_machine_evaluation"};
        }
      }
      const a=slot.current;if(!a.expectedId)a.expectedId=await documentRequestIdentity(a.body.request_id);
      let ack:DocumentDto|null=null;
      if(!readOnly){ack=await coreCommand<DocumentDto>(a.operation,{body:a.body});checkDoc(ack,a);}
      const doc=await coreCommand<DocumentDto>("document_version",{document_id:a.expectedId,version:1});checkDoc(doc,a);
      if(ack&&ack.content_sha256!==doc.content_sha256)throw new Error("写入读回 hash 不符");
      if(!alive.current)return;
      if(kind==="rubric") {setRubricRows(old=>[{document_id:doc.document_id,version:doc.version,title:doc.title,content_sha256:doc.content_sha256},...old.filter(x=>x.document_id!==doc.document_id)]);setTitle("");setPurpose("");setCriteria([{criterion_id:crypto.randomUUID(),label:"",expectation:""}]);}
      else {setSavedEvaluation(formSignature);setHistorical(doc);setEvaluationRows(old=>[{document_id:doc.document_id,version:doc.version,title:doc.title,content_sha256:doc.content_sha256},...old.filter(x=>x.document_id!==doc.document_id)]);}
      slot.current=null;setMessage("已登记并核对固定版本；这是人工观察，不授予机器资格、真人掌握度或专业真值。");
    }catch{if(alive.current)setMessage(slot.current?"写入未确认；冻结请求与全部表单保留。可核对或同 ID 重试，未报告成功。":"请补齐有限字段和逐项依据；没有创建请求。");}
    finally{end();}
  }
  const historyValue=historical?metadata(historical,"archeaxis_machine_evaluation") as MachineEvaluationDto:null;
  return <section aria-label="人工机器评测" className="semantic-panel">
    <h2>人工机器评测</h2><p role="status" aria-live="polite">{message}</p>
    <p>署名是人工声明；Core 根据可信调用身份拒绝机器冒充人。记录不会自动提升知识，也不授予真人掌握度或专业真值。</p>
    {taskId&&<p>新任务提示：{taskId} <button disabled={busy} onClick={applyHint}>使用新任务提示</button></p>}
    <fieldset disabled={busy||!!evaluationAttempt.current}><legend>持久化原答案</legend>
      <label>机器任务 ID<input value={taskInput} onChange={e=>setTaskInput(e.target.value)}/></label><button onClick={()=>void loadTask()}>读取原答案快照</button>
    </fieldset>
    {snapshot&&<section aria-label="固定原答案"><p>{snapshot.task_id} · {snapshot.model_version}</p><p>{snapshot.question}</p><pre>{snapshot.original_answer}</pre><p>答案 hash：{snapshot.original_answer_sha256}</p><RawReceiptButton label="机器答案快照" payload={snapshot}/></section>}
    <section aria-label="量规登记"><h3>新量规</h3><fieldset disabled={busy||!!rubricAttempt.current}><legend>人工定义准则</legend>
      <label>量规标题<input value={title} onChange={e=>setTitle(e.target.value)}/></label><label>量规用途<input value={purpose} onChange={e=>setPurpose(e.target.value)}/></label>
      {criteria.map((c,i)=><div key={c.criterion_id}><label>准则名称 {i+1}<input value={c.label} onChange={e=>setCriteria(old=>old.map((x,n)=>n===i?{...x,label:e.target.value}:x))}/></label><label>准则预期 {i+1}<textarea value={c.expectation} onChange={e=>setCriteria(old=>old.map((x,n)=>n===i?{...x,expectation:e.target.value}:x))}/></label></div>)}
      <button disabled={criteria.length>=64} onClick={()=>setCriteria(old=>[...old,{criterion_id:crypto.randomUUID(),label:"",expectation:""}])}>增加准则</button>
    </fieldset><button disabled={busy} onClick={()=>void execute("rubric")}>{rubricAttempt.current?"同 ID 重试量规":"登记新量规"}</button>
      <button disabled={busy||!rubricAttempt.current} onClick={()=>void execute("rubric",true)}>核对冻结量规</button>
      <button disabled={busy} onClick={()=>void list("rubric")}>读取量规列表</button><button disabled={busy||!rubricCursor} onClick={()=>void list("rubric",true)}>下一页量规</button>
      {rubricRows.map(row=><HistoryRow key={row.document_id} row={row} busy={busy} verb="固定量规" onOpen={v=>void openRubric(row,v)}/>)}
    </section>
    {rubric&&<p>固定量规：{rubric.doc.title} · {rubric.doc.document_id} · v{rubric.doc.version} · {rubric.doc.content_sha256}</p>}
    <fieldset disabled={busy||!!evaluationAttempt.current}><legend>逐项人工判断</legend>
      <label>评测者署名<input value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label>整体评测依据<textarea value={basis} onChange={e=>setBasis(e.target.value)}/></label>
      {rubric?.body.criteria.map((c,i)=><div key={c.criterion_id}><h4>{c.label}</h4><p>{c.expectation}</p>
        <label>判断 {i+1}<select value={judgments[i]?.outcome??"unmeasured"} onChange={e=>setJudgments(old=>old.map((j,n)=>n===i?{...j,outcome:e.target.value as Outcome}:j))}><option value="unmeasured">未测评</option><option value="passed">通过此准则</option><option value="failed">未通过此准则</option></select></label>
        <label>人工依据 {i+1}<textarea value={judgments[i]?.basis??""} onChange={e=>setJudgments(old=>old.map((j,n)=>n===i?{...j,basis:e.target.value}:j))}/></label></div>)}
    </fieldset>
    <p>整体观察：{judgments.length?overall(judgments):"unmeasured"}；按固定准则推导，不替人宣称能力。</p>
    <button disabled={busy||!snapshot||!rubric} onClick={()=>void execute("evaluation")}>{evaluationAttempt.current?"同 ID 重试评测":"登记人工评测"}</button>
    <button disabled={busy||!evaluationAttempt.current} onClick={()=>void execute("evaluation",true)}>核对冻结评测</button>
    <button disabled={busy||!!evaluationAttempt.current} onClick={()=>{setReviewer("");setBasis("");setJudgments(old=>old.map(j=>({...j,outcome:"unmeasured",basis:""})));setSavedEvaluation("");setMessage("仅清空本地判断；已登记历史不变。");}}>清空本地评测</button>
    <button disabled={busy} onClick={()=>void list("evaluation")}>读取评测历史</button><button disabled={busy||!evaluationCursor} onClick={()=>void list("evaluation",true)}>下一页评测</button>
    {evaluationRows.map(row=><HistoryRow key={row.document_id} row={row} busy={busy} verb="查看评测" onOpen={v=>void openHistory(row,v)}/>)}
    {historical&&historyValue&&<section aria-label="固定历史评测"><p>{historical.document_id} · v{historical.version}</p><p>任务：{historyValue.task_id} · 人工署名：{historyValue.reviewer}</p><p>{historyValue.basis}</p><p>{historyValue.outcome}</p><ul>{historyValue.judgments.map(j=><li key={j.criterion_id}>{j.criterion_id} · {j.outcome} · {j.basis}</li>)}</ul><RawReceiptButton label="历史人工评测" payload={historical}/></section>}
  </section>;
}
function HistoryRow({row,busy,verb,onOpen}:{row:MachineDocumentSummaryDto;busy:boolean;verb:string;onOpen:(version:number)=>void}) {
  const [version,setVersion]=useState(String(row.version));
  return <div><span>{row.title} · {row.document_id} · 最新列表 v{row.version}</span><label>{verb}版本 {row.document_id}<input type="number" min={1} value={version} disabled={busy} onChange={e=>setVersion(e.target.value)}/></label><button disabled={busy||!Number.isInteger(Number(version))||Number(version)<1||Number(version)>row.version} onClick={()=>onOpen(Number(version))}>{verb} {row.title}</button></div>;
}
