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
import type { LibrarySection } from "../components/ContextNav";

// SpaceView renders the active space content (AXW-UI-802).
export function SpaceView({
  spaceId,
  onInspect,
  onNavigate,
  libraryNavigation,
}: {
  spaceId: SpaceId;
  onInspect: (target: InspectionTarget) => void;
  onNavigate: (id: SpaceId) => void;
  libraryNavigation?: { section: LibrarySection; sequence: number };
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
  if (window.__TAURI__?.core?.invoke) {
    switch (spaceId) {
      case "workspace":
        return <><CanonicalCapabilitiesSpace onNavigate={onNavigate} /><BackupPanel /></>;
      case "library":
      case "intake":
      case "exchange":
        return <CanonicalLibrarySpace onKnowledge={()=>onNavigate("vault")} onInspect={onInspect} navigation={spaceId === "library" ? libraryNavigation : undefined} />;
      case "vault":
      case "evidence":
      case "ai-assets":
        return <CanonicalKnowledgeSpace onLearning={()=>onNavigate("learning")} />;
      case "learning":
        return <CanonicalLearningSpace />;
      case "settings":
        return <CanonicalCapabilitiesSpace onNavigate={onNavigate} />;
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
