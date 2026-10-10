import {CanonicalControlledAiSpace} from "./CanonicalControlledAiSpace";
import { findUiPage } from "../presentation/uiPages";
import { CanonicalWorkspaceSpace } from "./CanonicalWorkspaceSpace";
import { SpaceId } from "./spaces";
import { useEffect, useRef, useState } from "react";
import { CanonicalLibrarySpace } from "./CanonicalLibrarySpace";
import { CanonicalKnowledgeSpace } from "./CanonicalKnowledgeSpace";
import { CanonicalLearningJourneySpace } from "./CanonicalLearningJourneySpace";
import { CanonicalTeachingSpace } from "./CanonicalTeachingSpace";
import { CanonicalExchangeSpace } from "./CanonicalExchangeSpace";
import { CanonicalExpressionSpace } from "./CanonicalExpressionSpace";
import { CanonicalResearchSpace } from "./CanonicalResearchSpace";
import { CanonicalRelationSpace } from "./CanonicalRelationSpace";
import { PinnedReferencePanel } from "../components/PinnedReferencePanel";
import { CollectionPanel } from "../components/CollectionPanel";
import type { ObjectReference } from "../api/generated/research-contract";
import { CanonicalCapabilitiesSpace } from "./CanonicalCapabilitiesSpace";
import { CanonicalResourcesSpace } from "./CanonicalResourcesSpace";
import { BackupPanel } from "../components/BackupPanel";
import { VersionSourcePanel } from "../components/VersionSourcePanel";
import type { InspectionTarget } from "../components/Inspector";
import type { ObjectTrailLevel } from "../components/NavTrail";
import type { CanonicalSurface } from "../presentation/spaceSections";

// The desktop shell routes spaces onto canonical surfaces; the secondary level and
// the object trail must describe the surface that is really rendered, not the space name.
export function canonicalSurface(spaceId: SpaceId, desktop: boolean): CanonicalSurface {
  void desktop;
  switch (spaceId) {
    case "workspace": return "canonical_workspace";
    case "settings":
      return "canonical_capabilities";
    case "library":
    case "intake":
    case "exchange":
      return "canonical_library";
    case "vault":
    case "evidence":
    case "ai-assets":
      return "canonical_knowledge";
    case "learning":
      return "canonical_learning";
  }
}

import type { SourceJourneyTarget, CandidateJourneyTarget } from "../presentation/sourceJourney";

export type SpaceNavigation = { spaceId: SpaceId; section: string; sequence: number };

function navigationFor(spaceId: SpaceId, navigation?: SpaceNavigation) {
  return navigation && navigation.spaceId === spaceId
    ? { section: navigation.section, sequence: navigation.sequence }
    : undefined;
}

