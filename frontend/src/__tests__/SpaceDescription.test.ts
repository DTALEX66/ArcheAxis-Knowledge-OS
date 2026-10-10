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

  it("describes the same page in both hosts without promising browser-only capabilities", () => {
    const descriptions = SPACES.map(space => spaceDescription(space));
    window.__TAURI__ = {core:{invoke:async()=>({})}} as never;
    expect(SPACES.map(space => spaceDescription(space))).toEqual(descriptions);
    expect(spaceDescription(byId("workspace"))).toBe("本地文档与学习继续");
    expect(spaceDescription(byId("intake"))).toBe("本地原件与多格式导入");
  });
});
