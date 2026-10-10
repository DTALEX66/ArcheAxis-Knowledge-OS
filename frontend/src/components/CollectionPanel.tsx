import { useEffect, useRef, useState } from 'react';
import type { DocumentDto, ObjectReferenceDto } from '../api/generated/core-contract';
import { coreCommand } from '../api/core';
import { assertCollectionDto, parseCollection, type Collection, type CollectionProperty, type CollectionRecord, type CollectionView, type CollectionQueryDto, type CollectionRow, type JSONValue, type FormulaDefinition, type BoundedFormula } from '../api/generated/collection-contract';
import './collection-panel.css';

export type CollectionPanelProps = {
  document: DocumentDto | null; value: unknown | undefined; onChange: (value: Collection) => void;
  readOnly?: boolean; disabled?: boolean; onPendingEditChange?: (pending: boolean) => void;
  onOpenReference?: (ref: ObjectReferenceDto) => void;
};
type RawDraft = { raw: string; error?: string };
const engine = 'archeaxis.bounded-formula/v1';
const empty = (): Collection => ({ schema: 'archeaxis.collection/v1', properties: [], records: [], views: [{ view_id: 'table', name: '表格', kind: 'table' }] });
const encode = (value: unknown) => JSON.stringify(value, null, 2);
const canonical = (v: unknown): string => Array.isArray(v) ? '[' + v.map(canonical).join(',') + ']' : v && typeof v === 'object' ? '{' + Object.entries(v).sort(([a], [b]) => a.localeCompare(b)).map(([k, x]) => JSON.stringify(k) + ':' + canonical(x)).join(',') + '}' : JSON.stringify(v) ?? 'undefined';
const id = (prefix: string) => `${prefix}_${crypto.randomUUID()}`;
const format = (v: unknown) => v === undefined ? '未提供' : v === null ? '空值' : typeof v === 'string' ? v : JSON.stringify(v);
const groupLabel = (key: string) => { try { return format(JSON.parse(key)); } catch { return `无法解析分组键：${key}`; } };
function validateValues(values: Record<string, JSONValue>, properties: CollectionProperty[]) {
  for (const [key, v] of Object.entries(values)) {
    const p = properties.find(p => p.property_id === key);
    if (!p || p.kind === 'formula') throw new Error('未知属性或手填公式值；输入保留');
    if (v === null) continue;
    if (typeof v === 'number' && Number.isInteger(v) && !Number.isSafeInteger(v)) throw new Error('NumberRange：整数超出 IEEE754 安全范围；原输入保留');
    const valid = p.kind === 'text' ? typeof v === 'string' : p.kind === 'number' ? typeof v === 'number' && Number.isFinite(v)
      : p.kind === 'boolean' ? typeof v === 'boolean' : p.kind === 'select' ? typeof v === 'string' && (p.options ?? []).includes(v)
      : p.kind === 'date' ? typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v)
      : p.kind === 'relation' ? Array.isArray(v) && v.length <= 100 && v.every(x => { try { assertCollectionDto('ObjectReferenceDto', x); return true; } catch { return false; } }) : false;
    if (!valid) throw new Error(`属性 ${key} 类型不匹配；真实日期、引用和公式资格仍由 Core 校验`);
  }
}
function validateFormula(f: FormulaDefinition) {
  if (f.dialect !== engine) return;
  const ast = assertCollectionDto<BoundedFormula>('BoundedFormula', f.expression);
  let count = 0; const keys = new Set<string>();
  const visit = (n: BoundedFormula, depth: number) => {
    if (++count > 256 || depth > 16) throw new Error('AST 超出256节点或16层；输入保留');
    if (n.op === 'property') keys.add(n.key);
    else if (n.op === 'literal') {
      if (typeof n.value === 'string' && new TextEncoder().encode(n.value).length > 16384) throw new Error('AST 字符串超过16KiB');
      if (typeof n.value === 'number' && Number.isInteger(n.value) && !Number.isSafeInteger(n.value)) throw new Error('NumberRange：整数输入超出 IEEE754 安全范围');
    } else if (n.op === 'if') { visit(n.condition, depth + 1); visit(n.then, depth + 1); visit(n.otherwise, depth + 1); }
    else { visit(n.left, depth + 1); visit(n.right, depth + 1); }
  }; visit(ast, 0);
  if (new Set(f.dependencies).size !== f.dependencies.length || keys.size !== f.dependencies.length || f.dependencies.some(k => !keys.has(k))) throw new Error('依赖列表必须与 AST 的属性引用一致');
}

