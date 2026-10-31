import { AaosIcon, type AaosIconName } from "./AaosIcon";
import { FIRST_USE_STEPS, requestFirstUseGuide } from "./FirstUseGuide";
import "./UsageGuide.css";

export type GuideStep = { label: string; description: string; icon: AaosIconName };

const icons: readonly AaosIconName[] = ["Import", "Source", "Research", "Knowledge", "Review", "Settings", "HumanAi", "Review", "Source", "Apps"];
export const USAGE_GUIDE_STEPS: readonly GuideStep[] = FIRST_USE_STEPS.map((step, index) => ({ label: step.label, description: step.description, icon: icons[index] }));

/** Settings → 使用引导: the finite product loop without adding home-page chrome. */
export function UsageGuidePanel() {
  return <div className="usage-guide-panel">
    <p>用十步引导熟悉现有页面与双侧学习流程；普通导入、阅读和笔记不需要模型。引导记录与实际业务验收分别判断。</p>
    <button className="usage-guide-resume" type="button" onClick={requestFirstUseGuide}>开始或继续首次使用引导</button>
    <ol className="usage-guide-steps">
      {USAGE_GUIDE_STEPS.map((step, index) => <li key={step.label}>
        <span className="usage-guide-icon" aria-hidden="true"><AaosIcon name={step.icon} size={20}/></span>
        <span className="usage-guide-index" aria-hidden="true">{index + 1}</span>
        <span><strong>{step.label}</strong><small>{step.description}</small></span>
      </li>)}
    </ol>
    <p className="usage-guide-note">需要 AI 回答时：设置 → 模型与连接 → 一键连接本机 LM Studio。云端模型需要你自己录入密钥，且只在材料请求中按次确认上传与费用。</p>
  </div>;
}
