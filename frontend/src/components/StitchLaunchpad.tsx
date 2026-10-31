import { useRef, useState } from "react";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { CAPABILITY_NAVIGATION_ENTRIES, EFFECTIVE_NAVIGATION_ENTRIES, type EffectiveNavigationEntry } from "../presentation/navigation";
import { capabilityPresentation, capabilityDesignDetails, capabilityDetailText, CAPABILITY_DESIGN_DETAIL_COUNT } from "../presentation/capabilityCenter";
import { AaosIcon, type AaosIconName } from "./AaosIcon";
import "./StitchLaunchpad.css";

// A menu projection of existing routes and catalog entries, never an execution registry.
const frequentPages = ["16", "02", "03", "05", "04", "21", "06", "07", "13", "19"];
const pageIcons: Readonly<Record<string, AaosIconName>> = {
  "01": "Home", "02": "Knowledge", "03": "Write", "04": "Connection", "05": "Research",
  "06": "LearningPath", "07": "Learning", "08": "Learning", "09": "Evidence", "10": "Source",
  "11": "Review", "12": "Write", "13": "Context", "14": "Review", "15": "Extension",
  "16": "ImportDocument", "17": "Apps", "19": "Settings", "20": "Source", "21": "Canvas", "22": "Workflow",
};
function entryIcon(entry: EffectiveNavigationEntry): AaosIconName {
  if (entry.page) return pageIcons[entry.page.id] ?? "Source";
  const capabilityIcons: Readonly<Record<string, AaosIconName>> = {
    "CAP-0060": "Learning", "CAP-0070": "Workflow", "CAP-0080": "Spatial",
    "CAP-0100": "Extension", "CAP-0130": "Workflow", "CAP-0150": "HumanAi", "CAP-0160": "Workspace",
  };
  return capabilityIcons[entry.capability?.atlas.capability_id ?? ""] ?? "Extension";
}
type Category = "frequent" | "pages" | "extensions" | "capabilities";

export function StitchLaunchpad({ open, onOpenChange, onPage, onCapability }: {
  open: boolean; onOpenChange: (open: boolean) => void;
  onPage: (page: string) => boolean | void;
  onCapability: (id: string) => boolean | void;
}) {
  const [query, setQuery] = useState("");
  const searchInput = useRef<HTMLInputElement>(null);
  const [category, setCategory] = useState<Category>("frequent");
  const term = query.trim().toLocaleLowerCase();
  const rows = EFFECTIVE_NAVIGATION_ENTRIES.filter(entry => {
    if (entry.page) {
      if (entry.page.id === "18" || category === "extensions" || category === "capabilities") return false;
      if (category === "frequent" && !term && !frequentPages.includes(entry.page.id)) return false;
    } else if (entry.capability) {
      const presentation = capabilityPresentation(entry.capability);
      if (category === "pages" || (category === "frequent" && !term)) return false;
      if (category === "extensions" && presentation.group === "builtin") return false;
    } else return false;
    return !term || [entry.label, entry.description, ...entry.aliases, ...entry.keywords].join(" ").toLocaleLowerCase().includes(term) || Boolean(entry.capability && capabilityDesignDetails(entry.entry_id, term).length);
  });
  const close = () => onOpenChange(false);
  return <AaosDialog open={open} onOpenChange={onOpenChange} title="全部能力" description="“常用入口”只是部分工作页面。查看所有能力请选“全部能力族”；查看完整蓝图请点“查看完整能力目录”，再选“全部设计细项”。"
    overlayClassName="stitch-launchpad-overlay" contentClassName="stitch-launchpad"
    onOpenAutoFocus={event => { event.preventDefault(); searchInput.current?.focus(); }}
    onCloseAutoFocus={event => { event.preventDefault(); document.getElementById("stitch-launchpad-toggle")?.focus(); }}>
    <button className="stitch-launchpad-close" type="button" aria-label="关闭能力启动台" onClick={close}><AaosIcon name="Close"/></button>
    <div className="stitch-launchpad-catalog"><span>{CAPABILITY_NAVIGATION_ENTRIES.length} 个能力族 · {CAPABILITY_DESIGN_DETAIL_COUNT} 条设计细项</span><button type="button" onClick={() => { if (onPage("17") !== false) close(); }}>查看完整能力目录</button></div>
    <label className="stitch-launchpad-search"><AaosIcon name="Search"/><span className="aaos-sr-only">搜索能力</span>
      <input ref={searchInput} value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索能力、页面或用途…"/>
    </label>
    <div className="stitch-launchpad-categories" role="group" aria-label="能力分类">
      {([["frequent", "常用入口"], ["pages", "全部页面"], ["capabilities", "全部能力族"], ["extensions", "扩展与未来"]] as const).map(([id, label]) =>
        <button key={id} type="button" aria-pressed={category === id} onClick={() => setCategory(id)}>{label}</button>)}
    </div>
    <div className="stitch-launchpad-results">
      <ul className="stitch-launchpad-grid" aria-label="能力入口">
        {rows.map(entry => {
          const future = entry.capability && capabilityPresentation(entry.capability).group === "future";
          const description = entry.capability ? capabilityPresentation(entry.capability).purpose : entry.description;
          const status = entry.page ? "打开工作界面" : future ? "规划中 · 查看说明" : "查看接入条件";
          const matches = term && entry.capability ? capabilityDesignDetails(entry.entry_id, term) : [];
          return <li key={entry.entry_id}><button type="button" data-future={future || undefined} onClick={() => {
            const accepted = entry.page ? onPage(entry.page.id) : onCapability(entry.entry_id);
            if (accepted !== false) close();
          }}>
            <span className="stitch-launchpad-icon"><AaosIcon name={entryIcon(entry)} size={28}/></span>
            <span className="stitch-launchpad-label">{entry.label}</span>
            <span className="stitch-launchpad-purpose">{description}</span>
            {matches.length ? <span className="stitch-launchpad-match">匹配细项：{matches.slice(0, 2).map(capabilityDetailText).join("、")}{matches.length > 2 ? `等 ${matches.length} 项` : ""}<br/>设计内容 · 独立证据未核验</span> : null}
            <small>{status}</small>
          </button></li>;
        })}
      </ul>
      {!rows.length && <p className="stitch-launchpad-empty" role="status">未找到“{query}”。试试资料、研究、学习或恢复。</p>}
    </div>
    <footer><span>{category === "frequent" && !term ? `当前显示 ${rows.length} 个常用入口（部分工作页面）` : `${rows.length} 个入口`}</span><span>关闭菜单不会取消正在进行的任务</span></footer>
  </AaosDialog>;
}
