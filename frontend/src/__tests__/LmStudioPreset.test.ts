import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { addLmStudioPreset, LM_STUDIO_MODELS } from "../runtime/lmStudioPreset";
import type { ModelConfiguration } from "../api/generated/model-configuration-contract";

const empty: ModelConfiguration = {schema:"archeaxis.model-configuration/v1", revision:0, workspace_id:"a".repeat(32), restore_epoch:"initial", profiles:{}, bindings:[]};
const inventory = Object.values(LM_STUDIO_MODELS);
describe("LM Studio product preset", () => {
  it("keeps the DEEP destination aligned with the canonical MTP load profile", () => {
    const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
    const loadProfile = JSON.parse(readFileSync(resolve(root, "config/model-profiles/lm-studio.json"), "utf8"));
    expect(LM_STUDIO_MODELS.deep).toBe(loadProfile.profiles["deep-mtp"].identifier);
  });
  it("fills eight product lanes without touching workspace identity, revision or input", () => {
    const result = addLmStudioPreset(empty, inventory);
    expect(result).toMatchObject({revision:0,workspace_id:empty.workspace_id,restore_epoch:"initial"});
    expect(result.bindings).toHaveLength(8);
    for (const binding of result.bindings) expect(result.profiles[binding.profile_id].model).toBe(LM_STUDIO_MODELS[binding.lane]);
    expect(empty.profiles).toEqual({}); expect(empty.bindings).toEqual([]);
    expect(addLmStudioPreset(result, [])).toEqual(result);
  });
  it("preserves custom destinations and embedding identity, allocating around ID collisions", () => {
    const custom = {endpoint:"http://127.0.0.1:4321/v1",protocol:"openai" as const,model:"custom",credential_ref:null,max_tokens:512,timeout_s:30};
    const initial: ModelConfiguration = {...empty,revision:5,profiles:{"lmstudio-deep":custom,index:custom},bindings:[{purpose:"answer",lane:"deep",profile_id:"lmstudio-deep"},{purpose:"embedding",lane:"fast",profile_id:"index"}]};
    const result = addLmStudioPreset(initial, inventory);
    expect(result.profiles["lmstudio-deep"]).toBe(custom);
    expect(result.profiles["lmstudio-deep-2"].model).toBe(LM_STUDIO_MODELS.deep);
    expect(result.bindings).toEqual(expect.arrayContaining(initial.bindings));
    expect(result.bindings.filter(binding => binding.purpose === "answer" && binding.lane === "deep")).toEqual([initial.bindings[0]]);
    expect(result.bindings.some(binding => binding.purpose === "document_check")).toBe(false);
  });
  it("refuses the unaccelerated inventory key in place of the verified MTP instance without partial writes", () => {
    expect(() => addLmStudioPreset(empty, [LM_STUDIO_MODELS.fast, "qwen3.8-27b"])).toThrow(/先加载/);
    expect(empty.profiles).toEqual({}); expect(empty.bindings).toEqual([]);
  });
  it("rejects excess profiles even when all product lanes were already bound", () => {
    const full = addLmStudioPreset(empty, inventory);
    const template = full.profiles["lmstudio-fast"];
    const profiles = Object.fromEntries(Array.from({length:33}, (_,index) => [`profile-${index}`,template]));
    expect(() => addLmStudioPreset({...full,profiles}, inventory)).toThrow(/32/);
  });
});
