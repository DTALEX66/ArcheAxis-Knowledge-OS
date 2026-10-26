import { useDocumentWriteLease } from "../workspace/documentSessions";
import { useDraftOwner } from "../workspace/draftProtection";
import { useDraftRecoverySource } from "../workspace/draftRecovery";
import { useContext, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { StitchResearchOutlet } from "../components/StitchWorkspaceChrome";
import { coreCommand } from "../api/core";
import { OriginalTextCitation } from "../components/OriginalTextCitation";
import { PublicResearchPanel } from "../components/PublicResearchPanel";
import { usePublicResearch } from "../presentation/publicResearch";
import { appendEvidenceComparisons, type EvidenceComparison } from "../presentation/publicEvidenceComparison";
import type { PublicResearchSelectionDto } from "../api/generated/core-contract";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import type { DocumentDto, DocumentsListDto, DocumentSummaryDto, SourcesListDto, SourceDto, OriginalDto, SearchDto, DocumentExportDto, AnchorDto, AnchorResolutionDto } from "../api/generated/core-contract";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { focusVisibleTarget } from "../presentation/focus";
import type { ObjectTrailLevel } from "../components/NavTrail";
import "./research.css";

import type { ObjectReference, ResearchDocument, ResearchCitation } from "../api/generated/research-contract";
export type { ResearchEntry, ResearchConclusion } from "../api/generated/research-contract";
export type ResearchReference = ObjectReference;
export type ResearchValue = ResearchDocument;
type EntrySection = "hypotheses" | "methods" | "experiments" | "counterevidence" | "unresolved";
type Target = { kind: "material" } | { kind: EntrySection; id: string } | { kind: "conclusion"; id: string; field: "sources" | "basis" };
type Attempt = { operation: "document_create" | "document_draft"; payload: Record<string, unknown>; editor: Record<string, unknown>; serial: number; version: number; expectedDocumentId?: string };
type Buffer = { value: ResearchValue; envelope: Record<string, unknown>; title: string; base: DocumentDto | null; serial: number; dirty: boolean; attempt?: Attempt };
type CitationRead = { key:string; epoch:number; generation:number; state:"reading"|"read"|"failed"; result?:AnchorResolutionDto; observed_at:string };
type KnowledgeRead = {state:"not_read"}|{state:"reading"|"read"|"failed";query:string};
const citationStatusText: Record<AnchorResolutionDto["status"],string> = {
  CURRENT:"引文定位仍有效；仅核对定位，不表示内容已证实。",
  STALE:"引文定位已过期；历史快照仍保留，可核对当前原件。",
  UNSUPPORTED:"当前无法解析这种定位；历史快照仍保留。",
  MISSING:"未找到对应定位；历史快照仍保留。",
};
const sections: [EntrySection, string][] = [["hypotheses", "假设"], ["methods", "方法"], ["experiments", "实验"], ["counterevidence", "反证"], ["unresolved", "未决"]];
const blank = (): ResearchValue => ({ schema: "archeaxis.research/v1", question: "", materials: [], hypotheses: [], methods: [], experiments: [], counterevidence: [], conclusions: [], unresolved: [] });
function focusResearchTarget(element: HTMLElement | null | undefined) {
  if (!element) return;
  for (let container = element.parentElement; container && !container.classList.contains("console-window"); container = container.parentElement) {
    if (!/auto|scroll/.test(getComputedStyle(container).overflowY) || container.scrollHeight <= container.clientHeight) continue;
    container.scrollTop += element.getBoundingClientRect().top - container.getBoundingClientRect().top;
  }
  element.focus({preventScroll:true});
}
const bytes = (s: string) => new TextEncoder().encode(s).length;
function object(v: unknown): v is Record<string, unknown> { return !!v && typeof v === "object" && !Array.isArray(v); }
function keys(v: Record<string, unknown>, allowed: string[]) { return Object.keys(v).every(k => allowed.includes(k)); }
function token(v: unknown, max = 256): v is string { return typeof v === "string" && v.length > 0 && v.length <= max && v !== "." && v !== ".." && /^[A-Za-z0-9_.-]+$/.test(v); }
function reference(v: unknown): v is ResearchReference {
  if (!object(v)) return false;
  if (v.kind === "document") return keys(v,["kind","document_id","version","block_id"]) && token(v.document_id) && Number.isSafeInteger(v.version) && Number(v.version) > 0 && (v.block_id == null || token(v.block_id));
  if (v.kind === "source") return keys(v,["kind","source_id","sha256"]) && token(v.source_id) && typeof v.sha256 === "string" && /^[a-f0-9]{64}$/.test(v.sha256);
  return v.kind === "knowledge" && keys(v,["kind","knowledge_id"]) && token(v.knowledge_id);
}
function citation(v: unknown): v is ResearchCitation {
  if (!object(v) || !keys(v,["schema","anchor_id","source_sha256","anchor_position_sha256","quote","quote_sha256","read_snapshot_sha256"])) return false;
  return v.schema === "archeaxis.research-citation/v1" && token(v.anchor_id) && typeof v.quote === "string" && bytes(v.quote)>0 && bytes(v.quote)<=16384
    && [v.source_sha256,v.anchor_position_sha256,v.quote_sha256,v.read_snapshot_sha256].every(x=>typeof x==="string" && /^[a-f0-9]{64}$/.test(x));
}
async function sha256(value: Uint8Array): Promise<string> { return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",value.slice().buffer)),v=>v.toString(16).padStart(2,"0")).join(""); }
export function parseResearch(v: unknown): ResearchDocument | null {
  const fields = ["schema","question","materials","hypotheses","methods","experiments","counterevidence","conclusions","unresolved"];
  if (!object(v) || !keys(v,fields) || v.schema !== "archeaxis.research/v1" || typeof v.question !== "string" || bytes(v.question) > 16384 || !fields.slice(2).every(k=>Array.isArray(v[k]))) return null;
  const ids = new Set<string>(); let refCount = 0; let count = 0;
  function id(item: Record<string, unknown>) { count++; if (!token(item.id,128) || !/^[A-Za-z0-9_-]+$/.test(item.id) || ids.has(item.id)) return false; ids.add(item.id); return true; }
  function refs(value: unknown) { if (!Array.isArray(value)) return false; refCount += value.length; return value.every(reference); }
  for (const item of v.materials as unknown[]) if (!object(item) || !keys(item,["id","note","reference","citation"]) || !id(item) || typeof item.note !== "string" || bytes(item.note)>16384 || !refs([item.reference]) || (item.citation!==undefined && !citation(item.citation))) return null;
  for (const [section] of sections) for (const item of v[section] as unknown[]) if (!object(item) || !keys(item,["id","text","references"]) || !id(item) || typeof item.text !== "string" || bytes(item.text)>16384 || !refs(item.references)) return null;
  for (const item of v.conclusions as unknown[]) if (!object(item) || !keys(item,["id","text","sources","basis"]) || !id(item) || typeof item.text !== "string" || bytes(item.text)>16384 || !refs(item.sources) || !refs(item.basis)) return null;
  return count<=256 && refCount<=256 ? v as unknown as ResearchDocument : null;
}
function decode(doc: DocumentDto) { if (!object(doc.editor_json) || !object(doc.editor_json.attrs)) return null; return parseResearch(doc.editor_json.attrs.archeaxis_research); }
function encode(buffer: Buffer) { const e = structuredClone(buffer.envelope); return { ...e, attrs: { ...(object(e.attrs) ? e.attrs : {}), archeaxis_research: structuredClone(buffer.value) } }; }
function canonical(v: unknown): unknown { return Array.isArray(v) ? v.map(canonical) : object(v) ? Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])) : v; }
function same(a: unknown,b: unknown) { return JSON.stringify(canonical(a)) === JSON.stringify(canonical(b)); }
// Core may assign stable block IDs; all sent fields and unknown body data must still survive.
function preserved(sent: unknown, received: unknown): boolean { return Array.isArray(sent) ? Array.isArray(received) && sent.length===received.length && sent.every((v,i)=>preserved(v,received[i])) : object(sent) ? object(received) && Object.keys(sent).every(k=>preserved(sent[k],received[k])) : sent===received; }

