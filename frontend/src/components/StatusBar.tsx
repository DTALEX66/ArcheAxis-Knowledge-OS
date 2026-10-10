import { SpaceId, SPACES } from "../spaces/spaces";
import { useAaosTheme } from "../design-system/ThemeProvider";
import { AAOS_THEME_REGISTRY, BRAND_MARK_SLOT } from "../design-system/theme";
import { CAPABILITY_CATALOG } from "../api/generated/capability-catalog";
import { CommandPalette } from "./CommandPalette";
import { ThemePicker } from "./ThemePicker";
export type BackendDisplayState = "checking" | "available" | "unavailable" | "web";

interface StatusBarProps {
  activeSpace: SpaceId;
  backendState: BackendDisplayState;
  externalDev?: boolean;
  onPage?: (id:string)=>void;
  onNavigate?: (id: SpaceId) => void;
  onOpenCapability?: (id: string) => void;
  selectedCapabilityId?: string | null;
  onCommandPaletteOpenChange?: (open: boolean) => void;
  inspectorOpen?: boolean;
  onToggleInspector?: () => void;
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
  onNavigate = () => {}, onPage,
  onOpenCapability,
  selectedCapabilityId,
  onCommandPaletteOpenChange,
  inspectorOpen = true,
  onToggleInspector = () => {},
}: StatusBarProps) {
  const { theme } = useAaosTheme();
  const displayStatus = backendState === "web"
    ? "development"
    : backendState === "checking" ? "pending" : backendState;
  const activeLabel = selectedCapabilityId
    ? CAPABILITY_CATALOG.entries.find((entry) => entry.atlas.capability_id === selectedCapabilityId)?.atlas.canonical_name ?? selectedCapabilityId
    : SPACES.find((space) => space.id === activeSpace)?.label ?? "工作台";

  return (
    <header className="status-bar" role="banner">
      <div className="status-bar-brand">
        <img className="brand-mark" src={AAOS_THEME_REGISTRY[theme].brandMark} width={BRAND_MARK_SLOT.width} height={BRAND_MARK_SLOT.height} alt="" aria-hidden="true" />
        <span>星环知识平台</span>
        {externalDev ? <span className="dev-marker">开发</span> : null}
      </div>
      <CommandPalette onPage={onPage} onNavigate={onNavigate} onOpenCapability={onOpenCapability} onOpenChange={onCommandPaletteOpenChange} />
      <ThemePicker />
      <div className="status-bar-center">
        <span
          className={`status-pill status-pill--${displayStatus}`}
          data-status={displayStatus}
          title={BACKEND_LABELS[backendState]}
          role="status"
        >
          {BACKEND_LABELS[backendState]}
        </span>
      </div>
      <div className="status-bar-space" role="group" aria-label="当前空间">
        {activeLabel}
      </div>
      {!selectedCapabilityId ? <button type="button" className="inspector-trigger" title="展开/折叠检查器（Ctrl+Alt+I）" aria-keyshortcuts="Control+Alt+I" aria-label={inspectorOpen ? "折叠检查器" : "展开检查器"} aria-expanded={inspectorOpen} onClick={onToggleInspector}>◧</button> : null}
    </header>
  );
}
