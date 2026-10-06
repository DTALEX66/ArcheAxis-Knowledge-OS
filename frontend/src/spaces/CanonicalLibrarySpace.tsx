import { lazy, Suspense, useEffect, useRef, useState, type CSSProperties } from "react";
import type { JSONContent } from "@tiptap/core";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import type { SourceDto, DocumentDto, DocumentSummaryDto, OriginalDto, AnchorDto, DocumentExportDto, RevisionBasisDto } from "../api/generated/core-contract";
import { Section } from "../components/RealData";
import { MediaReader } from "../components/MediaReader";
import type { EpubPosition } from "../components/EpubParagraphs";
import { JobContent } from "../components/JobContent";
import { CheckPanel } from "../components/CheckPanel";
import { BackupPanel } from "../components/BackupPanel";
import "../components/content.css";
import type { InspectionTarget } from "../components/Inspector";
import type { LibrarySection } from "../components/ContextNav";

// PDF.js is a large renderer and is needed only when the selected original is a PDF.
const PdfReader = lazy(() => import("../components/PdfReader").then(module => ({ default: module.PdfReader })));
// Tiptap/ProseMirror are needed only after a versioned document is selected.
const DocumentEditor = lazy(() => import("../components/DocumentEditor").then(module => ({ default: module.DocumentEditor })));

