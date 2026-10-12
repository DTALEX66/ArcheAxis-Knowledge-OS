import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalKnowledgeSpace } from "../spaces/CanonicalKnowledgeSpace";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
beforeEach(() => {
  bridge.call.mockReset();
  bridge.call.mockImplementation(async (op: string, payload: {id?: string}) => {
    if (op === "search") return {items: ["one", "two"].map(id => ({knowledge_id:id,head:id,status:"candidate",active:false})),transforms:[]};
    if (op === "knowledge_get") return {knowledge_id:payload.id,title:payload.id,body:"synthetic candidate",version:"v1",status:"candidate"};
    if (op === "knowledge_qualification") return {};
    if (op === "knowledge_review") throw new Error("synthetic lost acknowledgement");
    throw new Error(op);
  });
});

async function openCandidate() {
  const user = userEvent.setup();
  render(<CanonicalKnowledgeSpace showMachine={false}/>);
  await user.click(screen.getByRole("button", {name:"搜索"}));
  await user.click(await screen.findByRole("button", {name:"one"}));
  await screen.findByLabelText("审核备注");
  return user;
}

it("keeps an unsubmitted note when recovery reloads the same candidate", async () => {
  const user = await openCandidate();
  await user.type(screen.getByLabelText("审核者"), "synthetic reviewer");
  await user.type(screen.getByLabelText("审核备注"), "retain this unsent note");
  await user.click(screen.getByRole("button", {name:"接受当前候选"}));
  await screen.findByText(/审核未完成/);
  await user.click(screen.getByRole("button", {name:"重新读取候选"}));
  expect(await screen.findByLabelText("审核备注")).toHaveValue("retain this unsent note");
  await user.click(screen.getByRole("button", {name:"two"}));
  await waitFor(() => expect(screen.getByLabelText("审核备注")).toHaveValue(""));
});

it.each(["failed", "pending"])("a %s qualification read does not approve or block a human choice", async mode => {
  const previous = bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation((op, payload) => op === "knowledge_qualification"
    ? mode === "failed" ? Promise.reject(new Error("synthetic annotation unavailable")) : new Promise(() => {})
    : previous(op, payload));
  const user = await openCandidate();
  await user.type(screen.getByLabelText("审核者"), "synthetic reviewer");
  expect(screen.getByRole("button", {name:"接受当前候选"})).toBeEnabled();
  expect(bridge.call.mock.calls.filter(([op]) => op === "knowledge_review")).toHaveLength(0);
  await user.click(screen.getByRole("button", {name:"接受当前候选"}));
  await waitFor(() => expect(bridge.call.mock.calls.filter(([op]) => op === "knowledge_review")).toHaveLength(1));
  expect(bridge.call.mock.calls.find(([op]) => op === "knowledge_review")![1].body).toMatchObject({action:"accepted",expected_version:"v1"});
});
