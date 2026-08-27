import { describe, expect, it } from "vitest";
import { stateLabel, userErrorMessage } from "../presentation/labels";

describe("Chinese-first presentation labels", () => {
  it("translates persisted operational states without changing storage values", () => {
    expect(stateLabel("completed")).toBe("已完成");
    expect(stateLabel("pending")).toBe("待处理");
    expect(stateLabel("approved")).toBe("已批准");
    expect(stateLabel("candidate")).toBe("候选");
    expect(stateLabel("unreviewed")).toBe("未复核");
  });

  it("fails closed for an unknown visible state", () => {
    expect(stateLabel("future_internal_state")).toBe("状态未知");
  });

  it("withholds endpoint and internal protocol details from visible errors", () => {
    expect(userErrorMessage("/api/v1/home -> 500")).toBe("本地数据暂时不可用，请稍后重试或打开系统诊断。");
    expect(userErrorMessage("NetworkError: fetch failed")).toBe("本地数据暂时不可用，请稍后重试或打开系统诊断。");
    expect(userErrorMessage("资料库没有读取权限")).toBe("资料库没有读取权限");
  });
});
