import { SpaceId, SPACES } from "../spaces/spaces";

export type BackendDisplayState = "checking" | "available" | "unavailable" | "web";

interface StatusBarProps {
  activeSpace: SpaceId;
  backendState: BackendDisplayState;
  externalDev?: boolean;
}

const BACKEND_LABELS: Record<BackendDisplayState, string> = {
  checking: "正在验证本地后端…",
  available: "后端状态：本地可用",
  unavailable: "后端状态：不可用",
  web: "浏览器开发模式",
};

// Presentation only: App owns every readiness transition and recovery action.
export function StatusBar({
  activeSpace,
  backendState,
  externalDev = false,
}: StatusBarProps) {
  const displayStatus = backendState === "web"
    ? "development"
    : backendState === "checking" ? "pending" : backendState;
  const activeLabel = SPACES.find((space) => space.id === activeSpace)?.label ?? "工作台";

  return (
    <header className="status-bar" role="banner">
      <div className="status-bar-brand">
        <span>星环知识平台</span>
        <small>ArcheAxis Knowledge</small>
        {externalDev ? <span className="dev-marker">开发</span> : null}
      </div>
      <div className="status-bar-center">
        <span
          className={`status-pill status-pill--${displayStatus}`}
          data-status={displayStatus}
        >
          {BACKEND_LABELS[backendState]}
        </span>
      </div>
      <div className="status-bar-space" aria-label="当前空间">
        {activeLabel}
      </div>
    </header>
  );
}
