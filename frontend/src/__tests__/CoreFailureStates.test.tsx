// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalKnowledgeSpace } from "../spaces/CanonicalKnowledgeSpace";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { ApiError } from "../api/client";
import { coreFailureReason, failureMessage } from "../presentation/labels";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

async function failSearch(error: unknown) {
  bridge.call.mockRejectedValueOnce(error);
  const user = userEvent.setup();
  render(<CanonicalKnowledgeSpace />);
  await user.type(screen.getByLabelText("搜索内容"), "样板");
  await user.click(screen.getByRole("button", { name: "搜索" }));
  return screen.findByText(/^(离线|冲突|权限|缺失|繁忙|不兼容|不可用)：/);
}

describe("UI-03 distinct failure states", () => {
  beforeEach(() => {
    bridge.call.mockReset();
  });

  it.each([
    [new ApiError(0, "请在本地桌面应用打开此内容。", "offline"), "离线"],
    [new ApiError(409, "版本已变化，请保留当前草稿并重新读取。", "unavailable"), "冲突"],
    [new ApiError(403, "本地核心拒绝了此操作的身份。", "unauthorized"), "权限"],
    [new ApiError(404, "本地核心找不到 search 所需的对象。", "unavailable"), "缺失"],
    [new ApiError(429, "本地核心繁忙，请稍后重试。", "unavailable"), "繁忙"],
    [new ApiError(502, "本地核心未能完成 search（502）。", "incompatible"), "不兼容"],
  ])("names a %s failure as %s without dropping the generic sentence", async (error, label) => {
    const found = await failSearch(error);
    expect(found.textContent).toContain(label);
    expect(await screen.findByText("搜索失败，请重试。不会将失败显示为空结果。")).toBeInTheDocument();
    expect(found.textContent).not.toMatch(/\d{3}/);
    expect(found.textContent).not.toMatch(/\/api|http|->/);
  });

  it("does not invent a reason when the failure is not one the Core contract describes", async () => {
    bridge.call.mockRejectedValueOnce(new Error("invalid search fields"));
    const user = userEvent.setup();
    render(<CanonicalKnowledgeSpace />);
    await user.type(screen.getByLabelText("搜索内容"), "样板");
    await user.click(screen.getByRole("button", { name: "搜索" }));
    expect(await screen.findByText("搜索失败，请重试。不会将失败显示为空结果。")).toBeInTheDocument();
    expect(screen.queryByText(/^(离线|冲突|权限|缺失|繁忙|不兼容|不可用)：/)).not.toBeInTheDocument();
  });

  it("keeps exactly one status live region so a supplementary reason cannot steal the announcement", async () => {
    bridge.call.mockRejectedValueOnce(new ApiError(409, "版本已变化，请保留当前草稿并重新读取。", "unavailable"));
    const user = userEvent.setup();
    render(<CanonicalKnowledgeSpace />);
    await user.type(screen.getByLabelText("搜索内容"), "样板");
    await user.click(screen.getByRole("button", { name: "搜索" }));
    await screen.findByText("搜索失败，请重试。不会将失败显示为空结果。");
    expect(await screen.findByText(/^冲突：/)).toBeInTheDocument();
    expect(screen.getAllByRole("status")).toHaveLength(1);
  });

  // Pages that host several sub-surfaces legitimately own more than one live
  // region, so the pin here is that the reason itself is never a live region.
  it.each([
    ["学习", () => render(<CanonicalLearningSpace />), new ApiError(404, "本地核心找不到 learning_items 所需的对象。", "unavailable"), /^缺失：/],
    ["全能力目录", () => render(<CanonicalCapabilitiesSpace onNavigate={() => {}} />), new ApiError(429, "本地核心繁忙，请稍后重试。", "unavailable"), /^繁忙：/],
  ])("shows the classified reason on %s as plain text, not as a second announcement", async (_page, renderPage, error, pattern) => {
    bridge.call.mockRejectedValue(error);
    renderPage();
    const reason = await screen.findByText(pattern);
    expect(reason.hasAttribute("role")).toBe(false);
    expect(reason).toHaveClass("state-reason");
  });

  it("keeps the legacy pages' 5xx wording while naming the classes they used to flatten", () => {
    expect(failureMessage(new ApiError(0, "local Core is offline", "offline"))).toMatch(/^离线：/);
    expect(failureMessage(new ApiError(403, "desktop write scope is unavailable", "unauthorized"))).toMatch(/^权限：/);
    expect(failureMessage(new ApiError(503, "workspace migration is in progress", "migrating"))).toMatch(/^迁移中：/);
    expect(failureMessage(new ApiError(503, "workspace migration is unavailable", "backend_starting"))).toMatch(/^正在启动：/);
    // A transport failure the Core contract does not describe keeps the established sentence.
    expect(failureMessage(new ApiError(500, "/workspace/api/v1/home -> 500", "unavailable"))).toBe(
      "本地数据暂时不可用，请稍后重试或打开系统诊断。",
    );
  });

  it("keeps the six classified reasons distinct, digit-free and free of transport detail", () => {
    const reasons = [
      new ApiError(0, "请在本地桌面应用打开此内容。", "offline"),
      new ApiError(409, "版本已变化，请保留当前草稿并重新读取。", "unavailable"),
      new ApiError(403, "本地核心拒绝了此操作的身份。", "unauthorized"),
      new ApiError(404, "本地核心找不到 document_restore 所需的对象。", "unavailable"),
      new ApiError(429, "本地核心繁忙，请稍后重试。", "unavailable"),
      new ApiError(502, "本地核心未能完成 document_draft（502）。", "incompatible"),
    ].map(coreFailureReason);

    expect(new Set(reasons).size).toBe(reasons.length);
    for (const reason of reasons) {
      expect(reason).not.toBeNull();
      expect(reason).not.toMatch(/\d/);
      expect(reason).not.toMatch(/\/api|https?:|->|_|\{|\}/);
      expect(reason).toMatch(/保留|重新读取|未改动|保持不变|未被替换|稍后重试|已停止/);
    }
    expect(coreFailureReason(new Error("invalid knowledge fields"))).toBeNull();
    expect(coreFailureReason(undefined)).toBeNull();
  });
});
