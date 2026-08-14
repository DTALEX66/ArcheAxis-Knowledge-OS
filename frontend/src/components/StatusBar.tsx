import { SpaceId } from "../spaces/spaces";

// Top status bar: backend/task status + current space (task pack §15.3).
export function StatusBar({ activeSpace }: { activeSpace: SpaceId }) {
  return (
    <header className="status-bar" role="banner">
      <div className="status-bar-brand">ArcheAxis Knowledge</div>
      <div className="status-bar-center">
        <span className="status-pill status-pill--pending" data-status="pending">
          后端状态：等待握手
        </span>
      </div>
      <div className="status-bar-space" aria-label="当前空间">
        {activeSpace}
      </div>
    </header>
  );
}
