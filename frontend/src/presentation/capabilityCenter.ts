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
const operationNames: Readonly<Record<string,string>> = {
 "archive.inventory":"压缩包清点", "canvas.structure":"画布结构读取", "document.detect":"文件格式识别",
 "html.structure":"网页结构读取", "image.caption":"图片内容说明", "image.ocr":"图片文字识别",
 "media.diarize":"说话人区分", "media.probe":"媒体信息读取", "media.transcribe":"音频转写",
 "media.video":"视频内容处理", "office.structure":"Office文档结构读取", "pdf.extract":"PDF内容提取",
 "subtitles.structure":"字幕读取", "machine.answer":"AI回答", "course.general":"通用课程", "search.semantic":"语义检索",
};
export function capabilityOperationName(operation:string):string{return operationNames[operation]??"处理步骤（名称待核对）";}
// Display translations only. Original declarations and search aliases stay intact.
const detailNames: Readonly<Record<string,string>> = {
 "approved root":"已获访问授权的资料目录", "hash before write":"写入前核对原件指纹", "hash 读回":"重新读取并核对内容指纹",
 "fixture":"可复现样例", "fixture 通过":"可复现样例通过", "CER/WER gate":"文字识别与转写错误率检查",
 "extension fallback":"可选扩展替代方案", "honest unavailable":"缺少支持时明确显示不可用",
 "truth/prediction pairs":"成对的人工真值与预测结果", "anchor 回跳":"返回引文原始位置", "EvidenceAnchor 绑定":"绑定可定位的来源依据",
 "experimental 受限":"实验功能限制使用", "fallback":"降级与替代方案", "统一 manifest":"统一的产物说明",
 "engine-agnostic 数据合同":"不绑定特定引擎的数据接口", "2D/text fallback":"二维图或文字替代方案",
 "expected-hash":"写入前核对预期内容指纹", "原子写":"完整写入或保持原内容", "C4 安全往返":"安全导出与导入往返",
 "restart readback":"重启后重新读取核对", "manifest":"能力与资料说明", "dry-run":"先预览执行影响", "sandbox":"隔离运行范围",
 "checkpoint":"保存恢复点", "trace":"可追溯的执行记录", "cancel":"可取消", "rollback":"可回退",
 "原件 / CAS":"原件与指纹存储", "稳定对象ID":"稳定对象编号", "损失与失败回执":"转换损失与失败详情",
 "使用回执":"使用记录", "五类交换合同":"五类内容交换方式", "知识ID与坐标":"知识编号与位置",
 "World / Room / Locus / Route":"场景、房间、位置与路线", "Profile / Recipe / Event":"学习画像、训练方案与学习事件",
 "LER与Learning Compiler":"学习内容编排与教学生成",
 "语义模型 / 维度 / 分块 / 哈希":"语义检索模型与内容分段", "混合检索与rerank":"混合检索与结果重排",
 "人工 / 导入 / AI推断关系身份":"区分人工、导入与AI推断的关系来源",
 "Tauri正式桌面":"正式桌面应用", "统一React产品界面":"统一产品界面", "宿主adapter":"桌面接入适配",
 "有限知识Job":"有限知识处理任务", "取消 / 检查点 / 回执":"取消、恢复点与运行记录", "受限runner":"受限任务执行",
 "Worker / Plugin / Skill / Provider / Tool身份":"执行引擎、插件、技能、服务与工具的身份", "模型 / Provider":"模型与服务提供方",
};
export function capabilityDetailText(text:string):string{return detailNames[text]??text;}
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
