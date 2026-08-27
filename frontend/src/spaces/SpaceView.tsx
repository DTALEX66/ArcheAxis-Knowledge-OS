import { SpaceId } from "./spaces";
import { WorkspaceSpace } from "./WorkspaceSpace";
import { LibrarySpace } from "./LibrarySpace";
import { EvidenceSpace } from "./EvidenceSpace";
import { LearningSpace } from "./LearningSpace";
import { AiAssetsSpace } from "./AiAssetsSpace";
import { SettingsSpace } from "./SettingsSpace";
import type { InspectionTarget } from "../components/Inspector";

// SpaceView renders the active six-space content (AXW-UI-802).
export function SpaceView({
  spaceId,
  onInspect,
  onNavigate,
}: {
  spaceId: SpaceId;
  onInspect: (target: InspectionTarget) => void;
  onNavigate: (id: SpaceId) => void;
}) {
  switch (spaceId) {
    case "workspace":
      return <WorkspaceSpace onNavigate={onNavigate} />;
    case "library":
      return <LibrarySpace onInspect={onInspect} />;
    case "evidence":
      return <EvidenceSpace onInspect={onInspect} />;
    case "learning":
      return <LearningSpace />;
    case "ai-assets":
      return <AiAssetsSpace onInspect={onInspect} />;
    case "settings":
      return <SettingsSpace />;
  }
}
