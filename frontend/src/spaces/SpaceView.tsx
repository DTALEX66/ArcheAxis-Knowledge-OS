import { SpaceId } from "./spaces";
import { WorkspaceSpace } from "./WorkspaceSpace";
import { LibrarySpace } from "./LibrarySpace";
import { IntakeSpace } from "./IntakeSpace";
import { VaultSpace } from "./VaultSpace";
import { EvidenceSpace } from "./EvidenceSpace";
import { LearningSpace } from "./LearningSpace";
import { AiAssetsSpace } from "./AiAssetsSpace";
import { ExchangeSpace } from "./ExchangeSpace";
import { SettingsSpace } from "./SettingsSpace";
import type { InspectionTarget } from "../components/Inspector";

// SpaceView renders the active space content (AXW-UI-802).
export function SpaceView({
  spaceId,
  onInspect,
  onNavigate,
}: {
  spaceId: SpaceId;
  onInspect: (target: InspectionTarget) => void;
  onNavigate: (id: SpaceId) => void;
}) {
  const content = (() => {
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

  return <div className="space-view" data-motion="enter">{content}</div>;
}
