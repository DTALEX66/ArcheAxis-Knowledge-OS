import type { ModelConfiguration, ModelLane, ModelProfile, ModelPurpose } from "../api/generated/model-configuration-contract";

// Product request destinations; LM Studio's separate load profile controls MTP.
export const LM_STUDIO_MODELS: Record<ModelLane, string> = {
  fast: "qwen3.5-4b",
  deep: "aaos-deep-27b-mtp",
};
const purposes: ModelPurpose[] = ["answer", "retest", "material", "companion"];
const lanes: ModelLane[] = ["fast", "deep"];

/** Fill missing bindings only. Never changes an existing profile, binding or index. */
export function addLmStudioPreset(configuration: ModelConfiguration, inventory: readonly string[]): ModelConfiguration {
  if (Object.keys(configuration.profiles).length > 32) throw Error("配置已超过 32 个模型上限，请先整理现有配置。");
  const profiles = { ...configuration.profiles };
  const bindings = [...configuration.bindings];
  for (const lane of lanes) {
    const missing = purposes.filter(purpose => !bindings.some(binding => binding.purpose === purpose && binding.lane === lane));
    if (!missing.length) continue;
    if (!inventory.includes(LM_STUDIO_MODELS[lane])) throw Error(`本地服务尚未提供 ${LM_STUDIO_MODELS[lane]}，请先加载相应模型。`);
    const profile: ModelProfile = {
      endpoint: "http://127.0.0.1:1234/v1", protocol: "openai", model: LM_STUDIO_MODELS[lane],
      credential_ref: null, max_tokens: 1024, timeout_s: 120,
    };
    let id = `lmstudio-${lane}`;
    for (let suffix = 2; profiles[id] && !Object.entries(profile).every(([key, value]) => profiles[id][key as keyof ModelProfile] === value); suffix++) id = `lmstudio-${lane}-${suffix}`;
    if (!profiles[id] && Object.keys(profiles).length >= 32) throw Error("配置已达到 32 个模型上限，请先整理现有配置。");
    profiles[id] ??= profile;
    bindings.push(...missing.map(purpose => ({ purpose, lane, profile_id: id })));
  }
  return { ...configuration, profiles, bindings };
}
