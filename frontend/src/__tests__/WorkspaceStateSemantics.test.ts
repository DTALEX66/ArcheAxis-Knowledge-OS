import { describe, expect, it } from "vitest";
import { workspaceStateClass } from "../spaces/WorkspaceSpace";

describe("workspace status color semantics", () => {
  it.each([
    ["已完成", "state-ok"],
    ["失败", "state-danger"],
    ["不可用", "state-danger"],
    ["未连接", "state-warn"],
    ["已弃用", "state-warn"],
    ["待处理", "state-pending"],
    ["未分类状态", ""],
  ])("maps %s to %s", (label, className) => {
    expect(workspaceStateClass(label)).toBe(className);
  });
});
