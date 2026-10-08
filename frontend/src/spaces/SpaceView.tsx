import { SpaceId } from "./spaces";
import { useEffect, useRef } from "react";
import { WorkspaceSpace } from "./WorkspaceSpace";
import { LibrarySpace } from "./LibrarySpace";
import { CanonicalLibrarySpace } from "./CanonicalLibrarySpace";
import { CanonicalKnowledgeSpace } from "./CanonicalKnowledgeSpace";
import { CanonicalLearningSpace } from "./CanonicalLearningSpace";
import { CanonicalCapabilitiesSpace } from "./CanonicalCapabilitiesSpace";
import { BackupPanel } from "../components/BackupPanel";
import { IntakeSpace } from "./IntakeSpace";
import { VaultSpace } from "./VaultSpace";
import { EvidenceSpace } from "./EvidenceSpace";
import { LearningSpace } from "./LearningSpace";
import { AiAssetsSpace } from "./AiAssetsSpace";
import { ExchangeSpace } from "./ExchangeSpace";
import { SettingsSpace } from "./SettingsSpace";
import type { InspectionTarget } from "../components/Inspector";
import type { ObjectTrailLevel } from "../components/NavTrail";
import type { CanonicalSurface } from "../presentation/spaceSections";

// The desktop shell routes spaces onto canonical surfaces; the secondary level and
// the object trail must describe the surface that is really rendered, not the space name.
export function canonicalSurface(spaceId: SpaceId, desktop: boolean): CanonicalSurface {
  if (!desktop) return "legacy";
  switch (spaceId) {
    case "workspace":
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
  navigation,
  selectedCapabilityId,
  onTrail,
}: {
  spaceId: SpaceId;
  onInspect: (target: InspectionTarget) => void;
  onNavigate: (id: SpaceId) => void;
  navigation?: SpaceNavigation;
  selectedCapabilityId?: string | null;
  onTrail?: (levels: readonly ObjectTrailLevel[]) => void;
}) {
  const view = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // Reuse the Avalonia AaosTheme route opacity transition (180ms), keeping
    // the existing content mounted so navigation never resets draft state.
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ||
        typeof view.current?.animate !== "function") return;
    const transition = view.current.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      { duration: 180, easing: "ease-out" },
    );
    return () => transition.cancel();
  }, [spaceId]);
  const content = (() => {
  if (selectedCapabilityId) {
    return <CanonicalCapabilitiesSpace onNavigate={onNavigate} selectedCapabilityId={selectedCapabilityId} navigation={navigation} onTrail={onTrail} />;
  }
  if (window.__TAURI__?.core?.invoke) {
    switch (spaceId) {
      case "workspace":
        return <>
          <CanonicalCapabilitiesSpace onNavigate={onNavigate} selectedCapabilityId={selectedCapabilityId} navigation={navigationFor(spaceId, navigation)} onTrail={onTrail} />
          <div className="space-section-region" data-section="backup" tabIndex={-1} aria-label="备份与恢复"><BackupPanel /></div>
        </>;
      case "library":
      case "intake":
      case "exchange":
        return <CanonicalLibrarySpace onKnowledge={()=>onNavigate("vault")} onInspect={onInspect} navigation={navigationFor(spaceId, navigation)} onTrail={onTrail} />;
      case "vault":
      case "evidence":
      case "ai-assets":
        return <CanonicalKnowledgeSpace onLearning={()=>onNavigate("learning")} onTrail={onTrail} />;
      case "learning":
        return <CanonicalLearningSpace onTrail={onTrail} />;
      case "settings":
        return <CanonicalCapabilitiesSpace onNavigate={onNavigate} selectedCapabilityId={selectedCapabilityId} navigation={navigationFor(spaceId, navigation)} onTrail={onTrail} />;
    }
  }
  switch (spaceId) {
    case "workspace":
      return <WorkspaceSpace onNavigate={onNavigate} />;
    case "library":
      return <LibrarySpace onInspect={onInspect} />;
    case "intake":
      return <IntakeSpace />;
    case "vault":
      return <VaultSpace />;
    case "evidence":
      return <EvidenceSpace onInspect={onInspect} />;
    case "learning":
      return <LearningSpace />;
    case "ai-assets":
      return <AiAssetsSpace onInspect={onInspect} />;
    case "exchange":
      return <ExchangeSpace />;
    case "settings":
      return <SettingsSpace />;
  }
  })();

  return <div ref={view} className="space-view" data-motion="enter">{content}</div>;
}
