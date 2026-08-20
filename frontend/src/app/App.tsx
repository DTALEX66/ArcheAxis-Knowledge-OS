import { useCallback, useState } from "react";
import { SpaceId, SPACES } from "../spaces/spaces";
import { StatusBar } from "../components/StatusBar";
import { SpaceRail } from "../components/SpaceRail";
import { ActivityDock } from "../components/ActivityDock";
import { Inspector, type InspectionTarget } from "../components/Inspector";
import { SpaceView } from "../spaces/SpaceView";

// AXW-UI-802: six-space shell following task pack §15.3 fixed structure:
// top status bar | left rail (six spaces) | context subnav | center view |
// right inspector | bottom activity dock.
export function App() {
  const [activeSpace, setActiveSpace] = useState<SpaceId>("workspace");
  const [inspectionTarget, setInspectionTarget] = useState<InspectionTarget | null>(null);

  const navigate = useCallback((id: SpaceId) => {
    setActiveSpace(id);
    setInspectionTarget(null);
  }, []);

  return (
    <div className="app-shell">
      <StatusBar activeSpace={activeSpace} />
      <div className="app-body">
        <SpaceRail active={activeSpace} onNavigate={navigate} spaces={SPACES} />
        <main className="app-center" role="main" aria-label="当前空间内容">
          <SpaceView spaceId={activeSpace} onInspect={setInspectionTarget} />
        </main>
        <Inspector target={inspectionTarget} />
      </div>
      <ActivityDock />
    </div>
  );
}
