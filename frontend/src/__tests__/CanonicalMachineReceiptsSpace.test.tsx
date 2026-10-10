import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CanonicalMachineReceiptsSpace } from "../spaces/CanonicalMachineReceiptsSpace";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const row = (id = "answer_a") => ({ task_id: id, principal: "machine", conditions: JSON.stringify({ question: "SYNTHETIC question", answer: { answer: "SYNTHETIC answer" } }), model_version: "fixture/model", scope: "runtime.answer", outcome: "unmeasured", knowledge_version: "knowledge_a@v1", method_version: null, tool_version: null, failure: null, retest_of: null, recorded_at: "2026-10-10" });
beforeEach(() => { bridge.call.mockReset(); });

it("SIMULATED: reads persisted conditions and keeps machine measurement separate", async () => {
  bridge.call.mockImplementation(async (op: string) => op === "machine_tasks_list" ? { items: [row()], next_cursor: null } : row());
  render(<CanonicalMachineReceiptsSpace />);
  fireEvent.click(await screen.findByRole("button", { name: "answer_a · 未测评" }));
  expect(await screen.findByText("SYNTHETIC answer")).toBeTruthy();
  expect(screen.getByText("SYNTHETIC question")).toBeTruthy();
  expect(bridge.call).toHaveBeenCalledWith("machine_task_get", { task_id: "answer_a" });
  expect(bridge.call.mock.calls.every(([op]) => !["machine_answer", "machine_correction", "machine_retest"].includes(op))).toBe(true);
});
it("SIMULATED: failed list cannot masquerade as empty or success", async () => {
  bridge.call.mockRejectedValue(new Error("read failed"));
  render(<CanonicalMachineReceiptsSpace />);
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText("尚无已保存的机器任务。执行回答后可在此读取实际回执。")).toBeNull();
});
it("SIMULATED: detail identity or conditions mismatch is rejected", async () => {
  bridge.call.mockImplementation(async (op: string) => op === "machine_tasks_list" ? { items: [row()], next_cursor: null } : { ...row(), conditions: "different" });
  render(<CanonicalMachineReceiptsSpace />);
  fireEvent.click(await screen.findByRole("button", { name: "answer_a · 未测评" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText("SYNTHETIC answer")).toBeNull();
});
it("SIMULATED: stable pagination adds unique receipts without running tasks", async () => {
  bridge.call.mockImplementation(async (_op: string, p: { cursor?: string }) => p.cursor ? { items: [row("answer_b")], next_cursor: null } : { items: [row()], next_cursor: "answer_a" });
  render(<CanonicalMachineReceiptsSpace />);
  fireEvent.click(await screen.findByRole("button", { name: "读取下一页任务回执" }));
  expect(await screen.findByRole("button", { name: "answer_b · 未测评" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "answer_a · 未测评" })).toBeTruthy();
  expect(bridge.call).toHaveBeenCalledWith("machine_tasks_list", { cursor: "answer_a" });
});
it("SIMULATED: closed detail ignores a late readback", async () => {
  let finish!: (value: unknown) => void;
  bridge.call.mockImplementation((op: string) => op === "machine_tasks_list" ? Promise.resolve({ items: [row()], next_cursor: null }) : new Promise(resolve => { finish = resolve; }));
  render(<CanonicalMachineReceiptsSpace />);
  fireEvent.click(await screen.findByRole("button", { name: "answer_a · 未测评" }));
  fireEvent.click(screen.getByRole("button", { name: "关闭回执详情" }));
  await act(async () => finish(row()));
  expect(screen.queryByText("SYNTHETIC answer")).toBeNull();
  expect(screen.getByText("选择实际任务，核对来源版本、条件与结果。")).toBeTruthy();
});
