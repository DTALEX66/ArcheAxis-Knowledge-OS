import { webcrypto } from "node:crypto";
import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, act, within } from "@testing-library/react";
import { CanonicalRelationSpace } from "../spaces/CanonicalRelationSpace";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../design-system/AaosPrimitives", () => ({ AaosDialog: ({ open, children, title }: any) => open ? <div role="dialog" aria-label={title}>{children}</div> : null }));
type J = Record<string, any>;
let docs: Map<string, J>, writes: J[], incomplete: boolean;
function doc(id: string, version = 1): J { return { document_id: id, title: id, version, source_id: null, source_revision: null, content_sha256: "a".repeat(64), blocks: [], text_projection: "body", editor_json: { type: "doc", attrs: { unknown: { retained: [1, 2] }, archeaxis_relations: { schema: "archeaxis.relations/v1", relations: [] } }, content: [{ type: "future_node", attrs: { block_id: "stable_body", unknown: true }, opaque: "retain" }] } }; }
const target = { kind: "document", document_id: "doc_b", version: 3, block_id: "old_block" };
function projection(d: J): J { return { schema: "archeaxis.relation-projection/v1", snapshot_sha256: "b".repeat(64), center: { document_id: d.document_id, version: d.version, content_sha256: d.content_sha256 }, scope: "current_source_versions_to_pinned_center", derived_only: true, nodes: [{ key: "a", reference: { kind: "document", document_id: d.document_id, version: d.version }, status: "resolved", object: {} }, { key: "b", reference: target, status: "resolved", object: {} }], edges: [{ id: "edge", from: "a", to: "b", direction: "outgoing", relation: { id: "relation_existing", kind: "supports", label: "证据支持", target }, source_snapshot: { document_id: d.document_id, version: d.version, content_sha256: d.content_sha256 } }], unsupported_sources: [], scan: { scanned: 20, next_cursor: incomplete ? "source20" : null, complete: !incomplete } }; }
beforeEach(() => { vi.stubGlobal("crypto", webcrypto); docs = new Map([['doc_a', doc('doc_a')], ['doc_b', doc('doc_b', 5)]]); writes = []; incomplete = false; bridge.call.mockReset(); bridge.call.mockImplementation(async (op: string, p: J = {}) => {
  if (op === 'documents_list') return { documents: [...docs.values()], snapshot_count: docs.size, next_cursor: null };
  if (op === 'document_get') return structuredClone(docs.get(p.document_id));
  if (op === 'document_version') return doc(p.document_id, p.version);
  if (op === 'document_graph') return projection(doc(p.document_id, p.version));
  if (op === 'document_create') { writes.push(structuredClone(p)); const bytes = await webcrypto.subtle.digest('SHA-256', new TextEncoder().encode(p.body.create_request_id)); const id = 'doc_req_' + Array.from(new Uint8Array(bytes)).map(x => x.toString(16).padStart(2,'0')).join(''); let d = docs.get(id); if (!d) { d = { ...doc(id), title:p.body.title, editor_json: structuredClone(p.body.editor_json) }; docs.set(d.document_id, d); } return structuredClone(d); }
  if (op === 'document_draft') { writes.push(structuredClone(p)); const d = docs.get(p.document_id)!; if (d.version !== p.body.expected_version) throw new Error('409'); const next = { ...d, version: d.version + 1, editor_json: structuredClone(p.body.editor_json) }; docs.set(p.document_id, next); return structuredClone(next); }
  throw new Error(op);
}); });
async function open(id = 'doc_a') { fireEvent.click(await screen.findByRole('button', { name: new RegExp('^' + id + ' ·') })); await screen.findByText(/关系已读取/); const editor=screen.getByText(/^编辑当前对象关系/,{selector:'summary'});if(!editor.parentElement!.hasAttribute('open'))fireEvent.click(editor); }
it('starts with the graph and exact object actions while advanced filters and relation edits remain collapsed',async()=>{
 render(<CanonicalRelationSpace/>);
 fireEvent.click(await screen.findByRole('button',{name:'打开关系：doc_a'}));
 await screen.findByText(/关系已读取/);
 expect(screen.getByLabelText('同版本关系图')).toBeVisible();
 expect(screen.getByLabelText('筛选关系方向')).not.toBeVisible();
 expect(screen.getByRole('button',{name:'选择关联对象'})).not.toBeVisible();
 fireEvent.click(screen.getByText(/^编辑当前对象关系/,{selector:'summary'}));
 expect(screen.getByRole('button',{name:'选择关联对象'})).toBeVisible();
 expect(writes).toHaveLength(0);
});
function add(label = 'NEW') { const manual = screen.getByText('手动指定对象', {selector:'summary'}); if (!manual.parentElement!.hasAttribute('open')) fireEvent.click(manual); fireEvent.change(screen.getByLabelText('关系说明'), { target: { value: label } }); fireEvent.change(screen.getByLabelText('目标对象ID'), { target: { value: 'doc_b' } }); fireEvent.change(screen.getByLabelText('固定目标版本'), { target: { value: '3' } }); fireEvent.click(screen.getByRole('button', { name: '加入关系草稿' })); }
it('selects an actual saved document by title and preserves pinned version, block and supports protocol value', async () => {
  const call = bridge.call.getMockImplementation()!;
  docs.get('doc_b')!.title = '目标笔记';
  docs.get('doc_b')!.blocks = [{block_id:'pinned_block',text_projection:'目标段落'}];
  bridge.call.mockImplementation(async (op:string,p:J) => { const result=await call(op,p); return op==='documents_list'?{...result,documents:result.documents.map((d:J)=>d.document_id==='doc_b'?{...d,version:3}:d)}:result; });
  render(<CanonicalRelationSpace/>); await open();
  expect(screen.getByLabelText('目标对象ID')).not.toBeVisible();
  expect([...screen.getByLabelText('目标类型').querySelectorAll('option')].map(option=>[option.value,option.textContent])).toEqual([['document','文档'],['source','来源原件'],['knowledge','知识']]);
  fireEvent.click(screen.getByRole('button',{name:'选择关联对象'}));
  fireEvent.click(screen.getByRole('button',{name:'浏览已保存文档'}));
  await screen.findByRole('option',{name:'目标笔记 · 第 3 版'});
  fireEvent.change(screen.getByLabelText('选择文档'),{target:{value:'doc_b'}});
  await screen.findByLabelText('选择文档片段');
  fireEvent.change(screen.getByLabelText('选择文档片段'),{target:{value:'pinned_block'}});
  fireEvent.click(screen.getByRole('button',{name:'加入此固定引用'}));
  expect(screen.getByLabelText('固定目标版本')).toHaveValue('5');
  expect(screen.getByText('当前目标：文档（名称尚未读取） · 第 5 版 · 段落；尚未加入关系草稿。')).toBeVisible();
  const relationType=screen.getByRole('combobox',{name:'关系类型'});
  fireEvent.change(relationType,{target:{value:'supports'}});
  expect(within(relationType).getByRole('option',{name:'支持'})).toHaveValue('supports');
  fireEvent.change(screen.getByLabelText('关系说明'),{target:{value:'所选资料支持此文档'}});
  fireEvent.click(screen.getByRole('button',{name:'加入关系草稿'}));
  expect(writes).toHaveLength(0);
  fireEvent.click(screen.getByRole('button',{name:'保存关系草稿'}));
  await screen.findByText('关系已保存并读回核对。');
  expect(writes[0].body.editor_json.attrs.archeaxis_relations.relations[0]).toMatchObject({kind:'supports',target:{kind:'document',document_id:'doc_b',version:5,block_id:'pinned_block'}});
});
it('reuses the original selector without asking the user to transcribe its identity or fingerprint', async () => {
  const call=bridge.call.getMockImplementation()!, sha='c'.repeat(64);
  bridge.call.mockImplementation(async(op:string,p:J)=>op==='sources_list'?{sources:[{source_id:'source_exact',source_revision:sha,sha256:sha,original_name:'原始图片.png',imported_at:'now'}]}:call(op,p));
  render(<CanonicalRelationSpace/>); await open();
  fireEvent.click(screen.getByRole('button',{name:'选择关联对象'}));
  fireEvent.click(screen.getByRole('button',{name:'浏览来源原件'}));
  await screen.findByRole('option',{name:'原始图片.png · ce_exact'});
  fireEvent.change(screen.getByLabelText('选择来源原件'),{target:{value:'source_exact'}});
  fireEvent.click(screen.getByRole('button',{name:'加入此固定引用'}));
  expect(screen.getByLabelText('来源文件指纹')).toHaveValue(sha);
  expect(screen.getByText('当前目标：来源原件（名称尚未读取）；尚未加入关系草稿。')).toBeVisible();
  expect(screen.getByLabelText('目标对象ID')).not.toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'加入关系草稿'}));
  fireEvent.click(screen.getByRole('button',{name:'保存关系草稿'}));
  await screen.findByText('关系已保存并读回核对。');
  expect(writes[0].body.editor_json.attrs.archeaxis_relations.relations[0].target).toEqual({kind:'source',source_id:'source_exact',sha256:sha});
});
it('graph and fallback list retain exact pinned target despite current target version5', async () => { const jump = vi.fn(); render(<CanonicalRelationSpace onOpenDocument={jump}/>); await open(); fireEvent.click(screen.getByRole('button', { name: '图形不可用，切换列表' })); expect(screen.queryByLabelText('同版本关系图')).toBeNull(); fireEvent.click(screen.getByRole('button', { name: /打开关联内容：文档（名称尚未读取） · 第 3 版/ })); expect(jump).toHaveBeenCalledWith('doc_b', 3, 'old_block'); expect(bridge.call).toHaveBeenCalledWith('document_graph', { document_id: 'doc_a', version: 1 }); });
it('filters the loaded graph and list together without changing pinned references or writing documents', async () => {
  const call = bridge.call.getMockImplementation()!, jump = vi.fn();
  bridge.call.mockImplementation(async (op: string, p: J) => {
    const result = await call(op, p);
    if (op === 'document_graph') {
      result.nodes.push({ key: 'source', reference: { kind: 'source', source_id: 'source_1', sha256: 'c'.repeat(64) }, status: 'resolved', object: {} });
      result.edges.push({ ...result.edges[0], id: 'source_edge', to: 'source', relation: { id: 'source_relation', kind: 'related', label: '原件材料', target: result.nodes[2].reference } });
      result.edges.push({ ...result.edges[0], id: 'backlink_edge', from: 'b', to: 'a', direction: 'backlink', source_snapshot: { document_id: 'doc_b', version: 3, content_sha256: 'a'.repeat(64) }, relation: { id: 'backlink_relation', kind: 'contradicts', label: '反向反证', target: result.nodes[0].reference } });
    }
    return result;
  });
  render(<CanonicalRelationSpace onOpenReference={jump}/>); await open();
  const list = screen.getByRole('list', { name: '同版本关系列表' });
  expect(within(list).getAllByRole('listitem')).toHaveLength(3);
  fireEvent.change(screen.getByLabelText('筛选关系方向'), { target: { value: 'backlink' } });
  expect(within(list).getAllByRole('listitem')).toHaveLength(1);
  expect(list).toHaveTextContent('反向反证');
  expect(screen.getByLabelText('同版本关系图').querySelectorAll('[data-relation-edge]')).toHaveLength(1);
  fireEvent.click(within(list).getByRole('button', { name: /打开关联内容：文档（名称尚未读取） · 第 3 版/ }));
  expect(jump).toHaveBeenLastCalledWith(target);
  fireEvent.change(screen.getByLabelText('筛选关联对象类型'), { target: { value: 'source' } });
  expect(screen.getByText(/当前筛选没有匹配关系/)).toBeVisible();
  expect(screen.queryByText('此页没有关系记录；仅限上述扫描范围。')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '重置关系筛选' }));
  fireEvent.change(screen.getByLabelText('筛选关系类型'), { target: { value: 'related' } });
  fireEvent.change(screen.getByLabelText('筛选关联对象类型'), { target: { value: 'source' } });
  expect(within(list).getAllByRole('listitem')).toHaveLength(1);
  expect(list).toHaveTextContent('原件材料');
  fireEvent.click(within(list).getByRole('button', { name: /打开关联内容：来源原件/ }));
  expect(jump).toHaveBeenLastCalledWith({ kind: 'source', source_id: 'source_1', sha256: 'c'.repeat(64) });
  fireEvent.click(screen.getByRole('button', { name: '重置关系筛选' }));
  expect(within(list).getAllByRole('listitem')).toHaveLength(3);
  expect(writes).toHaveLength(0);
  expect(bridge.call.mock.calls.filter(args => args[0] === 'document_graph')).toHaveLength(1);
});
it('incomplete scans cannot become a claim that the whole library has no relations', async () => { incomplete = true; const call = bridge.call.getMockImplementation()!; bridge.call.mockImplementation(async (op: string, p: J) => { const r = await call(op, p); if (op === 'document_graph') r.edges = []; return r; }); render(<CanonicalRelationSpace onOpenDocument={vi.fn()}/>); await open(); expect(screen.getByText(/扫描尚未完成，不能断言全库无关系/)).toBeVisible(); expect(screen.getByText('此页没有关系记录；仅限上述扫描范围。')).toBeVisible(); fireEvent.click(screen.getByRole('button', { name: '读取下一页反链' })); await waitFor(() => expect(bridge.call).toHaveBeenCalledWith('document_graph', { document_id: 'doc_a', version: 1, cursor: 'source20' })); });
it('preserves unknown envelope, body and stable block IDs on relation-only save', async () => { const prior = structuredClone(docs.get('doc_a')!.editor_json); render(<CanonicalRelationSpace onOpenDocument={vi.fn()}/>); await open(); add(); fireEvent.click(screen.getByRole('button', { name: '保存关系草稿' })); await screen.findByText('关系已保存并读回核对。'); expect(writes[0].body.expected_version).toBe(1); expect(writes[0].body.editor_json.content).toEqual(prior.content); expect(writes[0].body.editor_json.attrs.unknown).toEqual(prior.attrs.unknown); expect(writes[0].body.editor_json.attrs.archeaxis_relations.relations[0].target).toEqual({ kind: 'document', document_id: 'doc_b', version: 3 }); });
it('first-create lost acknowledgement retries frozen key/payload and preserves later editing', async () => { const call = bridge.call.getMockImplementation()!; let lost = true; bridge.call.mockImplementation(async (op: string, p: J) => { const r = await call(op, p); if (op === 'document_create' && lost) { lost = false; throw new Error('response lost'); } return r; }); render(<CanonicalRelationSpace onOpenDocument={vi.fn()}/>); add('FIRST'); fireEvent.click(screen.getByRole('button', { name: '保存关系草稿' })); await screen.findByRole('alert'); add('LATER'); fireEvent.click(screen.getByRole('button', { name: '重试本次保存' })); await screen.findByText('已保存发送时的版本；随后编辑仍是未保存草稿。'); expect(writes).toHaveLength(2); expect(writes[0]).toEqual(writes[1]); expect(docs.size).toBe(3); expect(screen.getByLabelText('关系草稿')).toHaveTextContent('LATER'); });
it('409 preserves draft and fixed expected version while showing latest read-only comparison', async () => { render(<CanonicalRelationSpace onOpenDocument={vi.fn()}/>); await open(); add('UNSAVED'); docs.set('doc_a', doc('doc_a', 2)); fireEvent.click(screen.getByRole('button', { name: '保存关系草稿' })); await screen.findByRole('alert'); fireEvent.click(screen.getByRole('button', { name: '核对最新版本（保留草稿）' })); await screen.findByText(/最新版本不同，仅只读比较/); fireEvent.click(screen.getByRole('button', { name: '返回当前草稿' })); expect(screen.getByLabelText('关系草稿')).toHaveTextContent('UNSAVED'); expect(writes[0].body.expected_version).toBe(1); });
it('cancelling switch and rerendering a theme retains relation draft', async () => { const v = render(<CanonicalRelationSpace onOpenDocument={vi.fn()}/>); await open(); add('DRAFT'); fireEvent.click(screen.getByRole('button', { name: /^doc_b ·/ })); fireEvent.click(screen.getByRole('button', { name: '取消切换' })); document.documentElement.dataset.aaosTheme = 'white'; v.rerender(<CanonicalRelationSpace onOpenDocument={vi.fn()}/>); expect(screen.getByLabelText('关系草稿')).toHaveTextContent('DRAFT'); });
it('unknown relation schema is preserved read-only without write conversion', async () => { docs.get('doc_a')!.editor_json.attrs.archeaxis_relations = { schema: 'archeaxis.relations/v99', opaque: [1, 2] }; render(<CanonicalRelationSpace onOpenDocument={vi.fn()}/>); await open(); expect(screen.getByRole('button', { name: '保存关系草稿' })).toBeDisabled(); expect(screen.getByText(/保留的原始文档/)).toBeVisible(); expect(writes).toHaveLength(0); });
it('graph failure is an error and not an empty-data success', async () => { const call = bridge.call.getMockImplementation()!; bridge.call.mockImplementation((op: string, p: J) => op === 'document_graph' ? Promise.reject(new Error('503')) : call(op, p)); render(<CanonicalRelationSpace onOpenDocument={vi.fn()}/>); fireEvent.click(await screen.findByRole('button', { name: /^doc_a ·/ })); expect(await screen.findByRole('alert')).toHaveTextContent('未报告无关系'); expect(screen.queryByText('此页没有关系记录；仅限上述扫描范围。')).toBeNull(); });

