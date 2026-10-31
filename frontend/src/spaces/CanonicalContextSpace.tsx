import { useDocumentWriteLease } from "../workspace/documentSessions";
import { useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import { assertCoreDto, type ContextGrantDto, type ContextConsumptionDto, type DocumentDto, type MachineDocumentSummaryDto, type MachineDocumentsPageDto, type KnowledgeDto, type SearchDto } from "../api/generated/core-contract";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { localExpiryValue, parseLocalExpiry, expiryDescription } from "../presentation/localExpiry";
import { compactIdentity, displayTitle } from "../presentation/display";
import { failureMessage, stateLabel } from "../presentation/labels";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import type { ObjectReference } from "../api/generated/research-contract";

type Draft = { value: ContextGrantDto; envelope: Record<string, unknown>; base: DocumentDto | null; serial: number; dirty: boolean };
type Attempt = { operation: "document_create" | "document_draft"; payload: Record<string, unknown>; expectedId: string; version: number; serial: number; value: ContextGrantDto };
const blank = (): Draft => ({ value: { schema: "archeaxis.context-grant/v1", purpose: "", consumer: "local-machine", operations: ["answer"], knowledge_id: null, provenance: [], authorization_basis: "", expires_at: null, state: "candidate" }, envelope: { type: "doc", content: [] }, base: null, serial: 0, dirty: false });
const record = (v: unknown): Record<string, unknown> => { if (!v || typeof v !== "object" || Array.isArray(v)) throw new Error("invalid object"); return v as Record<string, unknown>; };
function metadata(doc: DocumentDto) { return assertCoreDto<ContextGrantDto>("ContextGrantDto", record(record(doc.editor_json).attrs).archeaxis_context_grant); }
function canonical(value: unknown): unknown { return Array.isArray(value) ? value.map(canonical) : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).sort(([a],[b]) => a.localeCompare(b)).map(([key,item]) => [key,canonical(item)])) : value; }
function equal(a: unknown, b: unknown) { return JSON.stringify(canonical(a)) === JSON.stringify(canonical(b)); }
function requestedEditor(frozen: Attempt) { return record(frozen.payload.body).editor_json; }

import {resolveLearningJourney} from "../presentation/learningJourney";

