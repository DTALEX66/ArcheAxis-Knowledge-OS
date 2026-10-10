import { useCallback, useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { DocumentDto, DocumentsListDto, DocumentSummaryDto, DocumentExportDto, SourcesListDto, SourceDto, OriginalDto, SearchDto, KnowledgeDto } from "../api/generated/core-contract";
import type { RecordView, RecordPage } from "../api/generated/teaching-contract";
import { CanonicalExpressionBoard } from "../components/CanonicalExpressionBoard";
import { parseExpressionDocument, validExpressionMedia } from "../presentation/expression";
import type { ExpressionDocument, ExpressionMedia, ExpressionNode } from "../presentation/expression";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { MediaReader } from "../components/MediaReader";
import type { ObjectTrailLevel } from "../components/NavTrail";
type Buffer = {
    value: ExpressionDocument;
    base: DocumentDto | null;
    envelope: Record<string, unknown>;
    dirty: boolean;
    serial: number;
    attempt?: Attempt;
};
type Attempt = {
    operation: "document_create" | "document_draft";
    payload: Record<string, unknown>;
    editor: unknown;
    serial: number;
};
const blank = (): ExpressionDocument => ({ schema: "archeaxis.expression/v1", nodes: [], edges: [] });
function object(v: unknown): Record<string, unknown> {
    if (!v || typeof v !== "object" || Array.isArray(v))
        throw new Error("对象响应无效");
    return v as Record<string, unknown>;
}
function decode(d: DocumentDto): ExpressionDocument {
    const e = object(d.editor_json), a = object(e.attrs), v = object(a.archeaxis_expression);
    if (!parseExpressionDocument(v))
        throw new Error("此文档不是可编辑的表达对象；未转换原文");
    return structuredClone(v) as unknown as ExpressionDocument;
}
function encode(b: Buffer) { const e = structuredClone(b.envelope); return { ...e, attrs: { ...(e.attrs ? object(e.attrs) : {}), archeaxis_expression: structuredClone(b.value) } }; }
function canonical(v: unknown): unknown { return Array.isArray(v) ? v.map(canonical) : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b)).map(([k, x]) => [k, canonical(x)])) : v; }
function same(a: unknown, b: unknown) { return JSON.stringify(canonical(a)) === JSON.stringify(canonical(b)); }
async function original(m: ExpressionMedia): Promise<Uint8Array> {
    if (!validExpressionMedia(m))
        throw new Error("此媒体类型仅保留引用，不执行或渲染");
    const o = await coreCommand<OriginalDto>("source_original", { source_id: m.source_id });
    if (o.source_id !== m.source_id || o.sha256 !== m.sha256 || o.media_type !== m.media_type)
        throw new Error("来源身份、SHA 或 MIME 不符");
    const bytes = Uint8Array.from(atob(o.content_base64), c => c.charCodeAt(0));
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))).map(x => x.toString(16).padStart(2, "0")).join("");
    if (digest !== m.sha256)
        throw new Error("原件内容校验失败");
    return bytes;
}
function CasMedia({ media }: {
    media: ExpressionMedia;
}) {
    const [bytes, setBytes] = useState<Uint8Array | null>(null), [url, setUrl] = useState(""), [failure, setFailure] = useState("");
    useEffect(() => {
        let live = true, owned = "";
        setBytes(null);
        setUrl("");
        setFailure("");
        original(media).then(b => {
            if (!live)
                return;
            setBytes(b);
            if (media.media_type.startsWith("image/")) {
                owned = URL.createObjectURL(new Blob([b.slice().buffer], { type: media.media_type }));
                setUrl(owned);
            }
        }).catch(() => {
            if (live)
                setFailure("媒体读取或校验未完成；保留引用，未播放。");
        });
        return () => {
            live = false;
            if (owned)
                URL.revokeObjectURL(owned);
        };
    }, [media.source_id, media.sha256, media.media_type]);
    return failure ? <span role="status">{failure}</span> : url ? <img src={url} alt="CAS 原件" style={{ maxWidth: "100%", maxHeight: "100%" }}/> : bytes ? <MediaReader bytes={bytes} mediaType={media.media_type}/> : <span>读取本地原件…</span>;
}
/** Canonical Document persistence; editing a board never grants an engine capability. */
export function CanonicalExpressionSpace({ onTrail, onOpenCapability }: {
    onTrail?: (levels: readonly ObjectTrailLevel[]) => void;
    onOpenCapability?: (id: string) => void;
}) {
    const section = useRef<HTMLElement>(null), pendingBoard = useRef(false);
    const [boardPending, setBoardPending] = useState(false);
    const buffers = useRef(new Map<string, Buffer>()), active = useRef("new"), epoch = useRef(0), lock = useRef(false), listLock = useRef(false), mounted = useRef(true);
    if (!buffers.current.size)
        buffers.current.set("new", { value: blank(), base: null, envelope: { type: "doc", content: [] }, dirty: false, serial: 0 });
    const [, redraw] = useState(0), [rows, setRows] = useState<DocumentSummaryDto[]>([]), [cursor, setCursor] = useState<string | null>(null), [loading, setLoading] = useState(false), [busy, setBusy] = useState(false), [message, setMessage] = useState("读取已保存表达文档…"), [failed, setFailed] = useState(false), [pending, setPending] = useState<string | null>(null), [history, setHistory] = useState<DocumentDto | null>(null), [unsupported, setUnsupported] = useState<DocumentDto | null>(null), [version, setVersion] = useState("1");
    const [sources, setSources] = useState<SourceDto[]>([]), [sourceId, setSourceId] = useState(""), [query, setQuery] = useState(""), [knowledgeRows, setKnowledgeRows] = useState<SearchDto["items"]>([]), [courses, setCourses] = useState<{
        manifest_id: string;
        title: string;
        stale: boolean;
    }[]>([]), [proposals, setProposals] = useState<RecordView[]>([]);
    const b = buffers.current.get(active.current)!;
    function publish() { const dirty = [...buffers.current.values()].some(x => x.dirty || x.attempt) || lock.current || pendingBoard.current; window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: dirty })); redraw(x => x + 1); }
    const pendingChanged = useCallback((value: boolean) => {
        if (!mounted.current)
            return;
        pendingBoard.current = value;
        setBoardPending(value);
        publish();
    }, []);
    function note(text: string, error = false) {
        if (mounted.current) {
            setMessage(text);
            setFailed(error);
        }
    }
    useEffect(() => { mounted.current = true; void list(false); return () => { mounted.current = false; epoch.current++; window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: false })); }; }, []);
    useEffect(() => { onTrail?.([{ id: "page:21", label: "表达工作区", region: "expression" }, ...(b.base ? [{ id: b.base.document_id, label: b.base.title, region: "expression" }] : [])]); }, [b.base?.document_id, onTrail]);
    async function list(more: boolean) {
        if (listLock.current)
            return;
        listLock.current = true;
        setLoading(true);
        try {
            const result = await coreCommand<DocumentsListDto>("documents_list", more && cursor ? { cursor } : {});
            if (!mounted.current)
                return;
            setRows(old => more ? [...old, ...result.documents.filter(v => !old.some(o => o.document_id === v.document_id))] : result.documents);
            setCursor(result.next_cursor);
            note("文档列表已读取；打开时核对表达格式，普通文档不会被覆盖。");
        }
        catch {
            note("文档列表读取失败；未当成空列表。", true);
        }
        finally {
            listLock.current = false;
            if (mounted.current)
                setLoading(false);
        }
    }
    function change(v: ExpressionDocument) { const current = buffers.current.get(active.current)!; current.value = structuredClone(v); current.dirty = true; current.serial++; setHistory(null); publish(); }
    function capabilityNote(field: "animation_note" | "simulation_note" | "spatial_note", text: string) {
        if (new TextEncoder().encode(text).length > 4096) {
            note("能力说明超出 4096 UTF-8 字节；原说明与其他能力数据保留。", true);
            return;
        }
        const next = structuredClone(b.value);
        next.capability_metadata = { ...next.capability_metadata, [field]: text };
        if (!parseExpressionDocument(next)) {
            note("能力说明超过整体 16 KiB 或结构限制；未改变原有数据。", true);
            return;
        }
        change(next);
        note("能力说明已修改，尚未保存；引擎仍为 NOT_EXECUTED。");
    }
    async function open(key: string) {
        const request = ++epoch.current, priorKey = active.current, priorSerial = buffers.current.get(priorKey)!.serial;
        setPending(null);
        setHistory(null);
        setUnsupported(null);
        if (key === "__new") {
            const id = `local_${crypto.randomUUID()}`;
            buffers.current.set(id, { value: blank(), base: null, envelope: { type: "doc", content: [] }, dirty: false, serial: 0 });
            active.current = id;
            publish();
            return;
        }
        if (buffers.current.has(key)) {
            active.current = key;
            publish();
            return;
        }
        let received: DocumentDto | null = null;
        try {
            const doc = await coreCommand<DocumentDto>("document_get", { document_id: key });
            if (doc.document_id !== key)
                throw new Error("identity mismatch");
            received = doc;
            const value = decode(doc);
            if (request !== epoch.current || !mounted.current)
                return;
            if (active.current !== priorKey || buffers.current.get(priorKey)?.serial !== priorSerial) {
                note("读取已完成，期间新增编辑仍保留；请重新选择对象。");
                return;
            }
            buffers.current.set(key, { value, base: doc, envelope: structuredClone(object(doc.editor_json)), dirty: false, serial: 0 });
            active.current = key;
            publish();
            note("表达对象已读取。");
        }
        catch {
            if (request === epoch.current && mounted.current) {
                if (received)
                    setUnsupported(received);
                note("表达对象读取失败或格式不支持；当前草稿保留。原始文档仅只读查看，未转换或覆盖。", true);
            }
        }
    }
    function requestOpen(key: string) {
        if (pendingBoard.current) {
            note("先完成或取消位置／连线编辑；当前输入保留。", true);
            return;
        }
        if (lock.current)
            return;
        if (b.dirty || b.attempt)
            setPending(key);
        else
            void open(key);
    }
    async function validateContext(value: ExpressionDocument) {
        const context = value.context;
        if (!context)
            return;
        const k = context.knowledge_id ? await coreCommand<KnowledgeDto>("knowledge_get", { id: context.knowledge_id }) : null;
        if (k && k.knowledge_id !== context.knowledge_id)
            throw new Error("知识真实身份不匹配");
        if (context.course_id) {
            const course = object(await coreCommand("course_get", { course_id: context.course_id })), manifest = object(course.manifest);
            if (manifest.manifest_id !== context.course_id || !Array.isArray(course.bindings))
                throw new Error("课程真实身份无效");
            if (k && !course.bindings.some(x => { const v = object(x); return v.knowledge_id === k.knowledge_id && v.knowledge_version === k.knowledge_id; }))
                throw new Error("课程与显式知识绑定不匹配");
        }
        if (context.teaching_record_id) {
            const v = await coreCommand<RecordView>("teaching_get", { record_id: context.teaching_record_id });
            if (v.record.record_id !== context.teaching_record_id || v.withdrawn || !["proposal", "revision", "delivery"].includes(v.record.kind) || (k && (v.record.knowledge_id !== k.knowledge_id || v.record.knowledge_version !== k.knowledge_id)) || (context.course_id && v.record.course_id && v.record.course_id !== context.course_id))
                throw new Error("教学引用撤回或显式上下文不匹配");
        }
    }
    async function save() {
        if (pendingBoard.current) {
            note("先完成或取消位置／连线编辑；未发送旧画布，也未报告全部保存。", true);
            return;
        }
        if (lock.current)
            return;
        lock.current = true;
        setBusy(true);
        publish();
        const key = active.current, current = buffers.current.get(key)!;
        try {
            const attempt = current.attempt ?? (() => { const editor = encode(current); return { operation: current.base ? "document_draft" as const : "document_create" as const, payload: current.base ? { document_id: current.base.document_id, body: { expected_version: current.base.version, editor_json: editor } } : { body: { create_request_id: `expression_${crypto.randomUUID()}`, title: "表达工作区", editor_json: editor } }, editor, serial: current.serial }; })();
            current.attempt = attempt;
            await validateContext(object(object(attempt.editor).attrs).archeaxis_expression as ExpressionDocument);
            const saved = await coreCommand<DocumentDto>(attempt.operation, attempt.payload);
            if (current.base && saved.document_id !== current.base.document_id)
                throw new Error("保存身份不一致");
            const readback = await coreCommand<DocumentDto>("document_get", { document_id: saved.document_id });
            if (readback.document_id !== saved.document_id || readback.version !== saved.version || !same(readback.editor_json, attempt.editor))
                throw new Error("保存读回不一致");
            current.base = readback;
            buffers.current.set(readback.document_id, current);
            current.envelope = structuredClone(object(readback.editor_json));
            current.attempt = undefined;
            current.dirty = current.serial !== attempt.serial;
            if (!current.dirty)
                current.value = decode(readback);
            if (mounted.current) {
                setRows(old => [readback, ...old.filter(r => r.document_id !== readback.document_id)]);
                note(current.dirty ? "已保存发送时的版本；随后编辑仍是未保存草稿。" : "表达草稿已保存并读回核对。");
            }
        }
        catch {
            note("保存未确认；草稿与冻结请求保留。重试不会另建首份对象；版本冲突需先核对，未报告成功。", true);
        }
        finally {
            lock.current = false;
            if (mounted.current) {
                setBusy(false);
                publish();
            }
        }
    }
    async function reconcileSave() {
        if (!b.base || lock.current || pendingBoard.current)
            return;
        const key = active.current, current = buffers.current.get(key)!, id = current.base!.document_id;
        lock.current = true;
        setBusy(true);
        publish();
        try {
            const d = await coreCommand<DocumentDto>("document_get", { document_id: id });
            if (d.document_id !== id)
                throw new Error("读回身份不符");
            decode(d);
            const attempt = current.attempt;
            if (attempt?.operation === "document_draft" && d.version === current.base!.version + 1 && same(d.editor_json, attempt.editor)) {
                current.base = d;
                current.envelope = structuredClone(object(d.editor_json));
                current.attempt = undefined;
                current.dirty = current.serial !== attempt.serial;
                if (!current.dirty)
                    current.value = decode(d);
                if (mounted.current) {
                    setRows(old => [d, ...old.filter(r => r.document_id !== id)]);
                    note("最新 Core 读回与上次冻结保存匹配；未另写版本，随后编辑仍保留。");
                }
            }
            else if (d.version === current.base!.version) {
                note("当前 Core 版本未变化；原冻结请求与草稿保留，可重试。");
            }
            else if (mounted.current) {
                setUnsupported(d);
                note("最新版本不同，已提供只读原文；当前草稿与原 expected_version 保留，未自动覆盖或合并。", true);
            }
        }
        catch {
            note("最新保存版本核对失败；当前草稿保留。", true);
        }
        finally {
            lock.current = false;
            if (mounted.current) {
                setBusy(false);
                publish();
            }
        }
    }
    async function readHistory() {
        if (pendingBoard.current) {
            note("先完成或取消位置／连线编辑；历史读取未改变当前输入。", true);
            return;
        }
        if (!b.base)
            return;
        const id = b.base.document_id, n = Number(version), request = epoch.current;
        if (!Number.isInteger(n) || n < 1 || n > b.base.version) {
            note("请输入已有的正整数版本。", true);
            return;
        }
        try {
            const d = await coreCommand<DocumentDto>("document_version", { document_id: id, version: n });
            if (d.document_id !== id || d.version !== n)
                throw new Error("历史身份不符");
            decode(d);
            if (request === epoch.current && mounted.current) {
                setHistory(d);
                note("历史只读；当前草稿未替换。");
            }
        }
        catch {
            if (request === epoch.current)
                note("历史读取失败；当前草稿保留。", true);
        }
    }
    async function exportSnapshot() {
        if (!b.base || lock.current)
            return;
        lock.current = true;
        setBusy(true);
        publish();
        const base = b.base;
        try {
            const result = await coreCommand<DocumentExportDto>("document_export", { document_id: base.document_id, format: "markdown" });
            if (result.document_id !== base.document_id || result.version !== base.version)
                throw new Error("导出版本已变化");
            const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }));
            const a = document.createElement("a");
            a.href = url;
            a.download = `expression-${base.document_id}-v${base.version}-references.json`;
            a.click();
            setTimeout(() => URL.revokeObjectURL(url), 0);
            note("已导出 Core 保存版本快照与媒体引用；不是全媒体包，未发送任何 peer。");
        }
        catch {
            note("导出失败或版本变化；未报告成功。", true);
        }
        finally {
            lock.current = false;
            if (mounted.current) {
                setBusy(false);
                publish();
            }
        }
    }
    async function readSources() {
        try {
            const r = await coreCommand<SourcesListDto>("sources_list", {});
            if (mounted.current)
                setSources(r.sources);
        }
        catch {
            note("来源读取失败；未添加虚构媒体。", true);
        }
    }
    async function addMedia(): Promise<ExpressionMedia | null> {
        if (pendingBoard.current) {
            note("先完成或取消位置／连线编辑；媒体尚未添加。", true);
            return null;
        }
        const key = active.current, serial = buffers.current.get(key)!.serial;
        const s = sources.find(x => x.source_id === sourceId);
        if (!s) {
            note("先从真实来源列表选择媒体。", true);
            return null;
        }
        try {
            const o = await coreCommand<OriginalDto>("source_original", { source_id: s.source_id });
            if (o.source_id !== s.source_id || o.sha256 !== s.sha256)
                throw new Error("来源不符");
            const m = { source_id: s.source_id, sha256: s.sha256, media_type: o.media_type as ExpressionMedia["media_type"] };
            await original(m);
            return key === active.current && serial === buffers.current.get(key)?.serial && mounted.current ? m : null;
        }
        catch {
            note("媒体不支持、来源或 SHA 核对失败；未添加。", true);
            return null;
        }
    }
    async function search() {
        const request = epoch.current;
        try {
            const r = await coreCommand<SearchDto>("search", { q: query });
            if (request === epoch.current && mounted.current)
                setKnowledgeRows(r.items);
        }
        catch {
            note("知识搜索失败。", true);
        }
    }
    async function contextChoices() {
        const request = epoch.current;
        try {
            const [c, t] = await Promise.all([coreCommand("course_list", {}), coreCommand<RecordPage>("teaching_list", {})]);
            const rows = object(c).items;
            if (!Array.isArray(rows))
                throw new Error("课程目录无效");
            if (request === epoch.current && mounted.current) {
                setCourses(rows as typeof courses);
                setProposals(t.items.filter(v => !v.withdrawn && ["proposal", "revision", "delivery"].includes(v.record.kind)));
            }
        }
        catch {
            note("课程或方案目录读取失败；未假造空成功。", true);
        }
    }
    async function selectContext(field: "knowledge_id" | "course_id" | "teaching_record_id", id: string) {
        const key = active.current, current = buffers.current.get(key)!, serial = current.serial, next = structuredClone(current.value);
        next.context = { ...next.context, [field]: id || null };
        if (field === "knowledge_id") {
            next.context.course_id = null;
            next.context.teaching_record_id = null;
        }
        if (field === "course_id")
            next.context.teaching_record_id = null;
        try {
            await validateContext(next);
            if (key === active.current && serial === current.serial && mounted.current) {
                change(next);
                note("上下文真实身份已核对；尚未保存。");
            }
        }
        catch {
            note("上下文不匹配或读取失败；未改变草稿绑定。", true);
        }
    }
    const shown = history ? decode(history) : b.value;
    return <section ref={section} tabIndex={-1} className="ui-expression-page" aria-label="表达工作区"><h2>表达工作区</h2><p role={failed ? "alert" : "status"}>{message}</p><p>文字、媒体与关系保存在版本化 Document。外部引擎资格：NOT_EXECUTED；媒体仅引用已保全的 Source CAS。</p><div><button disabled={busy} onClick={() => requestOpen("__new")}>新表达草稿</button><button disabled={busy || loading} onClick={() => void list(false)}>刷新文档</button>{cursor ? <button disabled={loading} onClick={() => void list(true)}>更多文档</button> : null}<button disabled={busy || (!b.dirty && !b.attempt)} onClick={() => void save()}>{b.attempt ? "重试冻结保存" : "保存表达草稿"}</button><button disabled={busy || !b.base || boardPending} onClick={() => void reconcileSave()}>核对最新保存版本（不覆盖草稿）</button><button disabled={busy || !b.base || !!history} onClick={() => void exportSnapshot()}>导出已保存快照 / 引用</button>{onOpenCapability ? <button onClick={() => onOpenCapability("CAP-0160")}>能力与资格</button> : null}</div><ul aria-label="已保存文档">{rows.map(row => <li key={row.document_id}><button disabled={busy} onClick={() => requestOpen(row.document_id)}>{row.title} · v{row.version}</button></li>)}</ul><p>{boardPending ? "位置／连线输入尚未提交；先完成或取消位置／连线编辑。" : null}</p><p>{b.base ? `${b.base.document_id} · v${b.base.version}` : "本地未登记草稿"} · {b.dirty ? "未保存" : "无未保存编辑"}</p>
    <details><summary>上下文与来源</summary><label>知识搜索<input value={query} onChange={e => setQuery(e.target.value)}/></label><button onClick={() => void search()}>查找实际知识</button><label>知识版本<select value={b.value.context?.knowledge_id ?? ""} onChange={e => void selectContext("knowledge_id", e.target.value)}><option value="">无知识绑定</option>{b.value.context?.knowledge_id && !knowledgeRows.some(k => k.knowledge_id === b.value.context?.knowledge_id) ? <option>{b.value.context.knowledge_id}</option> : null}{knowledgeRows.map(k => <option key={k.knowledge_id} value={k.knowledge_id}>{k.head} · {k.status}</option>)}</select></label><button onClick={() => void contextChoices()}>读取实际课程与方案</button><label>课程<select value={b.value.context?.course_id ?? ""} onChange={e => void selectContext("course_id", e.target.value)}><option value="">无课程绑定</option>{courses.map(c => <option key={c.manifest_id} value={c.manifest_id}>{c.title} {c.stale ? "陈旧" : ""}</option>)}</select></label><label>方案 / 修订 / 交付<select value={b.value.context?.teaching_record_id ?? ""} onChange={e => void selectContext("teaching_record_id", e.target.value)}><option value="">无教学绑定</option>{proposals.map(p => <option key={p.record.record_id} value={p.record.record_id}>{p.record.purpose}</option>)}</select></label><button onClick={() => void readSources()}>读取媒体来源</button><label>Source CAS<select value={sourceId} onChange={e => setSourceId(e.target.value)}><option value="">选择来源</option>{sources.map(s => <option key={s.source_id} value={s.source_id}>{s.original_name}</option>)}</select></label></details>
    <>{unsupported ? <details aria-label="原始文档／核对版本（只读）"><summary>只读原文 {unsupported.document_id} · v{unsupported.version}</summary><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(unsupported.editor_json, null, 2)}</pre></details> : null}</><CanonicalExpressionBoard key={active.current + (history ? `:history:${history.version}` : "")} onPendingEditChange={pendingChanged} value={shown} onChange={change} onAddMedia={addMedia} renderMedia={(media: ExpressionMedia, _node: ExpressionNode) => <CasMedia media={media}/>} readOnly={!!history}/>
    <details><summary>后续表达能力说明</summary><p>动画、参数仿真、空间 / XR 引擎：NOT_EXECUTED。以下仅为文本说明，保存不执行脚本或场景；其他已有能力说明保留。</p>{([["animation_note", "动画产物说明", "CAP-0070"], ["simulation_note", "仿真参数说明", "CAP-0070"], ["spatial_note", "空间 XR 场景说明", "CAP-0080"]] as const).map(([field, label, cap]) => <div key={field}><label>{label}<textarea disabled={!!history} value={typeof shown.capability_metadata?.[field] === "string" ? shown.capability_metadata[field] as string : ""} onChange={e => capabilityNote(field, e.target.value)}/></label>{shown.capability_metadata?.[field] != null && typeof shown.capability_metadata[field] !== "string" ? <p>原说明采用其他结构，保持原值；输入文本时只替换此项。</p> : null}{onOpenCapability ? <button onClick={() => onOpenCapability(cap)}>查看{label}能力状态</button> : null}</div>)}</details><p>仅导出当前已保存版本；历史视图不导出。未保存编辑不进入导出快照。</p><label>历史版本<input inputMode="numeric" value={version} onChange={e => setVersion(e.target.value)}/></label><button disabled={!b.base} onClick={() => void readHistory()}>读取历史（只读）</button>{history ? <button onClick={() => setHistory(null)}>回到保留草稿</button> : null}
    <AaosDialog trigger={<button disabled={pending === null}>审阅对象切换</button>} onCloseAutoFocus={event => { event.preventDefault(); section.current?.focus(); }} open={pending !== null} onOpenChange={v => {
            if (!v)
                setPending(null);
        }} title="切换表达对象？" description="未保存草稿保留在当前页面内存；离开整个工作区需先保存。取消保持当前编辑。"><button onClick={() => setPending(null)}>取消切换</button><button disabled={boardPending} onClick={() => {
            if (pending && !pendingBoard.current)
                void open(pending);
        }}>保留草稿并切换</button></AaosDialog>
  </section>;
}