it('unified reference callback passes exact source snapshot and pinned block without current-library fallback', async () => { const jump = vi.fn(); render(<CanonicalRelationSpace onOpenReference={jump}/>); await open(); fireEvent.click(screen.getByRole('button', { name: 'doc_a · 第 1 版' })); expect(jump).toHaveBeenCalledWith({ kind: 'document', document_id: 'doc_a', version: 1 }); fireEvent.click(screen.getByRole('button', { name: /打开关联内容：文档（名称尚未读取） · 第 3 版/ })); expect(jump).toHaveBeenLastCalledWith(target); });

it('history loaded after a new relation edit cannot hide the working draft behind read-only UI', async () => { let resolve!: (d: J) => void; const call=bridge.call.getMockImplementation()!; bridge.call.mockImplementation((op:string,p:J)=>op==='document_version'?new Promise(r=>{resolve=r;}):call(op,p)); render(<CanonicalRelationSpace onOpenReference={vi.fn()}/>); await open(); fireEvent.click(screen.getByRole('button',{name:'读取历史关系（只读）'})); add('EDIT AFTER REQUEST'); await act(async()=>{resolve(doc('doc_a',1));}); expect(screen.queryByText(/只读比较 v1/)).toBeNull(); expect(screen.getByLabelText('关系草稿')).toHaveTextContent('EDIT AFTER REQUEST'); expect(screen.getByLabelText('目标对象ID')).toBeEnabled(); });
it('a pending collection edit prevents entering a historical view', async () => { render(<CanonicalRelationSpace onOpenReference={vi.fn()} renderCollection={(_d,_e,_change,onPending)=><button onClick={()=>onPending(true)}>Pending collection input</button>}/>); await open(); fireEvent.click(screen.getByRole('button',{name:'Pending collection input'})); fireEvent.click(screen.getByRole('button',{name:'读取历史关系（只读）'})); expect(bridge.call.mock.calls.filter(x=>x[0]==='document_version')).toHaveLength(0); expect(screen.getByRole('alert')).toHaveTextContent('当前输入保留'); });
it('a stale history failure cannot replace the status of a newly opened object', async () => { let reject!: (e:Error)=>void; const call=bridge.call.getMockImplementation()!; bridge.call.mockImplementation((op:string,p:J)=>op==='document_version'?new Promise((_r,j)=>{reject=j;}):call(op,p)); render(<CanonicalRelationSpace onOpenReference={vi.fn()}/>); await open(); fireEvent.click(screen.getByRole('button',{name:'读取历史关系（只读）'})); await open('doc_b'); await act(async()=>{reject(new Error('old history unavailable'));}); expect(screen.queryByRole('alert')).toBeNull(); expect(screen.getByRole('status')).toHaveTextContent('关系已读取'); });
it('returning to draft cancels an in-flight replacement history request', async () => { render(<CanonicalRelationSpace onOpenReference={vi.fn()}/>); await open(); fireEvent.click(screen.getByRole('button',{name:'读取历史关系（只读）'})); await screen.findByText(/只读比较 v1/); let resolve!:(d:J)=>void; const call=bridge.call.getMockImplementation()!; bridge.call.mockImplementation((op:string,p:J)=>op==='document_version'?new Promise(r=>{resolve=r;}):call(op,p)); fireEvent.change(screen.getByLabelText('历史版本'),{target:{value:'2'}}); fireEvent.click(screen.getByRole('button',{name:'读取历史关系（只读）'})); fireEvent.click(screen.getByRole('button',{name:'返回当前草稿'})); await act(async()=>{resolve(doc('doc_a',2));}); expect(screen.queryByText(/只读比较 v2/)).toBeNull(); expect(screen.getByLabelText('目标对象ID')).toBeEnabled(); });
for (const corrupt of ['id','title','source'] as const) it(`create ${corrupt} mismatch with identical body/version cannot be accepted`, async()=>{const call=bridge.call.getMockImplementation()!;bridge.call.mockImplementation(async(op:string,p:J)=>{const r=await call(op,p);if(op==='document_create'){if(corrupt==='id'){r.document_id='wrong_identity';docs.set('wrong_identity',structuredClone(r));}if(corrupt==='title')r.title='wrong title';if(corrupt==='source')r.source_id='wrong source';}return r;});render(<CanonicalRelationSpace onOpenReference={vi.fn()}/>);add('CREATE');fireEvent.click(screen.getByRole('button',{name:'保存关系草稿'}));expect(await screen.findByRole('alert')).toHaveTextContent('保存未确认');expect(screen.getByRole('button',{name:'重试本次保存'})).toBeEnabled();expect(screen.getByLabelText('关系草稿')).toHaveTextContent('CREATE');});

