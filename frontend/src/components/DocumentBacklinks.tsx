import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentDto, ObjectReferenceDto, RelationEdgeDto, RelationNodeDto, RelationProjectionDto } from "../api/generated/core-contract";
import "./document-backlinks.css";

type SavedCenter = Pick<DocumentDto, "document_id" | "version" | "content_sha256">;
const kindLabels = { related: "相关", supports: "支持", contradicts: "矛盾", depends_on: "依赖" } as const;
const EDGE_LIMIT = 1000;

function referenceLabel(reference: ObjectReferenceDto): string {
  if (reference.kind === "document") return `${reference.document_id} · v${reference.version}${reference.block_id ? ` · ${reference.block_id}` : ""}`;
  if (reference.kind === "source") return `${reference.source_id} · ${reference.sha256}`;
  return reference.knowledge_id;
}

/** The resolved source of an incoming edge, never a substitute for it. */
function sourceReference(edge: RelationEdgeDto, nodes: RelationNodeDto[]): ObjectReferenceDto | null {
  const node = nodes.find(item => item.key === edge.from);
  if (!node || node.status !== "resolved") return null;
  const reference = node.reference;
  if (reference.kind !== "document" || reference.document_id !== edge.source_snapshot.document_id) return null;
  return reference;
}

function readProjection(value: RelationProjectionDto, center: SavedCenter): RelationEdgeDto[] {
  if (value.schema !== "archeaxis.relation-projection/v1") throw new Error("关系投影结构不符");
  if (value.center.document_id !== center.document_id || value.center.version !== center.version || value.center.content_sha256 !== center.content_sha256) throw new Error("关系投影中心版本不符");
  if (!Array.isArray(value.nodes) || !Array.isArray(value.edges) || !Array.isArray(value.unsupported_sources)) throw new Error("关系投影缺少节点或边");
  const seen = new Set<string>();
  for (const edge of value.edges) {
    if (typeof edge.id !== "string" || seen.has(edge.id)) throw new Error("关系投影边身份重复");
    seen.add(edge.id);
    if (edge.direction !== "backlink" && edge.direction !== "outgoing") throw new Error("关系投影方向未知");
    if (!edge.source_snapshot || typeof edge.source_snapshot.document_id !== "string" || !Number.isSafeInteger(edge.source_snapshot.version) || typeof edge.source_snapshot.content_sha256 !== "string") throw new Error("关系投影来源快照无效");
    if (!edge.relation || typeof edge.relation.label !== "string" || !Object.hasOwn(kindLabels, edge.relation.kind)) throw new Error("关系投影关系类型无效");
  }
  return value.edges;
}

/** Read-only reading surface for references other notes make to this saved version.
 * Local projection only: it never claims a whole-library search. */
export function DocumentBacklinks({ document, onOpenReference }: { document: SavedCenter; onOpenReference?: (reference: ObjectReferenceDto) => void }) {
  const [projection, setProjection] = useState<RelationProjectionDto | null>(null);
  const [edges, setEdges] = useState<RelationEdgeDto[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const request = useRef(0);
  const center = `${document.document_id}:${document.version}:${document.content_sha256}`;
  const current = useRef(center);
  current.current = center;
  useEffect(() => { request.current++; setProjection(null); setEdges([]); setError(""); setBusy(false); }, [center]);

  async function load(cursor?: string) {
    if (busy) return;
    const token = ++request.current, identity = center;
    setBusy(true); setError("");
    try {
      const value = await coreCommand<RelationProjectionDto>("document_graph", cursor ? { document_id: document.document_id, version: document.version, cursor } : { document_id: document.document_id, version: document.version });
      if (token !== request.current || identity !== current.current) return;
      const next = readProjection(value, document);
      setProjection(value);
      setEdges(previous => {
        const backlinks = next.filter(edge => edge.direction === "backlink");
        if (!cursor) return backlinks;
        const known = new Set(previous.map(edge => edge.id));
        return [...previous, ...backlinks.filter(edge => !known.has(edge.id))].slice(0, EDGE_LIMIT);
      });
    } catch {
      if (token === request.current && identity === current.current) setError("反链读取失败；未显示为空或全库结论。当前文档与草稿保持不变，可重试。");
    } finally {
      if (token === request.current) setBusy(false);
    }
  }

  return <section className="document-backlinks" aria-label="本页反向链接">
    <h4>反向链接</h4>
    <p>读取当前保存版本的反链投影，只显示指向本页的引用。不查询全库，也不改动正文。</p>
    <button type="button" disabled={busy} onClick={() => void load()}>{projection ? "重新读取反向链接" : "读取反向链接"}</button>
    {busy ? <p role="status">正在读取固定版本反链…</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {projection ? <>
      <p role="status">扫描当前来源版本 {projection.scan.scanned} 项；{projection.scan.complete ? "这一范围扫描完成" : "扫描尚未完成，不能断言全库无反链"}；已显示 {edges.length} 条反链。</p>
      {projection.projection_truncated ? <p role="alert">这一页达到 {EDGE_LIMIT} 条关系上限，另有 {projection.omitted_edges ?? 0} 条未显示；当前反链只是部分投影。</p> : null}
      {projection.unsupported_sources.length ? <p role="status">有 {projection.unsupported_sources.length} 个来源的关系或集合元数据暂不支持，未当作无反链。</p> : null}
      {edges.length ? <ul aria-label="反向链接列表">{edges.map(edge => {
        const reference = sourceReference(edge, projection.nodes);
        return <li key={edge.id}>
          <p>{kindLabels[edge.relation.kind]} · {edge.relation.label || "未填写说明"}{edge.origin === "collection_property" ? ` · 集合记录 ${edge.record_id ?? "未知"}／属性 ${edge.property_id ?? "未知"}` : ""}</p>
          <p>来源 {edge.source_snapshot.document_id} · v{edge.source_snapshot.version}</p>
          {reference ? <button type="button" disabled={!onOpenReference} onClick={() => onOpenReference?.(reference)}>打开来源固定版本 {referenceLabel(reference)}</button>
            : <p role="status">来源对象不可用或身份不符；未替换为最新对象。</p>}
        </li>;
      })}</ul> : <p>{projection.scan.complete ? "这一范围扫描完成，没有反链记录。" : "此页没有反链记录；扫描未完成。"}</p>}
      {projection.scan.next_cursor ? <button type="button" disabled={busy} onClick={() => void load(projection.scan.next_cursor ?? undefined)}>读取下一页反链</button> : null}
    </> : null}
  </section>;
}
