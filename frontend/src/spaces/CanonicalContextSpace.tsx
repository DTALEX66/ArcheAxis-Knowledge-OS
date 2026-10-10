import { useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import { assertCoreDto, type ContextGrantDto, type ContextConsumptionDto, type DocumentDto, type MachineDocumentSummaryDto, type MachineDocumentsPageDto, type KnowledgeDto, type SearchDto } from "../api/generated/core-contract";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { failureMessage } from "../presentation/labels";
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

export function CanonicalContextSpace({ onUse, onOpenReference }: {
  onUse?: (value: ContextConsumptionDto, grant: ContextGrantDto) => void; onOpenReference?: (reference: ObjectReference) => void;
}) {
  const draft = useRef<Draft>(blank()); const attempt = useRef<Attempt | null>(null);
  const dirtyOwner = useId();
  const mounted = useRef(true), epoch = useRef(0), saving = useRef(false);
  const [, redraw] = useState(0);
  const [rows, setRows] = useState<MachineDocumentSummaryDto[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false), [listing, setListing] = useState(false);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null), [unsupported, setUnsupported] = useState<DocumentDto | null>(null);
  const [search, setSearch] = useState(""), [hits, setHits] = useState<Array<{ id: string; title: string }>>([]);
  const listEpoch = useRef(0), searchEpoch = useRef(0);
  function publish() { if (!mounted.current) return; redraw(v => v + 1); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: {owner:dirtyOwner,dirty:draft.current.dirty || !!attempt.current || saving.current} })); }
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
    if (saving.current || draft.current.value.state === "revoked") return;
    draft.current = { ...draft.current, value: { ...draft.current.value, ...change }, serial: draft.current.serial + 1, dirty: true }; publish();
  }
  function blocked() { if (saving.current || draft.current.dirty || attempt.current) { setMessage("当前草稿或写入尚未确认；请先保存并核对，再切换对象。"); return true; } return false; }
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
  async function save() {
    if (saving.current || unsupported) return;
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
      attempt.current = null; setMessage(current.dirty ? "发送版本已保存；随后编辑仍保留。" : frozen.value.state === "candidate" ? "上下文候选已保存并读回，尚未取得消费权限。" : frozen.value.state === "granted" ? "授权版本已保存并读回，消费时再次校验用途、知识与时效。" : "撤回版本已保存并读回，旧授权不能再次消费。"); void list();
    } catch (reason) {
      if (!acknowledged && reason instanceof ApiError && [400,403,422].includes(reason.status)) attempt.current = null;
      setError(failureMessage(reason)); setMessage("草稿保留；未确认请求保持冻结，重试同一请求或核对 Core 版本。");
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
        setMessage("冻结请求已在 Core 中确认；当前随后编辑保留。");
      } else { setUnsupported(doc); setMessage("Core 版本与冻结请求不同，最新对象只读；当前草稿保留。"); }
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
  const current = draft.current, grant = current.value;
  return <section aria-label="项目记忆与上下文" className="ui-content-main-side">
    <div><h2>项目记忆与上下文</h2><p>保存产品内的上下文与明确授权，来源固定到实际对象。候选可先保存；用途、允许操作与时效由你决定。</p>
      <button disabled={busy || listing} onClick={() => void list()}>刷新上下文</button>
      <button disabled={busy} onClick={() => { if (!blocked()) { epoch.current++; searchEpoch.current++; draft.current = blank(); setUnsupported(null); publish(); } }}>新建上下文候选</button>
      {listing ? <p role="status">正在读取上下文…</p> : null}
      {loaded && !listing && !error && rows.length === 0 ? <p>尚无已保存的上下文，可先创建候选。</p> : null}
      <ul className="action-list">{rows.map(row => <li key={row.document_id}><button disabled={busy} onClick={() => void open(row.document_id)}>{row.title} · v{row.version}</button></li>)}</ul>
      {cursor ? <button disabled={listing} onClick={() => void list(cursor)}>读取下一页上下文</button> : null}
      <p>当前消费范围为本地机器回答与复测。规则、技能和其它来源可保全为材料；任意工具执行、私人会话导入尚未接通。</p>
    </div>
    <div className="semantic-panel">
      {unsupported ? <><h3>原文只读</h3><RawReceiptButton label="完整上下文文档" payload={unsupported} /><button onClick={() => setUnsupported(null)}>返回保留的草稿</button></> : <>
        <h3>{current.base ? `上下文版本 ${current.base.version}` : "上下文候选草稿"}</h3><p>状态：{grant.state === "candidate" ? "候选，不能消费" : grant.state === "granted" ? "已授权，调用时再次校验" : "已撤回，旧版本保留"}</p>
        <label>用途 <textarea disabled={busy || grant.state === "revoked"} value={grant.purpose} onChange={e => edit({ purpose: e.target.value })} /></label>
        <label>查找已保存知识 <input disabled={busy || grant.state === "revoked"} value={search} onChange={e => setSearch(e.target.value)} /></label>
        <button disabled={busy || !search.trim() || grant.state === "revoked"} onClick={() => void searchKnowledge()}>查找上下文知识</button>
        {hits.map(hit => <button key={hit.id} disabled={busy || grant.state === "revoked"} onClick={() => void chooseKnowledge(hit.id)}>{hit.title} · {hit.id}</button>)}
        <p>固定知识：{grant.knowledge_id ?? "尚未选择"}</p>
        {grant.provenance.map((reference,index) => <button key={index} onClick={() => onOpenReference?.(reference)}>查看来源 {index + 1}</button>)}
        <label>授权依据 <textarea disabled={busy || grant.state === "revoked"} value={grant.authorization_basis} onChange={e => edit({ authorization_basis: e.target.value })} /></label>
        {(["answer", "retest"] as const).map(op => <label key={op}><input type="checkbox" disabled={busy || grant.state === "revoked"} checked={grant.operations.includes(op)} onChange={e => edit({ operations: e.target.checked ? [...grant.operations, op] : grant.operations.filter(value => value !== op) })} />{op === "answer" ? "允许本地回答" : "允许本地复测"}</label>)}
        <label>到期时间（本地时间，留空不限时） <input type="datetime-local" disabled={busy || grant.state === "revoked"} value={grant.expires_at ? new Date(grant.expires_at * 1000 - new Date(grant.expires_at * 1000).getTimezoneOffset() * 60000).toISOString().slice(0,16) : ""} onChange={e => {
          const value = e.target.value ? Math.floor(new Date(e.target.value).getTime() / 1000) : null;
          if (value !== null && !Number.isSafeInteger(value)) { setError("到期时间无效，原时效保留。"); return; } edit({ expires_at: value });
        }} /></label>
        <button disabled={busy || (grant.state === "revoked" && !current.dirty && !attempt.current)} onClick={() => void save()}>{attempt.current ? "重试冻结的上下文保存" : "保存上下文草稿"}</button>
        {attempt.current ? <button disabled={busy} onClick={() => void reconcile()}>核对冻结请求</button> : null}
        <button disabled={busy || grant.state !== "candidate" || !grant.knowledge_id || !grant.authorization_basis.trim() || !grant.operations.length} onClick={() => { edit({ state: "granted" }); void save(); }}>明确授权并保存</button>
        <button disabled={busy || !current.base || grant.state !== "granted"} onClick={() => { edit({ state: "revoked" }); void save(); }}>撤回上下文授权</button>
        <button disabled={busy || current.dirty || !!attempt.current || !current.base || grant.state !== "granted"} onClick={() => {
          if (!current.base || !grant.knowledge_id) return;
          onUse?.({ document_id: current.base.document_id, version: current.base.version, content_sha256: current.base.content_sha256, purpose: grant.purpose }, grant);
        }}>使用已保存上下文进入纠正与评测</button>
      </>}
      {message ? <p role="status">{message}</p> : null}{error ? <p role="alert">{error}</p> : null}
    </div>
  </section>;
}
