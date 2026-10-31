import { useRef, useState } from "react";
import { assertCoreDto, type DocumentRelationsDto, type ObjectReferenceDto, type RelationDto } from "../api/generated/core-contract";
import { PinnedReferencePanel } from "./PinnedReferencePanel";

const PAGE_SIZE = 3;

function embedTitle(relation: RelationDto): string {
  // This only shortens a known importer display label. Targets and permissions
  // always come from the validated typed reference, never this text.
  const imported = /^ingest_[a-f0-9]{64}$/.test(relation.id)
    ? /^Original CAS [a-f0-9]{64} · embed: (.+)$/s.exec(relation.label) : null;
  return imported ? `嵌入：${imported[1].replace(/ \(human-selected block\)(?= \| |$)/g, "（已选定块）")}` : relation.label;
}

function EmbedPage({ relations, onOpenReference }: { relations: RelationDto[]; onOpenReference?: (reference: ObjectReferenceDto) => void }) {
  const [page, setPage] = useState(0);
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set());
  const cards = useRef(new Map<string, HTMLElement>());
  const visible = relations.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  return <section className="ui-document-embeds" aria-label="文档嵌入内容">
    <h3>已绑定的嵌入内容</h3>
    <p>来自已保存文档的固定引用，正文和原件保留。每组最多展开三个；目标更新后仍阅读所绑定的版本。</p>
    <p aria-live="polite">第 {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, relations.length)} 项，共 {relations.length} 项</p>
    {visible.map(relation => <article key={relation.id} className="ui-document-embed" tabIndex={-1} ref={node => { if (node) cards.current.set(relation.id, node); else cards.current.delete(relation.id); }}>
      <header><h4>{embedTitle(relation)}</h4>{onOpenReference && <button type="button" onClick={() => onOpenReference(relation.target)}>打开固定引用</button>}</header>
      {embedTitle(relation) !== relation.label && <details><summary>原始关系说明</summary><p>{relation.label}</p></details>}
      {collapsed.has(relation.id)
        ? <button type="button" onClick={() => setCollapsed(previous => { const next = new Set(previous); next.delete(relation.id); return next; })}>展开嵌入 {embedTitle(relation)}</button>
        : <PinnedReferencePanel embedded reference={relation.target} onOpenReference={onOpenReference} onClose={() => { setCollapsed(previous => new Set(previous).add(relation.id)); cards.current.get(relation.id)?.focus(); }}/>}
    </article>)}
    {relations.length > PAGE_SIZE && <nav aria-label="嵌入分页">
      <button type="button" disabled={page === 0} onClick={() => setPage(value => value - 1)}>上一组嵌入</button>
      <button type="button" disabled={(page + 1) * PAGE_SIZE >= relations.length} onClick={() => setPage(value => value + 1)}>下一组嵌入</button>
    </nav>}
  </section>;
}

/** Consume the saved relation envelope, never derive a second graph from labels or
 * edited Markdown. Target readers do not mount this component recursively. */
export function DocumentEmbeds({ editor, onOpenReference }: { editor: unknown; onOpenReference?: (reference: ObjectReferenceDto) => void }) {
  const metadata = (editor as { attrs?: { archeaxis_relations?: unknown } } | null)?.attrs?.archeaxis_relations;
  if (metadata === undefined) return null;
  let relations: RelationDto[];
  try {
    const envelope = assertCoreDto<DocumentRelationsDto>("DocumentRelationsDto", metadata);
    if (envelope.relations.length > 256 || new Set(envelope.relations.map(item => item.id)).size !== envelope.relations.length) throw new Error("relation budget or duplicate identity");
    relations = envelope.relations.filter(relation => relation.presentation === "embed");
  } catch {
    return <p role="alert">嵌入关系结构不可用；原文保留，未猜测目标或读取其他版本。</p>;
  }
  if (!relations.length) return null;
  return <EmbedPage key={JSON.stringify(relations)} relations={relations} onOpenReference={onOpenReference}/>;
}
