import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { DiagnosticConsole } from "../components/DiagnosticConsole";
import { resetDiagnostics } from "../presentation/diagnostics";
import { localDateTime } from "../presentation/display";

const call = vi.hoisted(() => vi.fn());
vi.mock("../api/core", () => ({ coreCommand: call }));
const rawTime = "2026-10-28T23:15:49.961000+00:00";
const key = "learning-exact-key";
const assessment = { assessment_id: "assessment-exact", knowledge_version: "knowledge-exact", question_version: "question-exact", question: "实际问题", content: "核对内容" };
let scheduled: unknown;
let receiptTime: unknown;
beforeEach(() => {
  resetDiagnostics(); scheduled = rawTime; receiptTime = rawTime;
  call.mockReset();
  call.mockImplementation(async (operation: string, payload?: Record<string, unknown>) => {
    if (operation === "learning_items") return { items: [{ item_key: key, display_title: "复习日期样本", next_review: scheduled }] };
    if (operation === "learning_state") return { item_key: payload?.item_key, learner: { assessment }, machine: { status: "not_recorded" } };
    if (operation === "learning_history") return { events: [] };
    if (operation === "learning_review") return { item_key: key, next_review: receiptTime };
    throw new Error(operation);
  });
});

it("SYNTHETIC queue and selected-object trail show a local date without mutating its ISO value", async () => {
  const onTrail = vi.fn();
  render(<CanonicalLearningSpace initialItemKey={key} onTrail={onTrail} />);
  await screen.findByLabelText("本次答案");
  await waitFor(() => expect(screen.getByRole("list", { name: "复习队列" })).toHaveTextContent(`下次复习 ${localDateTime(rawTime)}`));
  expect(screen.getByRole("list", { name: "复习队列" })).not.toHaveTextContent(rawTime);
  await waitFor(() => expect(onTrail).toHaveBeenLastCalledWith(expect.arrayContaining([expect.objectContaining({ id: `item:${key}`, detail: `下次复习 ${localDateTime(rawTime)}` })])));
  expect(scheduled).toBe(rawTime);
  expect(call).toHaveBeenCalledWith("learning_state", { item_key: key });
});

it.each([null, undefined, "", "   "])("SYNTHETIC missing queue time %s stays explicitly unscheduled", async value => {
  scheduled = value; const onTrail = vi.fn();
  render(<CanonicalLearningSpace initialItemKey={key} onTrail={onTrail} />);
  await screen.findByLabelText("本次答案");
  await waitFor(() => expect(screen.getByRole("list", { name: "复习队列" })).toHaveTextContent("下次复习 未安排"));
  await waitFor(() => expect(onTrail).toHaveBeenLastCalledWith(expect.arrayContaining([expect.objectContaining({ detail: "下次复习 未安排" })])));
});

it.each(["2026-02-30T08:00:00Z", "2026-10-28T08:00:00", "not-a-date"])("SYNTHETIC invalid or ambiguous time %s is not presented as a valid schedule", async value => {
  scheduled = value; const onTrail = vi.fn();
  render(<CanonicalLearningSpace initialItemKey={key} onTrail={onTrail} />);
  await screen.findByLabelText("本次答案");
  await waitFor(() => expect(screen.getByRole("list", { name: "复习队列" })).toHaveTextContent("下次复习 时间待核对"));
  expect(screen.getByRole("list", { name: "复习队列" })).not.toHaveTextContent(value);
  await waitFor(() => expect(onTrail).toHaveBeenLastCalledWith(expect.arrayContaining([expect.objectContaining({ detail: "下次复习 时间待核对" })])));
});

it.each([rawTime, "2026-02-30T08:00:00Z", null, ""])("SYNTHETIC review receipt %s formats only the UI and preserves exact request and diagnostic data", async value => {
  receiptTime = value;
  render(<><CanonicalLearningSpace initialItemKey={key} /><DiagnosticConsole /></>);
  fireEvent.change(await screen.findByLabelText("本次答案"), { target: { value: "我的独立答案" } });
  fireEvent.click(screen.getByRole("button", { name: "查看答案与核对内容" }));
  fireEvent.click(screen.getByLabelText("回答正确"));
  fireEvent.change(screen.getByLabelText("学习者自评"), { target: { value: "3" } });
  fireEvent.click(screen.getByRole("button", { name: "记录复习结果" }));
  const message = await screen.findByRole("status");
  expect(message).toHaveTextContent(typeof value === "string" && value.trim() ? `下次复习：${localDateTime(value)}` : "下次复习时间未提供");
  if (typeof value === "string" && value.trim()) expect(message).not.toHaveTextContent(value);
  expect(call.mock.calls.filter(([operation]) => operation === "learning_review")).toHaveLength(1);
  expect(call.mock.calls.find(([operation]) => operation === "learning_review")?.[1]).toEqual({ body: { item_key: key, client_event_id: expect.any(String), answer: "我的独立答案", correct: true, rating: 3, assessment_id: assessment.assessment_id, question_version: assessment.question_version, knowledge_version: assessment.knowledge_version } });
  fireEvent.click(screen.getByText("历史与回执"));
  fireEvent.click(screen.getByRole("button", { name: "状态与诊断：复习历史与提交详情" }));
  const diagnostic = JSON.parse(screen.getByLabelText("诊断控制台").querySelector("pre")!.textContent!);
  expect(diagnostic.receipt).toEqual({ item_key: key, next_review: value });
  expect(receiptTime).toBe(value);
});
