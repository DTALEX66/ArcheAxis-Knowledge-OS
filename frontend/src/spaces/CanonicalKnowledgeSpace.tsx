import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import { Section } from "../components/RealData";
import { CanonicalLibrarySpace } from "./CanonicalLibrarySpace";
import { MachineAnswerPanel } from "../components/MachineAnswerPanel";
import { KnowledgeCoursePanel } from "../components/KnowledgeCoursePanel";
import { coreFailureReason } from "../presentation/labels";
import type { ObjectTrailLevel } from "../components/NavTrail";

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid response");
  return value as Record<string, unknown>;
}
function records(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) throw new Error("invalid list");
  return value.map(record);
}
export function CanonicalKnowledgeSpace({onLearning,onTrail}:{onLearning?:()=>void;onTrail?:(levels:readonly ObjectTrailLevel[])=>void}) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [documents,setDocuments]=useState<Record<string,unknown>[]>([]);
  const [documentId,setDocumentId]=useState<string|null>(null);
  const [transforms, setTransforms] = useState<Record<string, unknown>[]>([]);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [qualification, setQualification] = useState<unknown>(null);
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const epoch = useRef(0);
  const draftDirty = useRef(false);
  function selectDocument(id:string|null) {
    if(id===documentId)return;
    if(draftDirty.current&&!window.confirm("草稿尚未保存，请先保留文字。仍要关闭或切换文档吗？"))return;
    setDocumentId(id);
  }
  async function search() {
    const current = ++epoch.current; setSelected(null); setMessage(""); setFailureReason(null);
    try {
      const result = record(await coreCommand("search", {q:query,active_only:false}));
      const found = records(result.items), extracted = records(result.transforms), docs = records(result.documents ?? []);
      if(docs.some(item=>typeof item.document_id!=="string"||typeof item.title!=="string"||typeof item.head!=="string"||typeof item.version!=="number"))throw new Error("invalid document search");
      if (found.some(item => typeof item.knowledge_id !== "string" || typeof item.head !== "string") || extracted.some(item => typeof item.source_id !== "string" || typeof item.head !== "string")) throw new Error("invalid search fields");
      if (current === epoch.current) {setItems(found);setTransforms(extracted);setDocuments(docs);}
    } catch (error) {setMessage("搜索失败，请重试。不会将失败显示为空结果。");setFailureReason(coreFailureReason(error));}
  }
  async function open(id: string) {
    const current = ++epoch.current; setSelected(null); setQualification(null); setNote(""); setFailureReason(null);
    try {
      const [detail, proof] = await Promise.all([coreCommand("knowledge_get",{id}),coreCommand("knowledge_qualification",{id})]);
      const data = record(detail);
      if (data.knowledge_id !== id || typeof data.body !== "string" || typeof data.version !== "string" || !data.version) throw new Error("invalid knowledge fields");
      if (current === epoch.current) {setSelected(data);setQualification(proof);setMessage("");}
    } catch (error) {setMessage("候选与证据读取失败，审核按钮不可用。");setFailureReason(coreFailureReason(error));}
  }
  async function review(action: "accepted"|"rejected"|"deprecated") {
    if (!selected || !reviewer.trim() || busy) return;
    const current = epoch.current; setBusy(true);
    try {
      const receipt = record(await coreCommand("knowledge_review",{id:selected.knowledge_id,body:{action,reviewer:reviewer.trim(),note,expected_version:selected.version}}));
      if (typeof receipt.knowledge_id !== "string" || typeof receipt.version !== "string") throw new Error("invalid review receipt");
      if (current === epoch.current) {await open(receipt.knowledge_id);setMessage("审核决定已由本地核心记录。");}
    } catch (error) {setMessage("审核未完成，可能版本已变化。保留备注并重新读取候选后再决定。");setFailureReason(coreFailureReason(error));}
    finally {setBusy(false);}
  }
  async function study() {
    if (!selected || busy) return;
    setBusy(true);
    const item_key = `assessment_${crypto.randomUUID()}`;
    try {
      await coreCommand("learning_reference", {item_key,body:{knowledge_id:selected.knowledge_id}});
      const assessment = record(await coreCommand("assessment_create", {item_key,body:{knowledge_id:selected.knowledge_id}}));
      if (assessment.item_key !== item_key || typeof assessment.assessment_id !== "string" || typeof assessment.question !== "string") throw new Error("invalid assessment");
      setMessage("已创建绑定此知识版本的问题，请在学习队列打开。");
      onLearning?.();
    } catch {setMessage("学习问题创建失败；Core 仅允许当前有效、已接受的知识。");}
    finally {setBusy(false);}
  }
  useEffect(() => {
    const levels: ObjectTrailLevel[] = [];
    if (selected) {
      levels.push(
        { id: "section:candidates", label: "知识候选与审核", region: "candidates" },
        { id: `knowledge:${String(selected.knowledge_id)}`, label: String(selected.title), detail: `${String(selected.knowledge_id)} · 版本 ${String(selected.version)} · ${String(selected.status)}`, region: "candidates" },
      );
    }
    onTrail?.(levels);
  }, [selected, onTrail]);
  return <Section title="知识库"><p>候选、已接受知识和提取文本分别展示；审核由当前使用者作出。</p>
    <form onSubmit={event=>{event.preventDefault();void search();}} tabIndex={-1} data-section="search"><label>搜索内容 <input value={query} onChange={event=>setQuery(event.target.value)} /></label><button>搜索</button></form>
    <ul tabIndex={-1} data-section="candidates" aria-label="知识候选列表">{items.map(item=><li key={String(item.knowledge_id)}><button onClick={()=>void open(String(item.knowledge_id))}>{String(item.head)}</button> · {String(item.status)} · {item.active === true ? "有效" : "非有效"}</li>)}</ul>
    <h4>来源提取文本</h4><ul tabIndex={-1} data-section="transforms" aria-label="来源提取文本列表">{transforms.map(item=><li key={String(item.transform_id)}>{String(item.head)} · 来源 {String(item.source_id)} · 引擎 {String(item.engine)}</li>)}</ul>
    <h4>普通文档</h4><p>原创与未核验内容可读取编辑；搜索命中不等同知识接受或核验通过。</p><ul tabIndex={-1} data-section="documents" aria-label="普通文档列表">{documents.map(item=><li key={String(item.document_id)}><button onClick={()=>selectDocument(String(item.document_id))}>{String(item.title)} · 版本 {String(item.version)}</button><p>{String(item.head)}</p></li>)}</ul>
    {documentId?<div><button onClick={()=>selectDocument(null)}>关闭搜索文档</button><CanonicalLibrarySpace key={documentId} initialDocumentId={documentId} onDirtyChange={value=>{draftDirty.current=value;}}/></div>:null}
    {selected ? <article aria-label="候选对照"><h4>类型 {String(selected.title)}</h4><pre>{String(selected.body)}</pre><p>状态 {String(selected.status)} · 版本 {String(selected.version)}</p><RawReceiptButton label="Core 证据与资格回执" payload={qualification} />
      <label>审核者 <input value={reviewer} onChange={event=>setReviewer(event.target.value)} /></label><label>审核备注 <textarea value={note} onChange={event=>setNote(event.target.value)} /></label>
      <button disabled={!reviewer.trim()||busy} onClick={()=>void review("accepted")}>接受当前候选</button><button disabled={!reviewer.trim()||busy} onClick={()=>void review("rejected")}>拒绝当前候选</button><button disabled={!reviewer.trim()||busy} onClick={()=>void review("deprecated")}>降级为弃用</button>
      <button disabled={busy} onClick={()=>void open(String(selected.knowledge_id))}>重新读取候选</button><button disabled={busy||selected.status!=="accepted"} onClick={()=>void study()}>由当前知识建立学习问题</button></article>:null}
    {selected?.status === "accepted" ? <>
      <KnowledgeCoursePanel key={`course:${String(selected.knowledge_id)}:${String(selected.version)}`} knowledgeId={String(selected.knowledge_id)} onLearning={onLearning} />
      <MachineAnswerPanel key={`${String(selected.knowledge_id)}:${String(selected.version)}`} knowledgeId={String(selected.knowledge_id)} />
    </> : null}
    {message?<p role="status">{message}</p>:null}
    {failureReason?<p className="state-reason">{failureReason}</p>:null}</Section>;
}
