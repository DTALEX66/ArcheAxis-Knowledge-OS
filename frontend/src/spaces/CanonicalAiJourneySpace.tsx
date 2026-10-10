import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { assertCoreDto, type ContextConsumptionDto, type ContextGrantDto, type DocumentDto, type MachineDocumentSummaryDto, type MachineDocumentsPageDto } from "../api/generated/core-contract";
import type { AssetPacketRequest } from "../api/generated/ai-asset-contract";
import type { AssetConsumption } from "../presentation/assetConsumption";
import { AssetMachineSlots } from "../components/AssetMachineSlots";
import { MachineAnswerPanel } from "../components/MachineAnswerPanel";
import { MachineEvaluationPanel } from "../components/MachineEvaluationPanel";
import { failureMessage } from "../presentation/labels";
import { RawReceiptButton } from "../components/DiagnosticConsole";

type Selection = { document: DocumentDto; grant: ContextGrantDto; snapshot: ContextConsumptionDto; current: boolean };
const record = (value: unknown): Record<string,unknown> => { if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("上下文格式不兼容"); return value as Record<string,unknown>; };
function readGrant(document: DocumentDto): ContextGrantDto { return assertCoreDto<ContextGrantDto>("ContextGrantDto",record(record(document.editor_json).attrs).archeaxis_context_grant); }
function snapshot(document: DocumentDto, grant: ContextGrantDto): ContextConsumptionDto { return {document_id:document.document_id,version:document.version,content_sha256:document.content_sha256,purpose:grant.purpose}; }
function same(a: ContextConsumptionDto,b: ContextConsumptionDto) { return a.document_id===b.document_id && a.version===b.version && a.content_sha256===b.content_sha256 && a.purpose===b.purpose; }
function eligible(selection: Selection | null, operation: "answer"|"retest", knowledgeId: string|null) {
  return !!selection && selection.current && selection.grant.state==="granted" && selection.grant.consumer==="local-machine"
    && selection.grant.operations.includes(operation) && !!knowledgeId && selection.grant.knowledge_id===knowledgeId
    && (selection.grant.expires_at===null || selection.grant.expires_at>Math.floor(Date.now()/1000));
}

