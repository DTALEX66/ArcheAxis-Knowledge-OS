import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CanonicalMachineReceiptsSpace } from "../spaces/CanonicalMachineReceiptsSpace";
import { DiagnosticConsole } from "../components/DiagnosticConsole";
import { resetDiagnostics } from "../presentation/diagnostics";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const row = (id = "answer_a") => ({ task_id: id, principal: "machine", conditions: JSON.stringify({ question: "SYNTHETIC question", answer: { answer: "SYNTHETIC answer" } }), model_version: "fixture/model", scope: "runtime.answer", outcome: "unmeasured", knowledge_version: "knowledge_a@v1", method_version: null, tool_version: null, failure: null, retest_of: null, recorded_at: "2026-10-10" });
beforeEach(() => { bridge.call.mockReset(); resetDiagnostics(); });

it("SIMULATED: reads persisted conditions and keeps machine measurement separate", async () => {
  bridge.call.mockImplementation(async (op: string) => op === "machine_tasks_list" ? { items: [row()], next_cursor: null } : row());
  render(<CanonicalMachineReceiptsSpace />);
  fireEvent.click(await screen.findByRole("button", { name: "AI 回答 1 · 未测评" }));
  expect(await screen.findByText("SYNTHETIC answer")).toBeTruthy();
  expect(screen.getByText("SYNTHETIC question")).toBeTruthy();
  expect(bridge.call).toHaveBeenCalledWith("machine_task_get", { task_id: "answer_a" });
  expect(bridge.call.mock.calls.every(([op]) => !["machine_answer", "machine_correction", "machine_retest"].includes(op))).toBe(true);
});
it("SIMULATED: failed list cannot masquerade as empty or success", async () => {
  bridge.call.mockRejectedValue(new Error("read failed"));
  render(<CanonicalMachineReceiptsSpace />);
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText("尚无已保存的机器任务。执行回答后可在此查看详细记录。")).toBeNull();
});
it("SIMULATED: shows the actual failed-evaluation scope and preserves its raw failure in diagnostics", async () => {
  const evaluation = { ...row("evaluation_a"), scope: "runtime.evaluation.failed", outcome: "failed", failure: "SYNTHETIC_RAW_FAILURE" };
  bridge.call.mockImplementation(async (op: string) => op === "machine_tasks_list" ? { items: [evaluation], next_cursor: null } : evaluation);
  render(<><CanonicalMachineReceiptsSpace /><DiagnosticConsole /></>);
  fireEvent.click(await screen.findByRole("button", { name: "回答评测 1 · 失败" }));
  await screen.findByText("SYNTHETIC answer");
  const failureNote = screen.getByText("SYNTHETIC_RAW_FAILURE");
  expect(failureNote.closest("details")).not.toHaveAttribute("open");
  fireEvent.click(screen.getByText("查看失败说明"));
  expect(failureNote).toHaveTextContent("SYNTHETIC_RAW_FAILURE");
  fireEvent.click(screen.getByRole("button", { name: "状态与诊断：完整任务详细信息" }));
  expect(screen.getByLabelText("诊断控制台")).toHaveTextContent("SYNTHETIC_RAW_FAILURE");
  expect(bridge.call).toHaveBeenCalledWith("machine_task_get", { task_id: "evaluation_a" });
  expect(bridge.call.mock.calls.some(([op]) => ["machine_answer", "machine_evaluate", "machine_retest"].includes(op))).toBe(false);
});
it("SIMULATED: detail identity or conditions mismatch is rejected", async () => {
  bridge.call.mockImplementation(async (op: string) => op === "machine_tasks_list" ? { items: [row()], next_cursor: null } : { ...row(), conditions: "different" });
  render(<CanonicalMachineReceiptsSpace />);
  fireEvent.click(await screen.findByRole("button", { name: "AI 回答 1 · 未测评" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText("SYNTHETIC answer")).toBeNull();
});
it("SIMULATED: stable pagination adds unique receipts without running tasks", async () => {
  bridge.call.mockImplementation(async (_op: string, p: { cursor?: string }) => p.cursor ? { items: [row("answer_b")], next_cursor: null } : { items: [row()], next_cursor: "answer_a" });
  render(<CanonicalMachineReceiptsSpace />);
  fireEvent.click(await screen.findByRole("button", { name: "查看更多任务记录" }));
  expect(await screen.findByRole("button", { name: "AI 回答 2 · 未测评" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "AI 回答 1 · 未测评" })).toBeTruthy();
  expect(bridge.call).toHaveBeenCalledWith("machine_tasks_list", { cursor: "answer_a" });
});
it("SIMULATED: closed detail ignores a late readback", async () => {
  let finish!: (value: unknown) => void;
  bridge.call.mockImplementation((op: string) => op === "machine_tasks_list" ? Promise.resolve({ items: [row()], next_cursor: null }) : new Promise(resolve => { finish = resolve; }));
  render(<CanonicalMachineReceiptsSpace />);
  fireEvent.click(await screen.findByRole("button", { name: "AI 回答 1 · 未测评" }));
  fireEvent.click(screen.getByRole("button", { name: "关闭任务详情" }));
  await act(async () => finish(row()));
  expect(screen.queryByText("SYNTHETIC answer")).toBeNull();
  expect(screen.getByText("选择实际任务，核对来源版本、条件与结果。")).toBeTruthy();
});
