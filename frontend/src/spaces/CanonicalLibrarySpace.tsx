import {MaterialQuestionPanel} from "../components/MaterialQuestionPanel";
import {ConversationPanel} from "../components/ConversationPanel";
import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import { useDocumentWriteLease } from "../workspace/documentSessions";
import { useDraftOwner } from "../workspace/draftProtection";
import { useDraftRecoverySource } from "../workspace/draftRecovery";
import type { WorkingDraft, WorkingEditor, PendingOriginal } from "../presentation/coreWorkingState";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { DocumentJournalError } from "../presentation/documentSaveStage";
import { confirmedImport } from "../presentation/importReceipt";
import { sha256 } from "../presentation/exchangeProof";
import { lazy, Suspense, useEffect, useId, useRef, useState, type CSSProperties } from "react";
import type { JSONContent } from "@tiptap/core";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import {TagNavigation,SavedDocumentMetadata,matchesTag} from "../components/DocumentTags";
import { DocumentEmbeds } from "../components/DocumentEmbeds";
import { DocumentBacklinks } from "../components/DocumentBacklinks";
import { CollectionPanel } from "../components/CollectionPanel";
import { DocumentSnapshot } from "../components/DocumentSnapshot";
import type { SourceDto, DocumentDto, DocumentSummaryDto, DocumentsListDto, OriginalDto, AnchorDto, DocumentExportDto, RevisionBasisDto } from "../api/generated/core-contract";
import { Section } from "../components/RealData";
import { MediaReader } from "../components/MediaReader";
import type { EpubPosition } from "../components/EpubParagraphs";
import { JobContent } from "../components/JobContent";
import { OriginalTextCitation } from "../components/OriginalTextCitation";
import {OcrImageReader,type OcrImageSeek} from "../components/OcrImageReader";
import { CheckPanel } from "../components/CheckPanel";
import { BackupPanel } from "../components/BackupPanel";
import { ContainerMemberChain } from "../components/ContainerMemberChain";
import { ContentDetectionPanel } from "../components/ContentDetectionPanel";
import { PdfPageRecognition } from "../components/PdfPageRecognition";
import { IngestRelationsPanel } from "../components/IngestRelationsPanel";
import {verifiedSource,type FolderMemberSelection} from "../presentation/ingestRelations";
import { FolderIngest } from "../components/FolderIngest";
import { TemplateLauncher } from "../templates/TemplateWorkspace";
import "../components/content.css";
import "./stitch-library.css";
import type { InspectionHandler } from "../components/Inspector";
import type { ObjectTrailLevel } from "../components/NavTrail";
import { coreFailureReason } from "../presentation/labels";
import { confirmOriginalNote, prepareOriginalNote, OriginalNoteRefused, type OriginalNoteAttempt } from "../presentation/originalNoteWrite";
import { XiaoqiPanel } from "../components/XiaoqiPanel";
import "../components/xiaoqi-trigger.css";

// PDF.js is a large renderer and is needed only when the selected original is a PDF.
const PdfReader = lazy(() => import("../components/PdfReader").then(module => ({ default: module.PdfReader })));
// Tiptap/ProseMirror are needed only after a versioned document is selected.
const DocumentEditor = lazy(() => import("../components/DocumentEditor").then(module => ({ default: module.DocumentEditor })));

import type { SourceJourneyTarget, CandidateJourneyTarget } from "../presentation/sourceJourney";

