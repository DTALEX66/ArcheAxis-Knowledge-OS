import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { CanonicalExpressionSpace } from "../spaces/CanonicalExpressionSpace";
import { webcrypto } from "node:crypto";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../design-system/AaosPrimitives", () => ({ AaosDialog: ({ open, children }: any) => open ? <div role="dialog">{children}</div> : null }));
type J = Record<string, any>;
let docs: Map<string, J>, requests: J[];
function dto(id: string, text: string, version = 1) { return { document_id: id, title: id, version, source_id: null, source_revision: null, content_sha256: "a".repeat(64), text_projection: text, blocks: [], editor_json: { type: "doc", attrs: { retained: "inert", archeaxis_expression: { schema: "archeaxis.expression/v1", nodes: [{ id: "n1", type: "text", x: 0, y: 0, width: 240, height: 160, text }], edges: [], capability_metadata: { qualification: "NOT_EXECUTED" } } }, content: [{ type: "paragraph", attrs: { block_id: `block_${id}`, preserved_body_field: "original" } }] } }; }
// SIMULATED codec behavior: every body paragraph without a stable block ID receives one.
function normalizeEditor(editor: J): J { const next = structuredClone(editor); next.content = next.content.map((node: J, i: number) => ({ ...node, attrs: { ...node.attrs, block_id: node.attrs?.block_id ?? `assigned_block_${i}` } })); return next; }
beforeEach(() => {
    docs = new Map([['doc_a', dto('doc_a', 'A')], ['doc_b', dto('doc_b', 'B')]]);
    requests = [];
    bridge.call.mockReset();
    bridge.call.mockImplementation(async (op: string, p: J = {}) => {
        if (op === 'documents_list')
            return { documents: [...docs.values()], snapshot_count: docs.size, next_cursor: null };
        if (op === 'document_get')
            return structuredClone(docs.get(p.document_id));
        if (op === 'document_create') {
            requests.push(structuredClone(p));
            let d = docs.get(p.body.create_request_id);
            if (!d) {
                d = { ...dto(p.body.create_request_id, ''), editor_json: normalizeEditor(p.body.editor_json) };
                docs.set(d.document_id, d);
            }
            return structuredClone(d);
        }
        if (op === 'document_draft') {
            requests.push(structuredClone(p));
            const d = docs.get(p.document_id)!;
            if (d.version !== p.body.expected_version)
                throw new Error('409');
            const next = { ...d, version: d.version + 1, editor_json: normalizeEditor(p.body.editor_json) };
            docs.set(d.document_id, next);
            return structuredClone(next);
        }
        if (op === 'document_version')
            return dto(p.document_id, 'HISTORY', p.version);
        throw new Error(op);
    });
});
function edit(text: string) {
    if (!screen.queryByLabelText('节点文字 1'))
        fireEvent.click(screen.getByRole('button', { name: '添加文本节点' }));
    fireEvent.change(screen.getByLabelText('节点文字 1'), { target: { value: text } });
}
async function open(name: string) { fireEvent.click(await screen.findByRole('button', { name: new RegExp('^' + name + ' ·') })); await waitFor(() => expect(screen.getByLabelText('节点文字 1')).toHaveValue(name === 'doc_a' ? 'A' : 'B')); }
it('keeps object drafts through cancelled and confirmed switching and theme rerender', async () => { const v = render(<CanonicalExpressionSpace />); await open('doc_a'); edit('UNSAVED A'); fireEvent.click(screen.getByRole('button', { name: /^doc_b ·/ })); fireEvent.click(screen.getByRole('button', { name: '取消切换' })); expect(screen.getByLabelText('节点文字 1')).toHaveValue('UNSAVED A'); fireEvent.click(screen.getByRole('button', { name: /^doc_b ·/ })); fireEvent.click(screen.getByRole('button', { name: '保留草稿并切换' })); await waitFor(() => expect(screen.getByLabelText('节点文字 1')).toHaveValue('B')); fireEvent.click(screen.getByRole('button', { name: /^doc_a ·/ })); expect(screen.getByLabelText('节点文字 1')).toHaveValue('UNSAVED A'); document.documentElement.dataset.aaosTheme = 'white'; v.rerender(<CanonicalExpressionSpace />); expect(screen.getByLabelText('节点文字 1')).toHaveValue('UNSAVED A'); });
it('initial create acknowledgement loss retries identical client key and frozen payload while retaining later editing', async () => {
    const original = bridge.call.getMockImplementation()!;
    let first = true;
    bridge.call.mockImplementation(async (op: string, p: J) => {
        const result = await original(op, p);
        if (op === 'document_create' && first) {
            first = false;
            throw new Error('lost ack');
        }
        return result;
    });
    render(<CanonicalExpressionSpace />);
    edit('FIRST');
    fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' }));
    await screen.findByRole('alert');
    edit('LATER');
    fireEvent.click(screen.getByRole('button', { name: '重试冻结保存' }));
    await screen.findByText(/随后编辑仍是未保存草稿/);
    expect(requests).toHaveLength(2);
    expect(requests[0]).toEqual(requests[1]);
    expect(docs.size).toBe(3);
    expect(screen.getByLabelText('节点文字 1')).toHaveValue('LATER');
    fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' }));
    await screen.findByText('表达草稿已保存并读回核对。');
    expect(requests[2].body.expected_version).toBe(1);
    expect(requests[2].body.editor_json.attrs.archeaxis_expression.nodes[0].text).toBe('LATER');
});
it('late successful save updates base version without replacing newly edited board', async () => {
    let resolve: (v: any) => void = () => { };
    const original = bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async (op: string, p: J) => {
        const result = await original(op, p);
        if (op === 'document_draft')
            await new Promise(r => { resolve = r; });
        return result;
    });
    render(<CanonicalExpressionSpace />);
    await open('doc_a');
    edit('SEND');
    fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' }));
    await waitFor(() => expect(requests).toHaveLength(1));
    edit('LATER');
    await act(async () => resolve(null));
    await screen.findByText(/随后编辑仍是未保存草稿/);
    expect(screen.getByLabelText('节点文字 1')).toHaveValue('LATER');
    expect(requests[0].body.expected_version).toBe(1);
});
it('409 failure keeps original editor and never claims success', async () => { const original = bridge.call.getMockImplementation()!; bridge.call.mockImplementation((op: string, p: J) => op === 'document_draft' ? Promise.reject(new Error('409 conflict')) : original(op, p)); render(<CanonicalExpressionSpace />); await open('doc_a'); edit('CONFLICT DRAFT'); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByRole('alert'); expect(screen.getByLabelText('节点文字 1')).toHaveValue('CONFLICT DRAFT'); expect(screen.queryByText('表达草稿已保存并读回核对。')).toBeNull(); });
it('history reads saved ID/version and does not replace unsaved current board', async () => { render(<CanonicalExpressionSpace />); await open('doc_a'); edit('CURRENT'); fireEvent.click(screen.getByRole('button', { name: '读取历史（只读）' })); await waitFor(() => expect(screen.getByLabelText('节点文字 1')).toHaveValue('HISTORY')); expect(screen.getByLabelText('节点文字 1')).toHaveAttribute('readonly'); fireEvent.click(screen.getByRole('button', { name: '回到保留草稿' })); expect(screen.getByLabelText('节点文字 1')).toHaveValue('CURRENT'); expect(bridge.call).toHaveBeenCalledWith('document_version', { document_id: 'doc_a', version: 1 }); });
it('list failure is visible instead of empty success and foreign document remains untouched', async () => { bridge.call.mockRejectedValue(new Error('503')); render(<CanonicalExpressionSpace />); await screen.findByText('文档列表读取失败；未当成空列表。'); expect(requests).toHaveLength(0); });
it('preserves foreign document attrs and inert capability metadata on save', async () => { render(<CanonicalExpressionSpace />); await open('doc_a'); edit('CHANGED'); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText('表达草稿已保存并读回核对。'); expect(requests[0].body.editor_json.attrs.retained).toBe('inert'); expect(requests[0].body.editor_json.attrs.archeaxis_expression.capability_metadata).toEqual({ qualification: 'NOT_EXECUTED' }); });
it('readback key ordering differences do not produce false save failure', async () => {
    const original = bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async (op: string, p: J) => {
        const result = await original(op, p);
        if (op === 'document_get') {
            const { editor_json, ...rest } = result;
            return { ...rest, editor_json: { content: editor_json.content, attrs: editor_json.attrs, type: editor_json.type } };
        }
        return result;
    });
    render(<CanonicalExpressionSpace />);
    await open('doc_a');
    edit('ORDER');
    fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' }));
    await screen.findByText('表达草稿已保存并读回核对。');
});
it('publishes aggregate dirty and clears on unmount', async () => { const states: boolean[] = []; const listener = (e: Event) => states.push((e as CustomEvent).detail); window.addEventListener('archeaxis-draft-dirty', listener); const v = render(<CanonicalExpressionSpace />); edit('DIRTY'); expect(states.at(-1)).toBe(true); v.unmount(); expect(states.at(-1)).toBe(false); window.removeEventListener('archeaxis-draft-dirty', listener); });
it('late document selection never overwrites edits made while get was pending', async () => {
    const original = bridge.call.getMockImplementation()!;
    let done: (v: any) => void = () => { };
    bridge.call.mockImplementation(async (op: string, p: J) => {
        const d = await original(op, p);
        if (op === 'document_get' && p.document_id === 'doc_b')
            await new Promise(r => { done = r; });
        return d;
    });
    render(<CanonicalExpressionSpace />);
    await open('doc_a');
    fireEvent.click(screen.getByRole('button', { name: /^doc_b ·/ }));
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith('document_get', { document_id: 'doc_b' }));
    edit('DURING READ');
    await act(async () => done(null));
    await screen.findByText(/期间新增编辑仍保留/);
    expect(screen.getByLabelText('节点文字 1')).toHaveValue('DURING READ');
});
it('real Board adds verified Source CAS reference without embedding bytes in Document', async () => { vi.stubGlobal('crypto', webcrypto); const sha = 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'; const original = bridge.call.getMockImplementation()!; bridge.call.mockImplementation((op: string, p: J) => op === 'sources_list' ? Promise.resolve({ sources: [{ source_id: 'source_cas_a', sha256: sha, source_revision: 'rev_a', original_name: 'fixture.png', imported_at: 'SIMULATED' }] }) : op === 'source_original' ? Promise.resolve({ source_id: 'source_cas_a', sha256: sha, name: 'fixture.png', media_type: 'image/png', content_base64: 'YQ==' }) : original(op, p)); vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:SIMULATED-CAS'), revokeObjectURL: vi.fn() })); render(<CanonicalExpressionSpace />); fireEvent.click(screen.getByRole('button', { name: '读取媒体来源' })); await waitFor(() => expect(screen.getByText('fixture.png')).toBeInTheDocument()); fireEvent.change(screen.getByLabelText('Source CAS'), { target: { value: 'source_cas_a' } }); fireEvent.click(screen.getByRole('button', { name: '添加媒体节点' })); await screen.findByLabelText('媒体说明 1'); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText('表达草稿已保存并读回核对。'); expect(requests[0].body.editor_json.attrs.archeaxis_expression.nodes[0].media).toEqual({ source_id: 'source_cas_a', sha256: sha, media_type: 'image/png' }); expect(JSON.stringify(requests[0])).not.toContain('content_base64'); vi.unstubAllGlobals(); });
it('SVG source is retained outside board and never executed as media', async () => { const original = bridge.call.getMockImplementation()!; bridge.call.mockImplementation((op: string, p: J) => op === 'sources_list' ? Promise.resolve({ sources: [{ source_id: 'svg_source', sha256: 'a'.repeat(64), original_name: 'unsafe.svg' }] }) : op === 'source_original' ? Promise.resolve({ source_id: 'svg_source', sha256: 'a'.repeat(64), media_type: 'image/svg+xml', content_base64: 'PHN2Zy8+' }) : original(op, p)); render(<CanonicalExpressionSpace />); fireEvent.click(screen.getByRole('button', { name: '读取媒体来源' })); await screen.findByText('unsafe.svg'); fireEvent.change(screen.getByLabelText('Source CAS'), { target: { value: 'svg_source' } }); fireEvent.click(screen.getByRole('button', { name: '添加媒体节点' })); await screen.findByText(/媒体不支持、来源或 SHA/); expect(screen.queryByLabelText('媒体说明 1')).toBeNull(); expect(requests).toHaveLength(0); });
it('course with mismatching explicit knowledge is rejected without upgrading references', async () => { const original = bridge.call.getMockImplementation()!; bridge.call.mockImplementation((op: string, p: J) => op === 'search' ? Promise.resolve({ items: [{ knowledge_id: 'knowledge_v1', head: 'Knowledge', status: 'accepted', active: true }] }) : op === 'knowledge_get' ? Promise.resolve({ knowledge_id: 'knowledge_v1', version: 'knowledge_v1', status: 'accepted' }) : op === 'course_list' ? Promise.resolve({ items: [{ manifest_id: 'stale_course', title: 'Stale', stale: true }] }) : op === 'teaching_list' ? Promise.resolve({ items: [], next_cursor: null }) : op === 'course_get' ? Promise.resolve({ stale: true, manifest: { manifest_id: 'stale_course' }, bindings: [] }) : original(op, p)); render(<CanonicalExpressionSpace />); fireEvent.click(screen.getByRole('button', { name: '查找实际知识' })); await screen.findByText('Knowledge · accepted'); fireEvent.change(screen.getByLabelText('知识版本'), { target: { value: 'knowledge_v1' } }); await screen.findByText(/上下文真实身份已核对/); fireEvent.click(screen.getByRole('button', { name: '读取实际课程与方案' })); await screen.findByText(/Stale/); fireEvent.change(screen.getByLabelText('课程'), { target: { value: 'stale_course' } }); await screen.findByText(/上下文不匹配或读取失败/); expect(screen.getByLabelText('课程')).toHaveValue(''); expect(screen.getByLabelText('知识版本')).toHaveValue('knowledge_v1'); });
it('history view disables current-version export without claiming a historical package', async () => { render(<CanonicalExpressionSpace />); await open('doc_a'); fireEvent.click(screen.getByRole('button', { name: '读取历史（只读）' })); await waitFor(() => expect(screen.getByLabelText('节点文字 1')).toHaveValue('HISTORY')); expect(screen.getByRole('button', { name: '导出已保存快照 / 引用' })).toBeDisabled(); expect(bridge.call).not.toHaveBeenCalledWith('document_export', expect.anything()); });
it('standalone historical course remains a valid reference without formal knowledge adoption', async () => { const original = bridge.call.getMockImplementation()!; bridge.call.mockImplementation((op: string, p: J) => op === 'course_list' ? Promise.resolve({ items: [{ manifest_id: 'old_course', title: 'Historical', stale: true }] }) : op === 'course_get' ? Promise.resolve({ stale: true, manifest: { manifest_id: 'old_course' }, bindings: [] }) : op === 'teaching_list' ? Promise.resolve({ items: [], next_cursor: null }) : original(op, p)); render(<CanonicalExpressionSpace />); fireEvent.click(screen.getByRole('button', { name: '读取实际课程与方案' })); await screen.findByText(/Historical/); fireEvent.change(screen.getByLabelText('课程'), { target: { value: 'old_course' } }); await screen.findByText(/上下文真实身份已核对/); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText('表达草稿已保存并读回核对。'); expect(requests[0].body.editor_json.attrs.archeaxis_expression.context).toMatchObject({ course_id: 'old_course' }); expect(bridge.call).not.toHaveBeenCalledWith('knowledge_get', expect.anything()); });
it('pending geometry participates in Shell dirty and blocks stale save/history/object switch until completed', async () => { const states: boolean[] = []; const listener = (e: Event) => states.push((e as CustomEvent).detail); window.addEventListener('archeaxis-draft-dirty', listener); render(<CanonicalExpressionSpace />); await open('doc_a'); edit('BOARD'); fireEvent.focus(screen.getByLabelText('节点文字 1')); const x = screen.getByLabelText('X 坐标'); fireEvent.change(x, { target: { value: '-' } }); await waitFor(() => expect(states.at(-1)).toBe(true)); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText(/未发送旧画布/); fireEvent.click(screen.getByRole('button', { name: '读取历史（只读）' })); await screen.findByText(/历史读取未改变当前输入/); fireEvent.click(screen.getByRole('button', { name: /^doc_b ·/ })); await screen.findByText(/当前输入保留/); expect(x).toHaveValue('-'); expect(requests).toHaveLength(0); expect(screen.getByLabelText('节点文字 1')).toHaveValue('BOARD'); fireEvent.change(x, { target: { value: '-10' } }); fireEvent.blur(x); await waitFor(() => expect(screen.queryByText('位置／连线输入尚未提交；先完成或取消位置／连线编辑。')).toBeNull()); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText('表达草稿已保存并读回核对。'); expect(requests[0].body.editor_json.attrs.archeaxis_expression.nodes[0].x).toBe(-10); window.removeEventListener('archeaxis-draft-dirty', listener); });
it('unknown expression fields are shown as readonly original JSON and never stripped or overwritten', async () => { docs.get('doc_b')!.editor_json.attrs.archeaxis_expression.unknown_payload = { keep: 'complete' }; const before = structuredClone(docs.get('doc_b')); render(<CanonicalExpressionSpace />); await open('doc_a'); fireEvent.click(screen.getByRole('button', { name: /^doc_b ·/ })); await screen.findByText(/原始文档仅只读查看/); expect(screen.getByText(/"unknown_payload"/)).toHaveTextContent('complete'); expect(screen.getByLabelText('节点文字 1')).toHaveValue('A'); expect(docs.get('doc_b')).toEqual(before); expect(requests).toHaveLength(0); });
it('unknown draft acknowledgement stays failure until explicit exact readback reconciliation then preserves later edit', async () => {
    const original = bridge.call.getMockImplementation()!;
    let first = true;
    bridge.call.mockImplementation(async (op: string, p: J) => {
        const result = await original(op, p);
        if (op === 'document_draft' && first) {
            first = false;
            throw new Error('ack lost');
        }
        return result;
    });
    render(<CanonicalExpressionSpace />);
    await open('doc_a');
    edit('SEND');
    fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' }));
    await screen.findByRole('alert');
    edit('LATER');
    fireEvent.click(screen.getByRole('button', { name: '核对最新保存版本（不覆盖草稿）' }));
    await screen.findByText(/最新 Core 读回与上次冻结保存匹配/);
    expect(screen.getByLabelText('节点文字 1')).toHaveValue('LATER');
    expect(requests).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' }));
    await screen.findByText('表达草稿已保存并读回核对。');
    expect(requests[1].body.expected_version).toBe(2);
    expect(docs.get('doc_a')!.version).toBe(3);
});
it('three inert capability notes preserve nested metadata and reject excess UTF8 without changing qualification', async () => { docs.get('doc_a')!.editor_json.attrs.archeaxis_expression.capability_metadata = { qualification: 'NOT_EXECUTED', nested: { scene: ['original', 3] } }; const capability = vi.fn(); render(<CanonicalExpressionSpace onOpenCapability={capability}/>); await open('doc_a'); fireEvent.change(screen.getByLabelText('动画产物说明'), { target: { value: '动画分步说明' } }); fireEvent.change(screen.getByLabelText('仿真参数说明'), { target: { value: '质量=1；时间步0.1；未执行' } }); fireEvent.change(screen.getByLabelText('空间 XR 场景说明'), { target: { value: '房间—记忆位置；未执行' } }); fireEvent.change(screen.getByLabelText('动画产物说明'), { target: { value: '字'.repeat(1366) } }); await screen.findByText(/超出 4096 UTF-8 字节/); expect(screen.getByLabelText('动画产物说明')).toHaveValue('动画分步说明'); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText('表达草稿已保存并读回核对。'); expect(requests[0].body.editor_json.attrs.archeaxis_expression.capability_metadata).toEqual({ qualification: 'NOT_EXECUTED', nested: { scene: ['original', 3] }, animation_note: '动画分步说明', simulation_note: '质量=1；时间步0.1；未执行', spatial_note: '房间—记忆位置；未执行' }); fireEvent.click(screen.getByRole('button', { name: '查看动画产物说明能力状态' })); expect(capability).toHaveBeenCalledWith('CAP-0070'); fireEvent.click(screen.getByRole('button', { name: '查看空间 XR 场景说明能力状态' })); expect(capability).toHaveBeenCalledWith('CAP-0080'); });
it('pending relation text blocks saving old edges until explicit cancellation then allows save', async () => { render(<CanonicalExpressionSpace />); await open('doc_a'); edit('BOARD'); fireEvent.change(screen.getByLabelText('新连线文字'), { target: { value: 'UNCOMMITTED EDGE' } }); await screen.findByText('位置／连线输入尚未提交；先完成或取消位置／连线编辑。'); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText(/未发送旧画布/); expect(requests).toHaveLength(0); fireEvent.click(screen.getByRole('button', { name: '取消未提交连线' })); await waitFor(() => expect(screen.getByLabelText('新连线文字')).toHaveValue('')); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText('表达草稿已保存并读回核对。'); expect(requests[0].body.editor_json.attrs.archeaxis_expression.edges).toEqual([]); });
it('new expression uses empty body matching normalized Core create shape and exact readback succeeds', async () => { render(<CanonicalExpressionSpace />); edit('CAPTION'); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText('表达草稿已保存并读回核对。'); expect(requests[0].body.editor_json.content).toEqual([]); expect(docs.get(requests[0].body.create_request_id)!.editor_json).toEqual(requests[0].body.editor_json); expect(normalizeEditor({ type: 'doc', content: [{ type: 'paragraph' }] }).content[0].attrs.block_id).toBe('assigned_block_0'); });
it('explicit new expression after an existing object also has no placeholder body block', async () => { render(<CanonicalExpressionSpace />); await open('doc_a'); fireEvent.click(screen.getByRole('button', { name: '新表达草稿' })); edit('NEW CAPTION'); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText('表达草稿已保存并读回核对。'); expect(requests[0].body.editor_json.content).toEqual([]); expect(requests[0].body.editor_json.attrs.archeaxis_expression.nodes[0].text).toBe('NEW CAPTION'); });
it('existing normalized body retains stable block IDs and unknown body fields under full-envelope comparison', async () => { render(<CanonicalExpressionSpace />); await open('doc_a'); edit('CHANGED EXPRESSION'); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByText('表达草稿已保存并读回核对。'); expect(requests[0].body.editor_json.content).toEqual([{ type: 'paragraph', attrs: { block_id: 'block_doc_a', preserved_body_field: 'original' } }]); expect(docs.get('doc_a')!.editor_json.content).toEqual(requests[0].body.editor_json.content); });
it('expression-only match never hides loss of an unknown ordinary body field in readback', async () => { const original = bridge.call.getMockImplementation()!; bridge.call.mockImplementation(async (op: string, p: J) => { const d = await original(op, p); if (op === 'document_get' && d.version === 2)
    delete d.editor_json.content[0].attrs.preserved_body_field; return d; }); render(<CanonicalExpressionSpace />); await open('doc_a'); edit('BOARD MATCHES'); fireEvent.click(screen.getByRole('button', { name: '保存表达草稿' })); await screen.findByRole('alert'); expect(screen.queryByText('表达草稿已保存并读回核对。')).toBeNull(); expect(screen.getByLabelText('节点文字 1')).toHaveValue('BOARD MATCHES'); expect(screen.getByRole('button', { name: '重试冻结保存' })).toBeEnabled(); });