it('saves an explicit embed presentation through the existing relation draft without changing body', async () => {
  const prior = structuredClone(docs.get('doc_a')!.editor_json);
  render(<CanonicalRelationSpace onOpenDocument={vi.fn()}/>); await open(); add();
  fireEvent.click(screen.getByRole('checkbox', {name: /^嵌入呈现 /}));
  fireEvent.click(screen.getByRole('button', {name: '保存关系草稿'})); await screen.findByText('关系已保存并读回核对。');
  expect(writes[0].body.editor_json.attrs.archeaxis_relations.relations[0].presentation).toBe('embed');
  expect(writes[0].body.editor_json.content).toEqual(prior.content);
  expect(writes[0].body.editor_json.attrs.unknown).toEqual(prior.attrs.unknown);
});

it('keeps opaque paging and full object identity in closed details while preserving the incomplete range warning',async()=>{
  incomplete=true;const call=bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation(async(op:string,p:J)=>{
    const result=await call(op,p);
    if(op==='document_graph'){result.projection_truncated=true;result.omitted_edges=7;}
    return result;
  });
  render(<CanonicalRelationSpace onOpenReference={vi.fn()}/>);await open();
  expect(screen.getByRole('heading',{name:'关系图与列表'})).toBeVisible();
  expect(screen.getByRole('button',{name:'刷新关系'})).toBeVisible();
  expect(screen.getByText(/扫描尚未完成，不能断言全库无关系/)).toBeVisible();
  expect(screen.getByText(/这一页达到 1000 条关系的显示上限，另有 7 条未显示/)).toBeVisible();
  const summary=screen.getByText('关系对象与扫描详情',{selector:'summary'}),details=summary.parentElement as HTMLDetailsElement;
  expect(details).not.toHaveAttribute('open');expect(within(details).getByText('列表加载位置：source20')).not.toBeVisible();
  fireEvent.click(summary);expect(within(details).getByText('列表加载位置：source20')).toBeVisible();
  expect(within(details).getByText('固定内容指纹：'+'b'.repeat(64))).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'读取下一页反链'}));
  await waitFor(()=>expect(bridge.call).toHaveBeenCalledWith('document_graph',{document_id:'doc_a',version:1,cursor:'source20'}));
});