export function CanonicalLibrarySpace({activationRevision,initialSourceTarget,purpose,onOpenDocument,onOpenImport,onKnowledge,initialDocumentId,onDirtyChange,onInspect,onOpenCapability,navigation,onTrail,onOpenReference}:{activationRevision?:number;initialSourceTarget?:SourceJourneyTarget;purpose?:"library"|"reader"|"history";onOpenDocument?:(id:string)=>void;onOpenImport?:()=>void;onKnowledge?:(target?:CandidateJourneyTarget)=>void;initialDocumentId?:string;onDirtyChange?:(dirty:boolean)=>void;onInspect?:InspectionHandler;onOpenCapability?:(id:string)=>void;navigation?:{section:string;sequence:number};onTrail?:(levels:readonly ObjectTrailLevel[])=>void;onOpenReference?:(reference:import("../api/generated/core-contract").ObjectReferenceDto)=>void}) {
  const workingContext=useOptionalCoreWorkingState();
  // Core working-state persistence belongs to the verified formal desktop host.
  // Browser presentation fixtures do not obtain a native persistence receipt.
  const working=window.__TAURI__?.core?.invoke?workingContext:null;
  const savedJournalPending=useRef(new Map<string,{sent:WorkingDraft;version:number}>());
  const [documentSearch,setDocumentSearch] = useState("");
  const [selectedTag,setSelectedTag] = useState("");
  const [contentFilter,setContentFilter] = useState<"all"|"original"|"linked"|"collection">("all");
  const [showSource,setShowSource] = useState(false);
  const [candidateEditing,setCandidateEditing]=useState(false);
  const [showVersions,setShowVersions] = useState(purpose === "history");
  const [showReaderDetails,setShowReaderDetails] = useState(purpose === "history");
  const readerDetailsId=useId();
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
  const listGeneration = useRef(0), listRefreshInFlight = useRef(false);
  const [listSnapshot,setListSnapshot] = useState(0);
  const sourceTargetKey=initialSourceTarget?JSON.stringify([initialSourceTarget.source_id,initialSourceTarget.source_revision,initialSourceTarget.sha256,initialSourceTarget.folder_member]):null;
  const sourceTargetAttempt=useRef<{key:string|null;navigation:number;editing:number;pending:boolean;consumed:boolean}|null>(null);
  const listHasSnapshot=useRef(false);
  const [refreshingLists,setRefreshingLists] = useState(true);
  const [listError,setListError] = useState<string|null>(null);
  const [listFailureReason,setListFailureReason] = useState<string|null>(null);
  const [openedDocuments, setOpenedDocuments] = useState<DocumentSummaryDto[]>([]);
  const [relationSelection,setRelationSelection]=useState<FolderMemberSelection|null>(null);
  const [relationToolsOpen,setRelationToolsOpen]=useState(false);
  const relationPending=useRef(false);
  const [folderJob,setFolderJob]=useState<{source_id:string;job_id?:string}|null>(null);
  const [source, setSource] = useState<SourceDto | null>(null);
  const [original, setOriginal] = useState<OriginalDto | null>(null);
  const [bytes, setBytes] = useState<Uint8Array | null>(null);
  const [documentSource, setDocumentSource] = useState<SourceDto | null>(null);
  const [documentOriginal, setDocumentOriginal] = useState<OriginalDto | null>(null);
  const [documentBytes, setDocumentBytes] = useState<Uint8Array | null>(null);
  const [document, setDocument] = useState<DocumentDto | null>(null);
  const documentLease=useDocumentWriteLease(document?.document_id);
  const dirtyOwner=useDraftOwner("library");
  const [documentDrafts, setDocumentDrafts] = useState<Record<string, {content:JSONContent;baseVersion:number}>>(()=>Object.fromEntries(Object.entries(working?.state.drafts??{}).map(([id,draft])=>[id,{content:structuredClone(draft.editor_json),baseVersion:draft.base_version}])));
  const documentDraftsRef = useRef(documentDrafts);
  documentDraftsRef.current = documentDrafts;
  const dirtyDocumentIds = useRef(new Set<string>(Object.keys(working?.state.drafts??{})));
  const [xiaoqiOpen, setXiaoqiOpen] = useState(false);
  // const [xiaoqiState, setXiaoqiState] = useState<XiaoqiState>('idle');
  const noteAttempt=useRef<OriginalNoteAttempt|null>(null);
  const [noteUncertain,setNoteUncertain]=useState(false);
  const [anchors, setAnchors] = useState<AnchorDto[]>([]);
  const [page, setPage] = useState(1);
  const [focusRequest, setFocusRequest] = useState(0);
  const [ocrSeek,setOcrSeek]=useState<OcrImageSeek>();
  const [epubSeek,setEpubSeek]=useState<{sourceId:string;position:EpubPosition}|undefined>();
  const [mediaSeek,setMediaSeek]=useState<{sourceId:string;milliseconds:number;sequence:number}|undefined>();
  const [mediaDuration,setMediaDuration]=useState<{sourceId:string;seconds:number}|undefined>();
  const [restoreVersion, setRestoreVersion] = useState("1");
  const [historicalDocument, setHistoricalDocument] = useState<DocumentDto | null>(null);
  const historyGeneration = useRef(0);
  const currentDocument = useRef(document);
  currentDocument.current = document;
  const [editorEpoch, setEditorEpoch] = useState(0);
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState(false);
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [importReceipt,setImportReceipt]=useState<{name:string;bytes:number;state:string}|null>(null);
  const [exportProof, setExportProof] = useState<DocumentExportDto | null>(null);
  const revisionBasis = useRef<RevisionBasisDto | null>(null);
  const dirty = useRef(false);
  useDraftRecoverySource(dirtyOwner, "文档草稿", () => [
    ...Object.entries(documentDraftsRef.current).map(([id, value]) => ({ label: `文档 · ${id}`, text: JSON.stringify({ document_id: id, base_version: value.baseVersion, editor_json: value.content }, null, 2) })),
    ...(noteAttempt.current ? [{ label: "尚未确认的原件笔记", text: JSON.stringify(noteAttempt.current.body, null, 2) }] : []),
  ]);
  const writeInFlight = useRef(false);
  const [busy, setBusy] = useState(false);
  const editGeneration = useRef(0);
  const generation = useRef(0);
  const textRegion = useRef<HTMLPreElement>(null);
  const [pendingTextLocation,setPendingTextLocation]=useState<{epoch:number;start?:number;end?:number}|null>(null);
  useEffect(()=>{
    if(!pendingTextLocation)return;
    if(pendingTextLocation.epoch!==generation.current){setPendingTextLocation(null);return;}
    const region=textRegion.current;
    if(!region)return;
    region.focus();
    const {start,end}=pendingTextLocation,node=region.firstChild;
    if(node&&start!==undefined&&end!==undefined&&start>=0&&start<=end&&end<=(node.textContent?.length??0)){
      const range=window.document.createRange();range.setStart(node,start);range.setEnd(node,end);
      const selection=window.getSelection();selection?.removeAllRanges();selection?.addRange(range);
    }
    setPendingTextLocation(null);
  },[pendingTextLocation,showSource,bytes]);
  const sourceNavigation = useRef<HTMLElement>(null);
  const documentNavigation = useRef<HTMLElement>(null);
  const anchorNavigation = useRef<HTMLElement>(null);
  const versionNavigation = useRef<HTMLDivElement>(null);
  function publishDirtyState() {
    dirty.current = dirtyDocumentIds.current.size > 0 || noteAttempt.current !== null || relationPending.current;
    onDirtyChange?.(dirty.current);
    window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: {owner:dirtyOwner,dirty:dirty.current} }));
  }
  function selectFolderRelations(selection:FolderMemberSelection) {
    if(relationPending.current||writeInFlight.current||dirty.current){setMessage("原关系请求、草稿或写入未确认，保留原映射；请先核对。");return;}
    setRelationSelection(selection);setRelationToolsOpen(true);
  }
  useEffect(()=>{
    const selection=initialSourceTarget?.folder_member;
    if(!selection)return;
    if(selection.source_id!==initialSourceTarget.source_id||selection.source_revision!==initialSourceTarget.source_revision||selection.source_revision!==initialSourceTarget.sha256){setMessage("批次成员与所选原件身份不符，未打开关系映射。");return;}
    selectFolderRelations(selection);
  },[sourceTargetKey]);
  function reportEditorDirty(id:string, value:boolean) {
    if(value) dirtyDocumentIds.current.add(id); else dirtyDocumentIds.current.delete(id);
    if(value) editGeneration.current += 1;
    if(!value) setDocumentDrafts(previous => { const next={...previous}; delete next[id]; return next; });
    publishDirtyState();
  }
  function rememberDraft(id:string, content:JSONContent, baseVersion:number) {
    if(!documentLease.canWrite)throw new Error("此文档视图只读；共享草稿保持不变");
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
    void Promise.all(working.state.opened_documents.map(id=>coreCommand<DocumentDto>("document_get",{document_id:id}))).then(items=>{if(alive)setOpenedDocuments(previous=>[...previous,...items.filter(item=>!previous.some(row=>row.document_id===item.document_id))]);}).catch(()=>{if(alive){setMessage("已打开文档暂时无法加载；你的草稿仍保留，请重试。");setFailure(true);}});
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
        { id: `source:${source.source_id}`, label: source.original_name, detail: document ? `关联文档第 ${document.version} 版` : "已保存原件", region: "sources" },
      );
    } else if (document) {
      levels.push(
        { id: "section:documents", label: "已保存文档", region: "documents" },
        { id: `document:${document.document_id}`, label: document.title, detail: `文档第 ${document.version} 版`, region: "documents" },
      );
    }
    if (document && historicalDocument?.document_id === document.document_id) {
      levels.push({ id: `version:${historicalDocument.version}`, label: `历史版本 v${historicalDocument.version}`, detail: "已保存的历史版本", region: "versions" });
    }
    onTrail?.(levels);
  }, [source, document, historicalDocument, onTrail]);
  useEffect(() => {
    if (!document && !source) return;
    onInspect?.({
      title: document?.title ?? source!.original_name,
      source: source ? "已保存的原件" : document?.source_id ? "关联原件的文档" : "原创笔记",
      lifecycle: document ? "已保存，内容审核需另行确认" : "原件已保存",
      rawSha256: document ? undefined : source?.sha256,
      version: document ? String(document.version) : undefined,
      updatedAt: source?.imported_at,
      detail: document ? (document.source_id ? "已关联原件；原件和文档版本分别保留。保存不代表内容已被证实。" : "此笔记未关联原件。保存不代表内容已被证实。") : `原件已保存，有 ${anchors.length} 个引用位置；处理结果需单独查看。`,
      identityDetails: document ? {document_id:document.document_id,version:document.version,content_sha256:document.content_sha256,source_id:document.source_id,source_revision:document.source_revision} : {source_id:source!.source_id,source_revision:source!.source_revision,raw_sha256:source!.sha256,anchor_count:anchors.length},
    }, { reveal: false });
  }, [document, source, anchors, onInspect]);
  useEffect(() => {
    libraryMounted.current = true;
    const refresh=()=>{void refreshLists();};
    window.addEventListener("archeaxis-job-changed",refresh);
    return () => { window.removeEventListener("archeaxis-job-changed",refresh); libraryMounted.current = false; listGeneration.current += 1; generation.current += 1; onDirtyChange?.(false); window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: {owner:dirtyOwner,dirty:false} })); };
  }, []);
  useEffect(()=>{sourceTargetAttempt.current={key:sourceTargetKey,navigation:generation.current,editing:editGeneration.current,pending:false,consumed:false};},[sourceTargetKey]);
  useEffect(()=>{void refreshLists();},[activationRevision,sourceTargetKey]);
  // List reads have their own generation. Refreshing never reopens selected content or resets a write.
  async function refreshLists() {
    const current=++listGeneration.current;
    listRefreshInFlight.current=true;documentPageInFlight.current=false;
    setRefreshingLists(true);setLoadingDocuments(false);setListError(null);setListFailureReason(null);
    try {
      const [sourcesResult,docsResult]=await Promise.all([
        coreCommand<{sources:SourceDto[]}>("sources_list"),coreCommand<DocumentsListDto>("documents_list"),
      ]);
      if(!libraryMounted.current||current!==listGeneration.current)return;
      setSources(sourcesResult.sources);setDocuments(docsResult.documents);setSourcePage(0);
      setNextDocumentCursor(docsResult.next_cursor ?? null);
      documentSnapshotCount.current = docsResult.snapshot_count ?? null;
      consumedDocumentCursors.current.clear();listHasSnapshot.current=true;setListSnapshot(current);
    }catch(error){if(libraryMounted.current&&current===listGeneration.current){setListError(listHasSnapshot.current?"资料列表刷新失败；已加载列表、当前内容与草稿保留，可重试。":"资料暂时无法读取，请检查本地核心。");setListFailureReason(coreFailureReason(error));}}
    finally{if(libraryMounted.current&&current===listGeneration.current){listRefreshInFlight.current=false;setRefreshingLists(false);setLibraryBootSettled(true);}}
  }
  async function loadMoreDocuments() {
    if (!nextDocumentCursor || documentPageInFlight.current || listRefreshInFlight.current) return;
    const cursor = nextDocumentCursor;
    const current=listGeneration.current;
    documentPageInFlight.current = true;
    setLoadingDocuments(true);
    try {
      const result = await coreCommand<DocumentsListDto>("documents_list", { cursor });
      if (!libraryMounted.current || current!==listGeneration.current) return;
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
      setListError(null); setListFailureReason(null);
    } catch (error) {
      if (libraryMounted.current && current===listGeneration.current) {
        setListError("更多文档读取失败；已加载文档与草稿仍保留，可重试。");
        setListFailureReason(coreFailureReason(error));
      }
    } finally {
      if (libraryMounted.current && current===listGeneration.current) {documentPageInFlight.current = false;setLoadingDocuments(false);}
    }
  }
  useEffect(()=>{if(initialDocumentId && !initialSourceTarget && libraryBootSettled && purpose!=="library")void openDocument(initialDocumentId);},[initialDocumentId,initialSourceTarget,libraryBootSettled,activationRevision,purpose]);
  useEffect(()=>{
    const attempt=sourceTargetAttempt.current;
    if(!initialSourceTarget||!attempt||attempt.key!==sourceTargetKey||attempt.pending||attempt.consumed||listSnapshot!==listGeneration.current)return;
    // A newer explicit selection or edit wins over delayed source navigation.
    if(attempt.navigation!==generation.current||attempt.editing!==editGeneration.current){attempt.consumed=true;return;}
    const matches=sources.filter(s=>s.source_id===initialSourceTarget.source_id&&s.source_revision===initialSourceTarget.source_revision&&s.sha256===initialSourceTarget.sha256);
    if(matches.length!==1){setFailure(true);setMessage("所选原件版本未唯一核对；不会切换为同名或新版原件。");return;}
    attempt.pending=true;setCandidateEditing(false);setShowSource(true);
    const reading=open(matches[0]);attempt.navigation=generation.current;
    void reading.then(result=>{
      if(sourceTargetAttempt.current!==attempt)return;
      attempt.pending=false;attempt.consumed=result!=="failure";
      // Failure waits for another successful list refresh; it never loops on its own.
    });
  },[sourceTargetKey,sources,listSnapshot]);
  async function importFile(file: File) {
    setImportReceipt({name:file.name,bytes:file.size,state:"正在检查原件"});
    if (file.size > 64 * 1024 * 1024) { setMessage("当前导入上限为 64 MiB，请选择不超过上限的原件。"); setFailure(true); setImportReceipt({name:file.name,bytes:file.size,state:"未导入：超过大小上限"}); return; }
    setImporting(true); setFailure(false); setMessage("正在导入原件…");
    try {
      const content = new Uint8Array(await file.arrayBuffer());
      const expectedSha256 = await sha256(content);
      let binary = "";
      for (let offset = 0; offset < content.length; offset += 8192) binary += String.fromCharCode(...content.subarray(offset, offset + 8192));
      confirmedImport(await coreCommand("source_import", { body: { name: file.name, content_base64: btoa(binary) } }), expectedSha256);
      setImportReceipt({name:file.name,bytes:file.size,state:"原件已保留；转换尚未执行"}); setMessage("原件已导入；选择它开始阅读。");
      await refreshLists();
    } catch (error) { setImportReceipt({name:file.name,bytes:file.size,state:"导入未确认，请保留原件"}); setMessage(error instanceof Error ? error.message : "导入未完成，请保留原件并重试。"); setFailure(true); }
    finally { setImporting(false); }
  }
  async function open(selected: SourceDto, linkDocument=true):Promise<"success"|"stale"|"failure"> {
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
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return "stale";
      readStage="原件版本核对";
      if (asset.source_id!==selected.source_id||asset.sha256 !== selected.sha256) throw new Error("source identity mismatch");
      const decoded = Uint8Array.from(atob(asset.content_base64), (character) => character.charCodeAt(0));
      readStage="原件字节核验";
      const actualHash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", decoded))).map((value) => value.toString(16).padStart(2, "0")).join("");
      if (actualHash !== selected.sha256) throw new Error("source bytes mismatch");
      const linked = linkDocument ? documents.find((item) => item.source_id === selected.source_id && item.source_revision === selected.source_revision) : undefined;
      readStage="草稿版本读取";
      const active = linked ? await coreCommand<DocumentDto>("document_get", { document_id: linked.document_id }) : null;
      if (epoch !== generation.current || editingEpoch !== editGeneration.current) return "stale";
      if(active&&(active.document_id!==linked!.document_id||active.source_id!==selected.source_id||active.source_revision!==selected.source_revision))throw new Error("linked document identity mismatch");
      setSource(selected); setOriginal(asset); setBytes(decoded); setDocument(active); setAnchors(evidence.anchors);
      setDocumentSource(active ? selected : null); setDocumentOriginal(active ? asset : null); setDocumentBytes(active ? decoded : null);
      if (active) setOpenedDocuments(previous => previous.some(item => item.document_id === active.document_id) ? previous : [...previous, active]);
      setExportProof(null); setFailureReason(null);
      setEditorEpoch((value) => value + 1); setPage(1); setMessage("原件哈希已核对；草稿与原件独立保存。");
      publishDirtyState();return "success";
    } catch (error) {
      if(epoch!==generation.current||editingEpoch!==editGeneration.current)return "stale";
      setFailure(true);setMessage(`${readStage}未完成；未替换当前内容，请保留原件重试。`);setFailureReason(coreFailureReason(error));return "failure";
    }
  }
  async function openFolderSource(id:string,jobId?:string,revision?:string) {
    if(dirty.current||writeInFlight.current||!revision){setMessage("草稿、未确认写入或来源版本尚未处理；当前内容保留。");setFailure(true);return;}
    // Reserve navigation at the click, before the first metadata await. An older
    // selection must never enter open() and displace a newer pending selection.
    let navigation=++generation.current;const editing=editGeneration.current;
    try {
      const selected=verifiedSource(await coreCommand<SourceDto>("source_get",{source_id:id}),id,revision);
      if(!libraryMounted.current||navigation!==generation.current||editing!==editGeneration.current||dirty.current||writeInFlight.current)return;
      const reading=open(selected,false);navigation=generation.current;
      const result=await reading;
      if(result==="success"&&libraryMounted.current&&navigation===generation.current&&editing===editGeneration.current&&!dirty.current&&!writeInFlight.current){setFolderJob({source_id:id,job_id:jobId});setSources(old=>[selected,...old.filter(s=>s.source_id!==id)]);}
    }catch{if(libraryMounted.current&&navigation===generation.current&&editing===editGeneration.current){setMessage("所选来源身份未读回；未替换为同名来源或文档。");setFailure(true);}}
  }
  async function relationWrite<T>(action:()=>Promise<T>):Promise<T> {
    if(writeInFlight.current||dirtyDocumentIds.current.size||noteAttempt.current)throw new Error("当前有草稿或写入，未提交关系");
    writeInFlight.current=true;setBusy(true);
    try{return await documentLease.write(action);}finally{writeInFlight.current=false;setBusy(false);}
  }
  function relationApplied(saved:DocumentDto){
    if(currentDocument.current?.document_id!==saved.document_id||dirtyDocumentIds.current.has(saved.document_id)){setMessage("关系已保存；期间新增草稿保留，请读取冲突版本核对。");return;}
    setDocument(saved);setDocuments(old=>old.map(d=>d.document_id===saved.document_id?saved:d));setOpenedDocuments(old=>old.map(d=>d.document_id===saved.document_id?saved:d));setEditorEpoch(v=>v+1);
  }
  async function openDocument(id: string) {
    // Retained readers must re-read a clean document on explicit reactivation.
    // Reopening never replaces an independent draft or interrupts an in-flight write.
    if (currentDocument.current?.document_id === id && (dirty.current || writeInFlight.current || working?.state.drafts[id])) return;
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
      if(listRefreshInFlight.current||documentPageInFlight.current)void refreshLists();
      setOpenedDocuments(previous => [created,...previous.filter(row=>row.document_id!==created.document_id)]);
      if(epoch!==generation.current||editingEpoch!==editGeneration.current){setMessage("原创笔记已建立，当前编辑内容仍保留；可从已保存文档打开新笔记。");return;}
      revisionBasis.current = null;
      setDocument(created);
      setSource(null); setOriginal(null); setBytes(null); setAnchors([]); setExportProof(null); setDocumentSource(null); setDocumentOriginal(null); setDocumentBytes(null);
      setEditorEpoch(value => value + 1); setMessage("原创笔记已建立。"); setFailure(false);
      publishDirtyState();
      if(attempt.body.source_id) await openDocument(created.document_id);
      if(purpose === "library") onOpenDocument?.(created.document_id);
    } catch(error) {
      if(!libraryMounted.current)return;
      if(error instanceof OriginalNoteRefused) {
        try{if(noteAttempt.current)await working?.session.finishOriginal(noteAttempt.current.body as PendingOriginal);}
        catch{setMessage("创建未被接受；请先确认上次操作的结果，草稿仍保留。");setFailure(true);return;}
        noteAttempt.current=null;setNoteUncertain(false);publishDirtyState();
        setMessage("原创笔记创建被明确拒绝；现有草稿保留，修正条件后可重新创建。");
      } else {
        setNoteUncertain(noteAttempt.current!==null);
        setMessage("笔记是否创建成功尚未确认；请重试同一次操作或检查结果，不会另建笔记。");
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
    // Share the durable frozen create journal, including source identity. A
    // lost ACK must never regenerate the request or substitute a newer source.
    if(!noteAttempt.current) {
      const attempt=await prepareOriginalNote();
      const plain=original.media_type.startsWith("text/")?new TextDecoder().decode(bytes):"";
      attempt.body.source_id=source.source_id;attempt.body.source_revision=source.source_revision;
      attempt.body.title=source.original_name;
      if(plain)attempt.body.editor_json.content![0].content=[{type:"text",text:plain}];
      if(/\.(md|markdown)$/i.test(source.original_name))attempt.body.editor_json.attrs={...attempt.body.editor_json.attrs,archeaxis_markup:"markdown"};
      noteAttempt.current=attempt;
    }
    await createOriginal();
  }
  async function save(content: JSONContent, expectedVersion: number) {
    return documentLease.write(()=>saveDraft(content,expectedVersion));
  }
  async function saveDraft(content: JSONContent, expectedVersion: number) {
    if (!document) throw new Error("document not loaded");
    const requestedDocumentId = document.document_id;
    const sentBasis = revisionBasis.current;
    const sent:WorkingDraft={base_version:expectedVersion,editor_json:structuredClone(content) as WorkingEditor};
    if(working){working.session.rememberDraft(requestedDocumentId,sent.editor_json,expectedVersion);try{await working.session.flush();}catch(error){throw new DocumentJournalError(error);}}
    const saved = await coreCommand<DocumentDto>("document_draft", { document_id: requestedDocumentId, body: { expected_version: expectedVersion, editor_json: content, ...(sentBasis ? {revision_basis:sentBasis} : {}) } });
    if (saved.document_id !== requestedDocumentId || saved.version!==expectedVersion+1) throw new Error("document identity or version mismatch");
    if (revisionBasis.current === sentBasis && currentDocument.current?.document_id === requestedDocumentId) revisionBasis.current = null;
    if(currentDocument.current?.document_id===saved.document_id) setDocument(saved);
    setDocuments((previous) => previous.map((item) => item.document_id === saved.document_id ? saved : item));
    if(listRefreshInFlight.current||documentPageInFlight.current)void refreshLists();
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
  async function readDocumentConflict(baseVersion:number) {
    if(!document)throw new Error("document not loaded");
    const id=document.document_id;
    // Preserve the independent draft before fetching snapshots. A read never
    // adopts the other version, overwrites input or grants write permission.
    if(working)await working.session.flush();
    const [base,current]=await Promise.all([
      coreCommand<DocumentDto>("document_version",{document_id:id,version:baseVersion}),
      coreCommand<DocumentDto>("document_get",{document_id:id}),
    ]);
    if(currentDocument.current?.document_id!==id||base.document_id!==id||current.document_id!==id
      ||base.version!==baseVersion||!Number.isSafeInteger(current.version)||current.version<baseVersion
      ||!/^([a-f0-9]{64})$/.test(current.content_sha256)
      ||base.source_id!==current.source_id||base.source_revision!==current.source_revision)throw new Error("conflict snapshot identity mismatch");
    return {base:{...base,editor_json:base.editor_json as JSONContent},current:{...current,editor_json:current.editor_json as JSONContent}};
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
        source: historicalSource ? "关联原件的历史文档" : "历史文档",
        lifecycle: "历史版本，只能查看；内容审核需另行确认",
        version: String(historical.version),
        rawSha256: historicalSource?.sha256,
        detail: "历史正文只读；当前草稿和最新版本不变。保存不代表内容已被证实。",
        identityDetails: {document_id:historical.document_id,version:historical.version,content_sha256:historical.content_sha256,source_id:historical.source_id,source_revision:historical.source_revision,raw_sha256:historicalSource?.sha256??null},
      });
    } catch {
      if (isCurrentHistoryRequest()) { setMessage("历史版本未读取，请重试。"); setFailure(true); }
    }
  }
  async function restore() {
    try{await documentLease.write(restoreDocument);}catch(error){setMessage(error instanceof Error?error.message:"此文档视图不可写入");setFailure(true);}
  }
  async function restoreDocument() {
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
      setDocuments(previous=>previous.map(item=>item.document_id===restored.document_id?restored:item));
      if(listRefreshInFlight.current||documentPageInFlight.current)void refreshLists();
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
    setShowSource(true);
    if(location.type==="ocr_line"){setOcrSeek(previous=>({sourceId:source.source_id,revision:source.source_revision,anchorId:String(attributes.anchor_id),position:String(attributes.position),sequence:(previous?.sequence??0)+1}));return;}
    const pdfPage = location.type === "pdf_line" && Array.isArray(location.path) && typeof location.path[0] === "string" && /^page-[1-9][0-9]*$/.test(location.path[0]) ? Number(location.path[0].slice(5)) : location.page;
    if (Number.isSafeInteger(pdfPage) && (pdfPage as number) > 0) { setPage(pdfPage as number); setFocusRequest((value) => value + 1); }
    else {
      setPendingTextLocation({epoch});
      if(location.type==="epub"){setEpubSeek({sourceId:source.source_id,position:location as EpubPosition});return;}
      if(location.type==="time"&&typeof location.start_ms==="number"&&Number.isFinite(location.start_ms)&&location.start_ms>=0){setMediaSeek(previous=>({sourceId:source.source_id,milliseconds:Number(location.start_ms),sequence:(previous?.sequence??0)+1}));return;}
      if (bytes && location.type === "text" && Number.isInteger(location.start) && Number.isInteger(location.end)) {
        try {
          const decoder=new TextDecoder("utf-8",{fatal:true});
          const start=decoder.decode(bytes.slice(0,Number(location.start))).length;
          const end=decoder.decode(bytes.slice(0,Number(location.end))).length;
          setPendingTextLocation({epoch,start,end});
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
  const sharedDraft=document?working?.state.drafts[document.document_id]:undefined;
  const documentEditor = document ? documentLease.canWrite?<Suspense fallback={<p>正在载入文档编辑器…</p>}><DocumentEditor key={`${document.document_id}:${editorEpoch}`} content={sharedDraft?.editor_json??documentDrafts[document.document_id]?.content ?? document.editor_json as JSONContent} documentTitle={document.title} version={sharedDraft?.base_version??documentDrafts[document.document_id]?.baseVersion ?? document.version} onSave={save} onReadConflict={readDocumentConflict} onRetryWorkingState={()=>retrySavedJournal(document.document_id)} onDirtyChange={value=>reportEditorDirty(document.document_id,value)} onDraftChange={(content,baseVersion)=>rememberDraft(document.document_id,content,baseVersion)} onCreateReference={source && original && bytes ? cite : undefined} onReferenceActivate={jump} /></Suspense>:<section aria-label="共享文档只读视图" data-business-session-key={documentLease.sessionKey}><p>此文档已在另一处编辑，当前只读显示共享草稿。</p><button disabled={!documentLease.canRevealOwner} onClick={documentLease.revealOwner}>打开文档写入视图</button><DocumentSnapshot label="共享文档当前内容" value={sharedDraft?.editor_json??document.editor_json as JSONContent}/></section> : null;

  const originalPane = document ? <article className="original-derived-pane" aria-label="不可变原件">
              <header><h4>不可变原件</h4><p>{linkedOriginal ? "原件身份、版本与字节指纹已核对。" : "关联原件尚未核对或当前未提供，不以其他原件替代。"}</p></header>
              {linkedOriginal && documentBytes && documentOriginal && documentSource ? <>
                <p>来源：{documentSource.original_name} · 文档第 {document.version} 版</p><RawReceiptButton label="关联原件身份" category="data" payload={{source_id:documentSource.source_id,source_revision:documentSource.source_revision,sha256:documentOriginal.sha256}}/>
                 {linkedPdf ? <Suspense fallback={<p>正在载入 PDF 阅读器…</p>}><><PdfReader bytes={documentBytes} page={page} onPageChange={setPage} focusRequest={focusRequest} /><PdfPageRecognition key={`pages:${documentSource.source_id}:${documentSource.source_revision}`} sourceId={documentSource.source_id} onPageSelect={setPage} currentPage={page}/></></Suspense> : documentOriginal.media_type.startsWith("text/") ? <pre ref={purpose === "reader" ? textRegion : undefined} tabIndex={0} aria-label="并排原件正文">{new TextDecoder().decode(documentBytes)}</pre> : documentOriginal.media_type.startsWith("image/") ? <OcrImageReader key={`${documentSource.source_id}:${documentSource.source_revision}`} sourceId={documentSource.source_id} revision={documentSource.source_revision} name={documentSource.original_name} original={documentOriginal} anchors={anchors} seek={ocrSeek}/> : documentOriginal.media_type.startsWith("audio/") || documentOriginal.media_type.startsWith("video/") ? <MediaReader key={`derived-media:${documentSource.source_id}`} bytes={documentBytes} mediaType={documentOriginal.media_type} seek={mediaSeek?.sourceId===documentSource.source_id?mediaSeek:undefined}/> : <p>暂不支持并排预览此格式。原件已保存在本地，可从原件列表打开。</p>}
              </> : <p>原件读取失败、身份不匹配或未绑定到此文档版本。正文指纹与原件指纹保持分开显示。</p>}
            </article> : null;
  const savedCollection = (saved: DocumentDto) => {
    const editor = saved.editor_json;
    if (!editor || typeof editor !== "object" || Array.isArray(editor)) return null;
    const attrs = (editor as Record<string, unknown>).attrs;
    if (!attrs || typeof attrs !== "object" || Array.isArray(attrs) || !Object.hasOwn(attrs, "archeaxis_collection")) return null;
    return <CollectionPanel key={`collection:${saved.document_id}:${saved.version}:${saved.content_sha256}`} document={saved} value={(attrs as Record<string, unknown>).archeaxis_collection} presentation="reader" onChange={()=>{}} onOpenReference={onOpenReference}/>;
  };
  const versionControls = document ? <><div ref={versionNavigation} tabIndex={-1} data-section="versions" aria-label="文档版本导航" className="draft-restore"><label>恢复历史版本 <input type="number" min="1" max={document.version} value={restoreVersion} onChange={(event) => setRestoreVersion(event.target.value)} /></label><button type="button" onClick={() => void readHistory()}>只读查看历史版本</button><button type="button" disabled={busy||!documentLease.canWrite} onClick={() => void singleWrite(restore)}>读取并恢复版本</button></div>
          {historicalDocument?.document_id===document.document_id?<section aria-label="历史版本详情"><h4>历史版本 {historicalDocument.version}</h4><SavedDocumentMetadata document={historicalDocument} onTag={setSelectedTag}/><pre>{historicalDocument.text_projection}</pre><DocumentEmbeds key={`${historicalDocument.document_id}:${historicalDocument.version}:${historicalDocument.content_sha256}`} editor={historicalDocument.editor_json} onOpenReference={onOpenReference}/>{savedCollection(historicalDocument)}{historicalDocument.revision_basis?<RawReceiptButton label="历史修订依据" payload={historicalDocument.revision_basis} />:<p>此版本没有记录修订依据。</p>}<button type="button" onClick={()=>{historyGeneration.current+=1;setHistoricalDocument(null);}}>关闭历史详情</button></section>:null}</> : null;
  const feedback = <>{noteUncertain?<div aria-label="待确认的笔记创建"><p>笔记创建结果尚未确认；先检查结果，再重试同一次操作。</p><button disabled={busy} onClick={()=>void singleWrite(createOriginal)}>重试同一次笔记创建</button><button disabled={busy} onClick={()=>void singleWrite(()=>createOriginal(true))}>检查笔记创建结果</button></div>:null}{message ? <p role={failure ? "alert" : "status"}>{message}</p> : null}{failureReason ? <p className="state-reason">{failureReason}</p> : null}</>;
  // List reads own one announcement; content/write outcomes remain independent.
  const listControls=<section className="library-list-controls" aria-label="资料列表刷新"><button type="button" disabled={refreshingLists} onClick={()=>void refreshLists()}>刷新资料列表</button>{refreshingLists?<p role="status">{libraryBootSettled?"正在刷新资料列表…":"正在读取资料…"}</p>:null}{listError?<><p role="alert">{listError}</p><p className="library-retry-help">先确认本地工作区已连接，再点“刷新资料列表”。读取失败时无法判断资料是否为空；已打开的内容和草稿仍保留。</p></>:null}{listFailureReason?<p className="state-reason">{listFailureReason}</p>:null}</section>;
  const filteredDocuments = documents.filter(item => {
    if(contentFilter === "original" && item.source_id) return false;
    if(contentFilter === "linked" && !item.source_id) return false;
    if(contentFilter === "collection" && item.has_collection !== true) return false;
    if(!matchesTag(item,selectedTag))return false;
    const sourceName=sources.find(value=>value.source_id === item.source_id)?.original_name ?? "";
    return `${item.title} ${sourceName}`.toLocaleLowerCase().includes(documentSearch.trim().toLocaleLowerCase());
  });
  const collectionPresenceUnknown = documents.some(item=>typeof item.has_collection!=="boolean");
  function selectForReading(id:string) {
    if(onOpenDocument) onOpenDocument(id); else void openDocument(id);
  }
  const tagInformationIncomplete=documents.some(item=>item.metadata_status!=="COMPLETE"||!Array.isArray(item.tags));
  const tagControls=<TagNavigation documents={documents} value={selectedTag} onChange={setSelectedTag}/>;
  const documentList = <>
    <nav ref={documentNavigation} tabIndex={-1} data-guide="saved-documents" data-section="documents" aria-label="已保存文档" className="stitch-document-list">
      <ul className="stitch-document-cards">
        {filteredDocuments.map(item => <li key={item.document_id}>
          <article className="stitch-document-card" data-context-surface="document-card">
            <span className="stitch-document-kind" aria-hidden="true">{item.has_collection === true ? "集合" : item.source_id ? "文档" : "笔记"}</span>
            <div className="stitch-document-card-copy"><h4>{item.title}</h4><p>{item.source_id ? "关联原件文档" : "原创笔记"}{item.source_id ? <> · {sources.find(value=>value.source_id===item.source_id)?.original_name ?? "已绑定来源"}</> : null}</p>{item.has_collection===true?<small>含保存版集合</small>:null}</div>
            <span className="stitch-document-version">v{item.version}</span>
            <button type="button" data-context-command="read" onClick={()=>selectForReading(item.document_id)} aria-label={`打开文档 ${item.title}`}>打开阅读</button>
          </article>
        </li>)}
      </ul>
      {contentFilter==="collection"&&collectionPresenceUnknown?<p role="status">部分已加载文档未提供集合信息，无法据此判断没有集合。可刷新列表或从全部内容打开文档查看。</p>:null}
      {!failure && !message && filteredDocuments.length===0 && !(contentFilter==="collection"&&collectionPresenceUnknown) && !(selectedTag&&tagInformationIncomplete) ? <p>{selectedTag ? documentSearch.trim()||contentFilter!=="all" ? "已加载文档中没有同时匹配当前筛选的内容。" : nextDocumentCursor ? "已加载文档中没有匹配标签；可继续加载更多文档。" : "已加载文档中没有匹配标签。" : contentFilter==="collection" ? documentSearch.trim()&&documents.some(item=>item.has_collection===true) ? "已加载集合中没有匹配文档。" : nextDocumentCursor ? "已加载文档中没有集合；可继续加载更多文档。" : "当前列表没有集合文档。" : documents.length ? "已加载内容中没有匹配文档。" : "暂无已保存文档，可以新建原创笔记。"}</p> : null}
    </nav>
    {nextDocumentCursor ? <button type="button" disabled={loadingDocuments} onClick={()=>void loadMoreDocuments()}>{loadingDocuments ? "正在加载文档…" : "加载更多文档"}</button> : null}
  </>;
  const originalTextCitation=source&&bytes&&/\.(txt|md)$/i.test(source.original_name)?<OriginalTextCitation sourceId={source.source_id} revision={source.source_revision} bytes={bytes} onAnchor={anchor=>setAnchors(previous=>[...previous.filter(item=>item.anchor_id!==anchor.anchor_id),anchor])}/>:null;
  const folderRelations=<>
    <div className="space-section-region" data-section="folder" tabIndex={-1} aria-label="目录批量导入"><FolderIngest onOpenSource={(id,job,revision)=>void openFolderSource(id,job,revision)} onSelectRelations={selectFolderRelations}/></div>
    {relationSelection?<IngestRelationsPanel key={JSON.stringify(relationSelection)} selection={relationSelection} document={document} documents={documents} dirty={dirtyDocumentIds.current.size>0||!!noteAttempt.current||!!sharedDraft} canWrite={documentLease.canWrite} write={relationWrite} onApplied={relationApplied} onPendingChange={pending=>{relationPending.current=pending;publishDirtyState();}} onOpenDocument={id=>{if(!dirty.current&&!writeInFlight.current)void openDocument(id);}} onMore={()=>void loadMoreDocuments()} hasMore={!!nextDocumentCursor}/>:null}
  </>;
  if(purpose === "library") return <section className="stitch-library-page" aria-label="知识库文档视图" data-stitch-library="library">
    <header className="stitch-library-heading"><div><span className="stitch-library-eyebrow">知识与原件</span><h2>知识库</h2></div><div className="stitch-library-actions"><button type="button" onClick={onOpenImport} disabled={!onOpenImport}>导入原件</button><button className="stitch-library-primary" type="button" disabled={busy||noteUncertain} onClick={()=>void singleWrite(createOriginal)}>新建笔记</button></div></header>
    {feedback}
    <div className="stitch-library-search"><label><span className="sr-only">筛选已加载文档标题与来源</span><input type="search" aria-label="筛选已加载文档标题与来源" placeholder="筛选标题、来源…" value={documentSearch} onChange={event=>setDocumentSearch(event.target.value)}/></label>{listControls}</div>
    <div className="stitch-library-browser">
      <aside className="stitch-library-facets" aria-label="内容与视图"><h3>快速视图</h3>
        <div className="stitch-library-quick-views" role="group" aria-label="内容筛选">
          <button type="button" aria-pressed={contentFilter==="all"} onClick={()=>setContentFilter("all")}>全部内容</button>
          <button type="button" aria-pressed={contentFilter==="original"} onClick={()=>setContentFilter("original")}>原创笔记</button>
          <button type="button" aria-pressed={contentFilter==="linked"} onClick={()=>setContentFilter("linked")}>关联原件</button>
          <button type="button" aria-pressed={contentFilter==="collection"} onClick={()=>setContentFilter("collection")}>集合文档</button>
        </div>
        <details open className="stitch-library-tags"><summary>保存版标签</summary>{tagControls}</details>
        <details className="stitch-library-guide"><summary>集合与视图</summary><p>从集合文档进入保存版表格、列表、看板、日历和画廊；筛选覆盖已加载文档，可继续分页。</p><button type="button" onClick={()=>setContentFilter("collection")}>查看集合文档</button><button type="button" onClick={()=>onOpenCapability?.("CAP-0020")} disabled={!onOpenCapability}>查看集合能力详情</button></details>
      </aside>
      <section className="stitch-library-results" aria-label="已保存内容列表"><header><div><h3>已保存内容</h3><p>标题与来源筛选覆盖已加载文档；可继续加载当前列表。</p></div><span className="stitch-library-loaded-count">已加载 {documents.length} 篇</span></header>{documentList}</section>
    </div>
  </section>;
  // open() publishes these bytes only after checking the selected source identity and SHA.
  // An original can be read before it has any editable Document.
  const sourcePreview=source&&original&&bytes ? isPdf ? <Suspense fallback={<p>正在载入 PDF 阅读器…</p>}><><PdfReader bytes={bytes} page={page} onPageChange={setPage} focusRequest={focusRequest}/><PdfPageRecognition key={`pages:${source.source_id}:${source.source_revision}`} sourceId={source.source_id} onPageSelect={setPage} currentPage={page}/></></Suspense>
    : original.media_type.startsWith("image/") ? <OcrImageReader key={`${source.source_id}:${source.source_revision}`} sourceId={source.source_id} revision={source.source_revision} name={source.original_name} original={original} anchors={anchors} seek={ocrSeek}/>
    : original.media_type.startsWith("text/") ? <pre ref={textRegion} tabIndex={purpose==="reader"?0:-1} aria-label={purpose==="reader"?"并排原件正文":"原件正文"}>{new TextDecoder().decode(bytes)}</pre>
    : original.media_type.startsWith("audio/")||original.media_type.startsWith("video/") ? <MediaReader key={`media:${source.source_id}`} bytes={bytes} mediaType={original.media_type} seek={mediaSeek?.sourceId===source.source_id?mediaSeek:undefined} onDuration={seconds=>setMediaDuration({sourceId:source.source_id,seconds})}/>
    : <div className="reader-format-handoff"><p>原文件已核对。此格式暂不能在这里直接预览，可查看同一来源已提取的文字，或保留原件写笔记。</p>{purpose==="reader"?<button onClick={()=>setCandidateEditing(true)}>查看此原件的转换内容</button>:null}</div> : null;
  const readerSourceTools=purpose==="reader"&&source&&original&&bytes?<section className="stitch-reader-source-tools" aria-label="同源知识整理"><h3>来源 {source.original_name}</h3>{originalTextCitation}<RawReceiptButton label="原件编号与版本详细信息" category="data" payload={{source_id:source.source_id,source_revision:source.source_revision}}/>{!document?<>{sourcePreview}<button disabled={busy} onClick={()=>void singleWrite(create)}>创建可编辑草稿</button></>:null}<button aria-pressed={candidateEditing} onClick={()=>setCandidateEditing(true)}>整理此来源为知识候选</button>{candidateEditing?<JobContent key={`journey:${source.source_id}:${source.source_revision}`} sourceId={source.source_id} sourceRevision={source.source_revision} name={source.original_name} pinnedJobId={initialSourceTarget?.job_id} onKnowledge={onKnowledge} onDirtyChange={value=>{if(value)dirtyDocumentIds.current.add("source-candidate");else dirtyDocumentIds.current.delete("source-candidate");publishDirtyState();}} onAnchor={anchor=>setAnchors(previous=>[...previous.filter(a=>a.anchor_id!==anchor.anchor_id),anchor])}/>:null}</section>:null;
  const readerBatchTools=<details className="reader-batch-tools" open={relationToolsOpen} onToggle={event=>setRelationToolsOpen(event.currentTarget.open)}><summary>批次链接与附件{relationPending.current?" · 请求尚未确认":""}</summary><p>继续处理本批次，或点“读取历史批次”找回上次导入。链接只从固定原件解析；请明确选择已保存文档和目标，不会按同名猜测。</p>{folderRelations}</details>;
  if(purpose === "reader" || purpose === "history") return <section className="stitch-reader-page" aria-label={purpose==="history" ? "文档版本视图" : "阅读与编辑文档视图"} data-stitch-library={purpose} data-reader-layout={document&&!initialSourceTarget?"split":undefined} data-details-open={showReaderDetails||showVersions||purpose==="history"}>
    {feedback}
    {!document?<header className="stitch-reader-heading"><div><span className="stitch-library-eyebrow">知识与原件</span><h2>{purpose === "history" ? "文档历史" : "阅读与编辑"}</h2></div></header>:null}
    {!document?listControls:null}
    {!document&&readerSourceTools?<>{readerSourceTools}<details className="reader-source-help"><summary>阅读、转换与笔记有什么区别</summary><p>先对照原文件阅读。需要提取文字时，点“整理此来源为知识候选”，再执行内容转换；只想写笔记时，可点“创建可编辑草稿”。草稿保存在本地知识库，成为正式知识仍需另行审查。</p></details></>:null}
    {document ? <>
      <header className="stitch-reader-heading"><div><span className="stitch-library-eyebrow">{purpose === "history" ? "历史与版本" : "阅读与编辑"}</span><h2>{document.title}</h2></div><p><span>{document.source_id ? "关联原件文档" : "原创笔记"}</span><span className="stitch-document-version">v{document.version}{dirtyDocumentIds.current.has(document.document_id) ? " · 未保存" : ""}</span></p></header>
      <div className="stitch-reader-toolbar"><div className="stitch-reader-modes" role="group" aria-label="阅读辅助视图"><button type="button" aria-pressed={!showSource&&!showVersions&&purpose!=="history"} onClick={()=>{setShowSource(false);setShowVersions(false);setShowReaderDetails(false);}}>正文</button><button type="button" aria-pressed={showSource} onClick={()=>setShowSource(value=>!value)}>原件</button><button type="button" aria-pressed={showVersions||purpose==="history"} onClick={()=>setShowVersions(value=>!value)}>版本</button><button type="button" aria-expanded={showReaderDetails||showVersions||purpose==="history"} aria-controls={readerDetailsId} onClick={()=>{setShowReaderDetails(value=>!value);setShowVersions(false);}}>属性与引用</button></div>{listControls}</div>
      <div className="stitch-reader-workspace"><div className="stitch-reader-spread" role="region" aria-label="正文与原件滚动区" tabIndex={0} data-original-open={showSource}>
        <article className="stitch-reader-document" aria-label="文档正文与编辑">{purpose==="history"?<header><h3>当前保存正文</h3><small>只读显示；历史版本从版本工具单独读取。</small></header>:null}
          {purpose!=="history" ? documentEditor : <pre className="stitch-history-text">{document.text_projection}</pre>}
          <DocumentEmbeds key={`${document.document_id}:${document.version}:${document.content_sha256}`} editor={document.editor_json} onOpenReference={onOpenReference}/>{savedCollection(document)}
        </article>
        {showSource ? <section className="stitch-reader-original" aria-label="关联原件阅读">{document.source_id ? originalPane : <p>此原创笔记没有绑定来源原件。</p>}</section> : null}
        {readerSourceTools?<details className="reader-source-tools" open={Boolean(initialSourceTarget)||undefined}><summary>整理关联来源</summary>{readerSourceTools}</details>:null}
      </div>
<aside id={readerDetailsId} className="stitch-reader-details" aria-label="内容详情" hidden={!showReaderDetails&&!showVersions&&purpose!=="history"} tabIndex={0}><h3>内容详情</h3><dl><div><dt>内容身份</dt><dd>{document.source_id ? "关联原件文档" : "原创笔记"}</dd></div><div><dt>文档版本</dt><dd>v{document.version}{dirtyDocumentIds.current.has(document.document_id) ? " · 未保存更改" : ""}</dd></div><div><dt>来源版本</dt><dd>{document.source_id ? linkedOriginal ? "原件身份、版本与字节已核对" : "已绑定；原件读取尚未核对" : "未绑定；保存不要求来源"}</dd></div></dl>
        <SavedDocumentMetadata document={document} onTag={setSelectedTag}/>
        <details className="reader-backlinks"><summary>反向链接（谁引用了本页）</summary><DocumentBacklinks key={`backlinks:${document.document_id}:${document.version}:${document.content_sha256}`} document={document} onOpenReference={onOpenReference}/></details>
        {selectedTag?<section aria-label="标签关联文档"><h4>含此标签的文档</h4>{tagControls}{filteredDocuments.map(item=><button key={item.document_id} type="button" onClick={()=>selectForReading(item.document_id)}>{item.title} · v{item.version}</button>)}{nextDocumentCursor?<button type="button" disabled={loadingDocuments} onClick={()=>void loadMoreDocuments()}>加载更多文档</button>:null}</section>:null}
        <RawReceiptButton label="文档与来源详细信息" visibleLabel="文档与来源详细信息" payload={{document_id:document.document_id,source_id:document.source_id,source_revision:document.source_revision,content_sha256:document.content_sha256}}/>
        <details><summary>依据与修订记录</summary><CheckPanel key={`checks:${document.document_id}:${document.version}`} document={document} onRevisionBasis={value=>{revisionBasis.current=value;}}/></details>
        {showVersions||purpose==="history" ? <section aria-label="版本与影响">{versionControls}</section> : <button type="button" onClick={()=>setShowVersions(true)}>查看历史版本</button>}
        <details><summary>导出已保存文档</summary><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("markdown"))}>Markdown 导出到产品资料目录</button><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("obsidian"))}>Obsidian 包导出到产品资料目录</button>{exportProof?<RawReceiptButton label="导出详情与内容损失" payload={exportProof}/>:null}</details>
        <details className="reader-material-tools"><summary>围绕此文档提问</summary><MaterialQuestionPanel key={`material:${document.document_id}:${document.version}`} material={{kind:"document",document_id:document.document_id,version:document.version,content_sha256:document.content_sha256,block_id:null}} text={document.text_projection} materialTitle={document.title}/><ConversationPanel materialTitle={document.title} slot="reader" material={{kind:"document",document_id:document.document_id,version:document.version,content_sha256:document.content_sha256,block_id:null}}/></details>
      </aside>
      </div>
    </> : <section className="stitch-reader-empty"><h2>{refreshingLists?"正在读取资料":listError?"资料列表暂时无法读取":"选择已保存文档"}</h2><p>{refreshingLists?"读取完成后，可从文档列表选择内容。":listError?"先用上方的刷新操作重新读取，再选择资料；当前不会把读取失败当作没有资料。":documents.length?"点击下方“打开阅读”，查看正文；原件和旧版从阅读辅助视图打开。":"还没有可选文档。先导入一份资料，或新建一篇自己的笔记。"}</p>
      {!refreshingLists&&!listError&&documents.length===0 ? <div className="stitch-reader-empty-actions">{onOpenImport?<button type="button" className="stitch-library-primary" onClick={onOpenImport}>导入第一份资料</button>:null}<button type="button" data-guide="new-note" disabled={busy||noteUncertain} onClick={()=>void singleWrite(createOriginal)}>新建原创笔记</button></div> : null}
      {source?<details className="reader-other-documents"><summary>打开其他已保存文档</summary>{documentList}</details>:documentList}</section>}
    {purpose==="reader"?readerBatchTools:null}
  </section>;
  return <Section title="资料库">
    {listControls}
    <TemplateLauncher onOpen={id=>void openDocument(id)} onOpenCapability={onOpenCapability} onDirtyChange={value=>{if(value)dirtyDocumentIds.current.add("template-properties");else dirtyDocumentIds.current.delete("template-properties");publishDirtyState();}} />
    <p className="muted">原件保留其不可变版本；草稿自动保存到本地核心，引用绑定原件版本。</p>
    <label className="content-import" data-section="import" tabIndex={-1}>导入原件 <input type="file" aria-label="导入原件" disabled={importing} onChange={(event) => { const file = event.target.files?.[0]; if (file) void importFile(file); event.target.value = ""; }} /></label>
    {importReceipt?<dl className="receipt-grid" aria-label="导入结果"><div><dt>来源文件</dt><dd>{importReceipt.name}</dd></div><div><dt>原件大小</dt><dd>{importReceipt.bytes} 字节</dd></div><div><dt>导入状态</dt><dd>{importReceipt.state}</dd></div><div><dt>下一步</dt><dd>选择原件阅读或执行转换，再从实际引文整理待审核知识。</dd></div></dl>:null}
    {folderRelations}
    <div className="canonical-library">
      <nav ref={sourceNavigation} tabIndex={-1} className="canonical-sources" data-section="sources" aria-label="保留原件">
        {sources.length === 0 ? <p>暂无原件。</p> : sources.slice(sourcePage*30,(sourcePage+1)*30).map((item) => <button type="button" key={item.source_id} aria-current={source?.source_id === item.source_id ? "true" : undefined} onClick={() => void open(item)}>{item.original_name}</button>)}
        {sources.length>30?<div><button disabled={sourcePage===0} onClick={()=>setSourcePage(value=>value-1)}>上一组原件</button><span>{sourcePage+1} / {Math.ceil(sources.length/30)}</span><button disabled={(sourcePage+1)*30>=sources.length} onClick={()=>setSourcePage(value=>value+1)}>下一组原件</button></div>:null}
      </nav>
      {source && original && bytes ? <div className="canonical-content">
        <h4>{source.original_name}</h4>
        <div className="canonical-reading">
          <div>
          {sourcePreview}
          {originalTextCitation}
          <JobContent key={`job:${source.source_id}`} pinnedJobId={folderJob?.source_id===source.source_id?folderJob.job_id:undefined} sourceId={source.source_id} name={source.original_name} sourceRevision={source.source_revision} epubSeek={epubSeek?.sourceId===source.source_id?epubSeek.position:undefined} onEpubSeek={position=>setEpubSeek({sourceId:source.source_id,position})} onKnowledge={onKnowledge} onTimeSeek={seconds=>setMediaSeek(previous=>({sourceId:source.source_id,milliseconds:seconds*1000,sequence:(previous?.sequence??0)+1}))} onAnchor={anchor=>setAnchors(previous=>previous.some(item=>item.anchor_id===anchor.anchor_id)?previous:[...previous,anchor])} mediaDurationSeconds={mediaDuration?.sourceId===source.source_id?mediaDuration.seconds:undefined}/>
          <ContainerMemberChain key={`members:${source.source_id}`} sourceId={source.source_id} />
          {original && original.media_type === "application/octet-stream" ? <ContentDetectionPanel key={`detect:${source.source_id}`} sourceId={source.source_id} name={source.original_name} /> : null}
          </div>
          <aside ref={anchorNavigation} tabIndex={-1} data-section="anchors" aria-label="来源版本证据">
            <h4>来源与引用</h4>
            <p>引用绑定不可变原件版本，选择引用可回到已记录位置。</p>
            <p>原件内容与保存记录一致。</p><RawReceiptButton label="原件与来源详细信息" category="data" payload={{source_id:source.source_id,source_revision:source.source_revision,sha256:original.sha256}}/>
            {anchors.length===0?<p className="muted">此来源尚无引用记录。</p>:null}
            {anchors.map((anchor) => { let location: Record<string, unknown> = {}; try { location = JSON.parse(anchor.position); } catch { /* Preserve unresolved position, never invent a locator. */ }
              return <div key={anchor.anchor_id}><button type="button" disabled={anchor.location_status === "revision_mismatch"} onClick={() => void jump({ anchor_id:anchor.anchor_id, position:anchor.position, source_id: anchor.source_id, source_revision: anchor.source_revision })}>{typeof location.page === "number" ? `第 ${location.page} 页` : "来源引用"}{anchor.location_status === "revision_mismatch" ? " · 需重新定位" : anchor.location_status !== "located" ? " · 定位未核实" : ""}</button><RawReceiptButton label="引用来源详细信息" category="data" payload={{anchor_id:anchor.anchor_id,source_revision:anchor.source_revision,position:anchor.position,location_status:anchor.location_status}}/></div>;
            })}
          </aside>
        </div>
        {!document ? <button type="button" disabled={busy} onClick={() => void singleWrite(create)}>创建可编辑草稿</button> : null}
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
    {noteUncertain?<div aria-label="待确认的笔记创建"><p>笔记创建结果尚未确认，原请求保留。</p><button disabled={busy} onClick={()=>void singleWrite(createOriginal)}>重试同一次笔记创建</button><button disabled={busy} onClick={()=>void singleWrite(()=>createOriginal(true))}>检查笔记创建结果</button></div>:null}
    <nav ref={documentNavigation} tabIndex={-1} data-section="documents" aria-label="已保存文档">{documents.map(item => <button type="button" key={item.document_id} onClick={() => void openDocument(item.document_id)}>{item.title} · 文档</button>)}</nav>
    {nextDocumentCursor ? <button type="button" disabled={loadingDocuments} onClick={() => void loadMoreDocuments()}>{loadingDocuments ? "正在加载文档…" : "加载更多文档"}</button> : null}
    {!source && navigation?.section === "anchors" ? <section ref={anchorNavigation} tabIndex={-1} data-section="anchors" aria-label="来源版本证据"><p>请先选择实际来源原件；原创笔记可以没有来源锚点。</p></section> : null}
    {!document && navigation?.section === "versions" ? <div ref={versionNavigation} tabIndex={-1} data-section="versions" aria-label="文档版本导航"><p>请先选择已保存文档，再查看它的历史版本。</p></div> : null}
        {document ? <>
          {document.source_id ? <section className="original-derived-split" aria-label="原件与派生文档并排阅读" style={{"--derived-focus":1} as CSSProperties}>
            {originalPane}
            <article className="original-derived-pane" aria-label="派生文档与版本核验">
              <header><h4>派生文档</h4><p>文档第 {document.version} 版</p><RawReceiptButton label="文档内容详细信息" category="data" payload={{document_id:document.document_id,version:document.version,content_sha256:document.content_sha256}}/></header>
               {documentEditor}
              <CheckPanel key={`checks:${document.document_id}:${document.version}`} document={document} onRevisionBasis={value=>{revisionBasis.current=value;}} />
            </article>
          </section> : <>
           {documentEditor}
          <CheckPanel key={`checks:${document.document_id}:${document.version}`} document={document} onRevisionBasis={value=>{revisionBasis.current=value;}} />
          </>}
          <DocumentEmbeds key={`${document.document_id}:${document.version}:${document.content_sha256}`} editor={document.editor_json} onOpenReference={onOpenReference}/>{savedCollection(document)}
          {versionControls}
          <div className="space-section-region" data-section="export" tabIndex={-1} aria-label="文档导出"><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("markdown"))}>Markdown 导出到产品资料目录</button><button type="button" disabled={busy} onClick={()=>void singleWrite(()=>exportDocument("obsidian"))}>Obsidian 包导出到产品资料目录</button></div>
          {exportProof?<RawReceiptButton label="导出详情与内容损失" payload={exportProof} />:null}
        </> : null}
    {message ? <p role={failure ? "alert" : "status"}>{message}</p> : null}
    {failureReason ? <p className="state-reason">{failureReason}</p> : null}
    <BackupPanel hasUnsavedDrafts={dirty.current} />
    {purpose === "reader" && (
      <>
        <button
          className="xiaoqi-trigger-btn"
          onClick={() => setXiaoqiOpen(true)}
          aria-label="打开小栖助手"
        >
          💬
        </button>
        <XiaoqiPanel
          isOpen={xiaoqiOpen}
          onClose={() => setXiaoqiOpen(false)}
          currentContext={document?.title || source?.original_name}
        />
      </>
    )}
  </Section>;
}