export function CanonicalResearchSpace({ onOpenReference, onOpenDocument, onTrail }: { onOpenReference?: (reference: ObjectReference) => void; onOpenDocument?: (id: string, version: number, block?: string) => void; onTrail?: (levels: readonly ObjectTrailLevel[]) => void }) {
  const buffers = useRef(new Map<string,Buffer>()); if (!buffers.current.size) buffers.current.set("new",{value:blank(),envelope:{type:"doc",content:[]},title:"研究草稿",base:null,serial:0,dirty:false});
  const active=useRef("new"), epoch=useRef(0), mounted=useRef(true), saving=useRef(false), listLock=useRef(false);
  const relatedOutlet = useContext(StitchResearchOutlet);
  const [, redraw]=useState(0); const [rows,setRows]=useState<DocumentSummaryDto[]>([]),[cursor,setCursor]=useState<string|null>(null),[loading,setLoading]=useState(false),[busy,setBusy]=useState(false);
  const [message,setMessage]=useState("读取研究文档…"),[error,setError]=useState(false),[switchTo,setSwitchTo]=useState<string|null>(null),[history,setHistory]=useState<DocumentDto|null>(null),[unsupported,setUnsupported]=useState<DocumentDto|null>(null),[historyVersion,setHistoryVersion]=useState("1");
  const [target,setTarget]=useState<Target|null>(null),[materialNote,setMaterialNote]=useState(""),[picked,setPicked]=useState<ResearchReference|null>(null),[pickedDoc,setPickedDoc]=useState<DocumentDto|null>(null),[documentBusy,setDocumentBusy]=useState(false),[searchBusy,setSearchBusy]=useState(false),[sources,setSources]=useState<SourceDto[]>([]),[query,setQuery]=useState(""),[knowledgeRows,setKnowledgeRows]=useState<SearchDto["items"]>([]),[sourceRead,setSourceRead]=useState<{ref:ResearchReference;name:string;sha256:string;length:number;raw:Uint8Array;materialId?:string;owner:string;text?:string;focusOrigin:Element|null}|null>(null);
  const [materialSelection,setMaterialSelection]=useState<{owner:string;id:string}|null>(null);
  const [researchPane,setResearchPane]=useState("overview");
  const documentTools = useRef<HTMLDetailsElement>(null);
  const paneFocus = useRef<string | null>(null);
  useLayoutEffect(() => {
    if (!paneFocus.current) return;
    const element = researchRegion.current?.querySelector<HTMLElement>(paneFocus.current);
    paneFocus.current = null;
    focusResearchTarget(element);
  }, [researchPane]);
  const pickerBusy=documentBusy||searchBusy;
  const historyGeneration=useRef(0);
  const [citationRead,setCitationRead]=useState<CitationRead|null>(null);
  const [knowledgeRead,setKnowledgeRead]=useState<KnowledgeRead>({state:"not_read"});
  const citationRequest=useRef(0),messageRevision=useRef(0);
  const researchRegion=useRef<HTMLDivElement>(null),pickerOpener=useRef<HTMLElement|null>(null),switchOpener=useRef<HTMLElement|null>(null);
  useEffect(()=>{
    if(!sourceRead||!sourceRead.focusOrigin?.isConnected||document.activeElement!==sourceRead.focusOrigin)return;
    const viewer=researchRegion.current?.querySelector<HTMLElement>('[data-research-pane="original"]');
    focusResearchTarget(viewer);
  },[sourceRead]);
  function restoreDialogFocus(event:Event,opener:typeof pickerOpener){event.preventDefault();focusVisibleTarget(opener.current,researchRegion.current);opener.current=null;}
  const pickerSession=useRef(0), referenceRequest=useRef(0), searchRequest=useRef(0), sourceRequest=useRef(0);
  const pending=useRef(false); pending.current=target!==null || pickerBusy;
  const b=buffers.current.get(active.current)!;
  function refName(ref: ResearchReference) {
    if(ref.kind==="document") {
      const doc=pickedDoc?.document_id===ref.document_id&&pickedDoc.version===ref.version?pickedDoc:rows.find(row=>row.document_id===ref.document_id&&row.version===ref.version);
      return `${doc?.title??"文档名称尚未读取"} · 版本 ${ref.version}${ref.block_id?" · 已固定片段":""}`;
    }
    if(ref.kind==="source") {
      const name=sourceRead&&same(sourceRead.ref,ref)?sourceRead.name:sources.find(source=>source.source_id===ref.source_id&&source.sha256===ref.sha256)?.original_name;
      return `${name??"原件名称尚未读取"} · 已绑定内容指纹`;
    }
    return `${knowledgeRows.find(item=>item.knowledge_id===ref.knowledge_id)?.head??"知识名称尚未读取"} · 固定知识版本`;
  }
  const documentLease=useDocumentWriteLease(b.base?.document_id);
  const dirtyOwner=useDraftOwner("research");
  useDraftRecoverySource(dirtyOwner, "研究草稿", () => [...new Set(buffers.current.values())].filter(value => value.dirty || value.attempt).map(value => ({
    label: `研究 · ${value.title}`, text: JSON.stringify({ title: value.title, editor_json: encode(value), ...(value.attempt ? { pending_save: value.attempt.editor } : {}) }, null, 2),
  })));
  function publish() { if (!mounted.current) return; window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:dirtyOwner,dirty:[...buffers.current.values()].some(v=>v.dirty||!!v.attempt)||saving.current||pending.current}})); redraw(n=>n+1); }
  function note(text:string, failed=false) { if(mounted.current){messageRevision.current++;setMessage(text);setError(failed);} }
  useEffect(()=>{ mounted.current=true;void list(false);return()=>{mounted.current=false;epoch.current++;window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:dirtyOwner,dirty:false}}));};},[]);
  useEffect(()=>{publish();},[target,pickerBusy]);
  useEffect(()=>{onTrail?.([{id:"page:05",label:"研究空间",region:"research"},...(b.base?[{id:b.base.document_id,label:b.base.title,detail:`版本 ${b.base.version}`,region:"research"}]:[])]);},[b.base?.document_id,b.base?.version,onTrail]);
  async function list(more:boolean) {
    if(listLock.current)return;listLock.current=true;setLoading(true);
    try{const page=await coreCommand<DocumentsListDto>("documents_list",more&&cursor?{cursor}:{});if(!Array.isArray(page.documents)||!Number.isSafeInteger(page.snapshot_count)||!(page.next_cursor===null||typeof page.next_cursor==="string"))throw new Error("list shape");if(mounted.current){setRows(old=>more?[...old,...page.documents.filter(d=>!old.some(o=>o.document_id===d.document_id))]:page.documents);setCursor(page.next_cursor);note("已读取真实文档；打开时核对研究格式。");}}
    catch{note("文档列表读取失败；未当成空研究列表。",true);}finally{listLock.current=false;if(mounted.current)setLoading(false);}
  }
  function edit(next:ResearchValue){if(!documentLease.canWrite)return;if(!parseResearch(next)){note("研究结构超出条目／引用／文字限制；当前内容保留。",true);return;}const cur=buffers.current.get(active.current)!;cur.value=structuredClone(next);cur.serial++;cur.dirty=true;historyGeneration.current++;setHistory(null);publish();}
  function changeText(change:()=>ResearchValue,text:string){if(bytes(text)>16384){note("文字超过 16384 UTF-8 字节；未截断或覆盖原文。",true);return;}edit(change());}
  function addEntry(section:EntrySection){edit({...b.value,[section]:[...b.value[section],{id:crypto.randomUUID(),text:"",references:[]}]});}
  async function open(key:string){historyGeneration.current++;sourceRequest.current++;const request=++epoch.current;const old=active.current,serial=buffers.current.get(old)!.serial;setSwitchTo(null);setHistory(null);setUnsupported(null);setSourceRead(null);
    if(key==="__new"){const id=`local_${crypto.randomUUID()}`;buffers.current.set(id,{value:blank(),envelope:{type:"doc",content:[]},title:"研究草稿",base:null,serial:0,dirty:false});active.current=id;publish();return;}
    if(buffers.current.has(key)){active.current=key;publish();if(documentTools.current)documentTools.current.open=false;return;}
    let received:DocumentDto|null=null;
    try{const doc=await coreCommand<DocumentDto>("document_get",{document_id:key});received=doc;if(doc.document_id!==key)throw new Error("identity");const value=decode(doc);if(!value)throw new Error("unsupported");if(request!==epoch.current||!mounted.current)return;if(active.current!==old||buffers.current.get(old)?.serial!==serial||saving.current){note("读取期间新增编辑保留；请重新选择文档。",true);return;}buffers.current.set(key,{value:structuredClone(value),envelope:structuredClone(doc.editor_json as Record<string,unknown>),title:doc.title,base:doc,serial:0,dirty:false});active.current=key;publish();if(documentTools.current)documentTools.current.open=false;note("研究对象已读取；内容是作者记录，尚未采用为已核验知识。");}
    catch{if(request===epoch.current&&mounted.current){if(received&&active.current===old&&buffers.current.get(old)?.serial===serial)setUnsupported(received);note("研究读取失败或格式不支持；当前草稿与原始完整文档保留，不转换或覆盖。",true);}}
  }
  function requestOpen(key:string){if(pending.current){note("先完成或取消引用选择；当前临时输入保留。",true);return;}if(saving.current){note("保存尚未确认，当前对象不切换。",true);return;}if(b.dirty||b.attempt){switchOpener.current=document.activeElement instanceof HTMLElement?document.activeElement:null;setSwitchTo(key);return;}void open(key);}
  function makeAttempt(cur:Buffer):Attempt{const editor=encode(cur);return {operation:cur.base?"document_draft":"document_create",payload:cur.base?{document_id:cur.base.document_id,body:{expected_version:cur.base.version,editor_json:editor}}:{body:{create_request_id:`research_${crypto.randomUUID()}`,title:cur.title,editor_json:editor}},editor,serial:cur.serial,version:cur.base?cur.base.version+1:1};}
  function accept(cur:Buffer,attempt:Attempt,doc:DocumentDto){const expectedMetadata=object(attempt.editor.attrs)?attempt.editor.attrs.archeaxis_research:null;if(!decode(doc)||doc.version!==attempt.version||!same(decode(doc),expectedMetadata)||!preserved(attempt.editor,doc.editor_json))throw new Error("readback content");cur.base=doc;cur.envelope=structuredClone(doc.editor_json as Record<string,unknown>);cur.attempt=undefined;cur.dirty=cur.serial!==attempt.serial;if(!cur.dirty)cur.value=structuredClone(decode(doc)!);buffers.current.set(doc.document_id,cur);if(mounted.current)setRows(old=>[doc,...old.filter(r=>r.document_id!==doc.document_id)]);note(cur.dirty?"发送时的研究版本已读回；随后编辑仍未保存。":"研究草稿已保存并读回；未变为核验或采用状态。");}
  async function save(){try{await documentLease.write(saveResearch);}catch(error){note(error instanceof Error?error.message:"此文档视图只读",true);}}
  async function saveResearch(){if(saving.current)return;if(pending.current){note("先完成或取消引用选择；保存未发送，临时输入保留。",true);return;}if(unsupported||history){note("原始或历史文档只读；返回当前草稿后保存。",true);return;}historyGeneration.current++;const cur=buffers.current.get(active.current)!;const attempt=cur.attempt??makeAttempt(cur);cur.attempt=attempt;saving.current=true;setBusy(true);publish();
    try{const createBody=attempt.operation==="document_create"?attempt.payload.body as {create_request_id:string;title:string}:null;if(createBody&&!attempt.expectedDocumentId)attempt.expectedDocumentId=await documentRequestIdentity(createBody.create_request_id);const expectedId=attempt.expectedDocumentId??cur.base!.document_id;const matchesIdentity=(doc:DocumentDto)=>doc.document_id===expectedId&&doc.version===attempt.version&&(!createBody||(doc.title===createBody.title&&doc.source_id===null&&doc.source_revision===null));const result=await coreCommand<DocumentDto>(attempt.operation,structuredClone(attempt.payload));if(!matchesIdentity(result))throw new Error("save identity");const read=await coreCommand<DocumentDto>("document_get",{document_id:expectedId});if(!matchesIdentity(read)||read.content_sha256!==result.content_sha256||!same(read.editor_json,result.editor_json))throw new Error("readback identity");accept(cur,attempt,read);}
    catch{note("保存未确认（可能冲突或回执丢失）；草稿和原冻结请求保留。重试相同请求，不另建研究对象。",true);}finally{saving.current=false;if(mounted.current){setBusy(false);publish();}}
  }
  async function reconcile(){if(!b.base||saving.current||pending.current)return;const cur=buffers.current.get(active.current)!;saving.current=true;setBusy(true);publish();try{const read=await coreCommand<DocumentDto>("document_get",{document_id:cur.base!.document_id});if(read.document_id!==cur.base!.document_id)throw new Error("identity");if(cur.attempt&&read.version===cur.attempt.version&&preserved(cur.attempt.editor,read.editor_json))accept(cur,cur.attempt,read);else if(read.version===cur.base!.version)note("已保存版本未变化；草稿及原保存请求仍保留，可重试。");else{setUnsupported(read);note("已保存版本发生变化；最新文档只读，当前草稿和原保存版本不会自动覆盖。",true);}}catch{note("核对最新版本失败；当前草稿保留。",true);}finally{saving.current=false;if(mounted.current){setBusy(false);publish();}}}
  async function readHistory(){if(pending.current||saving.current){note("先完成或取消引用选择／保存；历史未改变临时输入。",true);return;}if(!b.base)return;const id=b.base.document_id,v=Number(historyVersion),request=epoch.current,key=active.current,serial=b.serial,generation=++historyGeneration.current;if(!Number.isSafeInteger(v)||v<1||v>b.base.version){note("请输入已有的正整数历史版本。",true);return;}const current=()=>generation===historyGeneration.current&&request===epoch.current&&active.current===key&&buffers.current.get(key)?.serial===serial&&mounted.current;try{const doc=await coreCommand<DocumentDto>("document_version",{document_id:id,version:v});if(doc.document_id!==id||doc.version!==v)throw new Error("history identity");if(current()){setHistory(doc);note("历史只读，当前草稿未替换。");}}catch{if(current())note("历史读取失败；当前草稿保留。",true);}}
  async function beginPick(next:Target){if(saving.current)return;pickerOpener.current=document.activeElement instanceof HTMLElement?document.activeElement:null;const session=++pickerSession.current;sourceRequest.current++;setDocumentBusy(false);setSearchBusy(false);setKnowledgeRead({state:"not_read"});setTarget(next);setPicked(null);setPickedDoc(null);setMaterialNote("");setSourceRead(null);const request=epoch.current;try{const result=await coreCommand<SourcesListDto>("sources_list");if(request===epoch.current&&session===pickerSession.current&&mounted.current){if(!Array.isArray(result.sources))throw new Error("sources shape");setSources(result.sources);}}catch{note("来源列表读取失败；引用选择未伪造来源。",true);}}
  async function pickDocument(id:string){const request=epoch.current,cur=active.current,session=pickerSession.current,serial=++referenceRequest.current;setPicked(null);setPickedDoc(null);setDocumentBusy(true);try{const doc=await coreCommand<DocumentDto>("document_get",{document_id:id});if(doc.document_id!==id||!Number.isSafeInteger(doc.version)||doc.version<1)throw new Error("reference identity");if(request===epoch.current&&session===pickerSession.current&&serial===referenceRequest.current&&active.current===cur&&mounted.current){setPickedDoc(doc);setPicked({kind:"document",document_id:id,version:doc.version,block_id:null});}}catch{if(session===pickerSession.current&&serial===referenceRequest.current)note("材料文档读取失败；未猜测引用版本。",true);}finally{if(mounted.current&&session===pickerSession.current&&serial===referenceRequest.current)setDocumentBusy(false);}}
  async function searchKnowledge(){
    const request=epoch.current,session=pickerSession.current,serial=++searchRequest.current,submitted=query;
    const current=()=>request===epoch.current&&session===pickerSession.current&&serial===searchRequest.current&&mounted.current;
    setSearchBusy(true);setKnowledgeRead({state:"reading",query:submitted});setPicked(previous=>previous?.kind==="knowledge"?null:previous);
    try{
      const result=await coreCommand<SearchDto>("search",{q:submitted,active_only:false});
      if(!Array.isArray(result.items))throw new Error("search shape");
      if(current()){setKnowledgeRows(result.items);setKnowledgeRead({state:"read",query:submitted});}
    }catch{if(current()){setKnowledgeRead({state:"failed",query:submitted});note("本地检索失败；未显示虚构结果或空结果。",true);}}
    finally{if(current())setSearchBusy(false);}
  }
  function cancelPick(){pickerSession.current++;referenceRequest.current++;searchRequest.current++;setTarget(null);setPicked(null);setPickedDoc(null);setMaterialNote("");setDocumentBusy(false);setSearchBusy(false);}
  function addPicked(){if(!target||!picked||pickerBusy)return;const next=structuredClone(b.value);if(target.kind==="material")next.materials.push({id:crypto.randomUUID(),note:materialNote,reference:picked});else if(target.kind==="conclusion"){const item=next.conclusions.find(v=>v.id===target.id);if(item)item[target.field].push(picked);}else{const item=next[target.kind].find(v=>v.id===target.id);if(item)item.references.push(picked);}if(!parseResearch(next)){note("研究条目或引用超过保存限制；临时选择保留。",true);return;}edit(next);cancelPick();}
  function keepUnboundMaterial(){if(!target||target.kind!=="material")return;const next=structuredClone(b.value);next.unresolved.push({id:crypto.randomUUID(),text:materialNote,references:[]});if(!parseResearch(next)){note("待整理材料说明超过限制，原输入保留。",true);return;}edit(next);cancelPick();note("说明已保留为未决草稿；未伪造材料来源。");}
  async function readSource(ref:Extract<ResearchReference,{kind:"source"}>,materialId?:string){const request=epoch.current,serial=++sourceRequest.current,focusOrigin=document.activeElement;setSourceRead(null);try{const original=await coreCommand<OriginalDto>("source_original",{source_id:ref.source_id});if(original.source_id!==ref.source_id||original.sha256!==ref.sha256)throw new Error("CAS identity");const raw=Uint8Array.from(atob(original.content_base64),c=>c.charCodeAt(0));const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",raw))).map(n=>n.toString(16).padStart(2,"0")).join("");if(hash!==ref.sha256)throw new Error("CAS bytes");if(request===epoch.current&&serial===sourceRequest.current&&mounted.current)setSourceRead({ref,name:original.name,sha256:hash,length:raw.length,raw,materialId,owner:active.current,focusOrigin,...(original.media_type.startsWith("text/")?{text:new TextDecoder().decode(raw)}:{})});}catch{if(request===epoch.current&&serial===sourceRequest.current)note("原件读取或内容指纹核对失败，未显示未经核对的内容。",true);}}
  async function exportSaved(){if(!b.base||saving.current)return;const base=b.base;saving.current=true;setBusy(true);publish();try{const result=await coreCommand<DocumentExportDto>("document_export",{document_id:base.document_id,format:"markdown"});if(result.document_id!==base.document_id||result.version!==base.version)throw new Error("export version");const artifact={schema:"archeaxis.authored-research-snapshot/v1",document:base,projection:result,role:"authored_not_verified"};const url=URL.createObjectURL(new Blob([JSON.stringify(artifact,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=`research-${base.document_id}-v${base.version}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),0);note("已导出保存版本与引用；未保存草稿不在此快照，未打包原件或传给外部检索。");}catch{note("导出失败或版本已变化；没有报告导出成功。",true);}finally{saving.current=false;if(mounted.current){setBusy(false);publish();}}}
  function navigateRef(ref:ResearchReference){if(pending.current){note("先完成或取消引用选择，当前输入保留。",true);return;}if(onOpenReference){onOpenReference(structuredClone(ref));return;}if(ref.kind==="source"){void readSource(ref);return;}if(b.dirty||b.attempt){note("当前研究未保存；请先保存或保留草稿再打开引用。",true);return;}if(ref.kind==="document")onOpenDocument?.(ref.document_id,ref.version,ref.block_id??undefined);}
  async function captureMaterial(anchor:AnchorDto){
    const read=sourceRead,request=epoch.current;
    if(!read?.materialId||read.ref.kind!=="source"||read.owner!==active.current||saving.current||b.attempt||history||unsupported)return;
    try{
      const position=JSON.parse(anchor.position),start=position.start,end=position.end;
      if(anchor.source_id!==read.ref.source_id||anchor.source_revision!==read.sha256||anchor.location_status!=="located"||position.type!=="text"||!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||end<=start||end>read.raw.length)throw new Error("capture identity");
      const selected=read.raw.slice(start,end),quote=new TextDecoder("utf-8",{fatal:true,ignoreBOM:true}).decode(selected);
      const quoteSha=await sha256(selected),positionSha=await sha256(new TextEncoder().encode(anchor.position));
      if(position.checksum!==quoteSha||quote.length===0||selected.length>16384)throw new Error("capture checksum");
      if(request!==epoch.current||read.owner!==active.current||!mounted.current)return;
      const current=buffers.current.get(active.current)!;
      if(current.attempt||saving.current)return;
      const item=current.value.materials.find(m=>m.id===read.materialId);
      if(!item||!same(item.reference,read.ref))throw new Error("capture target changed");
      const captured:ResearchCitation={schema:"archeaxis.research-citation/v1",anchor_id:anchor.anchor_id,source_sha256:read.sha256,anchor_position_sha256:positionSha,quote,quote_sha256:quoteSha,read_snapshot_sha256:read.sha256};
      edit({...current.value,materials:current.value.materials.map(m=>m.id===item.id?{...m,citation:captured}:m)});
      note("原件引文快照已放入草稿；保存后随研究版本保留，不代表内容已证实。");
    }catch{if(request===epoch.current)note("引文快照未确认；材料说明和原输入保留。",true);}
  }
  async function replayCitation(captured:ResearchCitation,ref:ResearchReference){
    if(ref.kind!=="source")return;
    const request=epoch.current,generation=historyGeneration.current,serial=++citationRequest.current,key=JSON.stringify([ref,captured]);
    const current=()=>request===epoch.current&&generation===historyGeneration.current&&serial===citationRequest.current&&mounted.current;
    note("正在核验所选引文的位置…");const notice=messageRevision.current;
    setCitationRead({key,epoch:request,generation,state:"reading",observed_at:new Date().toISOString()});
    let result:AnchorResolutionDto|undefined;
    try{
      result=await coreCommand<AnchorResolutionDto>("anchor_resolve",{source_id:ref.source_id,anchor_id:captured.anchor_id});
      if(!current())return;
      if(result.source_id!==ref.source_id||result.anchor_id!==captured.anchor_id||result.source_revision!==captured.source_sha256||result.scope!=="locator_provenance_only"||typeof result.position!=="string"||await sha256(new TextEncoder().encode(result.position))!==captured.anchor_position_sha256)throw new Error("resolution identity");
      if(!current())return;
      setCitationRead({key,epoch:request,generation,state:"read",result,observed_at:new Date().toISOString()});
      if(messageRevision.current===notice)note(citationStatusText[result.status],result.status!=="CURRENT");
    }catch{if(current()){
      setCitationRead({key,epoch:request,generation,state:"failed",result,observed_at:new Date().toISOString()});
      if(messageRevision.current===notice)note("引文当前定位未确认；历史快照仍保留。",true);
    }}
  }
  function showCitation(captured:ResearchCitation|undefined,ref:ResearchReference){
    if(!captured)return null;
    const observation=citationRead?.key===JSON.stringify([ref,captured])&&citationRead.epoch===epoch.current&&citationRead.generation===historyGeneration.current?citationRead:null;
    return <aside className="research-citation" aria-label="已保存版本的引文快照"><blockquote style={{whiteSpace:"pre-wrap"}}>{captured.quote}</blockquote><p>引文保留所选原件版本与位置；当前定位有效性需重新核验。</p>
      {observation?<p>{observation.state==="reading"?"正在核验当前引文定位…":`最近一次定位核验：${observation.state==="read"&&observation.result?citationStatusText[observation.result.status]:"定位尚未确认，历史快照仍保留。"}`}</p>:null}
      <div className="research-reference-actions"><RawReceiptButton label="研究引文原始记录" payload={{reference:ref,citation:captured}} category="data"/>
        <button type="button" disabled={ref.kind!=="source"||observation?.state==="reading"} onClick={()=>void replayCitation(captured,ref)}>重新核验引文定位</button>
        {observation&&observation.state!=="reading"?<RawReceiptButton label="引文定位核验记录" payload={{reference:ref,citation:captured,result:observation.result??null,observed_at:observation.observed_at,outcome:observation.state}} category="data"/>:null}
      </div></aside>;
  }
  function showRefs(refs:ResearchReference[],remove?:(index:number)=>void){return <ul className="research-reference-list">{refs.map((ref,i)=><li key={`${JSON.stringify(ref)}-${i}`}><span className="research-reference-name">{refName(ref)}</span><RawReceiptButton label={`研究引用 ${i+1} 的原始身份`} payload={ref} category="data"/>{ref.kind!=="knowledge"||onOpenReference?<button type="button" onClick={()=>navigateRef(ref)}>{ref.kind==="source"?"读取校验原件":ref.kind==="knowledge"?"打开不变知识版本":"打开固定版本"}</button>:<span>作者引用；不表示知识已接受或AI资格</span>}{remove?<button type="button" onClick={()=>remove(i)} aria-label={`删除引用 ${i+1}`}>删除引用</button>:null}</li>)}</ul>;}
  const readonly=!!history||!!unsupported||!documentLease.canWrite;const shown=history??unsupported;const shownValue=shown?decode(shown):null;
  function keepPublicMaterial(selection:PublicResearchSelectionDto):boolean {
    if(readonly||busy||b.attempt||pending.current||saving.current)return false;
    const content=selection.representation==="metadata"?"仅元数据；未取得摘要或全文":`${selection.representation}${selection.truncated?"；已截断":""}`;
    const relation=`请求 ${selection.request_id} / ${selection.family} / ${selection.hit_id}`;
    const next={...b.value,materials:[...b.value.materials,
      {id:crypto.randomUUID(),reference:structuredClone(selection.reference),note:`公开资料派生快照（未核验，未知识采用）\n${selection.title}\n${content}\n${selection.note}\n${relation}\n对应原始 API：${selection.raw_reference.source_id} / ${selection.raw_reference.sha256}`},
      {id:crypto.randomUUID(),reference:structuredClone(selection.raw_reference),note:`原始 API 响应字节已保全（未核验；不是文章全文）\n${relation}\n对应派生快照：${selection.reference.source_id} / ${selection.reference.sha256}`},
    ]};
    if(!parseResearch(next))return false;
    edit(next);return true;
  }
  function keepPublicComparison(bindings:readonly EvidenceComparison[]):boolean {
    if(readonly||busy||b.attempt||pending.current||saving.current)return false;
    try{
      const cur=buffers.current.get(active.current)!;
      const attrs=object(cur.envelope.attrs)?cur.envelope.attrs:{};
      const next=appendEvidenceComparisons(cur.value,attrs.archeaxis_relations,bindings);
      if(!parseResearch(next.research))throw Error("comparison research bounds");
      cur.envelope={...cur.envelope,attrs:{...attrs,archeaxis_relations:next.relations}};
      edit(next.research);return true;
    }catch{note("比较条目或引用超限／身份冲突；原研究正文、属性与人工判断保留，未部分追加。",true);return false;}
  }
  const publicResearch=usePublicResearch(`${active.current}:${!!shown}`,keepPublicMaterial,keepPublicComparison);
  function keepPublicResearchNote(text:string):boolean {
    if(readonly||busy||b.attempt||pending.current){note("先完成引用选择或保存核对；公开检索准备仍留在本页。",true);return false;}
    const next={...b.value,unresolved:[...b.value.unresolved,{id:crypto.randomUUID(),text,references:[]}]};
    if(!parseResearch(next)){note("对照文字或未决条目超过保存限制；本页输入和原研究保留。",true);return false;}
    edit(next);return true;
  }
  const knowledgeCurrent=knowledgeRead.state==="read"&&knowledgeRead.query===query;
  const selectedMaterialId=materialSelection?.owner===active.current&&b.value.materials.some(m=>m.id===materialSelection.id)?materialSelection.id:b.value.materials[0]?.id;
  const noteCount=sections.reduce((total,[key])=>total+b.value[key].length,0);
  const draftState=readonly?"只读研究记录":b.attempt?"冻结保存待核对":b.dirty?"草稿有未保存修改":b.base?"已读取保存版本":"尚未保存的草稿";
  function focusResearchPane(pane:string){
    setResearchPane(pane);
    paneFocus.current = `[data-research-pane="${pane}"]`;
    if (researchPane !== pane) return;
    const element=researchRegion.current?.querySelector<HTMLElement>(`[data-research-pane="${pane}"]`);
    paneFocus.current = null;
    focusResearchTarget(element);
  }
  function selectMaterial(id:string){
    setMaterialSelection({owner:active.current,id});setResearchPane("evidence");
    paneFocus.current = `[data-research-material="${id}"]`;
    if (researchPane !== "evidence") return;
    const element=researchRegion.current?.querySelector<HTMLElement>(`[data-research-material="${id}"]`);
    paneFocus.current = null;
    focusResearchTarget(element);
  }
  const relatedMaterials = <aside className="research-related-materials" aria-label="相关资料"><header><h3>相关资料 ({b.value.materials.length})</h3><span>当前研究草稿</span></header><p>仅列出本研究已绑定对象；选择资料定位到对应证据卡。</p>
      {b.value.materials.length?<ul>{b.value.materials.map((m,i)=><li key={m.id} data-selected={selectedMaterialId===m.id}><button type="button" aria-pressed={selectedMaterialId===m.id} onClick={()=>{selectMaterial(m.id);relatedOutlet?.onLocate();}} aria-label={`定位相关材料 ${i+1}`}><span>材料 {i+1}{selectedMaterialId===m.id?" · 当前选中":""}</span><strong>{m.note||"尚未填写材料说明"}</strong><span>{refName(m.reference)}</span><span>{m.citation?"已固定引文快照；有效性需回读核对":"尚无摘录定位"}</span></button></li>)}</ul>:<p className="research-empty">尚无已绑定资料；未推测关联度。</p>}
      <div className="research-related-context"><h4>保存与依据</h4><p>{draftState}</p><p>支持、反对与冲突保留为作者判断。公开检索结果须显式固定来源，再加入草稿并保存。</p><button type="button" onClick={()=>{focusResearchPane("conclusions");relatedOutlet?.onLocate();}}>查看结论与引用依据</button></div>
    </aside>;
  return <section className="stitch-research-space" aria-label="研究专题内容"><div className="research-editor" ref={researchRegion} tabIndex={-1} role="region" aria-label="研究编辑区" data-section="research" data-active-pane={researchPane}>
    <header className="research-topic-header">
      <div><h2>{shown?.title??b.base?.title??b.title}</h2><button type="button" className="research-question-summary" onClick={()=>focusResearchPane("overview")}><strong>核心研究问题：</strong>{b.value.question||"填写本专题要研究的问题"}</button></div>
      <div className="research-topic-actions"><button type="button" disabled={busy||readonly||!!b.attempt} onClick={()=>void beginPick({kind:"material"})}>＋ 资料与证据</button><button type="button" disabled={readonly} onClick={()=>focusResearchPane("conclusions")}>形成结论</button></div>
    </header>
    <nav className="research-pane-nav" aria-label="研究内容导航">{[["overview","概览"],["evidence",`证据对比 (${b.value.materials.length})`],["notes",`研究笔记 (${noteCount})`],["conclusions",`结论 (${b.value.conclusions.length})`]].map(([id,label])=><button type="button" key={id} aria-pressed={researchPane===id} onClick={()=>focusResearchPane(id)}>{label}</button>)}</nav>
    <div className="research-stage-status"><span className="research-state" role="status" aria-label="研究草稿状态">{draftState}</span><p role={error?"alert":"status"} aria-label="研究操作状态">{message}</p></div>
    {error&&b.attempt?<div className="research-save-recovery"><p>这次保存的结果还没确认。当前草稿保留；继续核对或重试同一次请求，避免重复创建。</p><button type="button" disabled={busy||readonly} onClick={()=>void save()}>重试原保存请求</button></div>:null}
    {!documentLease.canWrite?<p role="status">此文档已有写入视图；研究记录只读，草稿保留。</p>:null}
    <details ref={documentTools} className="research-document-tools"><summary>研究文档与版本</summary>    <div className="research-document-switcher"><h3>研究文档</h3><div className="research-reference-actions"><button type="button" disabled={busy} onClick={()=>requestOpen("__new")}>新建研究草稿</button><button type="button" disabled={loading} onClick={()=>void list(false)}>刷新文档列表</button></div>
    <ul aria-label="研究文档列表">{rows.map(row=><li key={row.document_id}><button type="button" onClick={()=>requestOpen(row.document_id)}>{row.title} · 版本 {row.version}</button></li>)}</ul>{cursor?<button type="button" disabled={loading} onClick={()=>void list(true)}>更多文档</button>:null}</div>
    <div className="research-version-controls">{b.base?<><button type="button" disabled={busy} onClick={()=>void exportSaved()}>导出已存研究快照</button><button type="button" disabled={busy} onClick={()=>void reconcile()}>核对最新保存版本</button><label>历史版本<input aria-label="研究历史版本" value={historyVersion} onChange={e=>setHistoryVersion(e.target.value)}/></label><button type="button" onClick={()=>void readHistory()}>读取研究历史</button></>:null}</div>

</details>
    <div className="research-workspace-grid" data-related-external={relatedOutlet ? true : undefined}><div className="research-main-column">
    <div className="research-stage-content">    {shown?<aside aria-label="只读文档"><h3>{shown.title} · 版本 {shown.version} · 只读</h3>{shownValue?<><p style={{whiteSpace:"pre-wrap"}}>问题：{shownValue.question}</p><h4>材料</h4>{shownValue.materials.map(m=><article key={m.id}><p style={{whiteSpace:"pre-wrap"}}>{m.note}</p>{showRefs([m.reference])}{showCitation(m.citation,m.reference)}</article>)}{sections.map(([key,label])=><section key={key} aria-label={`历史${label}`}><h4>{label}</h4>{shownValue[key].map(e=><article key={e.id}><p style={{whiteSpace:"pre-wrap"}}>{e.text}</p>{showRefs(e.references)}</article>)}</section>)}<h4>结论（作者记录）</h4>{shownValue.conclusions.map(c=><div key={c.id}><p style={{whiteSpace:"pre-wrap"}}>{c.text}</p><h4>来源</h4>{showRefs(c.sources)}<h4>依据</h4>{showRefs(c.basis)}</div>)}</>:<p>不支持的研究属性保持完整原文，只读不转换。</p>}<RawReceiptButton label="完整原文与未知载荷" payload={shown.editor_json}/><button type="button" onClick={()=>{historyGeneration.current++;setHistory(null);setUnsupported(null);}}>返回当前研究草稿</button></aside>:null}


    <fieldset className="research-authoring" disabled={readonly}><legend className="research-editor-legend">{b.base?`${b.base.title} · 当前基准版本 ${b.base.version}`:"尚未持久化研究草稿"}</legend>
    <div hidden={researchPane!=="overview"}>{!b.base?<label>研究标题<input aria-label="研究标题" value={b.title} disabled={busy||!!b.attempt} onChange={event=>{b.title=event.target.value;b.serial++;b.dirty=true;publish();}}/></label>:null}
<p className="research-scope-note">作者研究记录可非线性编辑。保存不代表核验、专业采用或 AI 资格；来源与作者判断分别保留。公开检索需明确输入关键词，多步自动研究当前未接通。</p></div>
    <section hidden={researchPane!=="overview"} className="research-question-card" data-research-pane="overview" tabIndex={-1} aria-label="核心研究问题"><h3>核心研究问题</h3>
    <details className="research-first-steps" open={!b.base&&!b.value.question}><summary>第一次做研究：先比较一个具体问题</summary><ol><li>写下问题，例如“这两份资料的结论为什么不同？”</li><li>点“资料与证据”添加实际材料，在“证据对比”查看出处。</li><li>在“研究笔记”保留支持、反对或未决问题，再记录结论。</li><li>点底部“保存研究草稿”；保存后从“研究文档与版本”重开。</li></ol><p>“未决”就是还没弄清的问题；“依据”是支持判断的理由。公开检索没接通时，仍可先整理本地材料。</p></details>
    <label>研究问题<textarea aria-label="研究问题" placeholder="例如：这两份资料对同一问题有哪些相同和不同？" value={b.value.question} style={{width:"100%",boxSizing:"border-box"}} onChange={event=>changeText(()=>({...b.value,question:event.target.value}),event.target.value)}/></label><p className="research-context-summary">当前草稿：{b.value.materials.length} 项材料 · {noteCount} 项笔记 · {b.value.conclusions.length} 项结论。来源独立性与专业核验需分别判断。</p></section>
    <section hidden={researchPane!=="evidence"} className="research-evidence-section" data-research-pane="evidence" tabIndex={-1} aria-label="材料与原文"><h3>材料与原文</h3><button type="button" onClick={()=>void beginPick({kind:"material"})}>添加材料或待整理说明</button><ul className="research-evidence-cards">{b.value.materials.map((m,i)=><li key={m.id} tabIndex={-1} data-research-material={m.id} data-selected={selectedMaterialId===m.id}><div className="research-evidence-heading"><button type="button" aria-pressed={selectedMaterialId===m.id} onClick={()=>setMaterialSelection({owner:active.current,id:m.id})}>材料 {i+1}{selectedMaterialId===m.id?" · 当前选中":" · 选择对照"}</button><span>{m.citation?"已有固定引文快照":"尚无摘录定位"}</span></div><p className="research-evidence-preview">{m.citation?.quote||m.note||"尚未填写材料说明"}</p><div className="research-evidence-detail" hidden={selectedMaterialId!==m.id}><label>材料说明 {i+1}<textarea aria-label={`材料说明 ${i+1}`} value={m.note} onChange={e=>changeText(()=>({...b.value,materials:b.value.materials.map(v=>v.id===m.id?{...v,note:e.target.value}:v)}),e.target.value)}/></label>{showRefs([m.reference])}{showCitation(m.citation,m.reference)}{m.reference.kind==="source"?<button type="button" disabled={busy||!!b.attempt} onClick={()=>{if(m.reference.kind==="source")void readSource(m.reference,m.id);}}>摘录材料 {i+1}原文</button>:null}<button type="button" onClick={()=>edit({...b.value,materials:b.value.materials.filter(v=>v.id!==m.id)})}>删除材料 {i+1}</button></div><div className="research-evidence-source"><span>{refName(m.reference)}</span><button type="button" onClick={()=>navigateRef(m.reference)}>查看出处原文</button></div></li>)}</ul>{b.value.materials.length===0?<p className="research-empty">尚未绑定材料。添加实际文档、原件或知识引用后，相关资料会同步显示。</p>:null}</section>
    <div hidden={researchPane!=="notes"} className="research-notes" data-research-pane="notes" tabIndex={-1}><h3>研究笔记与论证</h3>{sections.map(([key,label])=><section className="research-note-section" key={key} aria-label={label}><h3>{label}</h3><button type="button" onClick={()=>addEntry(key)}>添加{label}</button>{b.value[key].map((entry,i)=><article key={entry.id}><label>{label} {i+1}<textarea aria-label={`${label} ${i+1}`} value={entry.text} style={{width:"100%",boxSizing:"border-box"}} onChange={e=>changeText(()=>({...b.value,[key]:b.value[key].map(v=>v.id===entry.id?{...v,text:e.target.value}:v)}),e.target.value)}/></label>{showRefs(entry.references,index=>edit({...b.value,[key]:b.value[key].map(v=>v.id===entry.id?{...v,references:v.references.filter((_,i)=>i!==index)}:v)}))}<button type="button" onClick={()=>void beginPick({kind:key,id:entry.id})}>为{label} {i+1}添加引用</button><button type="button" onClick={()=>edit({...b.value,[key]:b.value[key].filter(v=>v.id!==entry.id)})}>删除{label} {i+1}</button></article>)}</section>)}</div>
    <section hidden={researchPane!=="conclusions"} className="research-conclusion-section" data-research-pane="conclusions" tabIndex={-1} aria-label="结论"><h3>结论 · 作者记录</h3><button type="button" onClick={()=>edit({...b.value,conclusions:[...b.value.conclusions,{id:crypto.randomUUID(),text:"",sources:[],basis:[]}]})}>添加结论</button>{b.value.conclusions.map((c,i)=><article key={c.id}><label>结论 {i+1}<textarea aria-label={`结论 ${i+1}`} value={c.text} style={{width:"100%",boxSizing:"border-box"}} onChange={e=>changeText(()=>({...b.value,conclusions:b.value.conclusions.map(v=>v.id===c.id?{...v,text:e.target.value}:v)}),e.target.value)}/></label>{(["sources","basis"] as const).map(field=><section key={field} aria-label={`结论 ${i+1}${field==="sources"?"来源":"依据"}`}><h4>{field==="sources"?"来源／原文":"依据／论证引用"}</h4>{showRefs(c[field],index=>edit({...b.value,conclusions:b.value.conclusions.map(v=>v.id===c.id?{...v,[field]:v[field].filter((_,i)=>i!==index)}:v)}))}<button type="button" onClick={()=>void beginPick({kind:"conclusion",id:c.id,field})}>为结论 {i+1}添加{field==="sources"?"来源":"依据"}</button></section>)}<button type="button" onClick={()=>edit({...b.value,conclusions:b.value.conclusions.filter(v=>v.id!==c.id)})}>删除结论 {i+1}</button></article>)}</section>
</fieldset>
        {sourceRead?<section className="research-original-view" tabIndex={-1} data-research-pane="original" aria-label="已读取并核对指纹的原件"><h3>已读取并核对指纹的原件</h3><p>{sourceRead.name} · {sourceRead.length} 字节 · 内容指纹已核对</p><RawReceiptButton label="研究原件读取记录" payload={{reference:sourceRead.ref,name:sourceRead.name,sha256:sourceRead.sha256,byte_length:sourceRead.length}} category="data"/>{sourceRead.text!==undefined?<>{sourceRead.materialId&&!readonly&&!b.attempt?<OriginalTextCitation sourceId={sourceRead.ref.kind==="source"?sourceRead.ref.source_id:""} revision={sourceRead.sha256} bytes={sourceRead.raw} onAnchor={anchor=>void captureMaterial(anchor)}/>:<p style={{whiteSpace:"pre-wrap"}}>{sourceRead.text}</p>}</>:<p>保留二进制原件，当前不执行或伪造正文。</p>}</section>:null}

    <div hidden={researchPane!=="overview"}>    {!shown?<PublicResearchPanel key={active.current} snapshot={publicResearch.snapshot} receipt={publicResearch.receipt} requestId={publicResearch.target?.request_id} journal={publicResearch.journal} message={publicResearch.message} acting={publicResearch.acting} onSearch={(q,f,site)=>void publicResearch.search(q,f,site)} onCancel={()=>void publicResearch.cancel()} onRead={r=>void publicResearch.read(r)} onList={()=>void publicResearch.list()} onMaterialize={hit=>{const record=publicResearch.receipt?.channels?.flatMap(c=>c.hits).find(h=>h.id===hit.id&&h.family===hit.family);if(record)void publicResearch.materialize(record);}} onOpenRaw={navigateRef} onKeepNote={keepPublicResearchNote} onCompare={choices=>publicResearch.compare(choices)} readOnly={readonly||busy||!!b.attempt||pending.current}/>:null}
</div>    {!documentLease.canWrite&&!shown?<RawReceiptButton label="只读研究引用记录" payload={{base_document:b.base?{document_id:b.base.document_id,version:b.base.version}:null,draft:b.value,draft_dirty:b.dirty,save_pending:!!b.attempt}} category="data"/>:null}

    </div></div>{relatedOutlet ? relatedOutlet.host ? createPortal(relatedMaterials, relatedOutlet.host) : null : relatedMaterials}</div>
    <footer className="research-save-bar"><div><strong>保存在本地研究文档</strong><span>{draftState} · 结论 {b.value.conclusions.length} 项</span></div><div><button type="button" onClick={()=>focusResearchPane("conclusions")}>草稿预览</button><button type="button" disabled={busy||readonly} onClick={()=>void save()}>{b.attempt?"重试冻结研究保存":"保存研究草稿"}</button><button type="button" disabled={!b.base||busy} onClick={()=>void exportSaved()}>导出研究快照</button></div></footer>

    <AaosDialog title="选择研究引用" description="只使用本地已有对象和固定版本；取消不改变研究草稿。" open={target!==null} onOpenChange={open=>{if(!open)cancelPick();}} onCloseAutoFocus={event=>restoreDialogFocus(event,pickerOpener)}>
      {target?.kind==="material"?<label>待整理材料说明<textarea aria-label="待整理材料说明" value={materialNote} onChange={e=>setMaterialNote(e.target.value)}/></label>:null}
      <label>文档<select aria-label="引用文档" value={picked?.kind==="document"?picked.document_id:""} onChange={e=>{if(e.target.value)void pickDocument(e.target.value);}}><option value="">选择实际文档</option>{rows.map(row=><option key={row.document_id} value={row.document_id}>{row.title} · 版本 {row.version}</option>)}</select></label>
      {pickedDoc?<label>固定版本中的片段<select aria-label="引用块" value={picked?.kind==="document"?picked.block_id??"":""} onChange={e=>setPicked({kind:"document",document_id:pickedDoc.document_id,version:pickedDoc.version,block_id:e.target.value||null})}><option value="">整个固定版本</option>{pickedDoc.blocks.map(block=><option key={block.block_id} value={block.block_id}>片段 {block.ordinal+1} · {block.text_projection||"无文字预览"}</option>)}</select></label>:null}
      <label>原件来源<select aria-label="引用原件" value={picked?.kind==="source"?picked.source_id:""} onChange={e=>{const src=sources.find(v=>v.source_id===e.target.value);if(src){referenceRequest.current++;setDocumentBusy(false);setPickedDoc(null);setPicked({kind:"source",source_id:src.source_id,sha256:src.sha256});}}}><option value="">选择实际来源</option>{sources.map(src=><option key={src.source_id} value={src.source_id}>{src.original_name}</option>)}</select></label>
      <label>本地知识检索<input aria-label="研究本地知识检索" value={query} onChange={e=>{if(e.target.value!==query)setPicked(previous=>previous?.kind==="knowledge"?null:previous);setQuery(e.target.value);}}/></label><button type="button" disabled={pickerBusy} onClick={()=>void searchKnowledge()}>检索本地知识</button>
      <p role={knowledgeRead.state==="failed"?"alert":knowledgeRead.state==="not_read"?undefined:"status"}>{knowledgeRead.state==="not_read"?"尚未检索本地知识。":knowledgeRead.state==="reading"?"正在检索本地知识，请稍候。":knowledgeRead.state==="failed"?"本地检索失败，是否存在结果仍未知；可重新检索。":knowledgeCurrent?`本地检索完成：${knowledgeRows.length} 项结果。`:`以下是上次关键词“${knowledgeRead.query}”的结果；输入已变化，请重新检索。`}</p>
      {knowledgeRead.state==="read"||knowledgeRead.state==="reading"?<ul className="research-knowledge-results">{knowledgeRows.map((item,index)=><li key={item.knowledge_id}><button type="button" disabled={!knowledgeCurrent||pickerBusy} aria-label={`选择本地知识结果 ${index+1} · ${item.head}`} onClick={()=>{referenceRequest.current++;setDocumentBusy(false);setPickedDoc(null);setPicked({kind:"knowledge",knowledge_id:item.knowledge_id});}}>结果 {index+1} · {item.head}</button><RawReceiptButton label={`本地知识结果 ${index+1}`} payload={item} category="data"/></li>)}</ul>:null}
      {picked?<><p>将绑定 {refName(picked)}</p><RawReceiptButton label="所选研究引用身份" payload={picked} category="data"/></>:<p>未选择真实引用；不填充虚构来源。</p>}<button type="button" disabled={!picked||pickerBusy} onClick={addPicked}>添加所选引用</button>{target?.kind==="material"?<button type="button" disabled={pickerBusy} onClick={keepUnboundMaterial}>无来源说明先保留为未决草稿</button>:null}<button type="button" onClick={cancelPick}>取消引用选择</button>
    </AaosDialog>
    <AaosDialog title="保留研究草稿并切换" description="取消保留当前输入；确认切换只在本页保留各对象草稿，不表示已完成保存。" open={switchTo!==null} onOpenChange={open=>{if(!open)setSwitchTo(null);}} onCloseAutoFocus={event=>restoreDialogFocus(event,switchOpener)}><button type="button" onClick={()=>setSwitchTo(null)}>取消切换</button><button type="button" onClick={()=>{const next=switchTo;setSwitchTo(null);if(next)void open(next);}}>保留草稿并切换</button></AaosDialog>
  </div></section>;
}