it('uses only the matching fixed reference title and retains the original block jump payload',async()=>{
  const jump=vi.fn(),call=bridge.call.getMockImplementation()!;
  docs.get('doc_b')!.title='当前第五版标题，不得借用';
  bridge.call.mockImplementation(async(op:string,p:J)=>{
    const result=await call(op,p);
    if(op==='document_graph')result.nodes[1].object={document_id:'doc_b',version:3,title:'第三版历史证据'};
    return result;
  });
  render(<CanonicalRelationSpace onOpenReference={jump}/>);await open();
  const list=screen.getByRole('list',{name:'同版本关系列表'});
  const button=within(list).getByRole('button',{name:'打开关联内容：第三版历史证据 · 第 3 版 · 段落'});
  expect(button).not.toHaveTextContent('old_block');fireEvent.click(button);
  expect(jump).toHaveBeenCalledWith(target);
  const summary=within(list).getByText('关系来源与对象详情',{selector:'summary'}),details=summary.parentElement as HTMLDetailsElement;
  expect(details).not.toHaveAttribute('open');fireEvent.click(summary);expect(details).toHaveTextContent('doc_b · v3 · old_block');
});

it('does not borrow a current-version or mismatched source title for an older fixed reference',async()=>{
  const call=bridge.call.getMockImplementation()!;
  docs.get('doc_b')!.title='只属于第五版的名称';
  bridge.call.mockImplementation(async(op:string,p:J)=>{
    const result=await call(op,p);
    if(op==='document_graph'){
      result.nodes[1].object={document_id:'doc_b',version:5,title:'只属于第五版的名称'};
      result.nodes.push({key:'long-source-node',reference:{kind:'source',source_id:'source-long-id',sha256:'c'.repeat(64)},status:'resolved',object:{source_id:'source-long-id',sha256:'d'.repeat(64),original_name:'错误指纹的文件名'}});
    }
    return result;
  });
  render(<CanonicalRelationSpace/>);await open();
  const nodes=screen.getByRole('list',{name:'关系节点'});
  expect(within(nodes).getByRole('button',{name:'打开节点 2：文档（名称尚未读取） · 第 3 版 · 段落'})).toBeVisible();
  expect(within(nodes).getByRole('button',{name:'打开节点 3：来源原件（名称尚未读取）'})).toBeVisible();
  expect(nodes).not.toHaveTextContent('只属于第五版的名称');expect(nodes).not.toHaveTextContent('错误指纹的文件名');
  expect(within(nodes).getAllByText('对象与版本详情',{selector:'summary'}).every(item=>!item.parentElement!.hasAttribute('open'))).toBe(true);
});

