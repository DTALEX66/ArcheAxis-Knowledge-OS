import { AaosDialog } from "../design-system/AaosPrimitives";
import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { TeachingRecord, RecordView, RecordPage, WriteReceipt, ExchangeBundle, WithdrawalReceipt, ImportReceipt } from "../api/generated/teaching-contract";
import { assertTeachingDto } from "../api/generated/teaching-contract";
import { coreFailureReason } from "../presentation/labels";
import { CanonicalLearningSpace } from "./CanonicalLearningSpace";
import type { ObjectTrailLevel } from "../components/NavTrail";

type Kind = TeachingRecord["kind"];
type Knowledge = { knowledge_id: string; head: string };
type Course = { manifest_id: string; title: string; stale: boolean };
const pages = [ ["08", "教学需求"], ["09", "表达方案"], ["10", "交付与版本"], ["11", "练习 / Teach-back"], ["12", "反馈与修订"], ["16", "人工交换"] ] as const;
const kinds: Record<string, Kind[]> = { "08": ["observation", "requirement"], "09": ["proposal"], "10": ["delivery"], "11": ["teach_back"], "12": ["feedback", "revision"], "16": [] };
const names: Record<Kind, string> = { observation:"观察", requirement:"需求", proposal:"表达方案", delivery:"交付", teach_back:"Teach-back", feedback:"反馈", revision:"修订" };
const feedbackClasses = ["professional_basis", "evidence_fidelity", "recognition_quality", "expression_fit", "operation_fault", "mastery", "ai_qualification"] as const;
const parents: Partial<Record<Kind, Kind[]>> = { requirement:["observation"], proposal:["requirement"], delivery:["proposal","revision"], teach_back:["delivery"], feedback:["delivery"], revision:["feedback"] };
function object(value: unknown): Record<string, unknown> { if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid teaching response"); return value as Record<string, unknown>; }
function view(value: unknown): RecordView {
  return assertTeachingDto<RecordView>("RecordView",value);
}
function boundedId(prefix: string) { return `${prefix}_${crypto.randomUUID()}`; }
function blank(kind: Kind) { return { kind, purpose:"", content:"", scope:"personal" as TeachingRecord["scope"], privacy:"local_only" as TeachingRecord["privacy"], assisted:false, feedback_class: null as TeachingRecord["feedback_class"], rubric_version:"", producer_kind:"human_authored" as TeachingRecord["producer_kind"] }; }

/** Manual records share one canonical Core state; a record never constitutes a score. */
export function CanonicalTeachingSpace({pageId="08", onOpenPage, onTrail}: {pageId?:string; onOpenPage?:(id:string)=>void; onTrail?:(levels:readonly ObjectTrailLevel[])=>void}) {
  const [items,setItems]=useState<RecordView[]>([]), [cursor,setCursor]=useState<string|null>(null), [loaded,setLoaded]=useState(false);
  const [selected,setSelected]=useState<RecordView|null>(null), [draft,setDraft]=useState(()=>blank(kinds[pageId]?.[0] ?? "observation"));
  const [knowledge,setKnowledge]=useState<Knowledge|null>(null), [query,setQuery]=useState(""), [results,setResults]=useState<Knowledge[]>([]);
  const [courses,setCourses]=useState<Course[]>([]), [courseId,setCourseId]=useState<string|null>(null), [itemKey,setItemKey]=useState<string|null>(null), [assessmentId,setAssessmentId]=useState<string|null>(null);
  const [preparation,setPreparation]=useState<{document_id:string;version:number}|null>(null), [savedPreparation,setSavedPreparation]=useState("");
  const [parent,setParent]=useState<RecordView|null>(null), [busy,setBusy]=useState(false), [message,setMessage]=useState(""), [failure,setFailure]=useState<string|null>(null);
  const [pending,setPending]=useState(false), [withdrawReason,setWithdrawReason]=useState(""), [withdrawDialog,setWithdrawDialog]=useState(false);
  const [originalExchange,setOriginalExchange]=useState<File|null>(null);
  const [bundle,setBundle]=useState<ExchangeBundle|null>(null), [preview,setPreview]=useState<{record_count:number;duplicate_count:number;package_sha256:string}|null>(null), [exchangeDialog,setExchangeDialog]=useState(false), [practice,setPractice]=useState(false);
  const lock=useRef(false), epoch=useRef(0), listEpoch=useRef(0), fileEpoch=useRef(0);
  const createAttempt=useRef<TeachingRecord|null>(null), withdrawalAttempt=useRef<{schema:"archeaxis.teaching-withdrawal/v2";withdrawal_id:string;record_id:string;reason:string}|null>(null);
  const preparationAttempt=useRef<{operation:"document_create"|"document_draft";payload:Record<string,unknown>;snapshot:string}|null>(null);
  const currentSelection=useRef<string|null>(null), currentBundle=useRef<ExchangeBundle|null>(null);
  function note(text:string) {setMessage(text);setFailure(null);}
  function merge(item:RecordView) {setItems(previous=>[item,...previous.filter(row=>row.record.record_id!==item.record.record_id)]);}
  async function load(next?:string) {
    const request=++listEpoch.current;
    try { const value=object(await coreCommand<RecordPage>("teaching_list",next?{cursor:next}:{}));
      if(!Array.isArray(value.items) || !(value.next_cursor===null || typeof value.next_cursor==="string")) throw new Error("invalid teaching page");
      const rows=value.items.map(view); if(new Set(rows.map(item=>item.record.record_id)).size!==rows.length) throw new Error("duplicate teaching page");
      if(request===listEpoch.current) {setItems(previous=>next?[...previous,...rows.filter(item=>!previous.some(row=>row.record.record_id===item.record.record_id))]:rows);setCursor(value.next_cursor as string|null);setLoaded(true);}
    } catch(error) {if(request===listEpoch.current){setLoaded(false);setMessage("教学记录读取失败；不会把失败显示为空列表。");setFailure(coreFailureReason(error));}}
  }
  useEffect(()=>{void load();return()=>{epoch.current++;listEpoch.current++;fileEpoch.current++;};},[]);
  useEffect(()=>{epoch.current++;if(!createAttempt.current){setDraft(previous=>({...previous,kind:kinds[pageId]?.[0] ?? previous.kind}));}setPractice(false);},[pageId]);
  useEffect(()=>{const dirty=JSON.stringify({purpose:draft.purpose,content:draft.content})!==savedPreparation&&(!!draft.content||!!draft.purpose)||pending;window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:dirty}));},[draft.content,draft.purpose,pending,savedPreparation]);
  useEffect(()=>()=>{window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:false}));},[]);
  useEffect(()=>{onTrail?.(selected?[{id:`teaching:${selected.record.record_id}`,label:names[selected.record.kind],region:"teaching"}]:[]);},[selected,onTrail]);
  async function run(task:(request:number)=>Promise<void>) {if(lock.current)return;lock.current=true;setBusy(true);setFailure(null);const request=epoch.current;try{await task(request);}catch(error){if(request===epoch.current){setMessage("操作未确认完成，请保留文字并重试；不会显示为成功。");setFailure(coreFailureReason(error));}}finally{lock.current=false;setBusy(false);}}
  function changeSelection() {epoch.current++;setSelected(null);currentSelection.current=null;setAssessmentId(null);setPractice(false);withdrawalAttempt.current=null;setWithdrawDialog(false);}
  async function open(row:RecordView) {
    if(lock.current||pending)return;changeSelection();const request=epoch.current;currentSelection.current=row.record.record_id;
    await run(async()=>{const saved=view(await coreCommand<RecordView>("teaching_get",{record_id:row.record.record_id}));if(saved.record.record_id!==row.record.record_id)throw new Error("teaching identity changed");if(request===epoch.current){setSelected(saved);merge(saved);note("已读取实际教学记录；此记录不计分。");}});
  }
  function beginChild(row:RecordView) {
    if(lock.current||pending)return;
    const allowed=parents[draft.kind];if(row.withdrawn || !allowed?.includes(row.record.kind)){note("此记录不能作为当前类型的父记录。请保留真实父关系，撤回记录不能继续派生。");return;}
    changeSelection();setParent(row);setKnowledge({knowledge_id:row.record.knowledge_id,head:`父记录绑定知识 ${row.record.knowledge_id}`});setCourseId(row.record.course_id);setItemKey(null);setAssessmentId(null);note("已选择实际父记录并保留其知识、课程版本；尚未保存新记录。");
  }
  async function search() {await run(async request=>{const value=object(await coreCommand("search",{q:query,active_only:true}));if(!Array.isArray(value.items))throw new Error("invalid knowledge search");const found=value.items.map(object);if(found.some(row=>typeof row.knowledge_id!=="string"||typeof row.head!=="string"))throw new Error("invalid knowledge identity");if(request===epoch.current){setResults(found as Knowledge[]);note(found.length?"请选择并核对来源知识。":"没有匹配的来源知识。");}});}
  async function chooseKnowledge(row:Knowledge) {if(pending||lock.current)return;changeSelection();await run(async request=>{const saved=object(await coreCommand("knowledge_get",{id:row.knowledge_id}));if(saved.knowledge_id!==row.knowledge_id||saved.status!=="accepted")throw new Error("teaching source knowledge is not accepted");const catalog=object(await coreCommand("course_list",{}));if(!Array.isArray(catalog.items))throw new Error("invalid course catalog");const catalogRows=catalog.items.map(object);if(catalogRows.some(row=>typeof row.manifest_id!=="string"||typeof row.title!=="string"||typeof row.stale!=="boolean"))throw new Error("invalid course catalog identity");if(request===epoch.current){setKnowledge(row);setParent(null);setCourseId(null);setItemKey(null);setCourses(catalogRows as Course[]);note("已核对接受状态与不可变知识身份。课程仍需选择后独立核对绑定。");}});}
  async function chooseCourse(id:string) {if(pending||lock.current)return;setAssessmentId(null);setItemKey(null);if(!id){setCourseId(null);return;}await run(async request=>{const saved=object(await coreCommand("course_get",{course_id:id})),manifest=object(saved.manifest);if(saved.stale!==false||manifest.manifest_id!==id||!Array.isArray(saved.bindings)||!Array.isArray(manifest.artifacts))throw new Error("invalid course binding");const bindings=saved.bindings.map(object);if(!knowledge||!bindings.some(row=>row.knowledge_id===knowledge.knowledge_id&&row.knowledge_version===knowledge.knowledge_id))throw new Error("course is bound to different knowledge");const artifact=manifest.artifacts.map(object).find(row=>row.artifact_type==="lesson"&&row.renderer==="native-lesson");if(!artifact||typeof artifact.artifact_id!=="string")throw new Error("no native lesson");if(request===epoch.current){setCourseId(id);setItemKey(`course:${id}:artifact:${artifact.artifact_id}`);note("课程与知识版本已核对。尚未声明学习成绩。");}});}
  async function readAssessment() {if(!itemKey)return;await run(async request=>{const saved=object(await coreCommand("assessment_get",{item_key:itemKey}));if(typeof saved.assessment_id!=="string"||saved.knowledge_id!==knowledge?.knowledge_id||saved.knowledge_version!==knowledge?.knowledge_id)throw new Error("assessment knowledge mismatch");if(request===epoch.current){setAssessmentId(saved.assessment_id);note("已读取真实学习问题身份；Teach-back记录仍不计分。");}});}
  async function savePreparation() {
    await run(async request=>{const editor_json={type:"doc",content:draft.content.split("\n").map(text=>({type:"paragraph",...(text?{content:[{type:"text",text}]}:{})}))};
      const attempt=preparationAttempt.current??{operation:preparation?"document_draft" as const:"document_create" as const,payload:preparation?{document_id:preparation.document_id,body:{expected_version:preparation.version,editor_json}}:{body:{create_request_id:boundedId("preparation"),title:draft.purpose.trim()||"教学准备草稿",editor_json}},snapshot:JSON.stringify({purpose:draft.purpose,content:draft.content})};
      preparationAttempt.current=attempt;
      const snapshot=attempt.snapshot;
      const result=object(await coreCommand(attempt.operation,attempt.payload));
      if(typeof result.document_id!=="string"||!Number.isInteger(result.version)||preparation&&result.document_id!==preparation.document_id)throw new Error("invalid preparation document receipt");
      const readback=object(await coreCommand("document_get",{document_id:result.document_id}));if(readback.document_id!==result.document_id||readback.version!==result.version)throw new Error("preparation readback mismatch");
      if(request===epoch.current){setPreparation({document_id:result.document_id,version:result.version as number});setSavedPreparation(snapshot);preparationAttempt.current=null;note("准备正文已保存并读回；允许缺少需求字段或正式知识绑定。登记版本化记录是另一步操作。");}
    });
  }
  async function save() {
    await run(async request=>{
      let record=createAttempt.current;
      if(!record){if(!knowledge||!draft.purpose.trim()||draft.purpose.length>512||!draft.content.trim()||draft.content.length>65536)throw new Error("knowledge, bounded purpose and content required");
        if(parents[draft.kind] && draft.kind!=="requirement" && !parent)throw new Error("parent required");
        if(parent && (!parents[draft.kind]?.includes(parent.record.kind)||parent.withdrawn))throw new Error("invalid parent kind");
        if(draft.kind==="feedback"&&!draft.feedback_class)throw new Error("feedback class required");
        record={schema:"archeaxis.teaching-record/v2",record_id:boundedId("teaching"),kind:draft.kind,knowledge_id:knowledge.knowledge_id,knowledge_version:knowledge.knowledge_id,course_id:courseId,parent_id:parent?.record.record_id??null,purpose:draft.purpose.trim(),scope:draft.scope,privacy:draft.privacy,content:draft.content,feedback_class:draft.kind==="feedback"?draft.feedback_class:null,assessment_id:draft.kind==="teach_back"?assessmentId:null,rubric_version:draft.rubric_version.trim()||null,assisted:draft.assisted,producer_kind:draft.producer_kind};
        createAttempt.current=record;setPending(true);
      }
      const receipt=object(await coreCommand<WriteReceipt>("teaching_create",{body:record}));const saved=view(receipt.item);
      if(saved.record.record_id!==record.record_id||typeof receipt.duplicate!=="boolean")throw new Error("create identity changed");
      if(request===epoch.current){merge(saved);setSelected(saved);currentSelection.current=saved.record.record_id;setDraft(blank(record.kind));setParent(null);createAttempt.current=null;setPending(false);note(receipt.duplicate?"已读回同一客户端记录，未重复创建。":"教学记录已保存；仍为不计分的人工作业记录。");}
    });
  }
  async function exportSelected() {if(!selected)return;const target=selected;await run(async request=>{if(target.record.scope!=="manual_exchange"||target.record.privacy!=="authorized_export")throw new Error("record is not authorized for manual exchange");const value=await coreCommand<ExchangeBundle>("teaching_export",{record_id:target.record.record_id});const result=object(value);if(result.schema!=="archeaxis.teaching-exchange/v2"||!Array.isArray(result.records)||typeof result.package_sha256!=="string")throw new Error("invalid exchange export");if(request!==epoch.current)return;const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:"application/json"}));const link=document.createElement("a");link.href=url;link.download=`teaching-${target.record.record_id}.json`;link.click();URL.revokeObjectURL(url);note("已导出人工交换包；没有发送给任何peer或执行外部材料。");});}
  function downloadOriginalExchange() {if(!originalExchange)return;const url=URL.createObjectURL(originalExchange);const link=document.createElement("a");link.href=url;link.download=originalExchange.name;link.click();URL.revokeObjectURL(url);note("已下载所选原始文件；未规范化内容、未登记或导入教学记录。");}
  async function chooseFile(file:File|undefined) {setOriginalExchange(file??null);const request=++fileEpoch.current;setBundle(null);currentBundle.current=null;setPreview(null);setExchangeDialog(false);if(!file)return;if(file.size>4*1024*1024){note("交换文件过大，请保留原文件并按Core合同检查。");return;}try{const value=JSON.parse(await file.text());if(request!==fileEpoch.current)return;const parsed=object(value);if(parsed.schema!=="archeaxis.teaching-exchange/v2"||!Array.isArray(parsed.records)||typeof parsed.package_sha256!=="string")throw new Error("invalid exchange bundle");currentBundle.current=value as ExchangeBundle;setBundle(value as ExchangeBundle);note("已读取用户选择的JSON；尚未通过Core校验、未导入或执行。");}catch(error){if(request===fileEpoch.current){setMessage("交换JSON读取失败；未导入。");setFailure(coreFailureReason(error));}}}
  async function previewImport() {const target=currentBundle.current;if(!target)return;const fileRequest=fileEpoch.current;await run(async()=>{const result=object(await coreCommand("teaching_import_preview",{body:target}));if(result.valid!==true||!Number.isInteger(result.record_count)||!Number.isInteger(result.duplicate_count)||result.package_sha256!==target.package_sha256)throw new Error("invalid exchange preview");if(fileRequest===fileEpoch.current&&currentBundle.current===target){setPreview(result as {record_count:number;duplicate_count:number;package_sha256:string});setExchangeDialog(true);note("Core只读校验已通过；请审阅内容来源与数量后确认人工导入。");}});}
  async function importBundle() {const target=currentBundle.current;if(!target||!preview||target.package_sha256!==preview.package_sha256)return;const fileRequest=fileEpoch.current;await run(async()=>{const result=object(await coreCommand<ImportReceipt>("teaching_import",{body:target}));if(!Array.isArray(result.items)||!Number.isInteger(result.duplicate_count)||result.package_sha256!==target.package_sha256)throw new Error("invalid import receipt");const imported=result.items.map(view);if(fileRequest===fileEpoch.current&&currentBundle.current===target){for(const item of imported)merge(item);setExchangeDialog(false);setPreview(null);note(`人工导入已读回 ${imported.length} 条，重复 ${result.duplicate_count} 条。外部材料未执行，未写入掌握或AI资格。`);}});}
  async function withdraw() {if(!selected||!withdrawReason.trim())return;const target=selected;await run(async request=>{const body=withdrawalAttempt.current??{schema:"archeaxis.teaching-withdrawal/v2" as const,withdrawal_id:boundedId("withdrawal"),record_id:target.record.record_id,reason:withdrawReason.trim()};withdrawalAttempt.current=body;await coreCommand<WithdrawalReceipt>("teaching_withdraw",{body});const saved=view(await coreCommand("teaching_get",{record_id:target.record.record_id}));if(saved.record.record_id!==target.record.record_id||!saved.withdrawn)throw new Error("withdrawal not read back");if(request===epoch.current){merge(saved);setSelected(saved);setWithdrawDialog(false);withdrawalAttempt.current=null;setWithdrawReason("");note("撤回已读回；保留历史记录与版本，没有删除原知识或课程。");void load();}});}
  const pageKinds=kinds[pageId]??[], visible=pageId==="16"?items:items.filter(row=>pageKinds.includes(row.record.kind));
  const eligible=items.filter(row=>!row.withdrawn&&parents[draft.kind]?.includes(row.record.kind));
  return <section className="ui-content-panel ui-teaching-journey" aria-label="手工教学旅程">
    <div className="ui-content-tabs">{pages.map(([id,label])=><button key={id} aria-pressed={pageId===id} disabled={busy||pending} onClick={()=>onOpenPage?.(id)}>{label}</button>)}</div>
    <p>手工记录保存实际父关系、知识和课程版本；所有记录 not_scored。人工反馈不改变掌握或 AI 资格。Core 按真实宿主身份决定写入权限，内容来源不是行为者证明。</p>
    <div className="ui-content-main-side"><div>
      <h2>{pages.find(([id])=>id===pageId)?.[1]??"教学旅程"}</h2>{message?<p role="status">{message}</p>:null}{failure?<p role="alert">{failure}</p>:null}<button disabled={busy} onClick={()=>void load()}>刷新教学记录</button>
      {loaded&&!visible.length?<p>本页尚无已保存记录；可读取实际来源后创建。</p>:null}
      <ul>{visible.map(row=><li key={row.record.record_id}><button disabled={busy||pending} onClick={()=>void open(row)}>{names[row.record.kind]} · {row.record.purpose}</button><small>{row.withdrawn?"已撤回 · 历史只读":"已保存 · 不计分"} · {row.record.record_id}</small></li>)}</ul>
      {cursor?<button disabled={busy} onClick={()=>void load(cursor)}>读取更多教学记录</button>:null}
      {selected?<article aria-label="已保存教学记录"><h3>{names[selected.record.kind]} · {selected.record.purpose}</h3><p style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{selected.record.content}</p><dl><dt>记录身份</dt><dd>{selected.record.record_id}</dd><dt>父关系</dt><dd>{selected.record.parent_id??"根记录"}</dd><dt>知识版本</dt><dd>{selected.record.knowledge_version}</dd><dt>课程身份</dt><dd>{selected.record.course_id??"未绑定"}</dd><dt>学习问题 / 辅助</dt><dd>{selected.record.assessment_id??"未绑定"} / {selected.record.assisted?"使用辅助":"未声明辅助"}</dd><dt>反馈分类 / 评分</dt><dd>{selected.record.feedback_class??"不适用"} / {selected.scoring_status}</dd><dt>内容来源 / 撤回</dt><dd>{selected.record.producer_kind} / {selected.withdrawn?"已撤回":"有效"}</dd></dl>
        <button disabled={busy||selected.withdrawn||selected.record.scope!=="manual_exchange"||selected.record.privacy!=="authorized_export"} onClick={()=>void exportSelected()}>导出人工交换 JSON</button><AaosDialog role="alertdialog" title="确认撤回教学记录" description="撤回保留历史；取消不执行写入。" open={withdrawDialog} onOpenChange={open=>{if(!busy)setWithdrawDialog(open);}} trigger={<button disabled={busy||selected.withdrawn}>审阅撤回记录</button>}><p>撤回 {selected.record.record_id}，保留知识、课程与历史，不删除原记录。</p><label>撤回原因<textarea disabled={busy||!!withdrawalAttempt.current} value={withdrawReason} onChange={event=>setWithdrawReason(event.target.value)}/></label><button disabled={busy||!withdrawReason.trim()} onClick={()=>void withdraw()}>确认撤回</button><button disabled={busy} onClick={()=>{setWithdrawDialog(false);}}>取消撤回</button></AaosDialog>
      </article>:null}
      {pageId!=="16"?<form onSubmit={event=>{event.preventDefault();void save();}} aria-label="创建教学记录">
        <fieldset disabled={busy||pending}><legend>登记版本化记录（独立于普通准备草稿）</legend><label>记录类型<select value={draft.kind} onChange={event=>{setDraft(previous=>({...previous,kind:event.target.value as Kind}));setParent(null);}}>{pageKinds.map(kind=><option key={kind} value={kind}>{names[kind]}</option>)}</select></label>
          <label>父记录<select value={parent?.record.record_id??""} onChange={event=>{const row=eligible.find(item=>item.record.record_id===event.target.value);if(row)beginChild(row);else setParent(null);}}><option value="">请选择真实父记录</option>{eligible.map(row=><option key={row.record.record_id} value={row.record.record_id}>{names[row.record.kind]} · {row.record.purpose}</option>)}</select></label>
          <label>用途<input maxLength={512} value={draft.purpose} onChange={event=>setDraft(previous=>({...previous,purpose:event.target.value}))}/></label><label>内容<textarea maxLength={65536} rows={8} value={draft.content} onChange={event=>setDraft(previous=>({...previous,content:event.target.value}))}/></label>
          <label>范围<select value={draft.scope} onChange={event=>setDraft(previous=>({...previous,scope:event.target.value as TeachingRecord["scope"]}))}><option value="personal">个人记录</option><option value="manual_exchange">人工交换</option></select></label><label>隐私<select value={draft.privacy} onChange={event=>setDraft(previous=>({...previous,privacy:event.target.value as TeachingRecord["privacy"]}))}><option value="local_only">仅本地</option><option value="authorized_export">授权导出</option></select></label>
          <label><input type="checkbox" checked={draft.assisted} onChange={event=>setDraft(previous=>({...previous,assisted:event.target.checked}))}/>使用了辅助（不自动判定行为者）</label><label>内容来源声明（不授予行为者权限）<select value={draft.producer_kind} onChange={event=>setDraft(previous=>({...previous,producer_kind:event.target.value as TeachingRecord["producer_kind"]}))}><option value="human_authored">人工撰写</option><option value="external_material">外部材料</option><option value="machine_generated">机器生成</option></select></label><label>Rubric版本<input value={draft.rubric_version} onChange={event=>setDraft(previous=>({...previous,rubric_version:event.target.value}))}/></label>
          {draft.kind==="feedback"?<label>反馈分类<select value={draft.feedback_class??""} onChange={event=>setDraft(previous=>({...previous,feedback_class:event.target.value as TeachingRecord["feedback_class"]}))}><option value="">请选择</option>{feedbackClasses.map(value=><option key={value}>{value}</option>)}</select></label>:null}
        </fieldset><p>知识：{knowledge?.knowledge_id??"尚未选择"} · 课程：{courseId??"未绑定"} · 学习问题：{assessmentId??"未绑定"}</p>
        <button disabled={busy||pending} type="button" onClick={()=>void savePreparation()}>保存准备正文草稿</button><p>普通准备正文可先保存，不要求完整需求、父记录或知识绑定。{preparation?`已保存文档 ${preparation.document_id} · v${preparation.version}`:"尚未保存准备正文"}</p><button disabled={busy} type="submit">{pending?"重试同一记录":"登记版本化记录"}</button>{pending?<p role="status">上次写入尚未确认；重试保持相同客户端身份和原内容，编辑暂冻结。</p>:null}
      </form>:<section aria-label="人工交换导入"><h3>用户选择 JSON → Core 只读预检 → 审阅导入</h3><input aria-label="选择人工交换 JSON" type="file" accept="application/json,.json" disabled={busy} onChange={event=>void chooseFile(event.target.files?.[0])}/><AaosDialog role="alertdialog" title="确认人工交换导入" description="Core预检只读；明确确认后才导入。" open={exchangeDialog} onOpenChange={open=>{if(!open&&!busy)setExchangeDialog(false);}} trigger={<button disabled={busy||!bundle} onClick={()=>void previewImport()}>Core 预检交换包</button>}>{preview?<><p>Core预检 {preview.record_count} 条，重复 {preview.duplicate_count} 条。包 {preview.package_sha256}。导入不会发送peer或执行材料。</p><button disabled={busy} onClick={()=>void importBundle()}>确认人工导入</button><button disabled={busy} onClick={()=>setExchangeDialog(false)}>取消导入</button></>:null}</AaosDialog>{originalExchange?<><button type="button" onClick={downloadOriginalExchange}>下载所选原始交换文件</button><p>原件：{originalExchange.name} · {originalExchange.size} 字节。下载保留未知字段或损坏JSON；不是规范记录导入。</p></>:null}<p>没有文件路径权限、不自动运行外部材料。损坏、身份冲突或权限不足由Core拒绝，重复包以Core回执为准。</p></section>}
    </div><aside className="ui-content-panel" aria-label="真实教学来源"><h3>选择实际来源</h3><form onSubmit={event=>{event.preventDefault();void search();}}><label>查找来源知识<input value={query} disabled={busy||pending} onChange={event=>setQuery(event.target.value)}/></label><button disabled={busy||pending}>搜索来源知识</button></form><ul>{results.map(row=><li key={row.knowledge_id}><button disabled={busy||pending} onClick={()=>void chooseKnowledge(row)}>{row.head}</button></li>)}</ul>
      <label>绑定实际课程<select disabled={busy||pending||!knowledge||!!parent} value={courseId??""} onChange={event=>void chooseCourse(event.target.value)}><option value="">不绑定课程</option>{courses.map(row=><option disabled={row.stale} key={row.manifest_id} value={row.manifest_id}>{row.title}{row.stale?" · 来源失效":""}</option>)}</select></label>
      {parent&&courseId?<button disabled={busy} onClick={()=>void chooseCourse(courseId)}>核对父课程并读取练习入口</button>:null}
      {pageId==="11"?<><button disabled={busy||!itemKey||pending} onClick={()=>void readAssessment()}>读取绑定的真实学习问题</button><button disabled={busy||!itemKey} onClick={()=>setPractice(value=>!value)}>打开真实练习队列</button><p>独立作答/成绩记录由真实学习合同承接；Teach-back只是手工记录，不调用旧Python评分。</p></>:null}
    </aside></div>
    {practice&&itemKey?<CanonicalLearningSpace initialItemKey={itemKey} onTrail={onTrail}/>:null}



  </section>;
}
