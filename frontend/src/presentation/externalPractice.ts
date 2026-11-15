import type { TeachingRecord } from "../api/generated/teaching-contract";

type Kind=TeachingRecord["kind"];
export const teachingParents:Partial<Record<Kind,readonly Kind[]>>={
  observation:["proposal","revision"],requirement:["observation"],proposal:["requirement"],
  delivery:["proposal","revision"],teach_back:["delivery"],feedback:["delivery","observation"],revision:["proposal","revision","feedback"],
};
export const teachingParentRequired=(kind:Kind)=>!["observation","requirement"].includes(kind);
export const practiceActions={
  requirement:{label:"明确实践需求",kind:"requirement",parents:[],outline:"想练习什么：\n\n为什么需要练习：\n\n计划如何检查：\n"},
  plan:{label:"拟定实践计划",kind:"proposal",parents:["requirement"],outline:"实践目标与步骤：\n\n可选教程名称或链接：\n\n预计使用的外部工具（可不连接）：\n\n如何记录过程和反馈：\n"},
  revise:{label:"调整实践计划",kind:"revision",parents:["proposal","revision","feedback"],outline:"计划要调整的内容：\n\n调整原因：\n\n调整后的步骤：\n"},
  skip:{label:"跳过教程",kind:"revision",parents:["proposal","revision"],outline:"决定跳过的教程名称或链接：\n\n跳过原因：\n\n保留或调整后的实践步骤：\n"},
  replace:{label:"替换教程",kind:"revision",parents:["proposal","revision"],outline:"原教程名称或链接：\n\n替换教程名称或链接：\n\n替换原因与新的实践步骤：\n"},
  start:{label:"记录本人开始实践",kind:"observation",parents:["proposal","revision"],outline:"本人开始的步骤与时间：\n\n使用的教程或工具（可无）：\n\n当前情况：\n\n这是本人记录，不证明外部工具已执行或已经掌握。\n"},
  note:{label:"记录实践过程",kind:"observation",parents:["proposal","revision"],outline:"实际做过的事情：\n\n遇到的问题和尝试：\n\n可选成果或链接（没有也可保存）：\n\n仍不确定的地方：\n"},
  complete:{label:"记录本人自报完成",kind:"observation",parents:["proposal","revision"],outline:"本人自报完成的步骤：\n\n实际结果与局限：\n\n可选成果或链接（没有也可保存）：\n\n仍需独立检查的地方：\n\n这是本人自报，不是独立评价或掌握证明。\n"},
  feedback:{label:"反馈文字实践记录",kind:"feedback",parents:["observation"],outline:"所针对的实际文字记录：\n\n反馈与理由：\n\n下一步建议：\n\n这是人工反馈，不自动计分或提升掌握。\n"},
} as const;
export type PracticeAction=keyof typeof practiceActions;
export function practiceDraft(action:PracticeAction) {
  const entry=practiceActions[action];
  return {kind:entry.kind,purpose:`外部实践 · ${entry.label}`,content:entry.outline};
}
/** UI admission is a convenience; Core alone checks currentness and authorization at write. */
export function usableTeachingSource(kind:Kind,row:Record<string,unknown>) {
  if(row.status!=="candidate"&&row.status!=="accepted")return false;
  return kind!=="delivery"||row.status==="accepted"||["PERSONAL_DEFINITION","PERSONAL_EXPERIENCE"].includes(String(row.knowledge_type));
}