it('distinguishes same-title pinned nodes with stable numbers and preserves each original target after filtering',async()=>{
  const jump=vi.fn(),call=bridge.call.getMockImplementation()!;
  const otherTarget={kind:'document',document_id:'doc_c',version:3,block_id:'other_block'};
  bridge.call.mockImplementation(async(op:string,p:J)=>{
    const result=await call(op,p);
    if(op==='document_graph'){
      result.nodes[1].object={document_id:'doc_b',version:3,title:'同名历史材料'};
      result.nodes.push({key:'c',reference:otherTarget,status:'resolved',object:{document_id:'doc_c',version:3,title:'同名历史材料'}});
      result.edges.push({...result.edges[0],id:'other-edge',to:'c',relation:{id:'other-relation',kind:'related',label:'另一份材料',target:otherTarget}});
    }
    return result;
  });
  render(<CanonicalRelationSpace onOpenReference={jump}/>);await open();
  const name='同名历史材料 · 第 3 版 · 段落';
  expect(screen.getAllByRole('button',{name:/^图节点 同名历史材料/})).toHaveLength(2);
  fireEvent.keyDown(screen.getByRole('button',{name:`图节点 ${name} · 节点 2 · resolved`}),{key:'Enter'});
  expect(jump).toHaveBeenNthCalledWith(1,target);
  fireEvent.keyDown(screen.getByRole('button',{name:`图节点 ${name} · 节点 3 · resolved`}),{key:' '});
  expect(jump).toHaveBeenNthCalledWith(2,otherTarget);
  fireEvent.change(screen.getByLabelText('筛选关系类型'),{target:{value:'related'}});
  expect(screen.queryByRole('button',{name:`图节点 ${name} · 节点 2 · resolved`})).toBeNull();
  expect(screen.getByRole('button',{name:`图节点 ${name} · 节点 3 · resolved`})).toBeVisible();
  fireEvent.click(within(screen.getByRole('list',{name:'关系节点'})).getByRole('button',{name:`打开节点 3：${name}`}));
  expect(jump).toHaveBeenNthCalledWith(3,otherTarget);
  fireEvent.click(screen.getByRole('button',{name:'重置关系筛选'}));
  expect(screen.getByRole('button',{name:`图节点 ${name} · 节点 2 · resolved`})).toBeVisible();
  expect(writes).toHaveLength(0);
  expect(bridge.call.mock.calls.filter(args=>args[0]==='document_graph')).toHaveLength(1);
});
