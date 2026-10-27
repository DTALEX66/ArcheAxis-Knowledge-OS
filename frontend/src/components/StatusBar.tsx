import { useState } from "react";
import type { SpaceId } from "../spaces/spaces";
import { CommandPalette } from "./CommandPalette";
import { ThemePicker } from "./ThemePicker";
import { DiagnosticCenterTrigger } from "./DiagnosticConsole";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { AAOS_THEME_REGISTRY } from "../design-system/theme";
import { useAaosTheme } from "../design-system/ThemeProvider";
import type { ObjectReference } from "../api/generated/research-contract";
import "./StitchWindowToolbar.css";

export type BackendDisplayState = "checking" | "available" | "unavailable" | "web";
interface StatusBarProps {
  activeSpace: SpaceId;
  backendState: BackendDisplayState;
  externalDev?: boolean;
  onPage?: (id: string) => void;
  onOpenObject?: (reference: ObjectReference, contentSha?: string) => void;
  onNavigate?: (id: SpaceId) => void;
  onOpenCapability?: (id: string) => void;
  selectedCapabilityId?: string | null;
  onCommandPaletteOpenChange?: (open: boolean) => void;
  commandPaletteOpenRequest?: number;
  inspectorOpen?: boolean;
  onToggleInspector?: () => void;
}
const BACKEND_LABELS: Record<BackendDisplayState, string> = {
  checking: "正在检查本地连接…", available: "本地连接可用", unavailable: "本地连接不可用", web: "浏览器预览",
};

/** App still owns readiness, recovery, commands and guarded navigation. No parallel state. */
export function StatusBar({ backendState, externalDev = false, onNavigate = () => {}, onPage, onOpenObject, onOpenCapability, selectedCapabilityId, onCommandPaletteOpenChange, commandPaletteOpenRequest, inspectorOpen = true, onToggleInspector = () => {} }: StatusBarProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { theme } = useAaosTheme();
  return <div className="stitch-window-tools" role="group" aria-label="搜索与工作空间工具">
    <span className="status-bar-brand" aria-hidden="true" style={{display:"none"}}><img src={AAOS_THEME_REGISTRY[theme].brandMark} alt=""/></span>
    <CommandPalette openRequest={commandPaletteOpenRequest} onPage={onPage} onOpenObject={onOpenObject} onNavigate={onNavigate} onOpenCapability={onOpenCapability} onOpenChange={onCommandPaletteOpenChange}/>
    <span className="stitch-connection-state" data-state={backendState} role="status" title={BACKEND_LABELS[backendState]}>{BACKEND_LABELS[backendState]}{externalDev ? " · 开发" : ""}</span>
    {!selectedCapabilityId ? <button type="button" className="inspector-trigger stitch-window-icon" aria-keyshortcuts="Control+Alt+I" aria-label={inspectorOpen ? "收起相关资料" : "显示相关资料"} aria-expanded={inspectorOpen} onClick={onToggleInspector} title="相关资料（Ctrl+Alt+I）">◧</button> : null}
    <DiagnosticCenterTrigger/>
    <AaosDialog title="界面与工具" description="调整界面主题或打开设置。" open={settingsOpen} onOpenChange={setSettingsOpen} trigger={<button type="button" className="stitch-window-tool-settings" aria-label="界面与工具设置">工具</button>} contentClassName="stitch-window-settings-dialog"><ThemePicker/><button type="button" onClick={()=>setSettingsOpen(false)}>关闭工具</button><button type="button" onClick={() => { setSettingsOpen(false); onPage?.("19"); }}>打开设置</button></AaosDialog>
  </div>;
}
