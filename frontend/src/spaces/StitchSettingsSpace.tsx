import { useId, useRef, useState, type KeyboardEvent } from "react";
import { BackupPanel } from "../components/BackupPanel";
import { ModelConfigurationPanel } from "../components/ModelConfigurationPanel";
import { ConfigurationPlanPanel } from "../components/ConfigurationPlanPanel";
import { UsageGuidePanel } from "../components/UsageGuide";
import "./stitch-settings.css";

const sections = [
  { id: "models", label: "模型与连接", description: "连接本地模型服务，管理配置与用途绑定。" },
  { id: "guide", label: "使用引导", description: "从导入到知识的完整使用顺序。" },
  { id: "workspace", label: "工作区与恢复", description: "创建一致备份，核对产物后预检与恢复工作区。" },
  { id: "plans", label: "配置计划", description: "读取本机配置与部署计划，核对来源和版本。" },
] as const;
type SettingsSection = typeof sections[number]["id"];

// Each real consumer stays mounted once. Changing the presentation never resets
// a model draft, a restore confirmation, or a read receipt.
export function StitchSettingsSpace({ hasUnsavedDrafts = false }: { hasUnsavedDrafts?: boolean }) {
  const [active, setActive] = useState<SettingsSection>("models");
  const id = useId();
  const tabs = useRef<Array<HTMLButtonElement | null>>([]);
  const current = sections.find(section => section.id === active)!;

  function moveTab(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next: number;
    if (event.key === "ArrowRight") next = (index + 1) % sections.length;
    else if (event.key === "ArrowLeft") next = (index + sections.length - 1) % sections.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = sections.length - 1;
    else return;
    event.preventDefault();
    setActive(sections[next].id);
    tabs.current[next]?.focus();
  }

  return <section className="stitch-settings" aria-label="系统与可靠性" data-section="backup" tabIndex={-1}>
    <header className="stitch-settings-topic">
      <div><p className="stitch-settings-eyebrow">本地设置</p><h2>设置 · 模型与连接</h2></div>
      <p>模型配置、工作区备份与配置计划</p>
    </header>
    <div className="stitch-settings-subnav">
      <div role="tablist" aria-label="设置分组">
        {sections.map((section, index) => <button
          key={section.id} type="button" role="tab"
          id={`${id}-tab-${section.id}`} aria-controls={`${id}-panel-${section.id}`}
          aria-selected={active === section.id} tabIndex={active === section.id ? 0 : -1}
          ref={element => { tabs.current[index] = element; }}
          onClick={() => setActive(section.id)} onKeyDown={event => moveTab(event, index)}
        >{section.label}</button>)}
      </div>
      <span>切换分组保留当前表单</span>
    </div>
    <p className="stitch-settings-intro">{current.description}</p>
    <div className="stitch-settings-content">
      <section className="stitch-settings-pane stitch-settings-models" role="tabpanel"
        id={`${id}-panel-models`} aria-labelledby={`${id}-tab-models`} hidden={active !== "models"} tabIndex={0}>
        <ModelConfigurationPanel />
      </section>
      <section className="stitch-settings-pane" role="tabpanel"
        id={`${id}-panel-guide`} aria-labelledby={`${id}-tab-guide`} hidden={active !== "guide"} tabIndex={0}>
        <UsageGuidePanel />
      </section>
      <section className="stitch-settings-pane stitch-settings-workspace" role="tabpanel"
        id={`${id}-panel-workspace`} aria-labelledby={`${id}-tab-workspace`} hidden={active !== "workspace"} tabIndex={0}>
        <div className="stitch-settings-notice"><p>普通笔记与草稿可先保存，依据分析、专业采用与 AI 资格分别记录。</p><p>权限配置界面尚未接通。恢复通过本地宿主执行，浏览器未连接时明确不可用。</p></div>
        <BackupPanel hasUnsavedDrafts={hasUnsavedDrafts} />
      </section>
      <section className="stitch-settings-pane stitch-settings-plans" role="tabpanel"
        id={`${id}-panel-plans`} aria-labelledby={`${id}-tab-plans`} hidden={active !== "plans"} tabIndex={0}>
        <ConfigurationPlanPanel />
      </section>
    </div>
  </section>;
}
