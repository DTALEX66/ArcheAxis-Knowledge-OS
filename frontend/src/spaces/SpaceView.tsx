import { SpaceId } from "./spaces";
import { WorkspaceSpace } from "./WorkspaceSpace";
import { LibrarySpace } from "./LibrarySpace";
import { EvidenceSpace } from "./EvidenceSpace";
import { LearningSpace } from "./LearningSpace";
import { AiAssetsSpace } from "./AiAssetsSpace";
import { SettingsSpace } from "./SettingsSpace";

// SpaceView renders the active six-space content (AXW-UI-802).
export function SpaceView({ spaceId }: { spaceId: SpaceId }) {
  switch (spaceId) {
    case "workspace":
      return <WorkspaceSpace />;
    case "library":
      return <LibrarySpace />;
    case "evidence":
      return <EvidenceSpace />;
    case "learning":
      return <LearningSpace />;
    case "ai-assets":
      return <AiAssetsSpace />;
    case "settings":
      return <SettingsSpace />;
  }
}