export function CanonicalContextSpace({ onUse, onOpenReference, initialLearningItemKey, proposedKnowledgeId, onKnowledgeBound }: {
  initialLearningItemKey?:string;proposedKnowledgeId?:string;onKnowledgeBound?:(id:string)=>void;
  onUse?: (value: ContextConsumptionDto, grant: ContextGrantDto) => void; onOpenReference?: (reference: ObjectReference) => void;
}) {
  const draft = useRef<Draft>(blank()); const attempt = useRef<Attempt | null>(null);
  const documentLease=useDocumentWriteLease(draft.current.base?.document_id);
  const dirtyOwner = useId();
  const mounted = useRef(true), epoch = useRef(0), saving = useRef(false);
  const [, redraw] = useState(0);
  const [rows, setRows] = useState<MachineDocumentSummaryDto[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false), [listing, setListing] = useState(false);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null), [unsupported, setUnsupported] = useState<DocumentDto | null>(null);
  const [search, setSearch] = useState(""), [hits, setHits] = useState<Array<{ id: string; title: string }>>([]);
  const [expiry, setExpiry] = useState<string | null>(null), expiryRef = useRef<string | null>(null);
  const listEpoch = useRef(0), searchEpoch = useRef(0);
  function publish() { if (!mounted.current) return; redraw(v => v + 1); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: {owner:dirtyOwner,dirty:draft.current.dirty || !!attempt.current || saving.current || expiryRef.current !== null} })); }
  async function list(next?: string) {
    const seq = ++listEpoch.current; setListing(true);
    try {
      const page = await coreCommand<MachineDocumentsPageDto>("machine_contexts_list", next ? { cursor: next } : {});
      if (seq !== listEpoch.current) return;
      setRows(old => next ? [...old, ...page.items.filter(row => !old.some(x => x.document_id === row.document_id))] : page.items);
      setCursor(page.next_cursor); setLoaded(true);
    } catch (reason) { if (seq === listEpoch.current) setError(failureMessage(reason)); }
    finally { if (seq === listEpoch.current) setListing(false); }
  }
  useEffect(() => { mounted.current = true; void list(); return () => { mounted.current = false; epoch.current++; listEpoch.current++; searchEpoch.current++; window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: {owner:dirtyOwner,dirty:false} })); }; }, []);
  function edit(change: Partial<ContextGrantDto>) {
    if (saving.current || !documentLease.canWrite || draft.current.value.state === "revoked") return;
    draft.current = { ...draft.current, value: { ...draft.current.value, ...change }, serial: draft.current.serial + 1, dirty: true }; publish();
  }
  function blocked() { if (saving.current || draft.current.dirty || attempt.current || expiryRef.current !== null) { setMessage("当前草稿或写入尚未确认；请先保存并核对，再切换对象。"); return true; } return false; }
  async function open(id: string) {
    if (blocked()) return; const seq = ++epoch.current; const serial = draft.current.serial;
    setBusy(true); setError(null);
    try {
      const doc = await coreCommand<DocumentDto>("document_get", { document_id: id });
      if (seq !== epoch.current || !mounted.current) return;
      if (doc.document_id !== id) throw new Error("context identity mismatch");
      if (draft.current.serial !== serial || draft.current.dirty || saving.current) { setMessage("读取期间的编辑已保留，请重新选择。"); return; }
      let value: ContextGrantDto;
      try { value = metadata(doc); } catch { setUnsupported(doc); setMessage("不支持的上下文原文保持只读。"); return; }
      draft.current = { value: structuredClone(value), envelope: structuredClone(record(doc.editor_json)), base: doc, serial: 0, dirty: false };
      attempt.current = null; setUnsupported(null); publish(); setMessage("已读取实际上下文对象及当前授权版本。");
    } catch (reason) { if (seq === epoch.current && mounted.current) setError(failureMessage(reason)); }
    finally { if (seq === epoch.current && mounted.current) setBusy(false); }
  }
  async function save() {try{await documentLease.write(saveContext);}catch(error){setError(error instanceof Error?error.message:"此文档视图只读");}}
  async function saveContext() {
    if (saving.current || unsupported) return;
    if (expiryRef.current !== null) { setMessage("请先应用或取消到期时间修改；原授权和日期输入均已保留。"); return; }
    const current = draft.current;
    if (!current.value.purpose.trim()) { setMessage("请填写用途。候选可先保存，授权另行决定。"); return; }
    saving.current = true; setBusy(true); setError(null); publish(); let acknowledged = false;
    try {
      if (!attempt.current) {
        const value = structuredClone(current.value);
        const attrs = current.envelope.attrs ? record(current.envelope.attrs) : {};
        const editor = { ...current.envelope, attrs: { ...attrs, archeaxis_context_grant: value } };
        const requestId = `context_${crypto.randomUUID()}`;
        attempt.current = current.base ? { operation: "document_draft", payload: { document_id: current.base.document_id, body: { expected_version: current.base.version, editor_json: editor } }, expectedId: current.base.document_id, version: current.base.version + 1, serial: current.serial, value }
          : { operation: "document_create", payload: { body: { create_request_id: requestId, title: value.purpose, editor_json: editor } }, expectedId: await documentRequestIdentity(requestId), version: 1, serial: current.serial, value };
      }
      const frozen = attempt.current;
      const written = await coreCommand<DocumentDto>(frozen.operation, structuredClone(frozen.payload)); acknowledged = true;
      const read = await coreCommand<DocumentDto>("document_get", { document_id: frozen.expectedId });
      if (written.document_id !== frozen.expectedId || written.version !== frozen.version || read.document_id !== frozen.expectedId || read.version !== frozen.version
        || written.content_sha256 !== read.content_sha256 || !equal(metadata(read), frozen.value) || !equal(read.editor_json, requestedEditor(frozen))) throw new Error("context saved snapshot mismatch");
      current.base = read; current.envelope = structuredClone(record(read.editor_json)); current.dirty = current.serial !== frozen.serial;
      attempt.current = null; setMessage(current.dirty ? "发送版本已保存；随后编辑仍保留。" : frozen.value.state === "candidate" ? "上下文候选已保存并读回，尚未取得使用权限。" : frozen.value.state === "granted" ? "授权版本已保存并读回，使用时再次校验用途、知识与时效。" : "撤回版本已保存并读回，旧授权不能再次使用。"); void list();
    } catch (reason) {
      if (!acknowledged && reason instanceof ApiError && [400,403,422].includes(reason.status)) attempt.current = null;
      setError(failureMessage(reason)); setMessage("草稿保留；保存结果尚未确认，可核对结果或手动重试同一次保存。");
    } finally { saving.current = false; if (mounted.current) { setBusy(false); publish(); } }
  }
  async function reconcile() {
    const frozen = attempt.current; if (!frozen || saving.current) return;
    saving.current = true; setBusy(true); publish();
    try {
      const doc = await coreCommand<DocumentDto>("document_get", { document_id: frozen.expectedId });
      if (doc.document_id !== frozen.expectedId) throw new Error("context identity mismatch");
      if (doc.version === frozen.version && equal(metadata(doc), frozen.value) && equal(doc.editor_json, requestedEditor(frozen))) {
        const current = draft.current; current.base = doc; current.envelope = structuredClone(record(doc.editor_json)); current.dirty = current.serial !== frozen.serial; attempt.current = null;
        setMessage("未确认的原请求已在 Core 中确认；当前随后编辑保留。");
      } else { setUnsupported(doc); setMessage("Core 版本与未确认的原请求不同，最新对象只读；当前草稿保留。"); }
    } catch (reason) { setError(failureMessage(reason)); }
    finally { saving.current = false; if (mounted.current) { setBusy(false); publish(); } }
  }
  async function searchKnowledge() {
    const seq = ++searchEpoch.current; setError(null);
    try {
      const page = await coreCommand<SearchDto>("search", { q: search, active_only: true });
      if (seq === searchEpoch.current && mounted.current) setHits(page.items.map(item => ({ id: item.knowledge_id, title: item.head })));
    } catch (reason) { if (seq === searchEpoch.current && mounted.current) setError(failureMessage(reason)); }
  }
  async function chooseKnowledge(id: string) {
    const seq = ++searchEpoch.current, serial = draft.current.serial; setError(null);
    try {
      const knowledge = await coreCommand<KnowledgeDto>("knowledge_get", { id });
      if (knowledge.knowledge_id !== id || knowledge.status !== "accepted") throw new Error("context knowledge is not accepted");
      if (seq !== searchEpoch.current || !mounted.current || serial !== draft.current.serial) return;
      edit({ knowledge_id: id, provenance: [{ kind: "knowledge", knowledge_id: id }] });
    } catch (reason) { if (seq === searchEpoch.current && mounted.current) setError(failureMessage(reason)); }
  }
  async function prepareJourneyContext(){
    if(blocked())return;const seq=++searchEpoch.current,serial=draft.current.serial;setBusy(true);setError(null);
    try{const target=proposedKnowledgeId??(initialLearningItemKey?(await resolveLearningJourney(initialLearningItemKey)).knowledge_id:null);if(!target)throw new Error("missing selected knowledge");const knowledge=await coreCommand<KnowledgeDto>("knowledge_get",{id:target});if(knowledge.knowledge_id!==target||knowledge.status!=="accepted"||typeof knowledge.body!=="string"||typeof knowledge.version!=="string")throw new Error("knowledge binding changed");if(seq!==searchEpoch.current||!mounted.current)return;if(draft.current.serial!==serial||draft.current.dirty){setMessage("读取期间的编辑已保留；指定知识未覆盖当前草稿。");return;}epoch.current++;draft.current=blank();draft.current.value={...draft.current.value,operations:[],knowledge_id:target,provenance:[{kind:"knowledge",knowledge_id:target}]};draft.current.dirty=true;setUnsupported(null);onKnowledgeBound?.(target);publish();setMessage("指定知识当前正文与接受状态已读回；仅建立上下文候选，用途、操作与授权仍需明确决定。");}
    catch(reason){if(seq===searchEpoch.current&&mounted.current)setError(failureMessage(reason));}finally{if(seq===searchEpoch.current&&mounted.current)setBusy(false);}
  }
  const current = draft.current, grant = current.value;
  return <section aria-label="项目记忆与上下文内容" className="ui-content-main-side">{!documentLease.canWrite?<p role="status">此文档已有写入视图；上下文授权只读，草稿保留。</p>:null}
    <div><h2>项目记忆与上下文</h2><p>保存产品内的上下文与明确授权，来源固定到实际对象。候选可先保存；用途、允许操作与时效由你决定。</p>
      {initialLearningItemKey||proposedKnowledgeId?<button disabled={busy} onClick={()=>void prepareJourneyContext()}>读取指定知识并建立上下文候选</button>:null}
      <button disabled={busy || listing} onClick={() => void list()}>刷新上下文</button>
      <button disabled={busy} onClick={() => { if (!blocked()) { epoch.current++; searchEpoch.current++; draft.current = blank(); setUnsupported(null); publish(); } }}>新建上下文候选</button>
      {listing ? <p role="status">正在读取上下文…</p> : null}
      {loaded && !listing && !error && rows.length === 0 ? <p>尚无已保存的上下文，可先创建候选。</p> : null}
      <ul className="action-list">{rows.map(row => <li key={row.document_id}><button disabled={busy} onClick={() => void open(row.document_id)}>{row.title} · v{row.version}</button></li>)}</ul>
      {cursor ? <button disabled={listing} onClick={() => void list(cursor)}>读取下一页上下文</button> : null}
      <p>当前使用范围为本地机器回答与复测。规则、技能和其它来源可保全为材料；任意工具执行、私人会话导入尚未接通。</p>
    </div>
    <div className="semantic-panel">
      {unsupported ? <><h3>原文只读</h3><RawReceiptButton label="完整上下文文档" payload={unsupported} /><button onClick={() => setUnsupported(null)}>返回保留的草稿</button></> : <>
        <h3>{current.base ? `上下文版本 ${current.base.version}` : "上下文候选草稿"}</h3><p>状态：{`${stateLabel(grant.state)}；${grant.state === "candidate" ? "尚未授权使用" : grant.state === "granted" ? "使用时再次核对" : "旧版本保留"}`}</p>
        <label>用途 <textarea disabled={busy || grant.state === "revoked"} value={grant.purpose} onChange={e => edit({ purpose: e.target.value })} /></label>
        <label>查找已保存知识 <input disabled={busy || grant.state === "revoked"} value={search} onChange={e => setSearch(e.target.value)} /></label>
        <button disabled={busy || !search.trim() || grant.state === "revoked"} onClick={() => void searchKnowledge()}>查找上下文知识</button>
        {hits.map((hit,index) => <div key={hit.id}><button title={`完整知识编号：${hit.id}`} disabled={busy || grant.state === "revoked"} onClick={() => void chooseKnowledge(hit.id)}>{displayTitle(hit.title,"未命名知识")} · 结果 {index + 1} · {compactIdentity(hit.id)}</button><RawReceiptButton label={`知识结果 ${index + 1} 完整编号`} visibleLabel="查看编号" category="data" payload={{knowledge_id:hit.id,title:hit.title}}/></div>)}
        <p>固定知识：{grant.knowledge_id ? <><span title={grant.knowledge_id}>{compactIdentity(grant.knowledge_id)}</span> <RawReceiptButton label="固定知识完整编号" visibleLabel="查看编号" category="data" payload={{knowledge_id:grant.knowledge_id}}/></> : "尚未选择"}</p>
        {grant.provenance.map((reference,index) => <button key={index} onClick={() => onOpenReference?.(reference)}>查看来源 {index + 1}</button>)}
        <label>授权依据 <textarea disabled={busy || grant.state === "revoked"} value={grant.authorization_basis} onChange={e => edit({ authorization_basis: e.target.value })} /></label>
        {(["answer", "retest"] as const).map(op => <label key={op}><input type="checkbox" disabled={busy || grant.state === "revoked"} checked={grant.operations.includes(op)} onChange={e => edit({ operations: e.target.checked ? [...grant.operations, op] : grant.operations.filter(value => value !== op) })} />{op === "answer" ? "允许本地回答" : "允许本地复测"}</label>)}
        <label>到期时间（本地时间） <input type="datetime-local" step="1" disabled={busy || !documentLease.canWrite || grant.state === "revoked"} value={expiry ?? localExpiryValue(grant.expires_at) ?? ""} onChange={e => { expiryRef.current = e.target.value; setExpiry(e.target.value); publish(); }} /></label>
        <p>当前到期：{expiryDescription(grant.expires_at)}。留空并应用表示不限时；修改后请先应用或取消。</p>
        {localExpiryValue(grant.expires_at) === null ? <><p role="status">日期选择器无法显示原到期时间，原值完整保留；只有明确应用新时间才会替换。</p><button disabled={busy || !documentLease.canWrite || grant.state === "revoked"} onClick={() => { expiryRef.current = ""; setExpiry(""); publish(); }}>修改为不限时</button></> : null}
        {expiry !== null ? <><button disabled={busy || !documentLease.canWrite || grant.state === "revoked"} onClick={() => { try { const value = parseLocalExpiry(expiry, grant.expires_at); edit({ expires_at: value }); expiryRef.current = null; setExpiry(null); publish(); } catch (e) { setError(e instanceof Error ? e.message : "到期时间无效，原时间保留。"); } }}>应用到期时间</button><button onClick={() => { expiryRef.current = null; setExpiry(null); publish(); }}>取消到期时间修改</button></> : null}
        <button disabled={busy || !documentLease.canWrite || (grant.state === "revoked" && !current.dirty && !attempt.current)} onClick={() => void save()}>{attempt.current ? "重试原上下文保存" : "保存上下文草稿"}</button>
        {attempt.current ? <button disabled={busy} onClick={() => void reconcile()}>核对原保存结果</button> : null}
        <button disabled={busy || !documentLease.canWrite || expiry !== null || grant.state !== "candidate" || !grant.knowledge_id || !grant.authorization_basis.trim() || !grant.operations.length} onClick={() => { edit({ state: "granted" }); void save(); }}>明确授权并保存</button>
        <button disabled={busy || !documentLease.canWrite || expiry !== null || !current.base || grant.state !== "granted"} onClick={() => { edit({ state: "revoked" }); void save(); }}>撤回上下文授权</button>
        <button disabled={busy || current.dirty || !!attempt.current || expiry !== null || !current.base || grant.state !== "granted"} onClick={() => {
          if (!current.base || !grant.knowledge_id) return;
          onUse?.({ document_id: current.base.document_id, version: current.base.version, content_sha256: current.base.content_sha256, purpose: grant.purpose }, grant);
        }}>使用已保存上下文进入纠正与评测</button>
        <RawReceiptButton label="完整上下文授权" payload={grant} />
      </>}
      {message ? <p role="status">{message}</p> : null}{error ? <p role="alert">{error}</p> : null}
    </div>
  </section>;
}
