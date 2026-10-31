import type { ModelConfiguration, ModelLane, ModelProfile, ModelPurpose } from "../api/generated/model-configuration-contract";

// Product request destinations; LM Studio's separate load profile controls MTP.
export const LM_STUDIO_MODELS: Record<ModelLane, string> = {
  fast: "qwen3.5-4b",
  deep: "aaos-deep-27b-mtp",
};
export const LM_STUDIO_DEFAULT_MAX_TOKENS = 4096;
const purposes: ModelPurpose[] = ["answer", "retest", "material", "companion"];
const lanes: ModelLane[] = ["fast", "deep"];

/** Fill missing bindings only. Never changes an existing profile, binding or index. */
export function addLmStudioPreset(configuration: ModelConfiguration, inventory: readonly string[]): ModelConfiguration {
  return fillLmStudioBindings(configuration, inventory, LM_STUDIO_MODELS, { fast: "lmstudio-fast", deep: "lmstudio-deep" });
}

/** Explicit quick connection fills gaps without replacing a user's saved choices. */
export function addLmStudioQuickConnection(configuration: ModelConfiguration, inventory: readonly string[]): ModelConfiguration {
  const chat = inventory.filter(name => !/embedding|reranker|vision|-vl|vl-/i.test(name));
  if (!chat.length) throw Error("本机服务没有可用的对话模型；请先在 LM Studio 加载模型并启动服务。");
  const fast = chat.includes("qwen3.5-4b") ? "qwen3.5-4b" : chat[0];
  const deep = chat.includes("qwen3.8-27b") ? "qwen3.8-27b" : fast;
  return fillLmStudioBindings(configuration, inventory, { fast, deep }, { fast: "lmstudio", deep: deep === fast ? "lmstudio" : "lmstudio-deep" });
}

function fillLmStudioBindings(configuration: ModelConfiguration, inventory: readonly string[], models: Record<ModelLane, string>, preferredIds: Record<ModelLane, string>): ModelConfiguration {
  if (Object.keys(configuration.profiles).length > 32) throw Error("配置已超过 32 个模型上限，请先整理现有配置。");
  const profiles = { ...configuration.profiles };
  const bindings = [...configuration.bindings];
  for (const lane of lanes) {
    const missing = purposes.filter(purpose => !bindings.some(binding => binding.purpose === purpose && binding.lane === lane));
    if (!missing.length) continue;
    if (!inventory.includes(models[lane])) throw Error(`本地服务尚未提供 ${models[lane]}，请先加载相应模型。`);
    const profile: ModelProfile = {
      endpoint: "http://127.0.0.1:1234/v1", protocol: "openai", model: models[lane],
      credential_ref: null, max_tokens: LM_STUDIO_DEFAULT_MAX_TOKENS, timeout_s: 120,
    };
    let id = preferredIds[lane];
    for (let suffix = 2; profiles[id] && !Object.entries(profile).every(([key, value]) => profiles[id][key as keyof ModelProfile] === value); suffix++) id = `${preferredIds[lane]}-${suffix}`;
    if (!profiles[id] && Object.keys(profiles).length >= 32) throw Error("配置已达到 32 个模型上限，请先整理现有配置。");
    profiles[id] ??= profile;
    bindings.push(...missing.map(purpose => ({ purpose, lane, profile_id: id })));
  }
  return { ...configuration, profiles, bindings };
}
