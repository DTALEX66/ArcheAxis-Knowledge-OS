import { SpaceId, SPACES } from "../spaces/spaces";
import { useAaosTheme } from "../design-system/ThemeProvider";
import { AAOS_THEME_REGISTRY, BRAND_MARK_SLOT } from "../design-system/theme";
import { CAPABILITY_CATALOG } from "../api/generated/capability-catalog";
import { CommandPalette } from "./CommandPalette";
import { ThemePicker } from "./ThemePicker";
import { AaosIcon } from "./AaosIcon";
import type { ObjectReference } from "../api/generated/research-contract";
import { SpaceTopNavigation } from "./SpaceTopNavigation";
export type BackendDisplayState = "checking" | "available" | "unavailable" | "web";

interface StatusBarProps {
  activeSpace: SpaceId;
  backendState: BackendDisplayState;
  externalDev?: boolean;
  onPage?: (id:string)=>void;
  onOpenObject?: (reference:ObjectReference,contentSha?:string)=>void;
  onNavigate?: (id: SpaceId) => void;
  onOpenCapability?: (id: string) => void;
  selectedCapabilityId?: string | null;
  onCommandPaletteOpenChange?: (open: boolean) => void;
  commandPaletteOpenRequest?: number;
  inspectorOpen?: boolean;
  onToggleInspector?: () => void;
  navigationAppearance?: "sidebar" | "top";
  onNavigationAppearance?: (value: "sidebar" | "top") => void;
  pageId?: string;
  learningFocus?: boolean;
}

const BACKEND_LABELS: Record<BackendDisplayState, string> = {
  checking: "正在检查本地连接…",
  available: "本地连接可用",
  unavailable: "本地连接不可用",
  web: "浏览器预览",
};

// Presentation only: App owns every readiness transition and recovery action.
export function StatusBar({
  activeSpace,
  backendState,
  externalDev = false,
  onNavigate = () => {}, onPage, onOpenObject,
  onOpenCapability,
  selectedCapabilityId,
  onCommandPaletteOpenChange,
  commandPaletteOpenRequest,
  inspectorOpen = true,
  onToggleInspector = () => {},
  navigationAppearance = "sidebar", onNavigationAppearance, pageId, learningFocus = false,
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
        <span className="brand-name">星环知识系统<small>ArcheAxis Knowledge</small></span>
        {externalDev ? <span className="dev-marker">开发</span> : null}
      </div>
      {navigationAppearance === "top" && !learningFocus && onPage ? <SpaceTopNavigation activeSpace={activeSpace} pageId={pageId} onPage={onPage} activeCapabilityId={selectedCapabilityId}/> : null}
      <CommandPalette openRequest={commandPaletteOpenRequest} onPage={onPage} onOpenObject={onOpenObject} onNavigate={onNavigate} onOpenCapability={onOpenCapability} onOpenChange={onCommandPaletteOpenChange} />
      {activeSpace !== "workspace" && navigationAppearance !== "top" ? <ThemePicker /> : null}
      <div className="status-bar-center">
        <span
          className={`status-pill status-pill--${displayStatus}`}
          data-status={displayStatus}
          title={BACKEND_LABELS[backendState]}
          role="status"
        >
          {backendState === "available" && activeSpace === "workspace" ? "本地可用" : BACKEND_LABELS[backendState]}
        </span>
      </div>
      <div className="status-bar-space" role="group" aria-label="当前空间">
        {activeLabel}
      </div>
      {!selectedCapabilityId ? <button type="button" className="inspector-trigger" title="展开/折叠检查器（Ctrl+Alt+I）" aria-keyshortcuts="Control+Alt+I" aria-label={inspectorOpen ? "折叠检查器" : "展开检查器"} aria-expanded={inspectorOpen} onClick={onToggleInspector}>◧</button> : null}
      <details className="cabin-settings"><summary aria-label="界面设置"><AaosIcon name="Settings" size={24}/></summary><div>{activeSpace === "workspace" || navigationAppearance === "top" ? <ThemePicker/> : null}{onNavigationAppearance ? <label className="navigation-appearance">导航呈现<select aria-label="导航呈现" value={navigationAppearance} onChange={event=>onNavigationAppearance(event.target.value as "sidebar" | "top")}><option value="sidebar">侧栏导航</option><option value="top">顶部菜单</option></select><small>仅保存在此浏览器，不更改工作区布局。</small></label> : null}<button type="button" onClick={()=>onPage?.("19")}>打开设置</button></div></details>
    </header>
  );
}
