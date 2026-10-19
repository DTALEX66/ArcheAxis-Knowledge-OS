import { coreCommand } from "../api/core";
import type { ModelConfiguration, ModelLane, ModelPurpose, ResolvedModel } from "../api/generated/model-configuration-contract";

export class ModelBindingRequiredError extends Error {
  constructor() { super("DEEP 尚未配置，请先在设置保存本地模型与用途绑定。"); }
}

/** Resolve once before preview/admission. Replays must use the frozen result. */
export async function resolveProductModel(purpose: ModelPurpose, lane: ModelLane): Promise<ResolvedModel | null> {
  const configuration = await coreCommand<ModelConfiguration>("model_configuration_get");
  if (configuration.revision === 0) {
    if (lane === "deep") throw new ModelBindingRequiredError();
    return null;
  }
  const resolved = await coreCommand<ResolvedModel>("model_configuration_resolve", {body:{purpose,lane}});
  if (resolved.purpose !== purpose || resolved.lane !== lane || resolved.configuration_revision !== configuration.revision
      || typeof configuration.workspace_id !== "string" || resolved.workspace_id !== configuration.workspace_id
      || typeof configuration.restore_epoch !== "string" || resolved.restore_epoch !== configuration.restore_epoch) {
    throw Error("MODEL_CONFIGURATION_IDENTITY_CHANGED");
  }
  return resolved;
}