// SpaceView renders the active space content (AXW-UI-802).
export function SpaceView({
  spaceId,
  onInspect,
  onNavigate,
  onOpenCapability, onOpenPage,
  navigation,
  selectedCapabilityId, uiPageId, initialDocumentId, onOpenDocument, hasUnsavedDrafts,
  onTrail,
  initialLearningItemKey, onReviewItem,
}: {
  spaceId: SpaceId;
  onInspect: (target: InspectionTarget) => void;
  onNavigate: (id: SpaceId) => void;
  onOpenCapability?: (id: string) => void; onOpenPage?: (id:string)=>void;
  navigation?: SpaceNavigation;
  selectedCapabilityId?: string | null;
  uiPageId?: string; initialDocumentId?: string; onOpenDocument?: (id:string)=>void;
  hasUnsavedDrafts?: boolean;
  onTrail?: (levels: readonly ObjectTrailLevel[]) => void;
  initialLearningItemKey?: string; onReviewItem?: (key:string)=>void;
}) {
  const [sourceTarget,setSourceTarget]=useState<SourceJourneyTarget>();
  const [candidateTarget,setCandidateTarget]=useState<CandidateJourneyTarget>();
  const externalDocument=useRef(initialDocumentId);
  useEffect(()=>{if(externalDocument.current!==initialDocumentId){externalDocument.current=initialDocumentId;setSourceTarget(undefined);}},[initialDocumentId]);
  const openJourneyDocument=(id:string)=>{setSourceTarget(undefined);onOpenDocument?.(id);};
  const candidateReview=(target?:CandidateJourneyTarget)=>{if(target)setCandidateTarget(target);else onNavigate("vault");};
  useEffect(()=>{const clear=(event:Event)=>{if((event as CustomEvent<{confirmed?:boolean}>).detail?.confirmed){setSourceTarget(undefined);setCandidateTarget(undefined);}};window.addEventListener("workspace-invalidated",clear);return()=>window.removeEventListener("workspace-invalidated",clear);},[]);
  const view = useRef<HTMLDivElement>(null);
  const [pinnedReference,setPinnedReference]=useState<ObjectReference|null>(null);
  useEffect(()=>{setPinnedReference(null);},[uiPageId,spaceId]);
  useEffect(() => {
    // Reuse the Avalonia AaosTheme route opacity transition (180ms), keeping
    // the existing content mounted so navigation never resets draft state.
    const motionPreference = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (motionPreference?.matches || document.visibilityState === "hidden" || !document.hasFocus() ||
        typeof view.current?.animate !== "function") return;
    const transition = view.current.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      { duration: 180, easing: "ease-out" },
    );
    const stop = () => transition.cancel();
    const onVisibility = () => { if (document.visibilityState === "hidden") stop(); };
    const onPreference = () => { if (motionPreference?.matches) stop(); };
    window.addEventListener("blur", stop);
    document.addEventListener("visibilitychange", onVisibility);
    motionPreference?.addEventListener("change", onPreference);
    return () => {
      window.removeEventListener("blur", stop);
      document.removeEventListener("visibilitychange", onVisibility);
      motionPreference?.removeEventListener("change", onPreference);
      stop();
    };
  }, [spaceId]);
  const content = (() => {
  if (selectedCapabilityId) {
    return <CanonicalCapabilitiesSpace onNavigate={onNavigate} selectedCapabilityId={selectedCapabilityId} navigation={navigation} onTrail={onTrail} />;
  }
  if (uiPageId === "02" || uiPageId === "03") return <CanonicalLibrarySpace purpose={uiPageId === "02" ? "library" : "reader"} initialSourceTarget={uiPageId==="03"?sourceTarget:undefined} initialDocumentId={initialDocumentId} onOpenDocument={openJourneyDocument} onOpenImport={()=>onNavigate("intake")} onKnowledge={candidateReview} onInspect={onInspect} onOpenCapability={onOpenCapability} navigation={{section:"documents",sequence:1}} onTrail={onTrail}/>;
  if (uiPageId === "21") return <CanonicalExpressionSpace onTrail={onTrail} onOpenCapability={onOpenCapability}/>;
  if (uiPageId === "04") return <CanonicalRelationSpace onOpenReference={setPinnedReference} renderCollection={(document,envelope,change,pending,readOnly)=>{
    const attrs=envelope.attrs && typeof envelope.attrs==="object" && !Array.isArray(envelope.attrs) ? envelope.attrs as Record<string,unknown> : {};
    return <CollectionPanel document={document} value={attrs.archeaxis_collection} readOnly={readOnly} onPendingEditChange={pending} onOpenReference={setPinnedReference} onChange={value=>change({...envelope,attrs:{...attrs,archeaxis_collection:value}})}/>;
  }}/>;
  if (uiPageId === "05") return <CanonicalResearchSpace onOpenReference={setPinnedReference} onTrail={onTrail}/>;
  if(uiPageId&&["13","14","22"].includes(uiPageId))return <CanonicalControlledAiSpace pageId={uiPageId} initialLearningItemKey={initialLearningItemKey} onOpenPage={onOpenPage} onOpenReference={setPinnedReference}/>;
  if (uiPageId === "15") return <CanonicalResourcesSpace onOpenDocument={onOpenDocument} onOpenCapability={onOpenCapability}/>;
  if (uiPageId === "06" || uiPageId === "07") return <CanonicalLearningJourneySpace pageId={uiPageId} initialItemKey={initialLearningItemKey} onLearningItem={onReviewItem} onOpenPage={onOpenPage} onTrail={onTrail}/>;
  if (uiPageId && ["08","09","10","11","12"].includes(uiPageId)) return <CanonicalTeachingSpace pageId={uiPageId} initialItemKey={initialLearningItemKey} onOpenPage={onOpenPage} onTrail={onTrail}/>;
  if (uiPageId === "16") return <CanonicalExchangeSpace onReadSource={target=>{setSourceTarget(target);setCandidateTarget(undefined);onOpenPage?.("03");}} initialDocumentId={initialDocumentId} onOpenDocument={onOpenDocument} onOpenPage={onOpenPage} onTrail={onTrail}/>;
  const semanticPage = uiPageId ? findUiPage(uiPageId) : undefined;
  if (semanticPage && !semanticPage.implemented) return <section className="ui-pending-page" aria-label={semanticPage.label}><h2>此页面尚未接通</h2><p>能力意图和页面入口已保留；当前没有此页面的完整真实用户路径。</p><p>承接任务 {semanticPage.task} · UI / {semanticPage.id}</p><button onClick={()=>onNavigate("settings")}>查看能力、依赖与系统状态</button></section>;
  if (spaceId === "workspace") return <CanonicalWorkspaceSpace onNavigate={id=>{if(uiPageId === "01" && onOpenPage && (id === "library" || id === "settings")) onOpenPage(id === "library" ? "02" : "17"); else onNavigate(id);}} onOpenDocument={onOpenDocument} onReviewItem={onReviewItem}/>;
  if (uiPageId === "19") return <section className="ui-reliability-panel" aria-label="系统与可靠性" data-section="backup" tabIndex={-1}>
    <h2>本地工作区与恢复</h2><p>普通笔记与草稿可先保存，依据分析、专业采用与 AI 资格分别记录。</p>
    <BackupPanel hasUnsavedDrafts={hasUnsavedDrafts} /><p>权限配置界面尚未接通。恢复通过本地宿主执行，浏览器未连接时明确不可用。</p>
  </section>;
  if (uiPageId === "20") return <><VersionSourcePanel /><CanonicalLibrarySpace purpose="history" initialDocumentId={initialDocumentId} onInspect={onInspect} navigation={{section:"versions",sequence:1}} onTrail={onTrail} /></>;
  if (uiPageId === "18") return <CanonicalCapabilitiesSpace onNavigate={onNavigate} onTrail={onTrail}/>;
  switch (spaceId) {
    case "library": case "intake": case "exchange":
      return <CanonicalLibrarySpace initialDocumentId={initialDocumentId} onKnowledge={candidateReview} onInspect={onInspect} onOpenCapability={onOpenCapability} navigation={navigationFor(spaceId,navigation)} onTrail={onTrail}/>;
    case "vault": case "evidence": case "ai-assets":
      return <CanonicalKnowledgeSpace onLearning={()=>onNavigate("learning")} onTrail={onTrail}/>;
    case "learning": return <CanonicalLearningJourneySpace onOpenPage={onOpenPage} onTrail={onTrail}/>;
    case "settings": return <CanonicalCapabilitiesSpace onNavigate={onNavigate} navigation={navigationFor(spaceId,navigation)} onTrail={onTrail}/>;
  }
  })();

  return <div ref={view} className="space-view" data-motion="enter">{content}{candidateTarget?<section aria-label="同源候选审核"><button onClick={()=>setCandidateTarget(undefined)}>关闭候选审核</button><CanonicalKnowledgeSpace key={candidateTarget.knowledge_id} initialCandidate={candidateTarget} showMachine={false} onLearning={key=>{if(key)onReviewItem?.(key);else onOpenPage?.("06");}}/></section>:null}{pinnedReference && <PinnedReferencePanel reference={pinnedReference} onClose={()=>setPinnedReference(null)} onOpenReference={setPinnedReference}/>}</div>;
}