/** No inferred knowledge/permission/model: only exact persisted consumption snapshots. */
export function CanonicalAiJourneySpace({ initialConsumption, initialAssetConsumption, onTask, onCandidate, onOpenContext }: {
  initialConsumption?: ContextConsumptionDto; initialAssetConsumption?:AssetPacketRequest; onTask?: (id:string)=>void; onCandidate?: (id:string)=>void;
  onOpenContext?: ()=>void;
}) {
  const [rows,setRows]=useState<MachineDocumentSummaryDto[]>([]),[cursor,setCursor]=useState<string|null>(null);
  const [loaded,setLoaded]=useState(false),[listing,setListing]=useState(false),[reading,setReading]=useState(false);
  const [error,setError]=useState<string|null>(null),[message,setMessage]=useState("");
  const [original,setOriginal]=useState<Selection|null>(null),[corrected,setCorrected]=useState<Selection|null>(null);
  const [candidateId,setCandidateId]=useState<string|null>(null);
  const [latestTask,setLatestTask]=useState<string>();
  const [assetAnswer,setAssetAnswer]=useState<AssetConsumption|null>(null),[assetRetest,setAssetRetest]=useState<AssetConsumption|null>(null);
  const mounted=useRef(true),listEpoch=useRef(0),readEpoch=useRef(0),dirty=useRef(new Set<string>());
  const initialKey=initialConsumption ? JSON.stringify(initialConsumption) : "";
  function blocked() { if (dirty.current.size) { setMessage("当前回答或纠正草稿尚未确认；请先提交或核对，再切换授权。"); return true; } return false; }
  async function list(next?:string) {
    const seq=++listEpoch.current;setListing(true);setError(null);
    try {
      const page=await coreCommand<MachineDocumentsPageDto>("machine_contexts_list",next?{cursor:next}:{});
      if(!Array.isArray(page.items) || new Set(page.items.map(row=>row.document_id)).size!==page.items.length
        || (page.next_cursor!==null && typeof page.next_cursor!=="string") || (next && page.next_cursor===next)) throw new Error("上下文分页身份不兼容");
      if(!mounted.current || seq!==listEpoch.current)return;
      setRows(previous=>next?[...previous,...page.items.filter(row=>!previous.some(old=>old.document_id===row.document_id))]:page.items);setCursor(page.next_cursor);setLoaded(true);
    } catch(reason) {if(mounted.current && seq===listEpoch.current)setError(failureMessage(reason));}
    finally {if(mounted.current && seq===listEpoch.current)setListing(false);}
  }
  async function select(which:"original"|"corrected",id:string,expected?:ContextConsumptionDto,refresh=false) {
    if(!refresh && blocked())return;
    const seq=++readEpoch.current;setReading(true);setError(null);
    try {
      const document=await coreCommand<DocumentDto>("document_get",{document_id:id});
      if(document.document_id!==id)throw new Error("上下文读回身份不符");
      const grant=readGrant(document),actual=snapshot(document,grant);
      if(expected && !same(expected,actual))throw new Error("消费快照已变化；请在项目记忆页核对当前版本后重新选择");
      if(!mounted.current || seq!==readEpoch.current)return;
      if(!refresh && blocked())return;
      const value:Selection={document,grant,snapshot:actual,current:true};
      if(which==="original"){setOriginal(value);if(original?.grant.knowledge_id!==grant.knowledge_id){setCandidateId(null);setCorrected(null);}}
      else setCorrected(value);
      setMessage(grant.state==="revoked"?"授权已撤回；历史仍可读取，新推理不可执行。":"已读取实际对象及消费快照；是否允许执行仍由 Core 校验。");
    } catch(reason) {
      if(mounted.current && seq===readEpoch.current){setError(failureMessage(reason));if(refresh){if(which==="original")setOriginal(old=>old?{...old,current:false}:null);else setCorrected(old=>old?{...old,current:false}:null);}}
    } finally {if(mounted.current && seq===readEpoch.current)setReading(false);}
  }
  useEffect(()=>{
    mounted.current=true;void list();
    const listener=(event:Event)=>{const value=(event as CustomEvent<{owner?:string;dirty?:boolean}>).detail;if(!value?.owner)return;if(value.dirty)dirty.current.add(value.owner);else dirty.current.delete(value.owner);};
    window.addEventListener("archeaxis-draft-dirty",listener);
    return ()=>{mounted.current=false;listEpoch.current++;readEpoch.current++;window.removeEventListener("archeaxis-draft-dirty",listener);};
  },[]);
  useEffect(()=>{if(initialConsumption)void select("original",initialConsumption.document_id,initialConsumption);},[initialKey]);
  const knowledgeId=original?.grant.knowledge_id??null;
  const answerPermission=eligible(original,"answer",knowledgeId)?original!.snapshot:undefined;
  const retestPermission=eligible(corrected,"retest",candidateId)?corrected!.snapshot:undefined;
  function receiveCandidate(id:string){setCandidateId(id);onCandidate?.(id);}
  function receiveTask(id:string){setLatestTask(id);onTask?.(id);}
  return <section aria-label="纠正、评测与复测" data-section="ai-journey">
    <h2>纠正、评测与复测</h2><p>原问题、机器回答和纠正候选分别保留；采用或调用成功都不等于独立评测通过。缺模型时保留草稿与历史，不自动下载。</p>
    {onOpenContext?<button onClick={onOpenContext}>返回项目记忆与授权</button>:null}
    <section aria-label="实际上下文授权">
      <h3>选择已保存授权</h3><button disabled={listing} onClick={()=>void list()}>刷新上下文列表</button>
      {listing?<p role="status">正在读取实际上下文…</p>:null}
      {loaded && !rows.length?<p>尚无已登记上下文。可在项目记忆页先保存候选，授权另行决定。</p>:null}
      <ul>{rows.map(row=><li key={row.document_id}><span>{row.title} · v{row.version}</span>{" "}<button disabled={reading} onClick={()=>void select("original",row.document_id)}>选择原知识授权 {row.title}</button>{" "}<button disabled={reading || !candidateId} onClick={()=>void select("corrected",row.document_id)}>选择纠正候选授权 {row.title}</button></li>)}</ul>
      {cursor?<button disabled={listing} onClick={()=>void list(cursor)}>读取更多上下文</button>:null}
    </section>
    {error?<p role="alert">{error}</p>:null}{message?<p role="status">{message}</p>:null}
    <div className="ai-journey-grants">{([original,corrected] as const).map((selection,index)=><section key={index} aria-label={index===0?"原知识授权快照":"纠正候选授权快照"}>
      <h3>{index===0?"原知识授权":"纠正候选授权"}</h3>{selection?<>
        <p>{selection.document.title} · v{selection.document.version} · {selection.grant.state}</p><p>用途：{selection.grant.purpose}</p>
        <p>知识：{selection.grant.knowledge_id??"尚未绑定"}；授权依据：{selection.grant.authorization_basis||"未填写"}</p>
        <p>有效期：{selection.grant.expires_at===null?"未设置到期时间":String(selection.grant.expires_at)}；范围：local-machine；操作：{selection.grant.operations.join(" / ")}</p>
        <p>{(index===0?answerPermission:retestPermission)?"当前快照可提交 Core 核验":"当前快照不允许该项新推理；历史只读保留。"}</p>
        <button disabled={reading} onClick={()=>void select(index===0?"original":"corrected",selection.document.document_id,selection.snapshot,true)}>核对此授权当前快照</button>
        <RawReceiptButton label={index===0?"原知识授权固定回执":"纠正候选授权固定回执"} payload={selection}/>
      </>:<p>尚未选择。{index===1?"实际纠正候选读回后再选择匹配其知识 ID 的授权。":"不会推测知识 ID 或授权。"}</p>}</section>)}</div>
    <AssetMachineSlots initial={initialAssetConsumption} onAnswer={setAssetAnswer} onRetest={setAssetRetest} blocked={blocked}/>
    {knowledgeId?<MachineAnswerPanel knowledgeId={knowledgeId} scoped contextGrant={answerPermission} retestContextGrant={retestPermission} assetScoped={!!assetAnswer} retestAssetScoped={!!assetRetest} assetContextGrant={assetAnswer?.current?assetAnswer.request:undefined} retestAssetContextGrant={assetRetest?.current?assetRetest.request:undefined} onTask={receiveTask} onCandidate={receiveCandidate}/>:<p>请先选择绑定真实知识的上下文对象；无绑定候选仍可在项目记忆页保存和阅读。</p>}
    <MachineEvaluationPanel taskId={latestTask}/>
    <p>固定 rubric 与人工比较由正式评测对象记录；此页不自动打分、不宣称模型资格或人类掌握。</p>
  </section>;
}
