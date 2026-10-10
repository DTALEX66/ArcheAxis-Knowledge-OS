import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import type { WorkingDraft, WorkingEditor, PendingOriginal } from "../presentation/coreWorkingState";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { lazy, Suspense, useEffect, useRef, useState, type CSSProperties } from "react";
import type { JSONContent } from "@tiptap/core";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import type { SourceDto, DocumentDto, DocumentSummaryDto, DocumentsListDto, OriginalDto, AnchorDto, DocumentExportDto, RevisionBasisDto } from "../api/generated/core-contract";
import { Section } from "../components/RealData";
import { MediaReader } from "../components/MediaReader";
import type { EpubPosition } from "../components/EpubParagraphs";
import { JobContent } from "../components/JobContent";
import { CheckPanel } from "../components/CheckPanel";
import { BackupPanel } from "../components/BackupPanel";
import { ContainerMemberChain } from "../components/ContainerMemberChain";
import { ContentDetectionPanel } from "../components/ContentDetectionPanel";
import { PdfPageRecognition } from "../components/PdfPageRecognition";
import { FolderIngest } from "../components/FolderIngest";
import { TemplateLauncher } from "../templates/TemplateWorkspace";
import "../components/content.css";
import type { InspectionTarget } from "../components/Inspector";
import type { ObjectTrailLevel } from "../components/NavTrail";
import { coreFailureReason } from "../presentation/labels";
import { confirmOriginalNote, prepareOriginalNote, OriginalNoteRefused, type OriginalNoteAttempt } from "../presentation/originalNoteWrite";

// PDF.js is a large renderer and is needed only when the selected original is a PDF.
const PdfReader = lazy(() => import("../components/PdfReader").then(module => ({ default: module.PdfReader })));
// Tiptap/ProseMirror are needed only after a versioned document is selected.
const DocumentEditor = lazy(() => import("../components/DocumentEditor").then(module => ({ default: module.DocumentEditor })));

import type { SourceJourneyTarget, CandidateJourneyTarget } from "../presentation/sourceJourney";

