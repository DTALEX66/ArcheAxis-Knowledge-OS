import type { CapabilityCatalogEntry } from "../api/generated/capability-catalog";

// User-purpose copy only. Identity/implementation remain in the generated Atlas/map;
// these labels neither register executable packages nor qualify a runtime.
const purposes: Readonly<Record<string, string>> = {
  "CAP-0010": "保留原件，整理资料与版本",
  "CAP-0020": "转换常用格式，保留定位与损失说明",
  "CAP-0030": "查看来源、引用与核验依据",
  "CAP-0040": "安排学习、练习与复习",
  "CAP-0050": "管理 AI 上下文、纠正与受控调用",
  "CAP-0060": "组织课程、课时与外部测验候选",
  "CAP-0070": "用动态解释与仿真理解知识",
  "CAP-0080": "探索空间记忆与沉浸学习",
  "CAP-0090": "组织研究问题、材料与结论",
  "CAP-0100": "连接外部工具与生态能力",
  "CAP-0110": "搜索内容，探索双链与知识关系",
  "CAP-0120": "管理桌面工作区与可靠性",
  "CAP-0130": "探索有边界的任务执行与编排",
  "CAP-0140": "备份、恢复与交换内容",
  "CAP-0150": "统一模型服务、用途与数据边界",
  "CAP-0160": "用可视化与空间表征辅助学习",
};
export type CapabilityGroup = "builtin" | "extension" | "future";
export function capabilityPresentation(entry: CapabilityCatalogEntry) {
  const future = entry.implementation.state === "not_implemented";
  const group: CapabilityGroup = future ? "future" : entry.atlas.capability_id === "CAP-0060" ? "extension" : "builtin";
  return {
    purpose: purposes[entry.atlas.capability_id] ?? entry.atlas.canonical_name,
    group,
    form: future ? "接入形态待实现" : group === "extension" ? "课程入口与可选适配器" : entry.implementation.state === "worker_backed" ? "内置底座入口 · 专用引擎按需使用" : "内置工作流",
    status: future ? "完整能力尚未接入" : "已有实现声明 · 运行状态需另核对",
  };
}
