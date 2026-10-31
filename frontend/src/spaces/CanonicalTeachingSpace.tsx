import { useDocumentWriteLease } from "../workspace/documentSessions";
import { useDraftOwner } from "../workspace/draftProtection";
import { useDraftRecoverySource } from "../workspace/draftRecovery";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { assertCoreDto, type DocumentDto, type DocumentSummaryDto, type DocumentsListDto } from "../api/generated/core-contract";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { sameValue } from "../presentation/exchangeProof";
import type { TeachingRecord, RecordView, RecordPage, WriteReceipt, ExchangeBundle, WithdrawalReceipt, ImportReceipt } from "../api/generated/teaching-contract";
import { assertTeachingDto } from "../api/generated/teaching-contract";
import { coreFailureReason } from "../presentation/labels";
import { KnowledgeCoursePanel } from "../components/KnowledgeCoursePanel";
import { TeachingStageWorkspace } from "../components/TeachingStageWorkspace";
import { CanonicalLearningSpace } from "./CanonicalLearningSpace";
import type { ObjectTrailLevel } from "../components/NavTrail";
import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import type { TeachingDraft } from "../presentation/coreWorkingState";

import {resolveLearningJourney,type LearningJourneyTarget} from "../presentation/learningJourney";
import {learningTitle} from "../presentation/learningTitle";
import {RawReceiptButton} from "../components/DiagnosticConsole";
import "./stitch-teaching.css";

