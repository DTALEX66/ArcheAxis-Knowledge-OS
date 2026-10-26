import { useEffect, useRef, useState, type ReactNode } from "react";
import { useDocumentWriteLease } from "../workspace/documentSessions";
import { useDraftOwner } from "../workspace/draftProtection";
import { useDraftRecoverySource } from "../workspace/draftRecovery";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
import type { DocumentDto, DocumentSummaryDto, DocumentsListDto, RelationProjectionDto, RelationDto, ObjectReferenceDto, OriginalDto, RelationNodeDto, RelationEdgeDto } from "../api/generated/core-contract";
import { ConstellationGraph } from "../components/ConstellationGraph";
import { ObjectReferencePicker } from "../components/ObjectReferencePicker";
import "./stitch-relations.css";
import type { ConstellationNode, ConstellationEdge } from "../presentation/neuralGraph";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { assertCoreDto, type DocumentRelationsDto } from "../api/generated/core-contract";
type J = Record<string, unknown>;
const relationKindLabels = { related: "相关", supports: "支持", contradicts: "矛盾", depends_on: "依赖" } as const;
const targetKindLabels = { document: "文档", source: "来源原件", knowledge: "知识" } as const;
function nodeTitle(value: object | null, reference: ObjectReferenceDto) { const title = (value as J | null)?.title; return typeof title === "string" ? title : label(reference); }
type Attempt = { operation: "document_create" | "document_draft"; payload: J; editor: J; serial: number; version:number; expectedDocumentId?:string };
type Buffer = { base: DocumentDto | null; envelope: J; relations: RelationDto[]; dirty: boolean; serial: number; attempt?: Attempt; unsupported: boolean };
function object(v: unknown): J { if (!v || typeof v !== "object" || Array.isArray(v)) throw new Error("无效文档结构"); return v as J; }
function canonical(v: unknown): unknown { return Array.isArray(v) ? v.map(canonical) : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b)).map(([k, x]) => [k, canonical(x)])) : v; }
function same(a: unknown, b: unknown) { return JSON.stringify(canonical(a)) === JSON.stringify(canonical(b)); }
function fromDoc(d: DocumentDto): Buffer { const envelope = structuredClone(object(d.editor_json)); let relations: RelationDto[] = [], unsupported = false;
  try { const attrs = envelope.attrs ? object(envelope.attrs) : {}, r = attrs.archeaxis_relations;
    if (r !== undefined) { const m = assertCoreDto<DocumentRelationsDto>("DocumentRelationsDto",r);
      relations = structuredClone(m.relations);
    }
  } catch { unsupported = true; }
  return { base: d, envelope, relations, dirty: false, serial: 0, unsupported };
}
function editor(b: Buffer) { return { ...structuredClone(b.envelope), attrs: { ...(b.envelope.attrs ? structuredClone(object(b.envelope.attrs)) : {}), archeaxis_relations: { schema: "archeaxis.relations/v1", relations: structuredClone(b.relations) } } }; }
function label(r: ObjectReferenceDto) { return r.kind === "document" ? `${r.document_id} · v${r.version}${r.block_id ? " · " + r.block_id : ""}` : r.kind === "source" ? `${r.source_id} · ${r.sha256}` : r.knowledge_id; }
function relationGraphNode(node: RelationNodeDto): ConstellationNode {
  return { id: node.key, label: nodeTitle(node.object, node.reference), referenceLabel: label(node.reference), status: node.status,
    group: node.status === "unavailable" ? "unavailable" : node.reference.kind === "source" ? "sources" : node.reference.kind === "knowledge" ? "knowledge" : node.reference.block_id ? "blocks" : "documents" };
}
function relationGraphEdge(edge: RelationEdgeDto): ConstellationEdge {
  return { id: JSON.stringify([edge.source_snapshot.document_id, edge.source_snapshot.version, edge.source_snapshot.content_sha256, edge.id, edge.relation.id, edge.from, edge.to, edge.direction, edge.origin, edge.record_id, edge.property_id]), sourceId: edge.id,
    from: edge.from, to: edge.to, label: edge.relation.label, kind: edge.relation.kind, direction: edge.direction };
}
export function CanonicalRelationSpace({ onOpenReference, onOpenDocument, renderCollection }: { onOpenReference?: (reference: ObjectReferenceDto) => void; onOpenDocument?: (id: string, version: number, block?: string) => void; renderCollection?: (document: DocumentDto | null, envelope: J, onChange:(envelope:J)=>void, onPendingChange:(pending:boolean)=>void, readOnly:boolean) => ReactNode }) {
  const section = useRef<HTMLElement>(null);
  const buffers = useRef(new Map<string, Buffer>()), active = useRef("new"), mounted = useRef(true), epoch = useRef(0), graphEpoch = useRef(0), locked = useRef(false), listLocked = useRef(false);
  if (!buffers.current.size) buffers.current.set("new", { base: null, envelope: { type: "doc", content: [] }, relations: [], dirty: false, serial: 0, unsupported: false });
  const [, redraw] = useState(0), [rows, setRows] = useState<DocumentSummaryDto[]>([]), [cursor, setCursor] = useState<string | null>(null), [busy, setBusy] = useState(false), [message, setMessage] = useState("读取文档列表…"), [failed, setFailed] = useState(false), [pending, setPending] = useState<string | null>(null);
  const [projection, setProjection] = useState<RelationProjectionDto | null>(null), [graphBusy, setGraphBusy] = useState(false), [listOnly, setListOnly] = useState(false), [history, setHistory] = useState<DocumentDto | null>(null), [version, setVersion] = useState("1"), [original, setOriginal] = useState<OriginalDto | null>(null);
  const [kind, setKind] = useState<RelationDto["kind"]>("related"), [relationLabel, setRelationLabel] = useState(""), [targetKind, setTargetKind] = useState<ObjectReferenceDto["kind"]>("document"), [targetId, setTargetId] = useState(""), [targetVersion, setTargetVersion] = useState("1"), [block, setBlock] = useState(""), [sha, setSha] = useState("");
  const [collectionPending,setCollectionPending]=useState(false);
  const [pickingTarget,setPickingTarget]=useState(false);
  const [directionFilter, setDirectionFilter] = useState("all"), [relationFilter, setRelationFilter] = useState("all"), [objectFilter, setObjectFilter] = useState("all");
  const b = buffers.current.get(active.current)!, formDirty = !!(targetId || relationLabel || block || sha) || collectionPending;
  const documentLease=useDocumentWriteLease(b.base?.document_id);
  const dirtyOwner=useDraftOwner("relations");
  useDraftRecoverySource(dirtyOwner, "关系草稿", () => [
    ...[...new Set(buffers.current.values())].filter(value => value.dirty || value.attempt).map(value => ({ label: `关系 · ${value.base?.title ?? "未命名草稿"}`, text: JSON.stringify({ editor_json: editor(value), ...(value.attempt ? { pending_save: value.attempt.editor } : {}) }, null, 2) })),
    ...(formDirty ? [{ label: "未提交关系输入", text: JSON.stringify({ kind, relationLabel, targetKind, targetId, targetVersion, block, sha }, null, 2) }] : []),
  ]);
  const pendingInput = useRef(false); pendingInput.current = formDirty;
  function note(m: string, error = false) { if (mounted.current) { setMessage(m); setFailed(error); } }
  function publish() { if (!mounted.current) return; const dirty=[...buffers.current.values()].some(x => x.dirty || x.attempt) || locked.current || formDirty;window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: {owner:dirtyOwner,dirty} })); redraw(x => x + 1); }
  useEffect(() => { mounted.current = true; void list(false); return () => { mounted.current = false; epoch.current++; graphEpoch.current++; window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: {owner:dirtyOwner,dirty:false} })); }; }, []);
  useEffect(() => { publish(); }, [targetId, relationLabel, block, sha, collectionPending]);
  async function list(more: boolean) { if (listLocked.current) return; listLocked.current = true; try { const r = await coreCommand<DocumentsListDto>("documents_list", more && cursor ? { cursor } : {}); if (!mounted.current) return; setRows(old => more ? [...old, ...r.documents.filter(x => !old.some(y => y.document_id === x.document_id))] : r.documents); setCursor(r.next_cursor); note("文档列表已读取；关系绑定实际对象版本。"); } catch { note("文档列表读取失败；未当成空列表。", true); } finally { listLocked.current = false; } }
  async function graph(d: DocumentDto, next?: string) { const token = ++graphEpoch.current; setGraphBusy(true); try { const r = await coreCommand<RelationProjectionDto>("document_graph", { document_id: d.document_id, version: d.version, ...(next ? { cursor: next } : {}) }); if (!mounted.current || token !== graphEpoch.current) return; if (r.center.document_id !== d.document_id || r.center.version !== d.version || r.center.content_sha256 !== d.content_sha256) throw new Error("图投影身份不符"); setProjection(r); note("关系投影已读取；图与列表共用这一页固定版本。"); } catch { if (mounted.current && token === graphEpoch.current) { setProjection(null); note("关系投影读取失败；未报告无关系。", true); } } finally { if (mounted.current && token === graphEpoch.current) setGraphBusy(false); } }
  async function open(key: string) { if (locked.current) return; const token = ++epoch.current, prior = active.current, serial = b.serial; graphEpoch.current++; setPending(null); setHistory(null); setOriginal(null); setProjection(null); setGraphBusy(false); setPickingTarget(false);
    if (key === "__new") { const k = `local_${crypto.randomUUID()}`; buffers.current.set(k, { base: null, envelope: { type: "doc", content: [] }, relations: [], dirty: false, serial: 0, unsupported: false }); active.current = k; publish(); return; }
    try { let current = buffers.current.get(key); if (!current) current = fromDoc(await coreCommand<DocumentDto>("document_get", { document_id: key })); if (current.base?.document_id !== key) throw new Error("文档身份不符"); if (!mounted.current || token !== epoch.current) return; if (active.current !== prior || buffers.current.get(prior)?.serial !== serial || pendingInput.current) { note("读取期间新增编辑仍保留；请重新选择对象。"); return; } buffers.current.set(key, current); active.current = key; publish(); if (current.unsupported) note("未知关系结构保留；仅只读，未转换。", true); if (current.base) void graph(current.base); } catch { if (mounted.current && token === epoch.current) note("读取失败；当前草稿保留。", true); }
  }
  function requestOpen(key: string) { if (locked.current) return; if (formDirty) { note("请先添加或取消未提交关系；输入保留。", true); return; } if (b.dirty || b.attempt) setPending(key); else void open(key); }
  function clearForm() { setTargetId(""); setRelationLabel(""); setBlock(""); setSha(""); setPickingTarget(false); }
  function chooseTarget(target: ObjectReferenceDto) {
    if (busy || !documentLease.canWrite || b.unsupported || history) return;
    setTargetKind(target.kind);
    setTargetId(target.kind === "document" ? target.document_id : target.kind === "source" ? target.source_id : target.knowledge_id);
    setTargetVersion(target.kind === "document" ? String(target.version) : "1");
    setBlock(target.kind === "document" ? target.block_id ?? "" : "");
    setSha(target.kind === "source" ? target.sha256 : "");
    setPickingTarget(false);
    note("关联对象已选择；请填写关系说明，再加入草稿。尚未保存。");
  }
  function change(relations: RelationDto[]) { if (b.unsupported || history || !documentLease.canWrite) return; b.relations = relations; b.serial++; b.dirty = true; publish(); }
  function add() { try { const id = targetId.trim(); if (!id) throw new Error(); let target: ObjectReferenceDto;
    if (targetKind === "document") { const v = Number(targetVersion); if (!Number.isSafeInteger(v) || v < 1) throw new Error(); target = { kind: "document", document_id: id, version: v, ...(block ? { block_id: block } : {}) }; }
    else if (targetKind === "source") { if (!/^[a-f0-9]{64}$/.test(sha)) throw new Error(); target = { kind: "source", source_id: id, sha256: sha }; }
    else target = { kind: "knowledge", knowledge_id: id };
    change([...b.relations, { id: `relation_${crypto.randomUUID()}`, kind, label: relationLabel, target }]); clearForm(); note("关系已加入草稿；尚未由本地知识库验证或保存。");
  } catch { note("请填写真实目标与正整数版本 / 来源SHA；输入保留。", true); } }
  async function save() { try{await documentLease.write(saveRelations);}catch(error){note(error instanceof Error?error.message:"此文档视图只读",true);} }
  async function saveRelations() { if (locked.current || b.unsupported || history || formDirty) { if (formDirty) note("未提交关系仍保留；请先添加或取消。", true); return; } locked.current = true; setBusy(true); publish(); const current = b; let writeAcknowledged = false;
    try { const attempt: Attempt = current.attempt ?? (() => { const e = editor(current); return { operation: current.base ? "document_draft" as const : "document_create" as const, payload: current.base ? { document_id: current.base.document_id, body: { expected_version: current.base.version, editor_json: e } } : { body: { create_request_id: `relations_${crypto.randomUUID()}`, title: "关系文档", editor_json: e } }, editor: e, serial: current.serial, version:current.base?current.base.version+1:1 }; })(); current.attempt = attempt;
      if (attempt.operation === "document_create" && !attempt.expectedDocumentId) attempt.expectedDocumentId = await documentRequestIdentity(String(object(attempt.payload.body).create_request_id));
      const saved = await coreCommand<DocumentDto>(attempt.operation, attempt.payload); writeAcknowledged = true;
      if (attempt.operation === "document_create" && (saved.document_id !== attempt.expectedDocumentId || saved.title !== object(attempt.payload.body).title || saved.source_id !== null || saved.source_revision !== null)) throw new Error("新建回执身份不符"); if (current.base && saved.document_id !== current.base.document_id) throw new Error("保存身份不符"); const d = await coreCommand<DocumentDto>("document_get", { document_id: saved.document_id }); if ((attempt.operation === "document_create" && (d.document_id !== attempt.expectedDocumentId || d.title !== object(attempt.payload.body).title || d.source_id !== null || d.source_revision !== null)) || d.document_id !== saved.document_id || d.version !== saved.version || d.version !== attempt.version || d.content_sha256 !== saved.content_sha256 || !same(d.editor_json, attempt.editor)) throw new Error("保存读回不一致"); accept(current, d, attempt); note(current.dirty ? "已保存发送时的版本；随后编辑仍是未保存草稿。" : "关系已保存并读回核对。"); void graph(d);
    } catch (error) { if (!writeAcknowledged && error instanceof ApiError && error.status === 400) { current.attempt = undefined; current.dirty = true; note("本地知识库已明确拒绝此请求，未保存；全部草稿保留，可修改后重新保存。", true); } else note("保存未确认；草稿与冻结请求保留。冲突需核对，未报告成功。", true); } finally { locked.current = false; if (mounted.current) { setBusy(false); publish(); } }
  }
  function accept(current: Buffer, d: DocumentDto, attempt: Attempt) { current.base = d; current.attempt = undefined; current.dirty = current.serial !== attempt.serial; if (!current.dirty) { current.envelope = structuredClone(object(d.editor_json)); current.relations = fromDoc(d).relations; } buffers.current.set(d.document_id, current); if (mounted.current) setRows(old => [d, ...old.filter(x => x.document_id !== d.document_id)]); }
  async function reconcile() { if (!b.base || locked.current) return; if (pendingInput.current) { note("请先完成或取消未提交关系／集合输入；当前输入保留。", true); return; } locked.current = true; setBusy(true); const current = b, serial = b.serial, key = active.current, token = epoch.current; try { const d = await coreCommand<DocumentDto>("document_get", { document_id: current.base!.document_id }); if (!mounted.current || active.current !== key || epoch.current !== token) return; if (pendingInput.current || current.serial !== serial) { note("核对期间新增输入保留；未切换版本，请完成输入后重新核对。"); return; } if (d.document_id !== current.base!.document_id) throw new Error(); const a = current.attempt; if (a?.operation === "document_draft" && d.version === current.base!.version + 1 && same(d.editor_json, a.editor)) { accept(current, d, a); note("最新保存版本与冻结保存匹配；随后编辑保留。"); void graph(d); } else if (d.version === current.base!.version) note("保存版本未变化；草稿与冻结请求保留。"); else { setHistory(d); note("最新版本不同，仅只读比较；原草稿和原保存版本保留。", true); } } catch { note("核对失败；草稿保留。", true); } finally { locked.current = false; setBusy(false); publish(); } }
  async function readHistory() { if (!b.base || locked.current) return; if (pendingInput.current) { note("请先完成或取消未提交关系／集合输入；未进入历史，当前输入保留。", true); return; } const v = Number(version); if (!Number.isSafeInteger(v) || v < 1) { note("历史版本必须是正整数。", true); return; }
    const token = ++epoch.current, key = active.current, current = b, serial = b.serial, id = b.base.document_id, baseVersion = b.base.version;
    try { const d = await coreCommand<DocumentDto>("document_version", { document_id: id, version: v }); if (!mounted.current || token !== epoch.current || active.current !== key) return; if (current.serial !== serial || current.base?.version !== baseVersion || pendingInput.current || locked.current) { note("历史读取期间新增编辑仍保留；未切换为只读历史，请重新审阅。"); return; } if (d.document_id !== id || d.version !== v) throw new Error(); setHistory(d); void graph(d); note("历史版本只读；当前关系草稿保留。"); }
    catch { if (mounted.current && token === epoch.current && active.current === key && current.serial === serial && current.base?.version === baseVersion) note("历史版本不可用；未替换为最新版本。", true); }
  }
  async function follow(r: ObjectReferenceDto) { if (onOpenReference) { onOpenReference(r); return; } if (r.kind === "document") { if (b.dirty || b.attempt || formDirty) { note("请先保存或留在此页；未跳转，草稿保留。", true); return; } if (onOpenDocument) onOpenDocument(r.document_id, r.version, r.block_id ?? undefined); else note("固定文档详情入口尚未接通；未跳转到最新版本。", true); }
    else if (r.kind === "source") { const token = epoch.current; const key = active.current; try { const o = await coreCommand<OriginalDto>("source_original", { source_id: r.source_id }); if (o.source_id !== r.source_id || o.sha256 !== r.sha256) throw new Error(); const bytes = Uint8Array.from(atob(o.content_base64), c => c.charCodeAt(0)); const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))).map(x => x.toString(16).padStart(2, "0")).join(""); if (digest !== r.sha256) throw new Error(); if (mounted.current && token === epoch.current && key === active.current) { setOriginal(o); note("来源原件身份与实际文件指纹已核对。"); } } catch { if (mounted.current && token === epoch.current && key === active.current) note("原件读取或文件指纹核对失败；未打开错误原件。", true); } }
    else note(`知识引用 ${r.knowledge_id}：本页未实现知识详情跳转；未伪造文档版本。`);
  }
  const shown = history ? fromDoc(history).relations : b.relations;
  // Filter only the loaded, fixed-version projection; never imply a whole-library query.
  const visibleEdges = projection?.edges.filter(edge =>
    (directionFilter === "all" || edge.direction === directionFilter) &&
    (relationFilter === "all" || edge.relation.kind === relationFilter) &&
    (objectFilter === "all" || (edge.direction === "backlink" ? projection.nodes.find(node => node.key === edge.from)?.reference.kind : edge.relation.target.kind) === objectFilter)) ?? [];
  const visibleKeys = new Set(visibleEdges.flatMap(edge => [edge.from, edge.to]));
  const filtersActive = directionFilter !== "all" || relationFilter !== "all" || objectFilter !== "all";
  const visibleNodes = projection?.nodes.filter(node => !filtersActive || visibleKeys.has(node.key) || (node.reference.kind === "document" && node.reference.document_id === projection.center.document_id && node.reference.version === projection.center.version)) ?? [];
  return <section ref={section} tabIndex={-1} aria-label="关系工作区" className="stitch-relations-page">
    <header className="stitch-relations-heading"><div><span>固定版本关系</span><h2>双链与关系工作区</h2></div><div className="stitch-relations-actions"><button onClick={() => requestOpen("__new")} disabled={busy}>新关系草稿</button><button onClick={() => void list(false)} disabled={busy}>刷新文档</button><button disabled={busy || !documentLease.canWrite || b.unsupported || !!history || formDirty || (!b.dirty && !b.attempt)} onClick={() => void save()}>{b.attempt ? "重试冻结保存" : "保存关系草稿"}</button><button onClick={() => void reconcile()} disabled={!b.base || busy}>核对最新版本（保留草稿）</button></div></header>
    <p role={failed ? "alert" : "status"} className="stitch-relations-feedback">{message}</p>
    <div className="stitch-relations-session"><p data-business-session-key={documentLease.sessionKey}>{!documentLease.canWrite?"此对象由其他视图持有写入租约；当前只读。 ":""}{b.base ? `${b.base.document_id} · v${b.base.version}` : "本地未登记草稿"} · {b.dirty ? "未保存编辑" : "无未保存编辑"}</p></div>
    <div className="stitch-relations-workspace">
      <section className="stitch-relations-stage" aria-label="固定版本关系投影"><header><h3>关系投影</h3><div className="stitch-relations-view-tools"><button disabled={!b.base || graphBusy} onClick={() => b.base && void graph(history ?? b.base)}>刷新关系投影</button><button onClick={() => setListOnly(x => !x)}>{listOnly ? "显示关系图" : "图形不可用，切换列表"}</button></div></header>
        {!projection ? <p className="stitch-relations-empty">{graphBusy ? "正在读取固定版本关系投影…" : b.base ? "关系投影尚未就绪；可刷新投影重试，当前草稿保留。" : "选择已保存文档以读取它的实际关系投影；新关系仍可先加入草稿。"}</p> : null}
        {projection && <><p>投影中心 {projection.center.document_id} · v{projection.center.version}；扫描当前来源版本 {projection.scan.scanned} 项；{projection.scan.complete ? "这一范围扫描完成" : "扫描尚未完成，不能断言全库无关系"}；游标 {projection.scan.next_cursor ?? "无"}；不支持的来源 {projection.unsupported_sources.length}</p>{projection.projection_truncated && <p role="alert">这一页达到 1000 条关系的显示上限，另有 {projection.omitted_edges} 条未显示；图与列表均为部分投影。请打开来源固定版本／集合视图查看完整定义。</p>}{projection.scan.next_cursor && <button disabled={graphBusy} onClick={() => void graph(history ?? b.base!, projection.scan.next_cursor!)}>读取下一页反链</button>}
      <fieldset className="stitch-relations-filters"><legend>当前页局部关系筛选</legend><label>关系方向<select aria-label="筛选关系方向" value={directionFilter} onChange={event => setDirectionFilter(event.target.value)}><option value="all">全部方向</option><option value="outgoing">出链</option><option value="backlink">反链</option></select></label><label>关系类型<select aria-label="筛选关系类型" value={relationFilter} onChange={event => setRelationFilter(event.target.value)}><option value="all">全部关系</option>{(["related", "supports", "contradicts", "depends_on"] as const).map(value => <option key={value} value={value}>{relationKindLabels[value]}</option>)}</select></label><label>关联对象类型<select aria-label="筛选关联对象类型" value={objectFilter} onChange={event => setObjectFilter(event.target.value)}><option value="all">全部对象</option><option value="document">文档</option><option value="source">来源原件</option><option value="knowledge">知识</option></select></label><button type="button" onClick={() => { setDirectionFilter("all"); setRelationFilter("all"); setObjectFilter("all"); }}>重置关系筛选</button><p aria-live="polite">当前页显示 {visibleEdges.length} / {projection.edges.length} 条关系；筛选仅作用于已加载的固定版本投影，未查询全库。</p></fieldset>
      {!listOnly && <ConstellationGraph
        key={`${projection.center.document_id}:${projection.center.version}:${projection.snapshot_sha256}`}
        nodes={visibleNodes.map(relationGraphNode)} layoutNodes={projection.nodes.map(relationGraphNode)} edges={visibleEdges.map(relationGraphEdge)}
        centerId={projection.nodes.find(node => node.reference.kind === "document" && node.reference.document_id === projection.center.document_id && node.reference.version === projection.center.version && !node.reference.block_id)?.key ?? null}
        onOpen={id => { const node = visibleNodes.find(item => item.key === id); if (node?.status === "resolved") void follow(node.reference); }}/>}
      <ul aria-label="同版本关系列表">{visibleEdges.map((e, i) => <li key={e.id + i}>{e.direction === "backlink" ? "反链" : "出链"} · {relationKindLabels[e.relation.kind]} · {e.relation.label}{e.origin === "collection_property" ? ` · 集合记录 ${e.record_id}／属性 ${e.property_id}` : ""} · 来源 <button onClick={() => void follow({ kind: "document", document_id: e.source_snapshot.document_id, version: e.source_snapshot.version })}>{e.source_snapshot.document_id} v{e.source_snapshot.version}</button><button onClick={() => void follow(e.direction === "backlink" ? (projection.nodes.find(n => n.key === e.from)?.reference ?? { kind: "document", document_id: e.source_snapshot.document_id, version: e.source_snapshot.version }) : e.relation.target)}>打开固定对象 {e.direction === "backlink" ? label(projection.nodes.find(n => n.key === e.from)?.reference ?? { kind: "document", document_id: e.source_snapshot.document_id, version: e.source_snapshot.version }) : label(e.relation.target)}</button></li>)}</ul>{!projection.edges.length && <p>此页没有关系记录；仅限上述扫描范围。</p>}{projection.edges.length > 0 && !visibleEdges.length && <p>当前筛选没有匹配关系；已加载关系仍保留，可重置筛选。</p>}<ul aria-label="投影节点">{visibleNodes.map(n => <li key={n.key}>{label(n.reference)} · {n.status === "resolved" ? "已解析" : "目标不可用，未替换最新对象"}<button disabled={n.status !== "resolved"} onClick={() => void follow(n.reference)}>打开节点 {n.key}</button></li>)}</ul></>}
      </section>
      <aside className="stitch-relations-tools" aria-label="关系对象与编辑工具">
        <section className="stitch-relations-card"><header><h3>文档与草稿</h3></header><ul aria-label="已保存文档">{rows.map(d => <li key={d.document_id}><button disabled={busy} onClick={() => requestOpen(d.document_id)}>{d.title} · v{d.version}</button></li>)}</ul>{cursor && <button onClick={() => void list(true)}>加载更多文档</button>}</section>
        <section className="stitch-relations-card"><fieldset disabled={busy || !documentLease.canWrite || b.unsupported || !!history}><legend>关系编辑</legend><label>关系类型<select value={kind} onChange={e => setKind(e.target.value as RelationDto["kind"])}>{(["related", "supports", "contradicts", "depends_on"] as const).map(x => <option key={x} value={x}>{relationKindLabels[x]}</option>)}</select></label><label>关系说明<input value={relationLabel} onChange={e => setRelationLabel(e.target.value)}/></label>
          <button type="button" onClick={() => setPickingTarget(true)}>选择关联对象</button>
          {pickingTarget ? <><ObjectReferencePicker disabled={busy || !documentLease.canWrite || b.unsupported || !!history} onPick={chooseTarget}/><button type="button" onClick={() => setPickingTarget(false)}>取消对象选择</button></> : null}
          {targetId ? <p>当前目标：{targetKind === "document" ? rows.find(row => row.document_id === targetId)?.title || targetId : targetId} · {targetKindLabels[targetKind]}{targetKind === "document" ? `，第 ${targetVersion} 版` : ""}；尚未加入关系草稿。</p> : <p>从已保存内容选择对象；也可展开下方高级选项手动定位。</p>}
          <details><summary>手动指定对象</summary><p>高级定位：请填写准确的对象编号、文档版本或原件文件指纹。加入草稿后仍需保存并核对，不会自动改用其他对象。</p><label>目标类型<select value={targetKind} onChange={e => setTargetKind(e.target.value as ObjectReferenceDto["kind"])}><option value="document">文档</option><option value="source">来源原件</option><option value="knowledge">知识</option></select></label><label>目标对象ID<input value={targetId} onChange={e => setTargetId(e.target.value)}/></label>{targetKind === "document" && <><label>固定目标版本<input value={targetVersion} onChange={e => setTargetVersion(e.target.value)}/></label><label>目标段落编号<input value={block} onChange={e => setBlock(e.target.value)}/></label></>}{targetKind === "source" && <label>来源文件指纹<input value={sha} onChange={e => setSha(e.target.value)}/></label>}</details><button onClick={add}>加入关系草稿</button><button onClick={clearForm}>取消未提交关系</button>
      <ul aria-label="关系草稿">{shown.map(r => <li key={r.id}>{relationKindLabels[r.kind]} · {r.label} · {label(r.target)} <label><input type="checkbox" aria-label={`嵌入呈现 ${r.id}`} checked={r.presentation === "embed"} onChange={event => change(b.relations.map(item => { if (item.id !== r.id) return item; const next = { ...item }; if (event.target.checked) next.presentation = "embed"; else delete next.presentation; return next; }))}/>在文档中显示固定嵌入</label> <button onClick={() => change(b.relations.filter(x => x.id !== r.id))} aria-label={`删除关系 ${r.id}`}>删除</button></li>)}</ul></fieldset></section>
        <section className="stitch-relations-card"><header><h3>历史与只读比较</h3></header><div className="stitch-relations-history"><label>历史版本<input value={version} onChange={e => setVersion(e.target.value)}/></label><button disabled={!b.base || busy} title={!b.base?"需要先打开或保存一份文档":undefined} onClick={() => void readHistory()}>读取历史关系（只读）</button>{history && <><p>只读比较 v{history.version}；未覆盖草稿</p><button onClick={() => { epoch.current++; setHistory(null); if (b.base) void graph(b.base); }}>返回当前草稿</button></>}</div></section>
        <details className="stitch-relations-card"><summary>关系保存与能力范围</summary><p>文档关系由本地知识库保存；图形只是同一份已保存内容的投影。学术检索与图谱增强尚未接入。</p></details>
        {b.unsupported && <details><summary>保留的原始文档（只读）</summary><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(b.envelope, null, 2)}</pre></details>}
        {original && <details open><summary>已核对本地原件</summary><p>{original.name} · {original.media_type} · {original.sha256}；原件字节已读取，不执行附件。</p></details>}
      </aside>
    </div>
    {renderCollection ? <section className="stitch-relations-collection" aria-label="保存版集合与关系属性">{renderCollection?.(history ?? b.base, history ? object(history.editor_json) : b.envelope, next=>{if(b.unsupported || history || !documentLease.canWrite)return;b.envelope=structuredClone(next);b.serial++;b.dirty=true;publish();},setCollectionPending,busy || !documentLease.canWrite || b.unsupported || !!history)}</section> : null}
    <AaosDialog onCloseAutoFocus={event => { event.preventDefault(); section.current?.focus(); }} trigger={<button disabled={!pending}>审阅关系对象切换</button>} open={!!pending} title="保留关系草稿后切换" description="未保存草稿保留在当前页；取消返回编辑。" onOpenChange={v => { if (!v) setPending(null); }}><p>当前草稿保留在本页会话；关闭页面后的恢复尚未证明。</p><button onClick={() => setPending(null)}>取消切换</button><button onClick={() => pending && void open(pending)}>保留草稿并切换</button></AaosDialog>
  </section>;
}
