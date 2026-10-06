import { afterEach, describe, expect, it } from "vitest";
import { SPACES, spaceDescription } from "../spaces/spaces";

afterEach(() => { delete window.__TAURI__; });

const byId = (id: string) => SPACES.find((space) => space.id === id)!;

// Several rail ids route to Canonical surfaces in the desktop shell, where the legacy
// web-mode wording promises capabilities that surface does not offer.
describe("space descriptions", () => {
  it("keeps the legacy wording outside the desktop shell", () => {
    expect(spaceDescription(byId("intake"))).toBe(byId("intake").description);
    expect(spaceDescription(byId("vault"))).toBe("本地笔记、搜索与画布");
  });

  it("describes what the desktop shell actually renders", () => {
    window.__TAURI__ = { core: { invoke: async () => ({}) } } as never;
    expect(spaceDescription(byId("workspace"))).toBe("任务、备份与能力状态");
    expect(spaceDescription(byId("intake"))).toBe("导入原件与多格式转换");
    expect(spaceDescription(byId("vault"))).toBe("文档、搜索与知识候选");
    expect(spaceDescription(byId("exchange"))).toBe("导出与投递回执");
    expect(spaceDescription(byId("settings"))).toBe("本机能力与状态");
    expect(spaceDescription(byId("library"))).toBe(byId("library").description);
  });
});