type Kind = TeachingRecord["kind"];
type Knowledge = { knowledge_id: string; head: string };
type Course = { manifest_id: string; title: string; stale: boolean };
type PreparationEditor = {type:"doc";content:{type:"paragraph";attrs:{block_id:string};content?:{type:"text";text:string}[]}[]};
type PreparationAttempt = NonNullable<TeachingDraft["preparation_attempt"]>;
const pages = [ ["08", "教学需求"], ["09", "表达方案"], ["10", "交付与版本"], ["11", "练习 / Teach-back"], ["12", "反馈与修订"], ["16", "人工交换"] ] as const;
const kinds: Record<string, Kind[]> = { "08": ["observation", "requirement"], "09": ["proposal"], "10": ["delivery"], "11": ["teach_back"], "12": ["feedback", "revision"], "16": [] };
const names: Record<Kind, string> = { observation:"观察", requirement:"需求", proposal:"表达方案", delivery:"交付", teach_back:"Teach-back", feedback:"反馈", revision:"修订" };
const feedbackClasses = ["professional_basis", "evidence_fidelity", "recognition_quality", "expression_fit", "operation_fault", "mastery", "ai_qualification"] as const;
const feedbackLabels: Record<typeof feedbackClasses[number], string> = { professional_basis:"专业依据", evidence_fidelity:"来源内容一致性", recognition_quality:"文字识别质量", expression_fit:"表达是否合适", operation_fault:"操作问题", mastery:"理解与掌握", ai_qualification:"AI 学习评估" };
const parents: Partial<Record<Kind, Kind[]>> = { requirement:["observation"], proposal:["requirement"], delivery:["proposal","revision"], teach_back:["delivery"], feedback:["delivery"], revision:["feedback"] };
function object(value: unknown): Record<string, unknown> { if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid teaching response"); return value as Record<string, unknown>; }
function view(value: unknown): RecordView {
  return assertTeachingDto<RecordView>("RecordView",value);
}
function boundedId(prefix: string) { return `${prefix}_${crypto.randomUUID()}`; }
function preparationText(doc:DocumentDto):string {
  const editor=object(doc.editor_json);
  if(doc.source_id!==null||doc.source_revision!==null||doc.revision_basis!==null||doc.title.length>512||editor.type!=="doc"||Object.keys(editor).some(key=>!["type","content"].includes(key))||!Array.isArray(editor.content)||!editor.content.length||doc.blocks.length!==editor.content.length||!/^[a-f0-9]{64}$/.test(doc.content_sha256))throw new Error("unsupported preparation document");
  const ids=new Set<string>();
  const lines=editor.content.map((value,index)=>{
    const node=object(value),attrs=object(node.attrs),block=doc.blocks[index];
    if(node.type!=="paragraph"||Object.keys(node).some(key=>!["type","attrs","content"].includes(key))||Object.keys(attrs).some(key=>key!=="block_id")||typeof attrs.block_id!=="string"||!attrs.block_id||ids.has(attrs.block_id))throw new Error("unsupported preparation paragraph");
    ids.add(attrs.block_id);
    if(node.content!==undefined&&(!Array.isArray(node.content)||node.content.length>1))throw new Error("unsupported preparation inline content");
    const child=Array.isArray(node.content)&&node.content.length?object(node.content[0]):null;
    if(child&&(child.type!=="text"||typeof child.text!=="string"||!child.text||Object.keys(child).some(key=>!["type","text"].includes(key))||(child.text as string).includes("\n")))throw new Error("unsupported preparation text");
    const text=child?child.text as string:"";
    if(block.block_id!==attrs.block_id||block.ordinal!==index||block.kind!=="paragraph"||block.codec_status!=="known"||block.text_projection!==text||!sameValue(block.node_json,node))throw new Error("preparation block mismatch");
    return text;
  });
  const text=lines.join("\n");
  if(text.length>65536||doc.text_projection!==lines.filter(Boolean).join("\n"))throw new Error("preparation projection mismatch");
  return text;
}
function blank(kind: Kind) { return { kind, purpose:"", content:"", scope:"personal" as TeachingRecord["scope"], privacy:"local_only" as TeachingRecord["privacy"], assisted:false, feedback_class: null as TeachingRecord["feedback_class"], rubric_version:"", producer_kind:"human_authored" as TeachingRecord["producer_kind"] }; }

type TeachingProps={initialItemKey?:string;pageId?:string;onOpenPage?:(id:string)=>void;onTrail?:(levels:readonly ObjectTrailLevel[])=>void};
/** A form belongs to one page/object and one acknowledged workspace epoch. */
export function CanonicalTeachingSpace(props:TeachingProps) {
  const working=useOptionalCoreWorkingState();
  const recoveryOwner=useDraftOwner("retained-teaching");
  useDraftRecoverySource(recoveryOwner, "保留的教学草稿", () => Object.entries(working?.state.teaching_drafts ?? {}).filter(([, value]) => value.pending_record || value.preparation_attempt || ((value.form.content || value.form.purpose) && JSON.stringify({purpose:value.form.purpose,content:value.form.content}) !== value.saved_preparation)).map(([key, value]) => ({ label: `教学 · ${key}`, text: JSON.stringify(value, null, 2) })));
  if(working&&(!working.server||working.server.recovery_requires_confirmation||working.status==="blocked"))return <section aria-label="教学草稿保全"><p role="status">{working.error??"请先检查并恢复待处理草稿；已保留的正文不会自动提交。"}</p>{Object.entries(working.state.teaching_drafts??{}).map(([key,draft])=><label key={key}>保留的教学正文 {key}<textarea readOnly value={draft.form.content}/></label>)}</section>;
  return <TeachingEditor key={working?`${working.server!.workspace_id}:${working.server!.restore_epoch}:${props.pageId??"08"}:${props.initialItemKey??""}`:undefined} {...props}/>;
}
/** Manual records share one canonical Core state; a record never constitutes a score. */
function TeachingEditor({pageId="08", onOpenPage, onTrail, initialItemKey}:TeachingProps) {
  const working=useOptionalCoreWorkingState(),draftKey=`${pageId}:${initialItemKey??""}`;
  const retained=working?.state.teaching_drafts?.[draftKey];
  const [journey,setJourney]=useState<LearningJourneyTarget>();
  const [returnedCourse,setReturnedCourse]=useState<LearningJourneyTarget>();
  const [courseRead,setCourseRead]=useState(0);
  useEffect(()=>{setReturnedCourse(undefined);},[pageId,initialItemKey]);
  const [journeyFailure,setJourneyFailure]=useState<string|null>(null);
  const journeyEpoch=useRef(0);
  function returnCourse(key:string,knowledgeId:string,knowledgeVersion:string) {
    if(!journey?.course||journey.item_key!==key||journey.knowledge_id!==knowledgeId||journey.knowledge_version!==knowledgeVersion||knowledgeVersion!==knowledgeId)return;
    setReturnedCourse(journey);setCourseRead(value=>value+1);
  }
  const [items,setItems]=useState<RecordView[]>([]), [cursor,setCursor]=useState<string|null>(null), [loaded,setLoaded]=useState(false);
  const [selected,setSelected]=useState<RecordView|null>(null), [draft,setDraft]=useState(()=>retained?.form??blank(kinds[pageId]?.[0] ?? "observation"));
  const [knowledge,setKnowledge]=useState<Knowledge|null>(()=>retained?.knowledge_id?{knowledge_id:retained.knowledge_id,head:`保留的来源 ${retained.knowledge_id}`}:null), [query,setQuery]=useState(""), [results,setResults]=useState<Knowledge[]>([]);
  const [courses,setCourses]=useState<Course[]>([]), [courseId,setCourseId]=useState<string|null>(retained?.course_id??null), [itemKey,setItemKey]=useState<string|null>(retained?.item_key??null), [assessmentId,setAssessmentId]=useState<string|null>(retained?.assessment_id??null);
  const [preparation,setPreparation]=useState<{document_id:string;version:number;title:string}|null>(retained?.preparation??null), [savedPreparation,setSavedPreparation]=useState(retained?.saved_preparation??"");
  const [preparationRows,setPreparationRows]=useState<DocumentSummaryDto[]>([]), [preparationCursor,setPreparationCursor]=useState<string|null>(null), [preparationListed,setPreparationListed]=useState(false);
  const documentLease=useDocumentWriteLease(preparation?.document_id);
  const dirtyOwner=useDraftOwner("teaching");
  const [parent,setParent]=useState<RecordView|null>(retained?.parent??null), [busy,setBusy]=useState(false), [message,setMessage]=useState(retained?"已恢复本地教学草稿；来源与父记录仍由正式保存合同核对，尚未登记新记录。":""), [failure,setFailure]=useState<string|null>(null);
  const [pending,setPending]=useState(Boolean(retained?.pending_record)), [withdrawReason,setWithdrawReason]=useState(""), [withdrawDialog,setWithdrawDialog]=useState(false);
  const [originalExchange,setOriginalExchange]=useState<File|null>(null);
  const [bundle,setBundle]=useState<ExchangeBundle|null>(null), [preview,setPreview]=useState<{record_count:number;duplicate_count:number;package_sha256:string}|null>(null), [exchangeDialog,setExchangeDialog]=useState(false), [practice,setPractice]=useState(false);
  const lock=useRef(false), epoch=useRef(0), listEpoch=useRef(0), fileEpoch=useRef(0);
  const createAttempt=useRef<TeachingRecord|null>(retained?.pending_record??null), withdrawalAttempt=useRef<{schema:"archeaxis.teaching-withdrawal/v2";withdrawal_id:string;record_id:string;reason:string}|null>(null);
  const preparationAttempt=useRef<PreparationAttempt|null>(retained?.preparation_attempt??null);
  const journalBaseline=useRef<string|null>(null);
  function teachingSnapshot():TeachingDraft {return {page_id:pageId as TeachingDraft["page_id"],context_item_key:initialItemKey??null,form:structuredClone(draft),knowledge_id:knowledge?.knowledge_id??null,course_id:courseId,item_key:itemKey,assessment_id:assessmentId,parent:parent?structuredClone(parent):null,preparation:preparation?{...preparation}:null,saved_preparation:savedPreparation,pending_record:createAttempt.current?structuredClone(createAttempt.current):null,...(preparationAttempt.current?{preparation_attempt:structuredClone(preparationAttempt.current)}:{})};}
  useDraftRecoverySource(dirtyOwner, "教学当前原稿", () => (((draft.purpose || draft.content) && JSON.stringify({purpose:draft.purpose,content:draft.content}) !== savedPreparation) || createAttempt.current || preparationAttempt.current || withdrawReason || withdrawalAttempt.current) ? [{ label: `教学当前输入 · ${pageId}`, text: JSON.stringify({ draft: teachingSnapshot(), ...(withdrawReason || withdrawalAttempt.current ? { withdrawal_reason: withdrawReason, pending_withdrawal: withdrawalAttempt.current } : {}) }, null, 2) }] : []);
  useEffect(()=>{
    if(!working||pageId==="16")return;
    const entry=teachingSnapshot(),json=JSON.stringify(entry);
    if(journalBaseline.current===json||!entry.form.content&&!entry.form.purpose&&!entry.pending_record&&!retained)return;
    try{working.session.rememberTeachingDraft(draftKey,entry);journalBaseline.current=json;}catch(error){setFailure(error instanceof Error?error.message:"教学草稿未保全，请保留当前正文。");}
  },[draft,knowledge,courseId,itemKey,assessmentId,parent,preparation,savedPreparation,pending,working?.session,draftKey]);
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
  useEffect(()=>{epoch.current++;if(!working&&!createAttempt.current){setDraft(previous=>({...previous,kind:kinds[pageId]?.[0] ?? previous.kind}));}setPractice(Boolean(initialItemKey&&["11","12"].includes(pageId)));},[pageId,initialItemKey]);
  useEffect(()=>{const request=++journeyEpoch.current;if(!initialItemKey||!["11","12"].includes(pageId)){setJourney(undefined);setJourneyFailure(null);return;}setJourney(previous=>previous?.item_key===initialItemKey?previous:undefined);setJourneyFailure(null);void resolveLearningJourney(initialItemKey).then(target=>{if(request!==journeyEpoch.current)return;setJourney(target);}).catch(error=>{if(request!==journeyEpoch.current)return;setJourney(undefined);setJourneyFailure(coreFailureReason(error)??"原学习项目的绑定回执不一致或不可用。");});return()=>{journeyEpoch.current++;};},[initialItemKey,pageId]);
  useEffect(()=>{const dirty=JSON.stringify({purpose:draft.purpose,content:draft.content})!==savedPreparation&&(!!draft.content||!!draft.purpose)||pending;window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:dirtyOwner,dirty}}));},[draft.content,draft.purpose,pending,savedPreparation,dirtyOwner]);
  useEffect(()=>()=>{window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:dirtyOwner,dirty:false}}));},[dirtyOwner]);
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
  async function savePreparation() {try{await documentLease.write(savePreparationDocument);}catch(error){setFailure(error instanceof Error?error.message:"此文档视图只读");}}
  function newPreparation() {
    if(lock.current||pending)return;
    if(preparationAttempt.current){note("上次准备正文保存尚未确认；请先重试同一请求，当前文字保留。");return;}
    setPreparation(null);setSavedPreparation("");note("当前用途与正文保留为新准备草稿；再次保存会创建新文档，原文档保留。");
  }
  async function listPreparations(more=false) {
    await run(async request=>{
      const page=assertCoreDto<DocumentsListDto>("DocumentsListDto",await coreCommand("documents_list",more&&preparationCursor?{cursor:preparationCursor}:{}));
      if(new Set(page.documents.map(doc=>doc.document_id)).size!==page.documents.length)throw new Error("duplicate document identity");
      if(request===epoch.current){setPreparationRows(previous=>more?[...previous,...page.documents.filter(doc=>!previous.some(row=>row.document_id===doc.document_id))]:page.documents);setPreparationCursor(page.next_cursor);setPreparationListed(true);note("已读取本地文档列表；打开时检查是否适合普通准备正文编辑。");}
    });
  }
  async function openPreparation(id:string) {
    if(lock.current||pending)return;
    const snapshot=JSON.stringify({purpose:draft.purpose,content:draft.content});
    if(preparationAttempt.current||snapshot!==savedPreparation&&(!!draft.purpose||!!draft.content)){note("当前准备正文尚未保存或保存未确认；请先保存并读回，当前文字保留。");return;}
    await run(async request=>{
      const doc=assertCoreDto<DocumentDto>("DocumentDto",await coreCommand("document_get",{document_id:id}));
      if(doc.document_id!==id)throw new Error("preparation identity changed");
      const content=preparationText(doc);
      if(request===epoch.current){setDraft(previous=>({...previous,purpose:doc.title,content}));setPreparation({document_id:id,version:doc.version,title:doc.title});setSavedPreparation(JSON.stringify({purpose:doc.title,content}));note("准备正文已从本地文档重开；继续保存使用当前版本，不登记正式知识或教学记录。");}
    });
  }
  async function savePreparationDocument() {
    await run(async request=>{
      const editor_json:PreparationEditor={type:"doc",content:draft.content.split("\n").map(text=>({type:"paragraph",attrs:{block_id:crypto.randomUUID()},...(text?{content:[{type:"text" as const,text}]}:{})}))};
      const currentSnapshot=JSON.stringify({purpose:draft.purpose,content:draft.content});
      const attempt:PreparationAttempt=preparationAttempt.current??(preparation
        ?{operation:"document_draft",payload:{document_id:preparation.document_id,body:{expected_version:preparation.version,editor_json}},snapshot:currentSnapshot,persistedPurpose:savedPreparation?JSON.parse(savedPreparation).purpose:"",expectedTitle:preparation.title}
        :{operation:"document_create",payload:{body:{create_request_id:boundedId("preparation"),title:draft.purpose.trim()||"教学准备草稿",editor_json}},snapshot:currentSnapshot,persistedPurpose:draft.purpose,expectedTitle:draft.purpose.trim()||"教学准备草稿"});
      const journal={...teachingSnapshot(),preparation_attempt:structuredClone(attempt)};
      if(working)working.session.rememberTeachingDraft(draftKey,journal);
      preparationAttempt.current=attempt;
      if(working){const ack=await working.session.flush();if(!sameValue(ack.state.teaching_drafts?.[draftKey]?.preparation_attempt,attempt))throw new Error("preparation journal not acknowledged");}
      const snapshot=attempt.snapshot;
      const expectedId=attempt.operation==="document_create"?await documentRequestIdentity(attempt.payload.body.create_request_id):attempt.payload.document_id;
      const expectedVersion=attempt.operation==="document_create"?1:attempt.payload.body.expected_version+1;
      const nodes=attempt.payload.body.editor_json.content;
      const texts=nodes.map(node=>(node.content??[]).map(child=>child.text).join(""));
      function verified(value:unknown):DocumentDto {
        const doc=assertCoreDto<DocumentDto>("DocumentDto",value);
        if(doc.document_id!==expectedId||doc.version!==expectedVersion||!/^[a-f0-9]{64}$/.test(doc.content_sha256)||doc.source_id!==null||doc.source_revision!==null
          ||doc.title!==attempt.expectedTitle
          ||!sameValue(doc.editor_json,attempt.payload.body.editor_json)||doc.text_projection!==texts.filter(text=>text.length>0).join("\n")
          ||doc.blocks.length!==nodes.length||doc.blocks.some((block,index)=>block.block_id!==nodes[index].attrs.block_id||block.kind!=="paragraph"||block.ordinal!==index||block.text_projection!==texts[index]||block.codec_status!=="known"||!sameValue(block.node_json,nodes[index])))throw new Error("preparation snapshot mismatch");
        return doc;
      }
      if(request!==epoch.current)return;
      let result:DocumentDto;
      if(attempt.operation==="document_draft"){
        const current=assertCoreDto<DocumentDto>("DocumentDto",await coreCommand("document_get",{document_id:expectedId}));
        if(current.document_id!==expectedId)throw new Error("preparation identity changed");
        result=current.version===expectedVersion?verified(current):verified(await coreCommand(attempt.operation,structuredClone(attempt.payload)));
      }else result=verified(await coreCommand(attempt.operation,structuredClone(attempt.payload)));
      const readback=verified(await coreCommand("document_get",{document_id:expectedId}));
      if(readback.content_sha256!==result.content_sha256||readback.title!==result.title)throw new Error("preparation readback mismatch");
      if(request!==epoch.current)return;
      const nextPreparation={document_id:result.document_id,version:result.version,title:result.title},nextSaved=JSON.stringify({purpose:attempt.persistedPurpose,content:JSON.parse(snapshot).content});
      if(working){
        if(!await working.session.finishTeachingPreparation(draftKey,attempt,nextPreparation,nextSaved))throw new Error("preparation intent changed; retained");
        const current=working.session.getSnapshot().state.teaching_drafts?.[draftKey];
        const finished:TeachingDraft={...journal,preparation:nextPreparation,saved_preparation:nextSaved};delete finished.preparation_attempt;
        journalBaseline.current=JSON.stringify(current??finished);
      }
      if(request===epoch.current){setPreparation(nextPreparation);setSavedPreparation(nextSaved);preparationAttempt.current=null;note("正文草稿已保存并核对；允许缺少需求字段或正式知识绑定。保存教学记录是另一步操作。"+(JSON.parse(snapshot).purpose!==attempt.persistedPurpose?"用途改动仍留在当前表单，未重命名已保存文档。":""));}
    });
  }
  async function save() {
    await run(async request=>{
      if(preparationAttempt.current)throw new Error("准备正文保存尚未确认；请先重试同一准备请求。");
      let record=createAttempt.current;
      if(!record){if(!knowledge||!draft.purpose.trim()||draft.purpose.length>512||!draft.content.trim()||draft.content.length>65536)throw new Error("knowledge, bounded purpose and content required");
        if(parents[draft.kind] && draft.kind!=="requirement" && !parent)throw new Error("parent required");
        if(parent && (!parents[draft.kind]?.includes(parent.record.kind)||parent.withdrawn))throw new Error("invalid parent kind");
        if(draft.kind==="feedback"&&!draft.feedback_class)throw new Error("feedback class required");
        record={schema:"archeaxis.teaching-record/v2",record_id:boundedId("teaching"),kind:draft.kind,knowledge_id:knowledge.knowledge_id,knowledge_version:knowledge.knowledge_id,course_id:courseId,parent_id:parent?.record.record_id??null,purpose:draft.purpose.trim(),scope:draft.scope,privacy:draft.privacy,content:draft.content,feedback_class:draft.kind==="feedback"?draft.feedback_class:null,assessment_id:draft.kind==="teach_back"?assessmentId:null,rubric_version:draft.rubric_version.trim()||null,assisted:draft.assisted,producer_kind:draft.producer_kind};
      }
      assertTeachingDto("TeachingRecord",record);
      const journal=teachingSnapshot();journal.pending_record=structuredClone(record);
      if(working)working.session.rememberTeachingDraft(draftKey,journal);
      createAttempt.current=record;setPending(true);
      if(working){const ack=await working.session.flush();if(!sameValue(ack.state.teaching_drafts?.[draftKey],journal))throw new Error("teaching draft journal not acknowledged");}
      const receipt=object(await coreCommand<WriteReceipt>("teaching_create",{body:record}));const saved=view(receipt.item);
      if(!sameValue(saved.record,record)||typeof receipt.duplicate!=="boolean")throw new Error("create identity or body changed");
      const readback=view(await coreCommand("teaching_get",{record_id:record.record_id}));
      if(!sameValue(readback.record,record)||readback.content_sha256!==saved.content_sha256||readback.scoring_status!=="not_scored")throw new Error("teaching saved readback mismatch");
      if(request!==epoch.current)return;
      if(working&&!await working.session.finishTeachingDraft(draftKey,journal))throw new Error("teaching draft changed after save; retained");
      if(request===epoch.current){merge(readback);setSelected(readback);currentSelection.current=readback.record.record_id;const cleared={...journal,form:blank(record.kind),parent:null,pending_record:null};journalBaseline.current=JSON.stringify(cleared);setDraft(cleared.form);setParent(null);createAttempt.current=null;setPending(false);note(receipt.duplicate?"已读回同一客户端记录，未重复创建。":"教学记录已保存；仍为不计分的人工作业记录。");}
    });
  }
  async function releasePending() {
    if(!working||!createAttempt.current)return;
    await run(async request=>{
      const journal=teachingSnapshot();
      if(!await working.session.releaseTeachingDraft(draftKey,journal))throw new Error("冻结记录身份已变化；原文保留。");
      if(request!==epoch.current)return;
      createAttempt.current=null;setPending(false);journal.pending_record=null;journalBaseline.current=JSON.stringify(journal);
      note("已解除冻结，正文与来源保留为可编辑草稿；旧请求身份已停用，重新登记会创建新身份。");
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
  const learningWorkspace=<div className="stitch-teaching-learning">{initialItemKey&&["11","12"].includes(pageId)?<section aria-label="同对象练习与复习"><h3>{learningTitle(journey?.display_title, "学习项目（标题尚未核对）")}</h3>{journey?<><RawReceiptButton label="同对象学习身份" category="data" payload={journey} /><CanonicalLearningSpace key={journey.item_key} initialItemKey={journey.item_key} expectedJourney={journey} onReturnCourse={journey.course?returnCourse:undefined} onTrail={onTrail}/></>:journeyFailure?<p role="alert">同对象学习身份未核对，不能提交结果。{journeyFailure}</p>:<p role="status">正在核对原学习项目、知识与问题身份…</p>}</section>:null}
    {returnedCourse?.course?<section aria-label="原课程与绑定版本"><h3>当前学习问题绑定的原课程</h3><p>仅阅读本题绑定的知识修订 {returnedCourse.knowledge_version}；不创建或升级课程、问题和复习记录。</p><button type="button" onClick={()=>setReturnedCourse(undefined)}>关闭课程并继续编辑</button><KnowledgeCoursePanel key={courseRead} readOnly courseId={returnedCourse.course.id} knowledgeId={returnedCourse.knowledge_id} expectedItemKey={returnedCourse.item_key} expectedCourse={returnedCourse.course}/></section>:null}
    {!initialItemKey&&practice&&itemKey?<CanonicalLearningSpace initialItemKey={itemKey} onTrail={onTrail}/>:null}</div>;
  return <section className="stitch-teaching" aria-label="手工教学旅程">
    <header className="stitch-teaching-topic"><div><p className="stitch-teaching-eyebrow">教学工作区</p><h2>{pages.find(([id])=>id===pageId)?.[1]??"教学旅程"}</h2></div><span>手工记录 · 不计分</span></header>
    <nav className="stitch-teaching-stages" aria-label="教学阶段">{pages.map(([id,label])=><button type="button" key={id} aria-pressed={pageId===id} disabled={busy||pending} onClick={()=>onOpenPage?.(id)}>{label}</button>)}</nav>
    {message?<p className="stitch-teaching-message" role="status">{message}</p>:null}{failure?<p className="stitch-teaching-failure" role="alert">{failure}</p>:null}
    <details className="stitch-teaching-rules"><summary>记录规则与资格说明</summary><p>手工记录保存实际父关系、知识和课程版本；所有教学记录均不计分。人工反馈不会自动改变学习掌握状态或 AI 使用资格。保存时会再次检查权限。</p></details>
    {learningWorkspace}
    <TeachingStageWorkspace pageId={pageId} parent={parent?.record??null} purpose={draft.purpose} content={draft.content} disabled={busy||pending} onOutline={content=>setDraft(previous=>({...previous,content}))}/>
    <div className="stitch-teaching-layout">
      <div className="stitch-teaching-current">
        <div className="stitch-teaching-selected">{selected?<article aria-label="已保存教学记录"><h3>{names[selected.record.kind]} · {selected.record.purpose}</h3><p style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{selected.record.content}</p><p>关联知识版本：{selected.record.knowledge_version}；{selected.record.assisted ? "使用了辅助" : "未声明辅助"}；{selected.withdrawn ? "记录已撤回，仅供查看" : "记录有效，不计分"}。</p><RawReceiptButton label="教学记录与关联详细信息" category="data" payload={selected}/>
        <button disabled={busy||selected.withdrawn||selected.record.scope!=="manual_exchange"||selected.record.privacy!=="authorized_export"} onClick={()=>void exportSelected()}>导出人工交换 JSON</button><AaosDialog role="alertdialog" title="确认撤回教学记录" description="撤回保留历史；取消不执行写入。" open={withdrawDialog} onOpenChange={open=>{if(!busy)setWithdrawDialog(open);}} trigger={<button disabled={busy||selected.withdrawn}>审阅撤回记录</button>}><p>撤回这条教学记录后仍会保留知识、课程和历史，不会删除原记录。</p><label>撤回原因<textarea disabled={busy||!!withdrawalAttempt.current} value={withdrawReason} onChange={event=>setWithdrawReason(event.target.value)}/></label><button disabled={busy||!withdrawReason.trim()} onClick={()=>void withdraw()}>确认撤回</button><button disabled={busy} onClick={()=>{setWithdrawDialog(false);}}>取消撤回</button></AaosDialog>
      </article>:null}</div>
        <section className="stitch-teaching-card stitch-teaching-editor" aria-label={pageId==="16"?"当前人工交换文件":"当前教学编辑"}>
          <header><h3>{pageId==="16"?"人工交换文件":pageId==="08"?"编写需求简报":pageId==="09"?"编写表达方案":pageId==="10"?"整理交付正文":pageId==="11"?"记录我的讲解":"编写反馈或修订"}</h3><span>{pending?"写入待确认":pageId==="16"?"选择后检查":"正文草稿"}</span></header>
          {pageId!=="16"?<form onSubmit={event=>{event.preventDefault();void save();}} aria-label="创建教学记录">
        <fieldset disabled={busy||pending}><legend>先写正文，随时保存本地准备草稿</legend>
          <label className="stitch-teaching-purpose">用途<input maxLength={512} value={draft.purpose} onChange={event=>setDraft(previous=>({...previous,purpose:event.target.value}))}/></label><label className="stitch-teaching-body">内容<textarea maxLength={65536} rows={12} value={draft.content} onChange={event=>setDraft(previous=>({...previous,content:event.target.value}))}/></label>
          <details className="stitch-teaching-properties"><summary>记录属性与关联</summary><div><label>记录类型<select value={draft.kind} onChange={event=>{setDraft(previous=>({...previous,kind:event.target.value as Kind}));setParent(null);}}>{pageKinds.map(kind=><option key={kind} value={kind}>{names[kind]}</option>)}</select></label>
          <label>父记录<select value={parent?.record.record_id??""} onChange={event=>{const row=eligible.find(item=>item.record.record_id===event.target.value);if(row)beginChild(row);else setParent(null);}}><option value="">请选择真实父记录</option>{eligible.map(row=><option key={row.record.record_id} value={row.record.record_id}>{names[row.record.kind]} · {row.record.purpose}</option>)}</select></label>
          <label>范围<select value={draft.scope} onChange={event=>setDraft(previous=>({...previous,scope:event.target.value as TeachingRecord["scope"]}))}><option value="personal">个人记录</option><option value="manual_exchange">人工交换</option></select></label><label>隐私<select value={draft.privacy} onChange={event=>setDraft(previous=>({...previous,privacy:event.target.value as TeachingRecord["privacy"]}))}><option value="local_only">仅本地</option><option value="authorized_export">授权导出</option></select></label>
          <label className="stitch-teaching-checkbox"><input type="checkbox" checked={draft.assisted} onChange={event=>setDraft(previous=>({...previous,assisted:event.target.checked}))}/>使用了辅助（不自动判定行为者）</label><label>内容来源声明（不授予行为者权限）<select value={draft.producer_kind} onChange={event=>setDraft(previous=>({...previous,producer_kind:event.target.value as TeachingRecord["producer_kind"]}))}><option value="human_authored">人工撰写</option><option value="external_material">外部材料</option><option value="machine_generated">机器生成</option></select></label><label>评测准则版本<input value={draft.rubric_version} onChange={event=>setDraft(previous=>({...previous,rubric_version:event.target.value}))}/></label>
          {draft.kind==="feedback"?<label>反馈分类<select value={draft.feedback_class??""} onChange={event=>setDraft(previous=>({...previous,feedback_class:event.target.value as TeachingRecord["feedback_class"]}))}><option value="">请选择</option>{feedbackClasses.map(value=><option key={value} value={value}>{feedbackLabels[value]}</option>)}</select></label>:null}
          </div></details>
        </fieldset><p>来源选择：知识{knowledge ? "已选择" : "尚未选择"}、课程{courseId ? "已关联" : "未关联"}、学习问题{assessmentId ? "已关联" : "未关联"}。</p><RawReceiptButton label="教学来源详细信息" category="data" payload={{knowledge_id:knowledge?.knowledge_id,course_id:courseId,assessment_id:assessmentId}}/>
        <button disabled={busy||pending||!documentLease.canWrite} type="button" onClick={()=>void savePreparation()}>保存准备正文草稿</button>{preparation?<button disabled={busy||pending} type="button" onClick={newPreparation}>作为新准备草稿</button>:null}<p>普通准备正文可先保存，不要求完整需求、父记录或知识绑定。{preparation?`已保存文档第 ${preparation.version} 版`:"尚未保存准备正文"}。首次用途作为文档标题；后续正文保存保留该标题。需要新标题可作为新准备草稿保存。</p>{preparation?<RawReceiptButton label="准备草稿文档详细信息" category="data" payload={preparation}/>:null}<button disabled={busy} type="submit">{pending?"重试同一记录":"保存教学记录"}</button>{pending?<><p role="status">上次写入尚未确认；重试保持相同客户端身份和原内容，编辑暂时锁定。</p>{working?<><button type="button" disabled={busy} onClick={()=>void releasePending()}>检查结果并恢复编辑</button><p>若记录尚未保存，正文会保留并可恢复编辑；若已保存，请重试同一次操作检查结果。</p></>:null}</>:null}
      </form>:<section aria-label="人工交换导入"><h3>选择人工交换文件，检查内容后确认导入</h3><input aria-label="选择人工交换 JSON" type="file" accept="application/json,.json" disabled={busy} onChange={event=>void chooseFile(event.target.files?.[0])}/><AaosDialog role="alertdialog" title="确认人工交换导入" description="先检查内容，只有你确认后才导入。" open={exchangeDialog} onOpenChange={open=>{if(!open&&!busy)setExchangeDialog(false);}} trigger={<button disabled={busy||!bundle} onClick={()=>void previewImport()}>检查交换文件</button>}>{preview?<><p>文件包含 {preview.record_count} 条记录，其中 {preview.duplicate_count} 条已存在。导入不会发送到其他设备或执行文件内容。</p><RawReceiptButton label="交换文件核对详细信息" category="data" payload={preview}/><button disabled={busy} onClick={()=>void importBundle()}>确认人工导入</button><button disabled={busy} onClick={()=>setExchangeDialog(false)}>取消导入</button></>:null}</AaosDialog>{originalExchange?<><button type="button" onClick={downloadOriginalExchange}>下载所选原始交换文件</button><p>原件：{originalExchange.name} · {originalExchange.size} 字节。下载保留原文件，即使内容无法导入。</p></>:null}<p>没有文件路径权限、不自动运行外部材料。文件损坏、记录冲突或权限不足时会拒绝导入；重复文件以检查结果为准。</p></section>}
        </section>
      </div>
      <aside className="stitch-teaching-support" aria-label="教学历史与来源">
        <section className="stitch-teaching-card stitch-teaching-source" aria-label="真实教学来源"><h3>选择实际来源</h3><form onSubmit={event=>{event.preventDefault();void search();}}><label>查找来源知识<input value={query} disabled={busy||pending} onChange={event=>setQuery(event.target.value)}/></label><button disabled={busy||pending}>搜索来源知识</button></form><ul>{results.map(row=><li key={row.knowledge_id}><button disabled={busy||pending} onClick={()=>void chooseKnowledge(row)}>{row.head}</button></li>)}</ul>
      <label>绑定实际课程<select disabled={busy||pending||!knowledge||!!parent} value={courseId??""} onChange={event=>void chooseCourse(event.target.value)}><option value="">不绑定课程</option>{courses.map(row=><option disabled={row.stale} key={row.manifest_id} value={row.manifest_id}>{row.title}{row.stale?" · 来源失效":""}</option>)}</select></label>
      {parent&&courseId?<button disabled={busy} onClick={()=>void chooseCourse(courseId)}>核对父课程并读取练习入口</button>:null}
      {pageId==="11"?<><button disabled={busy||!itemKey||pending} onClick={()=>void readAssessment()}>读取绑定的真实学习问题</button><button disabled={busy||!itemKey} onClick={()=>setPractice(value=>!value)}>打开真实练习队列</button>{!itemKey?<p className="muted">请先绑定真实学习项目，才能读取学习问题并打开练习队列。</p>:null}<p>独立作答与成绩记录由真实学习流程承接；Teach-back 只是手工记录，不调用旧 Python 评分。</p></>:null}
    </section>
        <details className="stitch-teaching-card stitch-teaching-history" open><summary>教学历史与记录</summary><div><button disabled={busy} onClick={()=>void load()}>刷新教学记录</button>
      {loaded&&!visible.length?<p>本页尚无已保存记录；可读取实际来源后创建。</p>:null}
      <ul>{visible.map(row=><li key={row.record.record_id}><button disabled={busy||pending} onClick={()=>void open(row)}>{names[row.record.kind]} · {row.record.purpose}</button><small>{row.withdrawn?"已撤回 · 历史只读":"已保存 · 不计分"}</small></li>)}</ul>
      {cursor?<button disabled={busy} onClick={()=>void load(cursor)}>读取更多教学记录</button>:null}</div></details>
        {pageId!=="16"?<details className="stitch-teaching-card stitch-teaching-preparations" open><summary>本地准备文档</summary><section aria-label="重开准备正文"><h3>重开本地正文文档</h3><button disabled={busy||pending} type="button" onClick={()=>void listPreparations()}>读取准备文档列表</button><p>列表包含本地文档；此处只编辑完整可识别的普通段落。富文本、未知字段或来源绑定文档保留原件，不转换为纯文字。</p>{preparationListed&&!preparationRows.length?<p>本地文档列表为空。</p>:null}<ul>{preparationRows.map(row=><li key={row.document_id}><button disabled={busy||pending} type="button" onClick={()=>void openPreparation(row.document_id)}>重开正文 · {row.title}</button><small>第 {row.version} 版</small></li>)}</ul>{preparationCursor?<button disabled={busy||pending} type="button" onClick={()=>void listPreparations(true)}>读取更多正文文档</button>:null}</section></details>:null}
      </aside>
    </div>
  </section>;
}