/** Controlled metadata editor. No Document create/draft commands or client formula evaluator. */
export function CollectionPanel({ document, value, onChange, readOnly = false, disabled = false, onPendingEditChange, onOpenReference }: CollectionPanelProps) {
  const collection = parseCollection(value);
  const locked = readOnly || disabled || (value !== undefined && !collection);
  const objectKey = document?.document_id ?? 'unsaved';
  const [drafts, setDrafts] = useState<Record<string, RawDraft>>({});
  const [selected, setSelected] = useState<Record<string, string>>({});
  const viewId = selected[objectKey] ?? collection?.views[0]?.view_id ?? '';
  const [query, setQuery] = useState<CollectionQueryDto | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const sequence = useRef(0), pendingRequest = useRef(false);
  const callback = useRef(onPendingEditChange); callback.current = onPendingEditChange;
  const queryIdentity = `${document?.document_id ?? ''}:${document?.version ?? ''}:${document?.content_sha256 ?? ''}:${viewId}`;
  const liveIdentity = useRef(queryIdentity); liveIdentity.current = queryIdentity;
  useEffect(() => { callback.current?.(Object.keys(drafts).length > 0); }, [drafts]);
  useEffect(() => () => { sequence.current++; callback.current?.(false); }, []);
  useEffect(() => { sequence.current++; pendingRequest.current = false; setBusy(false); setQuery(null); setError(''); }, [queryIdentity]);
  const change = (next: Collection) => { if (!locked) onChange(next); };
  const updateProperty = (p: CollectionProperty) => { if (collection) change({ ...collection, properties: collection.properties.map(x => x.property_id === p.property_id ? p : x) }); };
  const updateRecord = (r: CollectionRecord) => { if (collection) change({ ...collection, records: collection.records.map(x => x.record_id === r.record_id ? r : x) }); };
  const updateView = (v: CollectionView) => { if (collection) change({ ...collection, views: collection.views.map(x => x.view_id === v.view_id ? v : x) }); };
  const clear = (key: string) => setDrafts(old => { const next = { ...old }; delete next[key]; return next; });
  function jsonEditor(label: string, key: string, current: unknown, apply: (parsed: unknown) => void, schema?: string, readonly = false) {
    const fullKey = `${objectKey}:${key}`;
    const draft = drafts[fullKey];
    return <div className="collection-json-editor" key={fullKey}>
      <label>{label}<textarea aria-label={label} value={draft?.raw ?? encode(current) ?? 'null'} readOnly={locked || readonly}
        onChange={e => setDrafts(old => ({ ...old, [fullKey]: { raw: e.target.value } }))} /></label>
      {draft && <><button disabled={locked || readonly} onClick={() => {
        try { const parsed: unknown = JSON.parse(draft.raw); if (schema) assertCollectionDto(schema, parsed); apply(parsed); clear(fullKey); }
        catch (e) { setDrafts(old => ({ ...old, [fullKey]: { ...draft, error: `无法应用：${e instanceof Error ? e.message : String(e)}；输入已保留。` } })); }
      }}>应用 {label}</button><button disabled={disabled} onClick={() => clear(fullKey)}>取消 {label}</button>
      {draft.error && <p role="alert">{draft.error}</p>}</>}
    </div>;
  }
  async function load(offset = 0) {
    if (!document || !viewId || pendingRequest.current) return;
    pendingRequest.current = true; setBusy(true); setError(''); setQuery(null);
    const request = ++sequence.current, identity = queryIdentity;
    try {
      const raw = await coreCommand<unknown>('collection_query', { document_id: document.document_id, version: document.version, view_id: viewId, offset, limit: 20 });
      const next = assertCollectionDto<CollectionQueryDto>('CollectionQueryDto', raw);
      if (next.document_id !== document.document_id || next.version !== document.version || next.view.view_id !== viewId || next.content_sha256 !== document.content_sha256) throw new Error('Core 投影与请求的已保存快照不一致。');
      if (sequence.current === request && liveIdentity.current === identity) setQuery(next);
    } catch (e) { if (sequence.current === request && liveIdentity.current === identity) setError(`读取失败：${e instanceof Error ? e.message : String(e)}。未显示空列表作为成功。`); }
    finally { if (sequence.current === request) { pendingRequest.current = false; setBusy(false); } }
  }
  const reference = (r: ObjectReferenceDto) => <button type="button" disabled={!onOpenReference || disabled} onClick={() => onOpenReference?.(r)}>{r.kind === 'document' ? `${r.document_id} · v${r.version}${r.block_id ? ' · ' + r.block_id : ''}` : r.kind === 'source' ? `${r.source_id} · ${r.sha256}` : r.knowledge_id}</button>;
  const cell = (r: CollectionRow, p: CollectionProperty) => {
    const value = r.values[p.property_id];
    return r.formula_errors[p.property_id] ? <span role="status">错误：{r.formulas.find(f => f.property_id === p.property_id)?.error_code ?? 'FORMULA_ERROR'} · {r.formula_errors[p.property_id]}</span>
      : p.kind === 'relation' && Array.isArray(value) ? value.map((x, i) => <span key={i}>{reference(x as ObjectReferenceDto)}</span>) : format(value);
  };
  const card = (r: CollectionRow) => <article key={r.record_id} className="collection-card"><h4>{r.record_id}</h4>{reference(r.reference)}<dl>{query?.definition.properties.map(p => <div key={p.property_id}><dt>{p.name}</dt><dd>{cell(r, p)}</dd></div>)}</dl></article>;
  const projection = () => {
    if (!query) return null;
    const rows = query.items, kind = query.view.kind;
    if (kind === 'table') return <div className="collection-table-scroll"><table><caption>已保存 v{query.version} · {query.total} 条 · 当前页 {rows.length} 条</caption><thead><tr><th>记录引用</th>{query.definition.properties.map(p => <th key={p.property_id}>{p.name}</th>)}</tr></thead><tbody>{rows.map(r => <tr key={r.record_id}><td>{reference(r.reference)}</td>{query.definition.properties.map(p => <td key={p.property_id}>{cell(r, p)}</td>)}</tr>)}</tbody></table></div>;
    if (kind === 'board' || kind === 'calendar') {
      const key = kind === 'calendar' ? query.view.date_property : query.view.group_by;
      const groups = new Map<string, CollectionRow[]>();
      for (const r of rows) { const name = format(key ? r.values[key] : undefined); groups.set(name, [...(groups.get(name) ?? []), r]); }
      return <div className={`collection-${kind}`}>{[...groups].map(([name, items]) => <section key={name}><h4>{name}</h4>{items.map(card)}</section>)}</div>;
    }
    return <div className={`collection-${kind}`}>{rows.map(card)}</div>;
  };
  return <section className="collection-panel" aria-label="集合属性与视图">
    <h3>集合属性与视图</h3><p>编辑定义交给父级文档保存；计算、过滤和分页由 Core 读取已保存版本。公式使用有限 IEEE754 f64，不声明外部方言、精确大整数、单位或时区等价。</p>
    {value === undefined ? <button disabled={locked} onClick={() => change(empty())}>添加集合定义</button> : !collection ? <><p role="alert">未知或不支持的集合形状，只读保留原文；不会移除字段重新保存。</p><details><summary>保全原始内容</summary><pre>{encode(value)}</pre></details></> : <>
      {collection.source_payload !== undefined && <details><summary>来源原文（只读保全）</summary><pre>{encode(collection.source_payload)}</pre></details>}
      <details open><summary>属性</summary><button disabled={locked || collection.properties.length >= 64} onClick={() => change({ ...collection, properties: [...collection.properties, { property_id: id('property'), name: '新属性', kind: 'text' }] })}>添加属性</button>
        {collection.properties.map(p => { const unsupported = !!p.formula && (p.formula.dialect !== engine || p.formula.engine_version !== engine); return <fieldset key={p.property_id} disabled={locked}><legend>{p.property_id}</legend>
          <label>属性名称<input aria-label={`属性名称 ${p.property_id}`} value={p.name} onChange={e => updateProperty({ ...p, name: e.target.value })} disabled={unsupported} /></label>
          <label>属性类型<select aria-label={`属性类型 ${p.property_id}`} value={p.kind} disabled={unsupported} onChange={e => { const kind = e.target.value as CollectionProperty['kind']; updateProperty({ ...p, kind, formula: kind === 'formula' ? p.formula ?? { dialect: engine, engine_version: engine, expression: { op: 'literal', value: null }, dependencies: [], output_type: 'text' } : null }); }}>
            {['text','number','boolean','date','select','relation','formula'].map(k => <option key={k}>{k}</option>)}</select></label>
          {['unit','timezone'].map(k => <label key={k}>{k}<input aria-label={`${k} ${p.property_id}`} value={p[k as 'unit' | 'timezone'] ?? ''} disabled={unsupported} onChange={e => updateProperty({ ...p, [k]: e.target.value || null })} /></label>)}
          {p.kind === 'select' && jsonEditor(`选项 ${p.property_id}`, `property:${p.property_id}:options`, p.options ?? [], x => { if (!Array.isArray(x) || x.some(v => typeof v !== 'string')) throw new Error('选项须为字符串数组'); updateProperty({ ...p, options: x as string[] }); })}
          {p.formula && <>{unsupported && <p role="status">外部方言或引擎版本：NOT_EXECUTED。公式定义与来源原文只读保全；可删除整个属性（显式操作）。</p>}<p>有界 AST：literal、property、add/subtract/multiply/divide、concat、equal、if；最多256节点／16层。不执行脚本，依赖须列出真实属性键。</p>{jsonEditor(`公式 AST 与依赖 ${p.property_id}`, `property:${p.property_id}:formula`, p.formula, x => { const formula = x as FormulaDefinition; validateFormula(formula); updateProperty({ ...p, formula }); }, 'FormulaDefinition', unsupported)}</>}
          {p.source_payload !== undefined && <details><summary>属性来源（只读）</summary><pre>{encode(p.source_payload)}</pre></details>}
          <button onClick={() => change({ ...collection, properties: collection.properties.filter(x => x.property_id !== p.property_id), records: collection.records.map(r => ({ ...r, values: Object.fromEntries(Object.entries(r.values).filter(([k]) => k !== p.property_id)) })) })}>删除属性 {p.property_id}</button>
        </fieldset>; })}</details>
      <details><summary>记录与真实关系引用</summary><p>引用需真实 Document ID + version（可含 block_id）、Source ID + sha256 或不可变 Knowledge ID；Core 保存时验证，标题不能替代身份。关系字段使用引用数组。</p>
        <button disabled={locked || !document || collection.records.length >= 500} onClick={() => { if (document) change({ ...collection, records: [...collection.records, { record_id: id('record'), reference: { kind: 'document', document_id: document.document_id, version: document.version }, values: {} }] }); }}>添加记录（当前保存文档引用）</button>
        {collection.records.map(r => <fieldset key={r.record_id} disabled={locked}><legend>{r.record_id}</legend>{reference(r.reference)}
          {jsonEditor(`记录引用 ${r.record_id}`, `record:${r.record_id}:reference`, r.reference, x => updateRecord({ ...r, reference: x as CollectionRecord['reference'] }), 'ObjectReferenceDto')}
          {collection.properties.filter(p => p.kind !== 'formula').map(p => jsonEditor(`值 ${r.record_id} / ${p.property_id} (${p.kind})`, `record:${r.record_id}:value:${p.property_id}`, r.values[p.property_id] ?? null, x => { const values = { ...r.values, [p.property_id]: assertCollectionDto<JSONValue>('JSONValue', x) }; validateValues(values, collection.properties); updateRecord({ ...r, values }); }))}
          <p>公式值只由 Core 投影，不能手填。缺失与 null 均保留各自语义。</p>
          {jsonEditor(`全部原始值 ${r.record_id}`, `record:${r.record_id}:values`, r.values, x => { if (!x || typeof x !== 'object' || Array.isArray(x)) throw new Error('须为属性键值对象'); const values = x as Record<string, JSONValue>; assertCollectionDto('JSONValue', values); validateValues(values, collection.properties); updateRecord({ ...r, values }); })}
          {r.source_payload !== undefined && <details><summary>记录来源（只读）</summary><pre>{encode(r.source_payload)}</pre></details>}
          <button onClick={() => change({ ...collection, records: collection.records.filter(x => x.record_id !== r.record_id) })}>删除记录 {r.record_id}</button>
        </fieldset>)}</details>
      <details><summary>过滤、排序与视图定义</summary><button disabled={locked || collection.views.length >= 16} onClick={() => change({ ...collection, views: [...collection.views, { view_id: id('view'), name: '新视图', kind: 'table' }] })}>添加视图</button>
        {collection.views.map(v => <fieldset key={v.view_id} disabled={locked}><legend>{v.view_id}</legend><label>视图名称<input aria-label={`视图名称 ${v.view_id}`} value={v.name} onChange={e => updateView({ ...v, name: e.target.value })} /></label>
          <label>布局<select aria-label={`布局 ${v.view_id}`} value={v.kind} onChange={e => updateView({ ...v, kind: e.target.value as CollectionView['kind'] })}>{['table','list','board','calendar','gallery'].map(k => <option key={k}>{k}</option>)}</select></label>
          {['group_by','date_property'].map(k => <label key={k}>{k}<select aria-label={`${k} ${v.view_id}`} value={v[k as 'group_by'|'date_property'] ?? ''} onChange={e => updateView({ ...v, [k]: e.target.value || null })}><option value="">不设置</option>{collection.properties.map(p => <option key={p.property_id} value={p.property_id}>{p.name} ({p.kind})</option>)}</select></label>)}
          {jsonEditor(`过滤 ${v.view_id}`, `view:${v.view_id}:filter`, v.filter ?? null, x => { if (x !== null) assertCollectionDto('CollectionFilter', x); updateView({ ...v, filter: x as CollectionView['filter'] }); })}
          {jsonEditor(`排序 ${v.view_id}`, `view:${v.view_id}:sort`, v.sort ?? [], x => { if (!Array.isArray(x) || x.length > 8) throw new Error('排序最多8项'); x.forEach(s => assertCollectionDto('CollectionSort', s)); updateView({ ...v, sort: x as CollectionView['sort'] }); })}
          <button onClick={() => change({ ...collection, views: collection.views.filter(x => x.view_id !== v.view_id) })}>删除视图 {v.view_id}</button>
        </fieldset>)}</details>
      <div className="collection-query-controls"><label>读取保存版视图<select aria-label="读取保存版视图" value={viewId} disabled={busy} onChange={e => setSelected(old => ({ ...old, [objectKey]: e.target.value }))}>{collection.views.map(v => <option key={v.view_id} value={v.view_id}>{v.name}</option>)}</select></label><button disabled={disabled || busy || !document || !viewId} onClick={() => void load()}>读取已保存投影</button></div>
      {!document && <p>新文档尚未保存，暂不能查询。定义与记录草稿可继续编辑。</p>}
      {busy && <p role="status">读取 Core 保存版投影…</p>}{error && <p role="alert">{error}</p>}
      {query && <><p role="status">保存版 v{query.version} · {query.content_sha256}。{canonical(query.definition) !== canonical(collection) ? '当前缓冲定义尚未保存；以下不代表草稿计算结果。' : '与当前定义相符。'}</p><p>共 {query.total} 条匹配记录，当前页 {query.items.length} 条。看板／日期布局仅展示当前页；分组总数来自完整过滤结果。</p>{Object.keys(query.group_counts).length > 0 && <dl aria-label="分组总数">{Object.entries(query.group_counts).map(([key, count]) => <div key={key}><dt>{groupLabel(key)}</dt><dd>{count}</dd></div>)}</dl>}
        {query.total === 0 ? <p>Core 查询成功：没有匹配记录。</p> : projection()}
        {query.items.flatMap(r => r.formulas.map(f => <p key={`${r.record_id}:${f.property_id}`}>{r.record_id}/{f.property_id} · {f.status} · {f.qualification} · {f.numeric_semantics}{f.error ? ` · ${f.error_code}: ${f.error}` : ''}</p>))}
        {query.next_offset !== null && <button disabled={busy || disabled} onClick={() => void load(query.next_offset!)}>下一页</button>}</>}
    </>}
    {Object.keys(drafts).length > 0 && <details open><summary>有未应用的 JSON 编辑；先应用或取消再保存文档。切换对象不会自动清除输入。</summary>{Object.entries(drafts).map(([key, draft]) => <div key={key}><p>{key}</p><pre>{draft.raw}</pre><button disabled={disabled} onClick={() => clear(key)}>取消保留输入 {key}</button></div>)}</details>}
  </section>;
}
