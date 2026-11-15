import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { KnowledgeCurrentnessNotice } from "../components/KnowledgeCurrentnessNotice";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const current = (id = "knowledge-old") => ({ knowledge_id: id, exists: true, active: true,
  status: "accepted", currentness: "current", superseded_by: null, successor_count: 0, valid_to: null });
beforeEach(() => { bridge.call.mockReset(); });

it("a current candidate remains unaccepted and the observation grants no evaluation or execution", async () => {
  bridge.call.mockResolvedValue({ ...current(), status: "candidate" });
  render(<KnowledgeCurrentnessNotice knowledgeId="knowledge-old"/>);
  expect(await screen.findByText("当前知识候选：尚未接纳，不代表内容已核验。")).toBeInTheDocument();
  expect(screen.getByText(/不授予 AI 使用权限或人类掌握/)).toBeInTheDocument();
  expect(bridge.call.mock.calls).toEqual([["knowledge_qualification", { id: "knowledge-old" }]]);
});

it.each([
  ["different identity", { knowledge_id: "knowledge-other" }],
  ["missing proof", { exists: undefined }],
  ["unknown state", { currentness: "future_state" }],
  ["contradictory active", { active: false }],
  ["unbound successor", { superseded_by: "knowledge-next" }],
  ["self successor", { active: false, currentness: "superseded", superseded_by: "knowledge-old", successor_count: 1 }],
])("does not promote %s to current or silently follow its reference", async (_name, fields) => {
  bridge.call.mockResolvedValue({ ...current(), ...fields });
  const open = vi.fn();
  render(<KnowledgeCurrentnessNotice knowledgeId="knowledge-old" onOpenReference={open}/>);
  await screen.findByText(/当前性尚未核对/);
  expect(screen.queryByText(/^当前知识版本/)).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "查看首个后继修订" })).not.toBeInTheDocument();
  expect(open).not.toHaveBeenCalled();
});

it("refreshes the same old identity after revision and only navigates to a successor on explicit click", async () => {
  bridge.call.mockResolvedValueOnce(current()).mockResolvedValueOnce({ ...current(), active: false,
    currentness: "superseded", superseded_by: "knowledge-next", successor_count: 2 });
  const open = vi.fn();
  render(<KnowledgeCurrentnessNotice knowledgeId="knowledge-old" onOpenReference={open}/>);
  await screen.findByText(/^当前知识版本/);
  fireEvent.click(screen.getByRole("button", { name: "重新核对当前性" }));
  await screen.findByText("历史知识版本：已有后继修订，原引用保持不变。");
  expect(screen.getByText(/共 2 项；未自动选择/)).toBeInTheDocument();
  expect(bridge.call.mock.calls).toEqual(Array(2).fill(["knowledge_qualification", { id: "knowledge-old" }]));
  expect(open).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "查看首个后继修订" }));
  expect(open).toHaveBeenCalledTimes(1);
  expect(open).toHaveBeenCalledWith({ kind: "knowledge", knowledge_id: "knowledge-next" });
  expect(screen.getByLabelText("知识引用当前性")).toHaveAttribute("data-knowledge-id", "knowledge-old");
});

it("discards a late response after switching references", async () => {
  let finishOld!: (value: unknown) => void;
  bridge.call.mockImplementation((_op, payload) => payload.id === "knowledge-old"
    ? new Promise(resolve => { finishOld = resolve; })
    : Promise.resolve({ ...current("knowledge-new"), active: false, status: "deprecated", currentness: "not_current" }));
  const view = render(<KnowledgeCurrentnessNotice knowledgeId="knowledge-old"/>);
  view.rerender(<KnowledgeCurrentnessNotice knowledgeId="knowledge-new"/>);
  await screen.findByText(/^知识引用已失效/);
  await act(async () => finishOld(current()));
  expect(screen.getByText(/^知识引用已失效/)).toBeInTheDocument();
  expect(screen.queryByText(/^当前知识版本/)).not.toBeInTheDocument();
  expect(screen.getByLabelText("知识引用当前性")).toHaveAttribute("data-knowledge-id", "knowledge-new");
});

it("does not retain a prior current result across an unavailable refresh or a remount", async () => {
  bridge.call.mockResolvedValueOnce(current()).mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ ...current(), active: false, status: "rejected", currentness: "not_current" });
  const view = render(<KnowledgeCurrentnessNotice knowledgeId="knowledge-old"/>);
  await screen.findByText(/^当前知识版本/);
  fireEvent.click(screen.getByRole("button", { name: "重新核对当前性" }));
  await screen.findByText(/当前性尚未核对/);
  expect(screen.queryByText(/^当前知识版本/)).not.toBeInTheDocument();
  view.unmount();
  render(<KnowledgeCurrentnessNotice knowledgeId="knowledge-old"/>);
  await screen.findByText(/^知识引用已失效/);
  await waitFor(() => expect(bridge.call).toHaveBeenCalledTimes(3));
});

it("rejects an invalid reference without sending a request", async () => {
  render(<KnowledgeCurrentnessNotice knowledgeId="../other"/>);
  await screen.findByText(/当前性尚未核对/);
  expect(bridge.call).not.toHaveBeenCalled();
});