export function CanonicalLibrarySpace({onKnowledge,initialDocumentId,onDirtyChange,onInspect,navigation}:{onKnowledge?:()=>void;initialDocumentId?:string;onDirtyChange?:(dirty:boolean)=>void;onInspect?:(target:InspectionTarget)=>void;navigation?:{section:LibrarySection;sequence:number}}) {
  const [sources, setSources] = useState<SourceDto[]>([]);
  const [sourcePage, setSourcePage] = useState(0);
  const [documents, setDocuments] = useState<DocumentSummaryDto[]>([]);
  const [openedDocuments, setOpenedDocuments] = useState<DocumentSummaryDto[]>([]);
  const [source, setSource] = useState<SourceDto | null>(null);
  const [original, setOriginal] = useState<OriginalDto | null>(null);
  const [bytes, setBytes] = useState<Uint8Array | null>(null);
  const [documentSource, setDocumentSource] = useState<SourceDto | null>(null);
  const [documentOriginal, setDocumentOriginal] = useState<OriginalDto | null>(null);
  const [documentBytes, setDocumentBytes] = useState<Uint8Array | null>(null);
  const [document, setDocument] = useState<DocumentDto | null>(null);
  const [anchors, setAnchors] = useState<AnchorDto[]>([]);
  const [page, setPage] = useState(1);
  const [focusRequest, setFocusRequest] = useState(0);
  const [epubSeek,setEpubSeek]=useState<{sourceId:string;position:EpubPosition}|undefined>();
  const [mediaSeek,setMediaSeek]=useState<{sourceId:string;milliseconds:number;sequence:number}|undefined>();
  const [restoreVersion, setRestoreVersion] = useState("1");
  const [historicalDocument, setHistoricalDocument] = useState<DocumentDto | null>(null);
  const historyGeneration = useRef(0);
  const currentDocument = useRef(document);
  currentDocument.current = document;
  const [editorEpoch, setEditorEpoch] = useState(0);
  const [message, setMessage] = useState("正在读取资料…");
  const [failure, setFailure] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importReceipt,setImportReceipt]=useState<{name:string;bytes:number;state:string}|null>(null);
  const [exportProof, setExportProof] = useState<DocumentExportDto | null>(null);
  const revisionBasis = useRef<RevisionBasisDto | null>(null);
  const dirty = useRef(false);
  const writeInFlight = useRef(false);
  const [busy, setBusy] = useState(false);
  const [documentDirty, setDocumentDirty] = useState(false);
  const editGeneration = useRef(0);
  const generation = useRef(0);
  const textRegion = useRef<HTMLPreElement>(null);
  const sourceNavigation = useRef<HTMLElement>(null);
  const documentNavigation = useRef<HTMLElement>(null);
  const anchorNavigation = useRef<HTMLElement>(null);
  const versionNavigation = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!navigation?.sequence) return;
    const target = {sources:sourceNavigation,documents:documentNavigation,anchors:anchorNavigation,versions:versionNavigation}[navigation.section].current;
    target?.scrollIntoView?.({block:"nearest",behavior:"auto"});
    target?.focus();
  }, [navigation?.section, navigation?.sequence, source?.source_id, document?.document_id]);
  useEffect(() => {
    if (!document && !source) return;
    onInspect?.({
      title: document?.title ?? source!.original_name,
      source: source ? "CAS 原件 / Rust Core" : document?.source_id ? "有来源绑定的文档 / Rust Core" : "用户原创文档 / Rust Core",
      lifecycle: document ? "已保存；核验与依据分析独立记录" : "原件已保留",
      rawSha256: document ? undefined : source?.sha256,
      version: document ? String(document.version) : source?.source_revision,
      updatedAt: source?.imported_at,
      detail: document ? `文档 ${document.document_id}；正文指纹 ${document.content_sha256}；${document.source_id ? `关联原件 ${document.source_id}@${document.source_revision}（原件 SHA 独立）` : "没有来源原件绑定"}；保存不表示已证实。` : `原件 ${source!.source_id}；${anchors.length} 条定位记录；处理状态以实际任务为准。`,
    });
  }, [document, source, anchors, onInspect]);
  useEffect(() => {
    let alive = true;
    Promise.all([
      coreCommand<{ sources: SourceDto[] }>("sources_list"),
      coreCommand<{ documents: DocumentSummaryDto[] }>("documents_list"),
    ]).then(([sourcesResult, docsResult]) => {
      if (!alive) return;
      setSources(sourcesResult.sources); setDocuments(docsResult.documents); setMessage("");
    }).catch(() => { if (alive) { setMessage("资料暂时无法读取，请检查本地核心。"); setFailure(true); } });
    return () => { alive = false; generation.current += 1; onDirtyChange?.(false); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: false })); };
  }, []);
  useEffect(()=>{if(initialDocumentId)void openDocument(initialDocumentId);},[initialDocumentId]);
  async function importFile(file: File) {
    setImportReceipt({name:file.name,bytes:file.size,state:"正在检查原件"});
    if (file.size > 64 * 1024 * 1024) { setMessage("当前导入上限为 64 MiB，请选择不超过上限的原件。"); setFailure(true); setImportReceipt({name:file.name,bytes:file.size,state:"未导入：超过大小上限"}); return; }
    setImporting(true); setFailure(false); setMessage("正在导入原件…");
    try {
      const content = new Uint8Array(await file.arrayBuffer());
      let binary = "";
      for (let offset = 0; offset < content.length; offset += 8192) binary += String.fromCharCode(...content.subarray(offset, offset + 8192));
      await coreCommand("source_import", { body: { name: file.name, content_base64: btoa(binary) } });
      const list = await coreCommand<{ sources: SourceDto[] }>("sources_list");
      setSources(list.sources); setImportReceipt({name:file.name,bytes:file.size,state:"原件已保留；转换尚未执行"}); setMessage("原件已导入；选择它开始阅读。");
    } catch { setImportReceipt({name:file.name,bytes:file.size,state:"导入未确认，请保留原件"}); setMessage("导入未完成，请保留原件并重试。"); setFailure(true); }
    finally { setImporting(false); }
  }
  async function open(selected: SourceDto) {
    if (dirty.current) { setMessage("当前文档有未保存更改。请先保存，再切换资料；当前文字保持不变。"); return; }
    revisionBasis.current = null;
    const epoch = ++generation.current;
    const editingEpoch=editGeneration.current;
    setMessage("正在读取原件与文档…"); setFailure(false);
    let readStage="原件与引用读取";
    try {
      const [asset, evidence] = await Promise.all([
        coreCommand<OriginalDto>("source_original", { source_id: selected.source_id }),
        coreCommand<{ anchors: AnchorDto[] }>("anchors_list", { source_id: selected.source_id }),
      ]);
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return;
      readStage="原件版本核对";
      if (asset.source_id!==selected.source_id||asset.sha256 !== selected.sha256) throw new Error("source identity mismatch");
      const decoded = Uint8Array.from(atob(asset.content_base64), (character) => character.charCodeAt(0));
      readStage="原件字节核验";
      const actualHash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", decoded))).map((value) => value.toString(16).padStart(2, "0")).join("");
      if (actualHash !== selected.sha256) throw new Error("source bytes mismatch");
      const linked = documents.find((item) => item.source_id === selected.source_id);
      readStage="草稿版本读取";
      const active = linked ? await coreCommand<DocumentDto>("document_get", { document_id: linked.document_id }) : null;
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return;
      setSource(selected); setOriginal(asset); setBytes(decoded); setDocument(active); setAnchors(evidence.anchors);
      setDocumentSource(active ? selected : null); setDocumentOriginal(active ? asset : null); setDocumentBytes(active ? decoded : null);
      if (active) setOpenedDocuments(previous => previous.some(item => item.document_id === active.document_id) ? previous : [...previous, active]);
      setExportProof(null);
      setEditorEpoch((value) => value + 1); setPage(1); dirty.current = false; setDocumentDirty(false); setMessage("原件哈希已核对；草稿与原件独立保存。");
      onDirtyChange?.(false); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: false }));
    } catch { if (epoch === generation.current) { setFailure(true); setMessage(`${readStage}未完成；未替换当前内容，请保留原件重试。`); } }
  }
  async function openDocument(id: string) {
    if (currentDocument.current?.document_id === id) return;
    if (dirty.current) { setMessage("当前文档有未保存更改。请先保存，再切换标签；当前文字保持不变。"); return; }
    revisionBasis.current = null;
    const epoch = ++generation.current;
    const editingEpoch=editGeneration.current;
    try {
      const active = await coreCommand<DocumentDto>("document_get", { document_id: id });
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return;
      setDocument(active); setSource(null); setOriginal(null); setBytes(null); setAnchors([]);
      setDocumentSource(null); setDocumentOriginal(null); setDocumentBytes(null);
      setOpenedDocuments(previous => previous.some(item => item.document_id === active.document_id) ? previous.map(item => item.document_id === active.document_id ? active : item) : [...previous, active]);
      setEditorEpoch(value => value + 1); dirty.current = false; setDocumentDirty(false); setExportProof(null);
      setMessage("文档已读取；保存不要求来源引用或审核。"); setFailure(false);
      onDirtyChange?.(false); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: false }));
      const linked = sources.find(item => item.source_id === active.source_id && item.source_revision === active.source_revision && item.sha256 === active.source_revision);
      if (linked) {
        try {
          const [asset, evidence] = await Promise.all([
            coreCommand<OriginalDto>("source_original", { source_id: linked.source_id }),
            coreCommand<{anchors: AnchorDto[]}>("anchors_list", { source_id: linked.source_id }),
          ]);
          const decoded = Uint8Array.from(atob(asset.content_base64), char => char.charCodeAt(0));
          const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", decoded))).map(value => value.toString(16).padStart(2,"0")).join("");
          if (asset.source_id !== linked.source_id || asset.sha256 !== linked.sha256 || active.source_revision !== linked.source_revision || active.source_id !== linked.source_id || digest !== linked.sha256) throw new Error("source mismatch");
          if (epoch === generation.current) { setSource(linked); setOriginal(asset); setBytes(decoded); setAnchors(evidence.anchors); setPage(1); setDocumentSource(linked); setDocumentOriginal(asset); setDocumentBytes(decoded); }
        } catch { if (epoch === generation.current) setMessage("文档已读取；关联原件未完成核验，仍可编辑保存文档。"); }
      }
    } catch { if (epoch === generation.current && editingEpoch === editGeneration.current) { setMessage("文档读取未完成；当前内容仍保留。"); setFailure(true); } }
  }
  async function createOriginal() {
    if (dirty.current) { setMessage("当前文档有未保存更改。请先保存，再新建笔记；当前文字保持不变。"); return; }
    const epoch=++generation.current;
    const editingEpoch=editGeneration.current;
    try {
      const created = await coreCommand<DocumentDto>("document_create", { body: {
        title: "原创笔记", editor_json: { type: "doc", content: [{ type: "paragraph" }] },
      } });
      setDocuments(previous=>[...previous,created]);
      setOpenedDocuments(previous => [...previous, created]);
      if(epoch!==generation.current||editingEpoch!==editGeneration.current){setMessage("原创笔记已建立，当前编辑内容仍保留；可从已保存文档打开新笔记。");return;}
      revisionBasis.current = null;
      setDocument(created);
      setSource(null); setOriginal(null); setBytes(null); setAnchors([]); setExportProof(null); setDocumentSource(null); setDocumentOriginal(null); setDocumentBytes(null);
      setEditorEpoch(value => value + 1); dirty.current = false; setDocumentDirty(false); setMessage("原创笔记已建立。"); setFailure(false);
      onDirtyChange?.(false); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: false }));
    } catch { setMessage("原创笔记建立未确认；请重试。"); setFailure(true); }
  }
  // A second click during an in-flight create/restore/export would persist a duplicate
  // document, version, or export, so only one such write may be outstanding.
  async function singleWrite(action: () => Promise<unknown>) {
    if (writeInFlight.current) return;
    writeInFlight.current = true; setBusy(true);
    try { await action(); } finally { writeInFlight.current = false; setBusy(false); }
  }
  async function create() {
    if (!source || !original || !bytes) return;
    const epoch = generation.current;
    const editingEpoch=editGeneration.current;
    try {
      const plain = original.media_type.startsWith("text/") ? new TextDecoder().decode(bytes) : "";
      const created = await coreCommand<DocumentDto>("document_create", {
        body: {
        source_id: source.source_id, source_revision: source.source_revision, title: source.original_name,
        editor_json: { type: "doc", content: [{ type: "paragraph", ...(plain ? { content: [{ type: "text", text: plain }] } : {}) }] },
        },
      });
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return;
      setDocument(created); setDocuments((previous) => [...previous, created]); setOpenedDocuments(previous => [...previous, created]); setDocumentSource(source); setDocumentOriginal(original); setDocumentBytes(bytes); setEditorEpoch((value) => value + 1); setMessage("草稿已建立并持久化。"); setFailure(false);
    } catch { setMessage("草稿建立失败；原件仍保留。"); setFailure(true); }
  }
  async function save(content: JSONContent, expectedVersion: number) {
    if (!document) throw new Error("document not loaded");
    const epoch = generation.current;
    const sentBasis = revisionBasis.current;
    const saved = await coreCommand<DocumentDto>("document_draft", { document_id: document.document_id, body: { expected_version: expectedVersion, editor_json: content, ...(revisionBasis.current ? {revision_basis:revisionBasis.current} : {}) } });
    if (epoch === generation.current) {
      if (revisionBasis.current === sentBasis) revisionBasis.current = null;
      setDocument(saved);
      setDocuments((previous) => previous.map((item) => item.document_id === saved.document_id ? saved : item));
      setOpenedDocuments((previous) => previous.map((item) => item.document_id === saved.document_id ? saved : item));
    }
    return { content: saved.editor_json as JSONContent, version: saved.version };
  }
  async function readHistory() {
    if (!document) return;
    const epoch = generation.current;
    const request = ++historyGeneration.current;
    const requestedDocument = document;
    const isCurrentHistoryRequest = () => epoch === generation.current && request === historyGeneration.current
      && currentDocument.current?.document_id === requestedDocument.document_id
      && currentDocument.current?.version === requestedDocument.version
      && currentDocument.current?.content_sha256 === requestedDocument.content_sha256;
    const version = Number(restoreVersion);
    if (!Number.isInteger(version) || version < 1 || version > document.version) { setMessage("请输入已有的正整数版本。"); setFailure(true); return; }
    try {
      const historical = await coreCommand<DocumentDto>("document_version", { document_id: document.document_id, version });
      if (!isCurrentHistoryRequest()) return;
      if (historical.document_id !== document.document_id || historical.version !== version) throw new Error("history identity mismatch");
      setHistoricalDocument(historical); setMessage("历史版本已读取，当前草稿保持不变。"); setFailure(false);
      const historicalSource = sources.find(item => item.source_id === historical.source_id && item.source_revision === historical.source_revision);
      onInspect?.({
        title: historical.title,
        source: historicalSource ? "CAS 原件 / Rust Core 历史文档" : "Rust Core 历史文档",
        lifecycle: "历史版本；只读；核验与依据分析独立记录",
        version: String(historical.version),
        rawSha256: historicalSource?.sha256,
        detail: `文档 ${historical.document_id}；历史正文指纹 ${historical.content_sha256}；当前草稿与最新版本保持不变；保存不表示已证实。`,
      });
    } catch {
      if (isCurrentHistoryRequest()) { setMessage("历史版本未读取，请重试。"); setFailure(true); }
    }
  }
  async function restore() {
    if (!document) return;
    const epoch = generation.current;
    const editingEpoch=editGeneration.current;
    const previous = Number(restoreVersion);
    if (!Number.isInteger(previous) || previous < 1 || previous > document.version) { setMessage("请输入已有的正整数版本。"); setFailure(true); return; }
    if (dirty.current) { setMessage("恢复操作暂停：请先保存当前文字，再读取历史版本并恢复。"); return; }
    try {
      // Read the specific immutable version before requesting a new restored revision.
      await coreCommand<DocumentDto>("document_version", { document_id: document.document_id, version: previous });
      const restored = await coreCommand<DocumentDto>("document_restore", { document_id: document.document_id, body: { expected_version: document.version, restore_version: previous } });
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return;
      setDocument(restored); setEditorEpoch((value) => value + 1); dirty.current = false; setDocumentDirty(false);
      setOpenedDocuments(previous => previous.map(item => item.document_id === restored.document_id ? restored : item));
      setDocumentSource(source); setDocumentOriginal(original); setDocumentBytes(bytes);
      onDirtyChange?.(false); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: false }));
      setMessage(`已从版本 ${previous} 恢复为新版本 ${restored.version}。`); setFailure(false);
    } catch { if (epoch === generation.current && editingEpoch === editGeneration.current) { setMessage("恢复失败或版本已变化；当前草稿仍保留。"); setFailure(true); } }
  }
  async function cite(): Promise<JSONContent> {
    if (!source) throw new Error("source not loaded");
    const epoch = generation.current;
    const textBytes = !isPdf && original?.media_type.startsWith("text/") ? bytes : null;
    const checksum = textBytes ? Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", textBytes.slice().buffer)), (value) => value.toString(16).padStart(2, "0")).join("") : undefined;
    const anchor = await coreCommand<AnchorDto>("anchor_create", {
      source_id: source.source_id, body: { revision: source.source_revision,
      position: JSON.stringify(isPdf ? { type: "pdf_page", page } : textBytes ? { type: "text", start: 0, end: textBytes.length } : { type: "source", source_id: source.source_id }), ...(checksum ? { checksum } : {}) },
    });
    if (epoch !== generation.current) throw new Error("source changed during reference creation");
    if (!anchor.anchor_id || anchor.source_revision !== source.source_revision) throw new Error("anchor revision mismatch");
    setAnchors((previous) => [...previous, anchor]);
    return { type: "evidenceReference", attrs: { anchor_id: anchor.anchor_id, source_id: source.source_id, source_revision: source.source_revision, position: anchor.position, page: isPdf ? page : null, excerpt: isPdf ? `第 ${page} 页` : source.original_name } };
  }
  function jump(attributes: Record<string, unknown>) {
    if (!source || attributes.source_id !== source.source_id || attributes.source_revision !== source.source_revision) { setMessage("此引用绑定另一来源版本，请打开对应原件。不会自动迁移定位。"); return; }
    if (Number.isInteger(attributes.page) && (attributes.page as number) > 0) { setPage(attributes.page as number); setFocusRequest((value) => value + 1); }
    else {
      textRegion.current?.focus();
      let location = attributes;
      if (typeof attributes.position === "string") {try {location=JSON.parse(attributes.position);} catch {return;}}
      if(location.type==="epub"){setEpubSeek({sourceId:source.source_id,position:location as EpubPosition});return;}
      if(location.type==="time"&&typeof location.start_ms==="number"&&Number.isFinite(location.start_ms)&&location.start_ms>=0){setMediaSeek(previous=>({sourceId:source.source_id,milliseconds:Number(location.start_ms),sequence:(previous?.sequence??0)+1}));return;}
      if (bytes && location.type === "text" && Number.isInteger(location.start) && Number.isInteger(location.end)) {
        try {
          const decoder=new TextDecoder("utf-8",{fatal:true});
          const start=decoder.decode(bytes.slice(0,Number(location.start))).length;
          const end=decoder.decode(bytes.slice(0,Number(location.end))).length;
          const node=textRegion.current?.firstChild;
          if(node && start<=end && end<=(node.textContent?.length??0)) {const range=window.document.createRange();range.setStart(node,start);range.setEnd(node,end);const selection=window.getSelection();selection?.removeAllRanges();selection?.addRange(range);}
        } catch {setMessage("此引用的文本边界无法读取，保留引用并待重新定位。");}
      }
    }
  }
  async function exportDocument(format: "markdown"|"obsidian") {
    if (!document) return;
    const epoch = generation.current;
    try {
      const proof = await coreCommand<DocumentExportDto>("document_export", {document_id:document.document_id,format});
      if (epoch !== generation.current) return;
      setExportProof(proof);
      const saved = await coreCommand<unknown>("document_export_save", {document_id:document.document_id,format});
      if (!saved || typeof saved !== "object" || !("directory" in saved) || typeof saved.directory !== "string" || !("version" in saved) || saved.version !== proof.version) throw new Error("invalid export receipt");
      if (epoch === generation.current) {setMessage(`已导出到产品资料目录 ${saved.directory}。外部应用读取仍需单独验证。`);setFailure(false);}
    } catch {setMessage("导出未确认；原件与草稿仍保留。");setFailure(true);}
  }
  function closeDocumentTab(id: string) {
    if (dirty.current && currentDocument.current?.document_id === id) { setMessage("此标签有未保存更改，先保存后才能关闭；文字保持不变。"); return; }
    const remaining = openedDocuments.filter(item => item.document_id !== id);
    setOpenedDocuments(remaining);
    if (currentDocument.current?.document_id === id) {
      setDocument(null); setHistoricalDocument(null); setSource(null); setOriginal(null); setBytes(null); setAnchors([]); setDocumentSource(null); setDocumentOriginal(null); setDocumentBytes(null);
      onDirtyChange?.(false); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: false }));
      if (remaining[0]) void openDocument(remaining[0].document_id);
      else setMessage("文档标签已关闭。已保存文档仍可从列表重新打开。");
    }
  }
  const isPdf = original?.media_type === "application/pdf" || /\.pdf$/i.test(source?.original_name ?? "");
  const linkedOriginal = Boolean(document && document.source_id && document.source_revision
    && documentSource?.source_id === document.source_id
    && documentSource.source_revision === document.source_revision
    && documentOriginal?.source_id === document.source_id
    && documentBytes);
  const linkedPdf = documentOriginal?.media_type === "application/pdf" || /\.pdf$/i.test(documentSource?.original_name ?? "");
  return <Section title="资料库">
    <p className="muted">原件保留其不可变版本；草稿自动保存到本地核心，引用绑定原件版本。</p>
    <label className="content-import">导入原件 <input type="file" aria-label="导入原件" disabled={importing} onChange={(event) => { const file = event.target.files?.[0]; if (file) void importFile(file); event.target.value = ""; }} /></label>
    {importReceipt?<dl className="receipt-grid" aria-label="导入回执"><div><dt>来源文件</dt><dd>{importReceipt.name}</dd></div><div><dt>原件大小</dt><dd>{importReceipt.bytes} 字节</dd></div><div><dt>导入状态</dt><dd>{importReceipt.state}</dd></div><div><dt>下一步</dt><dd>选择原件阅读或执行转换，再从实际引文整理待审核知识。</dd></div></dl>:null}
    <div className="canonical-library">
      <nav ref={sourceNavigation} tabIndex={-1} className="canonical-sources" aria-label="保留原件">
        {sources.length === 0 ? <p>暂无原件。</p> : sources.slice(sourcePage*30,(sourcePage+1)*30).map((item) => <button type="button" key={item.source_id} aria-current={source?.source_id === item.source_id ? "true" : undefined} onClick={() => void open(item)}>{item.original_name}</button>)}
        {sources.length>30?<div><button disabled={sourcePage===0} onClick={()=>setSourcePage(value=>value-1)}>上一组原件</button><span>{sourcePage+1} / {Math.ceil(sources.length/30)}</span><button disabled={(sourcePage+1)*30>=sources.length} onClick={()=>setSourcePage(value=>value+1)}>下一组原件</button></div>:null}
      </nav>
      {source && original && bytes ? <div className="canonical-content">
        <h4>{source.original_name}</h4>
        <div className="canonical-reading">
          <div>
          {isPdf ? <PdfReader bytes={bytes} page={page} onPageChange={setPage} focusRequest={focusRequest} /> : original.media_type.startsWith("text/") ? <pre ref={textRegion} tabIndex={-1} aria-label="原件正文">{new TextDecoder().decode(bytes)}</pre> : null}
          {original.media_type.startsWith("audio/")||original.media_type.startsWith("video/")?<MediaReader key={`media:${source.source_id}`} bytes={bytes} mediaType={original.media_type} seek={mediaSeek?.sourceId===source.source_id?mediaSeek:undefined}/>:null}
          <JobContent key={`job:${source.source_id}`} sourceId={source.source_id} name={source.original_name} sourceRevision={source.source_revision} epubSeek={epubSeek?.sourceId===source.source_id?epubSeek.position:undefined} onEpubSeek={position=>setEpubSeek({sourceId:source.source_id,position})} onKnowledge={onKnowledge} onTimeSeek={seconds=>setMediaSeek(previous=>({sourceId:source.source_id,milliseconds:seconds*1000,sequence:(previous?.sequence??0)+1}))} onAnchor={anchor=>setAnchors(previous=>previous.some(item=>item.anchor_id===anchor.anchor_id)?previous:[...previous,anchor])}/>
          </div>
          <aside ref={anchorNavigation} tabIndex={-1} aria-label="来源版本证据">
            <h4>来源与引用</h4>
            <p>引用绑定不可变原件版本，选择引用可回到已记录位置。</p>
            <details><summary>更多信息：来源链与内容指纹</summary><dl className="receipt-grid"><div><dt>来源</dt><dd>{source.original_name}</dd></div><div><dt>来源 ID</dt><dd>{source.source_id}</dd></div><div><dt>来源版本（原件指纹）</dt><dd>{source.source_revision}</dd></div><div><dt>原件 SHA-256</dt><dd>{original.sha256}</dd></div><div><dt>读取核验</dt><dd>原件字节与 Core 内容指纹已匹配</dd></div></dl></details>
            {anchors.length===0?<p className="muted">此来源尚无引用记录。</p>:null}
            {anchors.map((anchor) => { let location: Record<string, unknown> = {}; try { location = JSON.parse(anchor.position); } catch { /* Preserve unresolved position, never invent a locator. */ }
              return <div key={anchor.anchor_id}><button type="button" disabled={anchor.location_status === "revision_mismatch"} onClick={() => jump({ ...location, source_id: anchor.source_id, source_revision: anchor.source_revision })}>{typeof location.page === "number" ? `第 ${location.page} 页` : "来源引用"}{anchor.location_status === "revision_mismatch" ? " · 需重新定位" : anchor.location_status !== "located" ? " · 定位未核实" : ""}</button><details><summary>引用来源记录</summary><dl className="receipt-grid"><div><dt>引用 ID</dt><dd>{anchor.anchor_id}</dd></div><div><dt>来源版本（原件指纹）</dt><dd>{anchor.source_revision}</dd></div><div><dt>记录位置</dt><dd>{anchor.position}</dd></div><div><dt>定位状态</dt><dd>{anchor.location_status === "located" ? "已核实" : anchor.location_status === "revision_mismatch" ? "版本不匹配，需重新定位" : "定位未核实"}</dd></div></dl></details></div>;
            })}
          </aside>
        </div>
        {!document ? <button type="button" disabled={busy} onClick={() => void singleWrite(create)}>建立版本化草稿</button> : null}
      </div> : <p className="muted">选择一个原件开始阅读。</p>}
    </div>
    {openedDocuments.length > 0 ? <nav className="document-tab-strip" role="tablist" aria-label="已打开文档标签">
      {openedDocuments.map(item => <div className="document-tab" key={item.document_id}>
        <button type="button" role="tab" aria-selected={document?.document_id === item.document_id} onClick={() => void openDocument(item.document_id)}>
          {item.title}<small>v{item.version}</small>
        </button>
        <button type="button" aria-label={`关闭文档标签 ${item.title}`} disabled={busy || (documentDirty && document?.document_id === item.document_id)} onClick={() => closeDocumentTab(item.document_id)}>×</button>
      </div>)}
    </nav> : null}
    <button type="button" disabled={busy} onClick={() => void singleWrite(createOriginal)}>新建原创笔记</button>
    <nav ref={documentNavigation} tabIndex={-1} aria-label="已保存文档">{documents.map(item => <button type="button" key={item.document_id} onClick={() => void openDocument(item.document_id)}>{item.title} · 文档</button>)}</nav>
    {!source && navigation?.section === "anchors" ? <section ref={anchorNavigation} tabIndex={-1} aria-label="来源版本证据"><p>请先选择实际来源原件；原创笔记可以没有来源锚点。</p></section> : null}
    {!document && navigation?.section === "versions" ? <div ref={versionNavigation} tabIndex={-1} aria-label="文档版本导航"><p>请先选择已保存文档，再查看它的历史版本。</p></div> : null}
        {document ? <>
          {document.source_id ? <section className="original-derived-split" aria-label="原件与派生文档并排阅读" style={{"--derived-focus":1} as CSSProperties}>
            <article className="original-derived-pane" aria-label="不可变原件">
              <header><h4>不可变原件</h4><p>{linkedOriginal ? "原件身份、版本与字节指纹已核对。" : "关联原件尚未核对或当前未提供，不以其他原件替代。"}</p></header>
              {linkedOriginal && documentBytes && documentOriginal && documentSource ? <>
                <dl className="original-derived-identity"><div><dt>来源 ID</dt><dd>{documentSource.source_id}</dd></div><div><dt>来源版本</dt><dd>{documentSource.source_revision}</dd></div><div><dt>原件 SHA-256</dt><dd>{documentOriginal.sha256}</dd></div></dl>
                 {linkedPdf ? <Suspense fallback={<p role="status">正在载入 PDF 阅读器…</p>}><PdfReader bytes={documentBytes} page={page} onPageChange={setPage} focusRequest={focusRequest} /></Suspense> : documentOriginal.media_type.startsWith("text/") ? <pre tabIndex={0} aria-label="并排原件正文">{new TextDecoder().decode(documentBytes)}</pre> : documentOriginal.media_type.startsWith("image/") ? <img className="original-derived-image" src={`data:${documentOriginal.media_type};base64,${documentOriginal.content_base64}`} alt={`原件 ${documentSource.original_name}`} /> : documentOriginal.media_type.startsWith("audio/") || documentOriginal.media_type.startsWith("video/") ? <MediaReader key={`derived-media:${documentSource.source_id}`} bytes={documentBytes} mediaType={documentOriginal.media_type} seek={mediaSeek?.sourceId===documentSource.source_id?mediaSeek:undefined}/> : <p>此格式没有原生并排查看器；原件仍保存在 CAS，可从原件列表使用现有 Reader。</p>}
              </> : <p role="status">原件读取失败、身份不匹配或未绑定到此文档版本。正文指纹与原件指纹保持分开显示。</p>}
            </article>
            <article className="original-derived-pane" aria-label="派生文档与版本核验">
              <header><h4>派生文档</h4><p>文档版本 {document.version} · 正文 SHA-256 {document.content_sha256}</p></header>
               <Suspense fallback={<p role="status">正在载入文档编辑器…</p>}><DocumentEditor key={`${document.document_id}:${editorEpoch}`} content={document.editor_json as JSONContent} version={document.version} onSave={save} onDirtyChange={(value) => { dirty.current = value; setDocumentDirty(value); if(value)editGeneration.current+=1; onDirtyChange?.(value); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: value })); }} onCreateReference={source && original && bytes ? cite : undefined} onReferenceActivate={jump} /></Suspense>
              <CheckPanel key={`checks:${document.document_id}:${document.version}`} document={document} onRevisionBasis={value=>{revisionBasis.current=value;}} />
            </article>
          </section> : <>
           <Suspense fallback={<p role="status">正在载入文档编辑器…</p>}><DocumentEditor key={`${document.document_id}:${editorEpoch}`} content={document.editor_json as JSONContent} version={document.version} onSave={save} onDirtyChange={(value) => { dirty.current = value; setDocumentDirty(value); if(value)editGeneration.current+=1; onDirtyChange?.(value); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: value })); }} onCreateReference={source && original && bytes ? cite : undefined} onReferenceActivate={jump} /></Suspense>
          <CheckPanel key={`checks:${document.document_id}:${document.version}`} document={document} onRevisionBasis={value=>{revisionBasis.current=value;}} />
          </>}
          <div ref={versionNavigation} tabIndex={-1} aria-label="文档版本导航" className="draft-restore"><label>恢复历史版本 <input type="number" min="1" max={document.version} value={restoreVersion} onChange={(event) => setRestoreVersion(event.target.value)} /></label><button type="button" onClick={() => void readHistory()}>只读查看历史版本</button><button type="button" disabled={busy} onClick={() => void singleWrite(restore)}>读取并恢复版本</button></div>
          {historicalDocument?.document_id===document.document_id?<section aria-label="历史版本详情"><h4>历史版本 {historicalDocument.version}</h4><pre>{historicalDocument.text_projection}</pre>{historicalDocument.revision_basis?<RawReceiptButton label="历史修订依据" payload={historicalDocument.revision_basis} />:<p>此版本没有记录修订依据。</p>}<button type="button" onClick={()=>{historyGeneration.current+=1;setHistoricalDocument(null);}}>关闭历史详情</button></section>:null}
          <div><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("markdown"))}>Markdown 导出到产品资料目录</button><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("obsidian"))}>Obsidian 包导出到产品资料目录</button></div>
          {exportProof?<RawReceiptButton label="导出格式与损失回执" payload={exportProof} />:null}
        </> : null}
    {message ? <p role={failure ? "alert" : "status"}>{message}</p> : null}
    <BackupPanel />
  </Section>;
}
