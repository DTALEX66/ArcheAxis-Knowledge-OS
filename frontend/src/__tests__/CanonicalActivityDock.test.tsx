import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ActivityDock } from "../components/ActivityDock";

const source = { source_id: "src_one", source_revision: "sha", sha256: "sha", original_name: "样本.txt", imported_at: "2026-10-05" };
const job = { job_id: "job_one", kind: "text", state: "failed", input_ref: source.source_id, created_at: "2026-10-05", completed_at: null, attempt: 1, error: "private local path" };

describe("canonical activity dock", () => {
  afterEach(() => { delete window.__TAURI__; vi.unstubAllGlobals(); });
  function bridge(result: unknown = { source_id: source.source_id, jobs: [job], jobs_capped: false }) {
    const invoke = vi.fn(async (command: string, args: any) => {
      if (command !== "core_command") throw new Error("legacy command forbidden");
      const { operation } = args.request;
      if (operation === "sources_list") return { status: 200, body: { sources: [source] } };
      if (operation === "source_jobs") return { status: 200, body: result };
      throw new Error(operation);
    });
    window.__TAURI__ = { core: { invoke } };
    return invoke;
  }
  it("reads failed durable jobs through finite Core commands without legacy delivery controls", async () => {
    const invoke = bridge(); const inspect = vi.fn(); const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    render(<ActivityDock onInspect={inspect} />);
    await screen.findByText("前 1 个原件的正典任务：1");
    const user = userEvent.setup(); await user.click(screen.getByRole("button", { name: "展开活动坞" }));
    await user.click(screen.getByRole("button", { name: "查看活动详情" }));
    expect(inspect.mock.calls[0][0].detail).toContain("存在处理错误");
    expect(inspect.mock.calls[0][0].detail).not.toContain("private local path");
    expect(screen.queryByRole("button", { name: "投递下一条" })).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
    expect(invoke.mock.calls.every(([command]) => command === "core_command")).toBe(true);
  });
  it.each([
    { source_id: "another", jobs: [job], jobs_capped: false },
    { source_id: source.source_id, jobs: [{ ...job, input_ref: "another" }], jobs_capped: false },
    { source_id: source.source_id, jobs: [{ ...job, attempt: "passed" }], jobs_capped: false },
  ])("refuses mismatched or malformed durable receipts", async result => {
    bridge(result); render(<ActivityDock />);
    await screen.findByText("正典任务读取未完成，请刷新重试。");
    expect(screen.queryByRole("button", { name: "查看活动详情" })).not.toBeInTheDocument();
  });
  it("refreshes from the Core when a real execution announces changed state", async () => {
    const invoke = bridge(); render(<ActivityDock />);
    await screen.findByText("前 1 个原件的正典任务：1");
    const before = invoke.mock.calls.length;
    act(() => window.dispatchEvent(new Event("archeaxis-job-changed")));
    await waitFor(() => expect(invoke.mock.calls.length).toBeGreaterThan(before));
  });
  it("does not present old task rows as current when refreshed Core readback fails", async () => {
    const invoke = bridge(); render(<ActivityDock />); const user = userEvent.setup();
    await screen.findByText("前 1 个原件的正典任务：1");
    await user.click(screen.getByRole("button", { name: "展开活动坞" }));
    expect(screen.getByRole("button", { name: "查看活动详情" })).toBeInTheDocument();
    invoke.mockRejectedValue(new Error("Core stopped"));
    await user.click(screen.getByRole("button", { name: "刷新任务" }));
    await screen.findByText("正典任务读取未完成，请刷新重试。");
    expect(screen.queryByRole("button", { name: "查看活动详情" })).not.toBeInTheDocument();
  });
});