export function CanonicalLibrarySpace({initialSourceTarget,purpose,onOpenDocument,onOpenImport,onKnowledge,initialDocumentId,onDirtyChange,onInspect,onOpenCapability,navigation,onTrail}:{initialSourceTarget?:SourceJourneyTarget;purpose?:"library"|"reader"|"history";onOpenDocument?:(id:string)=>void;onOpenImport?:()=>void;onKnowledge?:(target?:CandidateJourneyTarget)=>void;initialDocumentId?:string;onDirtyChange?:(dirty:boolean)=>void;onInspect?:(target:InspectionTarget)=>void;onOpenCapability?:(id:string)=>void;navigation?:{section:string;sequence:number};onTrail?:(levels:readonly ObjectTrailLevel[])=>void}) {
  const workingContext=useOptionalCoreWorkingState();
  // Core working-state persistence belongs to the verified formal desktop host.
  // Browser presentation fixtures do not obtain a native persistence receipt.
  const working=window.__TAURI__?.core?.invoke?workingContext:null;
  const savedJournalPending=useRef(new Map<string,{sent:WorkingDraft;version:number}>());
  const [documentSearch,setDocumentSearch] = useState("");
  const [contentFilter,setContentFilter] = useState<"all"|"original"|"linked">("all");
  const [showSource,setShowSource] = useState(false);
  const [candidateEditing,setCandidateEditing]=useState(false);
  const [showVersions,setShowVersions] = useState(purpose === "history");
  const [sources, setSources] = useState<SourceDto[]>([]);
  const [libraryBootSettled,setLibraryBootSettled] = useState(false);
  const [sourcePage, setSourcePage] = useState(0);
  const [documents, setDocuments] = useState<DocumentSummaryDto[]>([]);
  const [nextDocumentCursor, setNextDocumentCursor] = useState<string | null>(null);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const documentPageInFlight = useRef(false);
  const documentSnapshotCount = useRef<number | null>(null);
  const consumedDocumentCursors = useRef(new Set<string>());
  const libraryMounted = useRef(true);
  const [openedDocuments, setOpenedDocuments] = useState<DocumentSummaryDto[]>([]);
  const [source, setSource] = useState<SourceDto | null>(null);
  const [original, setOriginal] = useState<OriginalDto | null>(null);
  const [bytes, setBytes] = useState<Uint8Array | null>(null);
  const [documentSource, setDocumentSource] = useState<SourceDto | null>(null);
  const [documentOriginal, setDocumentOriginal] = useState<OriginalDto | null>(null);
  const [documentBytes, setDocumentBytes] = useState<Uint8Array | null>(null);
  const [document, setDocument] = useState<DocumentDto | null>(null);
  const [documentDrafts, setDocumentDrafts] = useState<Record<string, {content:JSONContent;baseVersion:number}>>(()=>Object.fromEntries(Object.entries(working?.state.drafts??{}).map(([id,draft])=>[id,{content:structuredClone(draft.editor_json),baseVersion:draft.base_version}])));
  const documentDraftsRef = useRef(documentDrafts);
  documentDraftsRef.current = documentDrafts;
  const dirtyDocumentIds = useRef(new Set<string>(Object.keys(working?.state.drafts??{})));
  const noteAttempt=useRef<OriginalNoteAttempt|null>(null);
  const [noteUncertain,setNoteUncertain]=useState(false);
  const [anchors, setAnchors] = useState<AnchorDto[]>([]);
  const [page, setPage] = useState(1);
  const [focusRequest, setFocusRequest] = useState(0);
  const [epubSeek,setEpubSeek]=useState<{sourceId:string;position:EpubPosition}|undefined>();
  const [mediaSeek,setMediaSeek]=useState<{sourceId:string;milliseconds:number;sequence:number}|undefined>();
  const [mediaDuration,setMediaDuration]=useState<{sourceId:string;seconds:number}|undefined>();
  const [restoreVersion, setRestoreVersion] = useState("1");
  const [historicalDocument, setHistoricalDocument] = useState<DocumentDto | null>(null);
  const historyGeneration = useRef(0);
  const currentDocument = useRef(document);
  currentDocument.current = document;
  const [editorEpoch, setEditorEpoch] = useState(0);
  const [message, setMessage] = useState("正在读取资料…");
  const [failure, setFailure] = useState(false);
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [importReceipt,setImportReceipt]=useState<{name:string;bytes:number;state:string}|null>(null);
  const [exportProof, setExportProof] = useState<DocumentExportDto | null>(null);
  const revisionBasis = useRef<RevisionBasisDto | null>(null);
  const dirty = useRef(false);
  const writeInFlight = useRef(false);
  const [busy, setBusy] = useState(false);
  const editGeneration = useRef(0);
  const generation = useRef(0);
  const textRegion = useRef<HTMLPreElement>(null);
  const sourceNavigation = useRef<HTMLElement>(null);
  const documentNavigation = useRef<HTMLElement>(null);
  const anchorNavigation = useRef<HTMLElement>(null);
  const versionNavigation = useRef<HTMLDivElement>(null);
  function publishDirtyState() {
    dirty.current = dirtyDocumentIds.current.size > 0 || noteAttempt.current !== null;
    onDirtyChange?.(dirty.current);
    window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: dirty.current }));
  }
  function reportEditorDirty(id:string, value:boolean) {
    if(value) dirtyDocumentIds.current.add(id); else dirtyDocumentIds.current.delete(id);
    if(value) editGeneration.current += 1;
    if(!value) setDocumentDrafts(previous => { const next={...previous}; delete next[id]; return next; });
    publishDirtyState();
  }
  function rememberDraft(id:string, content:JSONContent, baseVersion:number) {
    const next={...documentDraftsRef.current,[id]:{content:structuredClone(content),baseVersion}};
    documentDraftsRef.current=next;setDocumentDrafts(next);
    working?.session.rememberDraft(id,content as WorkingEditor,baseVersion);
  }
  useEffect(()=>{
    if(!working)return;
    let alive=true;
    const pending=working.state.pending_original;
    if(pending&&!noteAttempt.current){setNoteUncertain(true);void documentRequestIdentity(pending.create_request_id).then(id=>{if(alive&&!noteAttempt.current){noteAttempt.current={id,body:structuredClone(pending)};publishDirtyState();}});}
    for(const [id,draft] of Object.entries(working.state.drafts)) {
      dirtyDocumentIds.current.add(id);
      if(!documentDraftsRef.current[id]) {
        const next={...documentDraftsRef.current,[id]:{content:structuredClone(draft.editor_json),baseVersion:draft.base_version}};
        documentDraftsRef.current=next;setDocumentDrafts(next);
      }
    }
    if(working.status==="ready"&&!working.state.pending_original&&noteAttempt.current){noteAttempt.current=null;setNoteUncertain(false);}
    publishDirtyState();
    return()=>{alive=false;};
  },[working?.state,working?.status,working?.session]);
  useEffect(()=>{
    if(!working||!libraryBootSettled)return;
    let alive=true;
    void Promise.all(working.state.opened_documents.map(id=>coreCommand<DocumentDto>("document_get",{document_id:id}))).then(items=>{if(alive)setOpenedDocuments(previous=>[...previous,...items.filter(item=>!previous.some(row=>row.document_id===item.document_id))]);}).catch(()=>{if(alive){setMessage("已打开文档现场读取未完成；草稿仍保留。");setFailure(true);}});
    return()=>{alive=false;};
  },[libraryBootSettled,working?.session]);
  useEffect(() => {
    if (!navigation?.sequence) return;
    const regions: Record<string, { current: HTMLElement | null } | undefined> = {
      sources: sourceNavigation, documents: documentNavigation, anchors: anchorNavigation, versions: versionNavigation,
    };
    const target = regions[navigation.section]?.current;
    target?.scrollIntoView?.({ block: "nearest", behavior: "auto" });
    target?.focus();
  }, [navigation?.section, navigation?.sequence, source?.source_id, document?.document_id]);
  useEffect(() => {
    const levels: ObjectTrailLevel[] = [];
    if (source) {
      levels.push(
        { id: "section:sources", label: "来源原件", region: "sources" },
        { id: `source:${source.source_id}`, label: source.original_name, detail: `${source.source_id}@${source.source_revision}${document ? ` · 文档 v${document.version}` : ""}`, region: "sources" },
      );
    } else if (document) {
      levels.push(
        { id: "section:documents", label: "已保存文档", region: "documents" },
        { id: `document:${document.document_id}`, label: document.title, detail: `${document.document_id} · v${document.version}`, region: "documents" },
      );
    }
    if (document && historicalDocument?.document_id === document.document_id) {
      levels.push({ id: `version:${historicalDocument.version}`, label: `历史版本 v${historicalDocument.version}`, detail: historicalDocument.content_sha256, region: "versions" });
    }
    onTrail?.(levels);
  }, [source, document, historicalDocument, onTrail]);
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
    libraryMounted.current = true;
    Promise.all([
      coreCommand<{ sources: SourceDto[] }>("sources_list"),
      coreCommand<DocumentsListDto>("documents_list"),
    ]).then(([sourcesResult, docsResult]) => {
      if (!alive) return;
      setSources(sourcesResult.sources); setDocuments(docsResult.documents); if(generation.current === 0) setMessage("");
      setNextDocumentCursor(docsResult.next_cursor ?? null);
      documentSnapshotCount.current = docsResult.snapshot_count ?? null;
      consumedDocumentCursors.current.clear();
    }).catch((error: unknown) => { if (alive) { setMessage("资料暂时无法读取，请检查本地核心。"); setFailureReason(coreFailureReason(error)); setFailure(true); } }).finally(()=>{if(alive)setLibraryBootSettled(true);});
    return () => { alive = false; libraryMounted.current = false; generation.current += 1; onDirtyChange?.(false); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: false })); };
  }, []);
  async function loadMoreDocuments() {
    if (!nextDocumentCursor || documentPageInFlight.current) return;
    const cursor = nextDocumentCursor;
    documentPageInFlight.current = true;
    setLoadingDocuments(true);
    try {
      const result = await coreCommand<DocumentsListDto>("documents_list", { cursor });
      if (!libraryMounted.current) return;
      if (result.snapshot_count !== documentSnapshotCount.current || result.next_cursor === cursor
        || (result.next_cursor && consumedDocumentCursors.current.has(result.next_cursor))) {
        throw new Error("document pagination snapshot is incompatible");
      }
      consumedDocumentCursors.current.add(cursor);
      setDocuments(previous => {
        const existing = new Set(previous.map(item => item.document_id));
        return [...previous, ...result.documents.filter(item => !existing.has(item.document_id))];
      });
      setNextDocumentCursor(result.next_cursor);
      setMessage(""); setFailure(false); setFailureReason(null);
    } catch (error) {
      if (libraryMounted.current) {
        setMessage("更多文档读取失败；已加载文档与草稿仍保留，可重试。");
        setFailure(true); setFailureReason(coreFailureReason(error));
      }
    } finally {
      documentPageInFlight.current = false;
      if (libraryMounted.current) setLoadingDocuments(false);
    }
  }
  useEffect(()=>{if(initialDocumentId && !initialSourceTarget && libraryBootSettled)void openDocument(initialDocumentId);},[initialDocumentId,initialSourceTarget,libraryBootSettled]);
  useEffect(()=>{if(!initialSourceTarget||!libraryBootSettled)return;setCandidateEditing(false);const matches=sources.filter(s=>s.source_id===initialSourceTarget.source_id&&s.source_revision===initialSourceTarget.source_revision&&s.sha256===initialSourceTarget.sha256);if(matches.length!==1){setFailure(true);setMessage("所选原件版本未唯一核对；不会切换为同名或新版原件。");return;}setShowSource(true);void open(matches[0]);},[initialSourceTarget,libraryBootSettled]);
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
      const linked = documents.find((item) => item.source_id === selected.source_id && item.source_revision === selected.source_revision);
      readStage="草稿版本读取";
      const active = linked ? await coreCommand<DocumentDto>("document_get", { document_id: linked.document_id }) : null;
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return;
      if(active&&(active.document_id!==linked!.document_id||active.source_id!==selected.source_id||active.source_revision!==selected.source_revision))throw new Error("linked document identity mismatch");
      setSource(selected); setOriginal(asset); setBytes(decoded); setDocument(active); setAnchors(evidence.anchors);
      setDocumentSource(active ? selected : null); setDocumentOriginal(active ? asset : null); setDocumentBytes(active ? decoded : null);
      if (active) setOpenedDocuments(previous => previous.some(item => item.document_id === active.document_id) ? previous : [...previous, active]);
      setExportProof(null); setFailureReason(null);
      setEditorEpoch((value) => value + 1); setPage(1); setMessage("原件哈希已核对；草稿与原件独立保存。");
      publishDirtyState();
    } catch (error) { if (epoch === generation.current) { setFailure(true); setMessage(`${readStage}未完成；未替换当前内容，请保留原件重试。`); setFailureReason(coreFailureReason(error)); } }
  }
  async function openDocument(id: string) {
    if (currentDocument.current?.document_id === id) return;
    revisionBasis.current = null;
    const epoch = ++generation.current;
    const editingEpoch=editGeneration.current;
    try {
      const active = await coreCommand<DocumentDto>("document_get", { document_id: id });
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return;
      working?.session.rememberScene("03",active.document_id);
      setDocument(active); setSource(null); setOriginal(null); setBytes(null); setAnchors([]);
      setDocumentSource(null); setDocumentOriginal(null); setDocumentBytes(null);
      setOpenedDocuments(previous => previous.some(item => item.document_id === active.document_id) ? previous.map(item => item.document_id === active.document_id ? active : item) : [...previous, active]);
      setEditorEpoch(value => value + 1); setExportProof(null);
      setMessage("文档已读取；保存不要求来源引用或审核。"); setFailure(false);
      publishDirtyState();
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
  async function createOriginal(readOnly=false) {
    const epoch=++generation.current;
    const editingEpoch=editGeneration.current;
    try {
      if(!noteAttempt.current)noteAttempt.current=await prepareOriginalNote();
      setNoteUncertain(true);publishDirtyState();
      const attempt=noteAttempt.current;
      await working?.session.stageOriginal(attempt.body as PendingOriginal);
      const created = await confirmOriginalNote(attempt,readOnly);
      await working?.session.finishOriginal(attempt.body as PendingOriginal);
      noteAttempt.current=null;setNoteUncertain(false);publishDirtyState();
      if(!libraryMounted.current)return;
      setDocuments(previous=>[created,...previous.filter(row=>row.document_id!==created.document_id)]);
      setOpenedDocuments(previous => [created,...previous.filter(row=>row.document_id!==created.document_id)]);
      if(epoch!==generation.current||editingEpoch!==editGeneration.current){setMessage("原创笔记已建立，当前编辑内容仍保留；可从已保存文档打开新笔记。");return;}
      revisionBasis.current = null;
      setDocument(created);
      setSource(null); setOriginal(null); setBytes(null); setAnchors([]); setExportProof(null); setDocumentSource(null); setDocumentOriginal(null); setDocumentBytes(null);
      setEditorEpoch(value => value + 1); setMessage("原创笔记已建立。"); setFailure(false);
      publishDirtyState();
      if(purpose === "library") onOpenDocument?.(created.document_id);
    } catch(error) {
      if(!libraryMounted.current)return;
      if(error instanceof OriginalNoteRefused) {
        try{if(noteAttempt.current)await working?.session.finishOriginal(noteAttempt.current.body as PendingOriginal);}
        catch{setMessage("创建已明确拒绝；冻结请求清理尚未确认，请先核对工作状态。");setFailure(true);return;}
        noteAttempt.current=null;setNoteUncertain(false);publishDirtyState();
        setMessage("原创笔记创建被明确拒绝；现有草稿保留，修正条件后可重新创建。");
      } else {
        setNoteUncertain(noteAttempt.current!==null);
        setMessage("原创笔记建立未确认；冻结请求保留，请重试同一请求或核对结果，不会另建笔记。");
      }
      setFailure(true);
    }
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
    const requestedDocumentId = document.document_id;
    const sentBasis = revisionBasis.current;
    const sent:WorkingDraft={base_version:expectedVersion,editor_json:structuredClone(content) as WorkingEditor};
    if(working){working.session.rememberDraft(requestedDocumentId,sent.editor_json,expectedVersion);await working.session.flush();}
    const saved = await coreCommand<DocumentDto>("document_draft", { document_id: requestedDocumentId, body: { expected_version: expectedVersion, editor_json: content, ...(sentBasis ? {revision_basis:sentBasis} : {}) } });
    if (saved.document_id !== requestedDocumentId || saved.version!==expectedVersion+1) throw new Error("document identity or version mismatch");
    if (revisionBasis.current === sentBasis && currentDocument.current?.document_id === requestedDocumentId) revisionBasis.current = null;
    if(currentDocument.current?.document_id===saved.document_id) setDocument(saved);
    setDocuments((previous) => previous.map((item) => item.document_id === saved.document_id ? saved : item));
    setOpenedDocuments((previous) => previous.map((item) => item.document_id === saved.document_id ? saved : item));
    // Document ACK is already known. Journal failures must not rewind it or
    // send the same body again just to obtain a working-state cleanup receipt.
    let workingStateConfirmed=true;
    try {
      const cleared=working?await working.session.clearSaved(requestedDocumentId,sent,saved.version):true;
      const draft=documentDraftsRef.current[requestedDocumentId];
      if(draft&&JSON.stringify(draft.content)===JSON.stringify(content)&&cleared)reportEditorDirty(requestedDocumentId,false);
      else if(draft&&JSON.stringify(draft.content)!==JSON.stringify(content)) {
        rememberDraft(requestedDocumentId,draft.content,saved.version);
        if(working)await working.session.flush();
      } else if(!cleared)workingStateConfirmed=false;
    }catch {
      workingStateConfirmed=false;
      savedJournalPending.current.set(requestedDocumentId,{sent,version:saved.version});
      setMessage("正文版本已保存；工作草稿清理未确认，输入保留。请仅核对或重试工作状态，不要重复保存同一正文。");setFailure(true);
    }
    return { content: saved.editor_json as JSONContent, version: saved.version, workingStateConfirmed };
  }
  async function retrySavedJournal(id:string):Promise<boolean> {
    if(!working)return true;
    await working.session.load();
    const pending=savedJournalPending.current.get(id);
    const draft=working.session.getSnapshot().state.drafts[id];
    if(!draft){savedJournalPending.current.delete(id);reportEditorDirty(id,false);return true;}
    if(pending&&JSON.stringify(draft)===JSON.stringify(pending.sent)) {
      const cleared=await working.session.clearSaved(id,pending.sent,pending.version);
      if(cleared){savedJournalPending.current.delete(id);reportEditorDirty(id,false);return true;}
    }
    // Later editing is an independent draft based on the already confirmed
    // document version. Flush only the journal; never write document_draft here.
    await working.session.flush();return false;
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
    if (dirtyDocumentIds.current.has(document.document_id)) { setMessage("恢复操作暂停：请先保存当前文档，再读取历史版本并恢复。"); return; }
    try {
      // Read the specific immutable version before requesting a new restored revision.
      await coreCommand<DocumentDto>("document_version", { document_id: document.document_id, version: previous });
      const restored = await coreCommand<DocumentDto>("document_restore", { document_id: document.document_id, body: { expected_version: document.version, restore_version: previous } });
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return;
      setDocument(restored); setEditorEpoch((value) => value + 1); reportEditorDirty(restored.document_id,false);
      setOpenedDocuments(previous => previous.map(item => item.document_id === restored.document_id ? restored : item));
      setDocumentSource(source); setDocumentOriginal(original); setDocumentBytes(bytes);
      setMessage(`已从版本 ${previous} 恢复为新版本 ${restored.version}。`); setFailure(false);
    } catch (error) { if (epoch === generation.current && editingEpoch === editGeneration.current) { setMessage("恢复失败或版本已变化；当前草稿仍保留。"); setFailureReason(coreFailureReason(error)); setFailure(true); } }
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
  async function jump(attributes: Record<string, unknown>) {
    if (!source || attributes.source_id !== source.source_id || attributes.source_revision !== source.source_revision) { setMessage("此引用绑定另一来源版本，请打开对应原件。不会自动迁移定位。"); return; }
    if (typeof attributes.anchor_id !== "string" || typeof attributes.position !== "string") { setMessage("引用缺少可核验身份，保留记录并待重新定位。"); return; }
    const epoch = generation.current;
    let location: Record<string, unknown>;
    try {
      const proof = await coreCommand<import("../api/generated/core-contract").AnchorResolutionDto>("anchor_resolve", {source_id:source.source_id,anchor_id:attributes.anchor_id});
      if (epoch !== generation.current) return;
      if (proof.source_id !== source.source_id || proof.anchor_id !== attributes.anchor_id || proof.scope !== "locator_provenance_only"
        || proof.status !== "CURRENT" || proof.source_revision !== source.source_revision || proof.current_source_revision !== source.source_revision || proof.position !== attributes.position) {
        setMessage("引用定位未通过当前核验，保留来源记录并待重新定位。不会自动迁移定位。"); return;
      }
      const stored:unknown = JSON.parse(proof.position);
      if (!stored || typeof stored !== "object" || Array.isArray(stored)) throw new Error("invalid locator");
      location = stored as Record<string,unknown>;
    } catch { if (epoch === generation.current) setMessage("引用核验未完成，请保留来源记录后重试。"); return; }
    const pdfPage = location.type === "pdf_line" && Array.isArray(location.path) && typeof location.path[0] === "string" && /^page-[1-9][0-9]*$/.test(location.path[0]) ? Number(location.path[0].slice(5)) : location.page;
    if (Number.isSafeInteger(pdfPage) && (pdfPage as number) > 0) { setPage(pdfPage as number); setFocusRequest((value) => value + 1); }
    else {
      textRegion.current?.focus();
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
    if (dirtyDocumentIds.current.has(id) && !window.confirm(working?"此文档有未保存更改。关闭标签后独立工作草稿仍保留，确定关闭吗？":"此文档有未保存更改。关闭标签将丢弃仅保存在内存中的草稿，确定关闭吗？")) return;
    if(dirtyDocumentIds.current.has(id)&&!working) reportEditorDirty(id,false);
    const remaining = openedDocuments.filter(item => item.document_id !== id);
    setOpenedDocuments(remaining);
    working?.session.change(state=>{state.opened_documents=state.opened_documents.filter(value=>value!==id);if(state.active_document===id)state.active_document=remaining[0]?.document_id??null;});
    if (currentDocument.current?.document_id === id) {
      setDocument(null); setHistoricalDocument(null); setSource(null); setOriginal(null); setBytes(null); setAnchors([]); setDocumentSource(null); setDocumentOriginal(null); setDocumentBytes(null);
      publishDirtyState();
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
  // Chunk-load placeholder, deliberately not a live region: the page's own outcome region below already
  // announces "正在读取资料…" / "正在读取原件与文档…", so a second placeholder region would make one
  // page read announce several times. The text stays where the editor appears.
  const documentEditor = document ? <Suspense fallback={<p>正在载入文档编辑器…</p>}><DocumentEditor key={`${document.document_id}:${editorEpoch}`} content={documentDrafts[document.document_id]?.content ?? document.editor_json as JSONContent} version={documentDrafts[document.document_id]?.baseVersion ?? document.version} onSave={save} onRetryWorkingState={()=>retrySavedJournal(document.document_id)} onDirtyChange={value=>reportEditorDirty(document.document_id,value)} onDraftChange={(content,baseVersion)=>rememberDraft(document.document_id,content,baseVersion)} onCreateReference={source && original && bytes ? cite : undefined} onReferenceActivate={jump} /></Suspense> : null;

  const originalPane = document ? <article className="original-derived-pane" aria-label="不可变原件">
              <header><h4>不可变原件</h4><p>{linkedOriginal ? "原件身份、版本与字节指纹已核对。" : "关联原件尚未核对或当前未提供，不以其他原件替代。"}</p></header>
              {linkedOriginal && documentBytes && documentOriginal && documentSource ? <>
                <dl className="original-derived-identity"><div><dt>来源 ID</dt><dd>{documentSource.source_id}</dd></div><div><dt>来源版本</dt><dd>{documentSource.source_revision}</dd></div><div><dt>原件 SHA-256</dt><dd>{documentOriginal.sha256}</dd></div></dl>
                 {linkedPdf ? <Suspense fallback={<p>正在载入 PDF 阅读器…</p>}><PdfReader bytes={documentBytes} page={page} onPageChange={setPage} focusRequest={focusRequest} /></Suspense> : documentOriginal.media_type.startsWith("text/") ? <pre ref={purpose === "reader" ? textRegion : undefined} tabIndex={0} aria-label="并排原件正文">{new TextDecoder().decode(documentBytes)}</pre> : documentOriginal.media_type.startsWith("image/") ? <img className="original-derived-image" src={`data:${documentOriginal.media_type};base64,${documentOriginal.content_base64}`} alt={`原件 ${documentSource.original_name}`} /> : documentOriginal.media_type.startsWith("audio/") || documentOriginal.media_type.startsWith("video/") ? <MediaReader key={`derived-media:${documentSource.source_id}`} bytes={documentBytes} mediaType={documentOriginal.media_type} seek={mediaSeek?.sourceId===documentSource.source_id?mediaSeek:undefined}/> : <p>此格式没有原生并排查看器；原件仍保存在 CAS，可从原件列表使用现有 Reader。</p>}
              </> : <p>原件读取失败、身份不匹配或未绑定到此文档版本。正文指纹与原件指纹保持分开显示。</p>}
            </article> : null;
  const versionControls = document ? <><div ref={versionNavigation} tabIndex={-1} data-section="versions" aria-label="文档版本导航" className="draft-restore"><label>恢复历史版本 <input type="number" min="1" max={document.version} value={restoreVersion} onChange={(event) => setRestoreVersion(event.target.value)} /></label><button type="button" onClick={() => void readHistory()}>只读查看历史版本</button><button type="button" disabled={busy} onClick={() => void singleWrite(restore)}>读取并恢复版本</button></div>
          {historicalDocument?.document_id===document.document_id?<section aria-label="历史版本详情"><h4>历史版本 {historicalDocument.version}</h4><pre>{historicalDocument.text_projection}</pre>{historicalDocument.revision_basis?<RawReceiptButton label="历史修订依据" payload={historicalDocument.revision_basis} />:<p>此版本没有记录修订依据。</p>}<button type="button" onClick={()=>{historyGeneration.current+=1;setHistoricalDocument(null);}}>关闭历史详情</button></section>:null}</> : null;
  const feedback = <>{noteUncertain?<div aria-label="待确认的笔记创建"><p>冻结笔记请求已保留；先核对工作状态，再重试同一请求。</p><button disabled={busy} onClick={()=>void singleWrite(createOriginal)}>重试同一笔记请求</button><button disabled={busy} onClick={()=>void singleWrite(()=>createOriginal(true))}>核对笔记创建结果</button></div>:null}{message ? <p role={failure ? "alert" : "status"}>{message}</p> : null}{failureReason ? <p className="state-reason">{failureReason}</p> : null}</>;
  const filteredDocuments = documents.filter(item => {
    if(contentFilter === "original" && item.source_id) return false;
    if(contentFilter === "linked" && !item.source_id) return false;
    const sourceName=sources.find(value=>value.source_id === item.source_id)?.original_name ?? "";
    return `${item.title} ${sourceName}`.toLocaleLowerCase().includes(documentSearch.trim().toLocaleLowerCase());
  });
  function selectForReading(id:string) {
    if(onOpenDocument) onOpenDocument(id); else void openDocument(id);
  }
  const documentList = <>
    <nav ref={documentNavigation} tabIndex={-1} data-section="documents" aria-label="已保存文档" className="ui-document-list">
      <table><thead><tr><th>名称</th><th>内容身份</th><th>版本</th><th>操作</th></tr></thead><tbody>
        {filteredDocuments.map(item=><tr key={item.document_id}><td><strong>{item.title}</strong>{item.source_id ? <small>{sources.find(value=>value.source_id===item.source_id)?.original_name ?? "已绑定来源"}</small> : null}</td><td>{item.source_id ? "关联原件文档" : "原创笔记"}</td><td>v{item.version}</td><td><button type="button" onClick={()=>selectForReading(item.document_id)} aria-label={`打开文档 ${item.title}`}>打开</button></td></tr>)}
      </tbody></table>
      {!failure && !message && filteredDocuments.length===0 ? <p>{documents.length ? "已加载内容中没有匹配文档。" : "暂无已保存文档，可以新建原创笔记。"}</p> : null}
    </nav>
    {nextDocumentCursor ? <button type="button" disabled={loadingDocuments} onClick={()=>void loadMoreDocuments()}>{loadingDocuments ? "正在加载文档…" : "加载更多文档"}</button> : null}
  </>;
  if(purpose === "library") return <section className="ui-library-page" aria-label="知识库文档视图">
    <div className="ui-content-tabs" role="group" aria-label="内容筛选">
      <button type="button" aria-pressed={contentFilter==="all"} onClick={()=>setContentFilter("all")}>全部内容</button>
      <button type="button" aria-pressed={contentFilter==="original"} onClick={()=>setContentFilter("original")}>原创笔记</button>
      <button type="button" aria-pressed={contentFilter==="linked"} onClick={()=>setContentFilter("linked")}>关联原件</button>
    </div>
    <div className="ui-library-toolbar"><input type="search" aria-label="筛选已加载文档标题与来源" placeholder="搜索标题、来源…" value={documentSearch} onChange={event=>setDocumentSearch(event.target.value)}/><button type="button" onClick={onOpenImport} disabled={!onOpenImport}>导入原件</button><button className="ui-primary-action" type="button" disabled={busy||noteUncertain} onClick={()=>void singleWrite(createOriginal)}>新建笔记</button></div>
    <div className="ui-content-main-side"><section className="ui-content-panel"><header><h3>已保存内容</h3><p>标题与来源筛选覆盖已加载文档；可继续加载同一快照。</p></header>{documentList}</section>
      <aside className="ui-content-panel" aria-label="内容与视图"><h3>内容与视图</h3><p>笔记与关联原件共用文档版本。打开实际文档后阅读与编辑。</p><p>普通笔记无需依据即可保存；依据分析与用户采用分别记录。</p><h4>集合与视图</h4><p>集合、标签和其他视图尚未接通。</p><button type="button" onClick={()=>onOpenCapability?.("CAP-0020")} disabled={!onOpenCapability}>查看集合能力详情</button></aside>
    </div>{feedback}
  </section>;
  if(purpose === "reader" || purpose === "history") return <section className="ui-reader-page" aria-label={purpose==="history" ? "文档版本视图" : "阅读与编辑文档视图"}>
    {purpose==="reader"&&source&&original&&bytes?<section aria-label="同源知识整理"><h3>来源 {source.original_name}</h3><p>{source.source_id} · {source.source_revision}</p>{!document?<><pre ref={textRegion} tabIndex={0} aria-label="并排原件正文">{original.media_type.startsWith("text/")?new TextDecoder().decode(bytes):"原字节已核对；派生正文从真实转换作业读取。"}</pre><button disabled={busy} onClick={()=>void singleWrite(create)}>建立版本化草稿</button></>:null}<button aria-pressed={candidateEditing} onClick={()=>setCandidateEditing(true)}>整理此来源为知识候选</button>{candidateEditing?<JobContent key={`journey:${source.source_id}:${source.source_revision}`} sourceId={source.source_id} sourceRevision={source.source_revision} name={source.original_name} pinnedJobId={initialSourceTarget?.job_id} onKnowledge={onKnowledge} onDirtyChange={value=>{if(value)dirtyDocumentIds.current.add("source-candidate");else dirtyDocumentIds.current.delete("source-candidate");publishDirtyState();}} onAnchor={anchor=>setAnchors(previous=>[...previous.filter(a=>a.anchor_id!==anchor.anchor_id),anchor])}/>:null}</section>:null}
    {document ? <>
      <div className="ui-reader-toolbar"><div className="ui-content-tabs" role="group" aria-label="阅读辅助视图"><button type="button" aria-pressed={!showSource&&!showVersions} onClick={()=>{setShowSource(false);setShowVersions(false);}}>正文</button><button type="button" aria-pressed={showSource} onClick={()=>setShowSource(value=>!value)}>原件</button><button type="button" aria-pressed={showVersions||purpose==="history"} onClick={()=>setShowVersions(value=>!value)}>版本</button></div></div>
      <div className="ui-reader-layout"><article className="ui-reader-document" aria-label="文档正文与编辑"><header><p className="ui-document-meta">{document.source_id ? "关联原件文档" : "原创笔记"} · v{document.version} · 无需依据即可保存</p><h2>{document.title}</h2></header>{purpose!=="history" ? documentEditor : <p>{document.text_projection}</p>}
        {showSource ? <section className="ui-reader-original" aria-label="关联原件阅读">{document.source_id ? originalPane : <p>此原创笔记没有绑定来源原件。</p>}</section> : null}
      </article><aside className="ui-content-panel ui-reader-details" aria-label="内容详情"><h3>内容详情</h3><dl><div><dt>内容身份</dt><dd>{document.source_id ? "关联原件文档" : "原创笔记"}</dd></div><div><dt>文档版本</dt><dd>v{document.version}{dirtyDocumentIds.current.has(document.document_id) ? " · 未保存更改" : ""}</dd></div><div><dt>来源版本</dt><dd>{document.source_id ? linkedOriginal ? "原件身份、版本与字节已核对" : "已绑定；原件读取尚未核对" : "未绑定；保存不要求来源"}</dd></div></dl>
        <RawReceiptButton label="文档身份与来源指纹" payload={{document_id:document.document_id,source_id:document.source_id,source_revision:document.source_revision,content_sha256:document.content_sha256}}/>
        <details><summary>依据与修订记录</summary><CheckPanel key={`checks:${document.document_id}:${document.version}`} document={document} onRevisionBasis={value=>{revisionBasis.current=value;}}/></details>
        {showVersions||purpose==="history" ? <section aria-label="版本与影响">{versionControls}</section> : <button type="button" onClick={()=>setShowVersions(true)}>查看历史版本</button>}
        <details><summary>导出已保存文档</summary><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("markdown"))}>Markdown 导出到产品资料目录</button><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("obsidian"))}>Obsidian 包导出到产品资料目录</button>{exportProof?<RawReceiptButton label="导出格式与损失回执" payload={exportProof}/>:null}</details>
      </aside></div>
    </> : <section className="ui-content-panel"><h3>选择已保存文档</h3><p>从实际文档进入阅读，保留其来源与版本。</p>{documentList}</section>}
    {feedback}
  </section>;

  return <Section title="资料库">
    <TemplateLauncher onOpen={id=>void openDocument(id)} onOpenCapability={onOpenCapability} onDirtyChange={value=>{if(value)dirtyDocumentIds.current.add("template-properties");else dirtyDocumentIds.current.delete("template-properties");publishDirtyState();}} />
    <p className="muted">原件保留其不可变版本；草稿自动保存到本地核心，引用绑定原件版本。</p>
    <label className="content-import" data-section="import" tabIndex={-1}>导入原件 <input type="file" aria-label="导入原件" disabled={importing} onChange={(event) => { const file = event.target.files?.[0]; if (file) void importFile(file); event.target.value = ""; }} /></label>
    {importReceipt?<dl className="receipt-grid" aria-label="导入回执"><div><dt>来源文件</dt><dd>{importReceipt.name}</dd></div><div><dt>原件大小</dt><dd>{importReceipt.bytes} 字节</dd></div><div><dt>导入状态</dt><dd>{importReceipt.state}</dd></div><div><dt>下一步</dt><dd>选择原件阅读或执行转换，再从实际引文整理待审核知识。</dd></div></dl>:null}
    <div className="space-section-region" data-section="folder" tabIndex={-1} aria-label="目录批量导入"><FolderIngest /></div>
    <div className="canonical-library">
      <nav ref={sourceNavigation} tabIndex={-1} className="canonical-sources" data-section="sources" aria-label="保留原件">
        {sources.length === 0 ? <p>暂无原件。</p> : sources.slice(sourcePage*30,(sourcePage+1)*30).map((item) => <button type="button" key={item.source_id} aria-current={source?.source_id === item.source_id ? "true" : undefined} onClick={() => void open(item)}>{item.original_name}</button>)}
        {sources.length>30?<div><button disabled={sourcePage===0} onClick={()=>setSourcePage(value=>value-1)}>上一组原件</button><span>{sourcePage+1} / {Math.ceil(sources.length/30)}</span><button disabled={(sourcePage+1)*30>=sources.length} onClick={()=>setSourcePage(value=>value+1)}>下一组原件</button></div>:null}
      </nav>
      {source && original && bytes ? <div className="canonical-content">
        <h4>{source.original_name}</h4>
        <div className="canonical-reading">
          <div>
          {isPdf ? <PdfReader bytes={bytes} page={page} onPageChange={setPage} focusRequest={focusRequest} /> : original.media_type.startsWith("text/") ? <pre ref={textRegion} tabIndex={-1} aria-label="原件正文">{new TextDecoder().decode(bytes)}</pre> : null}
          {original.media_type.startsWith("audio/")||original.media_type.startsWith("video/")?<MediaReader key={`media:${source.source_id}`} bytes={bytes} mediaType={original.media_type} seek={mediaSeek?.sourceId===source.source_id?mediaSeek:undefined} onDuration={seconds=>setMediaDuration({sourceId:source.source_id,seconds})}/>:null}
          <JobContent key={`job:${source.source_id}`} sourceId={source.source_id} name={source.original_name} sourceRevision={source.source_revision} epubSeek={epubSeek?.sourceId===source.source_id?epubSeek.position:undefined} onEpubSeek={position=>setEpubSeek({sourceId:source.source_id,position})} onKnowledge={onKnowledge} onTimeSeek={seconds=>setMediaSeek(previous=>({sourceId:source.source_id,milliseconds:seconds*1000,sequence:(previous?.sequence??0)+1}))} onAnchor={anchor=>setAnchors(previous=>previous.some(item=>item.anchor_id===anchor.anchor_id)?previous:[...previous,anchor])} mediaDurationSeconds={mediaDuration?.sourceId===source.source_id?mediaDuration.seconds:undefined}/>
          <ContainerMemberChain key={`members:${source.source_id}`} sourceId={source.source_id} />
          {original && original.media_type === "application/octet-stream" ? <ContentDetectionPanel key={`detect:${source.source_id}`} sourceId={source.source_id} name={source.original_name} /> : null}
          <PdfPageRecognition key={`pages:${source.source_id}`} sourceId={source.source_id} />
          </div>
          <aside ref={anchorNavigation} tabIndex={-1} data-section="anchors" aria-label="来源版本证据">
            <h4>来源与引用</h4>
            <p>引用绑定不可变原件版本，选择引用可回到已记录位置。</p>
            <details><summary>更多信息：来源链与内容指纹</summary><dl className="receipt-grid"><div><dt>来源</dt><dd>{source.original_name}</dd></div><div><dt>来源 ID</dt><dd>{source.source_id}</dd></div><div><dt>来源版本（原件指纹）</dt><dd>{source.source_revision}</dd></div><div><dt>原件 SHA-256</dt><dd>{original.sha256}</dd></div><div><dt>读取核验</dt><dd>原件字节与 Core 内容指纹已匹配</dd></div></dl></details>
            {anchors.length===0?<p className="muted">此来源尚无引用记录。</p>:null}
            {anchors.map((anchor) => { let location: Record<string, unknown> = {}; try { location = JSON.parse(anchor.position); } catch { /* Preserve unresolved position, never invent a locator. */ }
              return <div key={anchor.anchor_id}><button type="button" disabled={anchor.location_status === "revision_mismatch"} onClick={() => void jump({ anchor_id:anchor.anchor_id, position:anchor.position, source_id: anchor.source_id, source_revision: anchor.source_revision })}>{typeof location.page === "number" ? `第 ${location.page} 页` : "来源引用"}{anchor.location_status === "revision_mismatch" ? " · 需重新定位" : anchor.location_status !== "located" ? " · 定位未核实" : ""}</button><details><summary>引用来源记录</summary><dl className="receipt-grid"><div><dt>引用 ID</dt><dd>{anchor.anchor_id}</dd></div><div><dt>来源版本（原件指纹）</dt><dd>{anchor.source_revision}</dd></div><div><dt>记录位置</dt><dd>{anchor.position}</dd></div><div><dt>定位状态</dt><dd>{anchor.location_status === "located" ? "已核实" : anchor.location_status === "revision_mismatch" ? "版本不匹配，需重新定位" : "定位未核实"}</dd></div></dl></details></div>;
            })}
          </aside>
        </div>
        {!document ? <button type="button" disabled={busy} onClick={() => void singleWrite(create)}>建立版本化草稿</button> : null}
      </div> : <p className="muted">选择一个原件开始阅读。</p>}
    </div>
    {openedDocuments.length > 0 ? <nav className="document-tab-strip" role="tablist" aria-label="已打开文档标签">
      {openedDocuments.map(item => <div className="document-tab" key={item.document_id}>
        <button type="button" role="tab" aria-selected={document?.document_id === item.document_id} onClick={() => void openDocument(item.document_id)}>
          {item.title}<small>v{item.version}{dirtyDocumentIds.current.has(item.document_id) ? " · 未保存" : ""}</small>
        </button>
        <button type="button" aria-label={`关闭文档标签 ${item.title}`} disabled={busy} onClick={() => closeDocumentTab(item.document_id)}>×</button>
      </div>)}
    </nav> : null}
    <button type="button" disabled={busy||noteUncertain} onClick={() => void singleWrite(createOriginal)}>新建原创笔记</button>
    {noteUncertain?<div aria-label="待确认的笔记创建"><p>笔记创建结果尚未确认，原请求保留。</p><button disabled={busy} onClick={()=>void singleWrite(createOriginal)}>重试同一笔记请求</button><button disabled={busy} onClick={()=>void singleWrite(()=>createOriginal(true))}>核对笔记创建结果</button></div>:null}
    <nav ref={documentNavigation} tabIndex={-1} data-section="documents" aria-label="已保存文档">{documents.map(item => <button type="button" key={item.document_id} onClick={() => void openDocument(item.document_id)}>{item.title} · 文档</button>)}</nav>
    {nextDocumentCursor ? <button type="button" disabled={loadingDocuments} onClick={() => void loadMoreDocuments()}>{loadingDocuments ? "正在加载文档…" : "加载更多文档"}</button> : null}
    {!source && navigation?.section === "anchors" ? <section ref={anchorNavigation} tabIndex={-1} data-section="anchors" aria-label="来源版本证据"><p>请先选择实际来源原件；原创笔记可以没有来源锚点。</p></section> : null}
    {!document && navigation?.section === "versions" ? <div ref={versionNavigation} tabIndex={-1} data-section="versions" aria-label="文档版本导航"><p>请先选择已保存文档，再查看它的历史版本。</p></div> : null}
        {document ? <>
          {document.source_id ? <section className="original-derived-split" aria-label="原件与派生文档并排阅读" style={{"--derived-focus":1} as CSSProperties}>
            {originalPane}
            <article className="original-derived-pane" aria-label="派生文档与版本核验">
              <header><h4>派生文档</h4><p>文档版本 {document.version} · 正文 SHA-256 {document.content_sha256}</p></header>
               {documentEditor}
              <CheckPanel key={`checks:${document.document_id}:${document.version}`} document={document} onRevisionBasis={value=>{revisionBasis.current=value;}} />
            </article>
          </section> : <>
           {documentEditor}
          <CheckPanel key={`checks:${document.document_id}:${document.version}`} document={document} onRevisionBasis={value=>{revisionBasis.current=value;}} />
          </>}
          {versionControls}
          <div className="space-section-region" data-section="export" tabIndex={-1} aria-label="文档导出"><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("markdown"))}>Markdown 导出到产品资料目录</button><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("obsidian"))}>Obsidian 包导出到产品资料目录</button></div>
          {exportProof?<RawReceiptButton label="导出格式与损失回执" payload={exportProof} />:null}
        </> : null}
    {message ? <p role={failure ? "alert" : "status"}>{message}</p> : null}
    {failureReason ? <p className="state-reason">{failureReason}</p> : null}
    <BackupPanel hasUnsavedDrafts={dirty.current} />
  </Section>;
}
