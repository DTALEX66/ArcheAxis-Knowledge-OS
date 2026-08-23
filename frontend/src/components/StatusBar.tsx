import { SpaceId } from "../spaces/spaces";

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
  web: "浏览器开发模式（Web development mode）",
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

  return (
    <header className="status-bar" role="banner">
      <div className="status-bar-brand">
        ArcheAxis Knowledge
        {externalDev ? <span className="dev-marker">DEV</span> : null}
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
        {activeSpace}
      </div>
    </header>
  );
}
