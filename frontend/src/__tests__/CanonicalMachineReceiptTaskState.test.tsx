import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CanonicalMachineReceiptsSpace } from "../spaces/CanonicalMachineReceiptsSpace";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

beforeEach(() => { bridge.call.mockReset(); });
it("parent and receipt-list refresh preserve pending cancellation, frozen budget and committed checkpoint", async () => {
  let state = "queued", request: string | null = null;
  const source = { source_id: "s1", source_revision: "rev1", sha256: "a".repeat(64), original_name: "synthetic.txt", imported_at: "2026-10-10" };
  const job = { job_id: "j1", kind: "text", state: "queued", input_ref: "s1", created_at: "2026-10-10", completed_at: null, attempt: null, error: null };
  const status = () => ({ job_id: "j1", input_ref: "s1", state, request_id: request, attempt: request ? 1 : null, error: null,
    attempts: request ? [{ attempt: 1, request_id: request, budget: { deadline_ms: 45000 }, steps: { accepted: "RECORDED" }, checkpoint: { status: "CORE_COMMITTED", output_ids: ["committed-output"] }, continuation: { resume_status: "NOT_SUPPORTED" } }] : [] });
  bridge.call.mockImplementation(async (op, payload) => {
    if (op === "machine_tasks_list") return { items: [], next_cursor: null };
    if (op === "sources_list") return { sources: [source] };
    if (op === "source_jobs") return { source_id: "s1", jobs: [job], jobs_capped: false };
    if (op === "jobs_get" || op === "job_execution_status") return status();
    if (op === "job_execute") { state = "running"; request = payload.request_id; return { job_id: "j1", request_id: request, state, replayed: false }; }
    if (op === "job_execution_cancel") return { job_id: "j1", request_id: request, cancel_requested: true };
    throw new Error(op);
  });
  const view = render(<CanonicalMachineReceiptsSpace />);
  await screen.findByRole("option", { name: "synthetic.txt · s1" });
  fireEvent.change(screen.getByRole("combobox", { name: /^已保存来源/ }), { target: { value: "s1" } });
  await screen.findByRole("option", { name: /j1/ });
  fireEvent.change(screen.getByRole("combobox", { name: /^来源任务/ }), { target: { value: "j1" } });
  await screen.findByText("queued", { exact: true });
  const budget = screen.getByLabelText("单次预算（毫秒）");
  fireEvent.change(budget, { target: { value: "45000" } });
  fireEvent.click(screen.getByRole("button", { name: "执行已保存任务" }));
  await screen.findByText("running", { exact: true });
  fireEvent.click(screen.getByRole("button", { name: "请求取消" }));
  await screen.findByText("取消待确认：继续轮询实际状态。");
  const frozenRequest = request;
  view.rerender(<CanonicalMachineReceiptsSpace />);
  fireEvent.click(screen.getByRole("button", { name: "刷新任务回执" }));
  await waitFor(() => expect(bridge.call.mock.calls.filter(([op]) => op === "machine_tasks_list")).toHaveLength(2));
  expect(screen.getByRole("combobox", { name: /^来源任务/ })).toHaveValue("j1");
  expect(screen.getByLabelText("单次预算（毫秒）")).toBeDisabled();
  expect(screen.getByLabelText("单次预算（毫秒）")).toHaveValue(45000);
  expect(screen.getByLabelText("已提交检查点")).toHaveTextContent("committed-output");
  expect(screen.getByText("取消待确认：继续轮询实际状态。")).toBeInTheDocument();
  expect(request).toBe(frozenRequest);
  expect(bridge.call.mock.calls.filter(([op]) => op === "job_execute")).toHaveLength(1);
});
