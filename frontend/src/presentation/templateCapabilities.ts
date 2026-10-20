import type { Availability, ImplementationState, RequirementRow, RequirementStatus } from "../templates/capabilityRequirements";
import { capabilityOperationName } from "./capabilityCenter";

// Display copy only: the resolver remains the source of identities and runtime verdicts.
const providers: Record<ImplementationState, string> = {
  worker_backed: "内置处理服务（已登记）",
  core_native: "应用内置处理（已登记）",
  not_implemented: "尚无接入实现",
  unlinked: "提供方待确认",
};
export const templateRequirementStatus: Record<RequirementStatus, string> = {
  qualified: "已有实现声明",
  declared_no_implementation: "需求已声明，尚未关联实现",
  provider_unknown: "提供方未确认",
};
const availabilityCopy: Record<Availability, { label: string; reason: string }> = {
  allowed: { label: "连接检查允许使用", reason: "已登记且连接检查允许使用；实际处理结果与质量仍需单独核对。" },
  disabled: { label: "已禁用", reason: "此处理步骤已被禁用，当前不能执行；仍可编辑和保存模板。" },
  handshake_incomplete: { label: "处理服务尚未就绪", reason: "尚未取得就绪状态，当前不能使用此处理步骤。" },
  enabled_unknown: { label: "使用权限未知", reason: "状态记录未提供使用权限，尚不能判断是否允许执行。" },
  runtime_absent: { label: "当前应用未接入此处理服务", reason: "本轮运行状态没有此处理步骤，当前不能通过它执行任务。" },
  no_live_surface: { label: "运行情况尚未验证", reason: "此步骤没有独立的连接检查记录；实现声明不代表本轮已执行成功。" },
  unlinked: { label: "尚未关联到能力目录", reason: "尚未建立能力对应关系，不能据此判断运行状态。" },
  not_read: { label: "尚未读取运行状态", reason: "本轮未读取运行状态，是否可用仍未知。" },
  read_failed: { label: "读取失败，运行状态未知", reason: "本轮运行状态读取失败，尚不能判断是否可用；可重新读取。" },
};

export function templateRequirementPresentation(row: RequirementRow) {
  let availability = availabilityCopy[row.availability];
  if (row.join_basis === "unknown_id") {
    availability = { label: "能力目录中未找到对应项", reason: "需求所指的能力尚未在目录中找到；需核对登记，不能借用其他能力的运行状态。" };
  } else if (row.join_basis === "unbound") {
    availability = { label: availability.label, reason: row.served_by.length
      ? "模板声明由应用内置操作承担，尚未与能力目录建立对应关系；本次未确认运行结果。"
      : "只有需求说明，尚未接入实际处理；可继续编辑和保存模板。" };
  } else if (row.implementation_state === "not_implemented") {
    availability = { label: "尚未接入", reason: "能力目录保留了此项需求，尚无实际处理实现。" };
  } else if (row.availability === "no_live_surface" && row.implementation_state === "worker_backed") {
    availability = { label: "声明与运行服务尚未对应", reason: "此需求与已登记的处理步骤尚未建立对应关系，不能借用其他步骤的运行状态。" };
  }
  return {
    name: capabilityOperationName(row.declared),
    provider: row.join_basis === "unbound" && row.served_by.length ? "应用内置操作（模板声明）" : providers[row.implementation_state],
    status: row.join_basis === "unbound" && row.served_by.length ? "内置操作尚未关联到能力目录" : templateRequirementStatus[row.status],
    availability: availability.label, reason: availability.reason,
  };
}
