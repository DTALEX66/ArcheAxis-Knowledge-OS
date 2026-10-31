import type { ReactNode } from "react";
import { useConsoleWindow } from "./ConsoleWindow";
import { AaosIcon } from "./AaosIcon";
import "./StitchWindowToolbar.css";

interface Breadcrumb { label: string; onClick?: () => void }

/** One window titlebar; App supplies its existing command/status tools as children. */
export function TopNavBar({ breadcrumbs, children }: { breadcrumbs: Breadcrumb[]; children?: ReactNode }) {
  const window = useConsoleWindow();
  return <header className="stitch-window-toolbar" aria-label="主控台工具栏">
    <div className="stitch-window-title" onPointerDown={event => window?.begin(event, "move")} onPointerMove={window?.move} onPointerUp={window?.end} onPointerCancel={window?.cancel} onLostPointerCapture={window?.end}>
      {window ? <><span id="console-window-help" className="sr-only">拖动标题移动；方向键移动，Shift 加方向键调整大小；Esc 取消；窄窗口自动铺满。</span><button type="button" className="console-move-handle stitch-window-icon" aria-label="移动主控台" aria-describedby="console-window-help" onKeyDown={window.keys} disabled={window.mode !== "floating"} title={window.mode === "floating" ? "移动主控台" : "当前主控台已铺满"}><AaosIcon name="Workspace" size={18}/></button></> : <AaosIcon name="Workspace" size={18}/>}
      <nav aria-label="当前工作位置"><ol>{breadcrumbs.map((crumb, index) => <li key={index} aria-current={index === breadcrumbs.length - 1 ? "page" : undefined}>{crumb.onClick ? <button type="button" onClick={crumb.onClick}>{crumb.label}</button> : <span title={crumb.label}>{crumb.label}</span>}</li>)}</ol></nav>
    </div>
    {children}
    {window ? <div className="stitch-window-controls" role="group" aria-label="主控台窗口操作"><button type="button" className="stitch-window-icon" aria-label={window.mode === "floating" ? "铺满主控台" : "还原主控台"} onClick={window.toggle} disabled={window.mode === "compact"} title={window.mode === "compact" ? "可用空间较小，主控台自动铺满" : undefined}>{window.mode === "floating" ? "□" : "▣"}</button><button type="button" className="stitch-window-icon" aria-label="复位主控台" onClick={window.reset} title="复位主控台的位置和大小">↺</button></div> : null}
  </header>;
}
