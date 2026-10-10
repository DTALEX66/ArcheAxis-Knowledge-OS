import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { PinnedReferencePanel } from "../components/PinnedReferencePanel";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const knowledge = { knowledge_id: "knowledge_v1", version: "immutable_v1", status: "candidate", body: "SYNTHETIC knowledge", source_id: "source_real", anchor_id: null };
const reference = { kind: "knowledge" as const, knowledge_id: "knowledge_v1" };
beforeEach(() => { bridge.call.mockReset(); });
it("SIMULATED: knowledge source jump uses the exact bound ID and immutable ingestion hash", async () => {
  bridge.call.mockImplementation(async (op: string) => op === "knowledge_get" ? knowledge : { sources: [{ source_id: "other", sha256: "b".repeat(64) }, { source_id: "source_real", sha256: "a".repeat(64) }] });
  const jump = vi.fn(); render(<PinnedReferencePanel reference={reference} onClose={() => {}} onOpenReference={jump} />);
  fireEvent.click(await screen.findByRole("button", { name: "读取知识绑定的来源原件" }));
  await screen.findByText("SYNTHETIC knowledge"); await act(async () => {});
  expect(jump).toHaveBeenCalledTimes(1);
  expect(jump).toHaveBeenCalledWith({ kind: "source", source_id: "source_real", sha256: "a".repeat(64) });
});
it("SIMULATED: missing bound source is an error and never substitutes another original", async () => {
  bridge.call.mockImplementation(async (op: string) => op === "knowledge_get" ? knowledge : { sources: [{ source_id: "other", sha256: "b".repeat(64) }] });
  const jump = vi.fn(); render(<PinnedReferencePanel reference={reference} onClose={() => {}} onOpenReference={jump} />);
  fireEvent.click(await screen.findByRole("button", { name: "读取知识绑定的来源原件" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("未换成其他原件"); expect(jump).not.toHaveBeenCalled();
});
it("SIMULATED: late source lookup cannot replace a newly selected knowledge object", async () => {
  let done!: (value: unknown) => void;
  bridge.call.mockImplementation((op: string, p: { knowledge_id?: string }) => op === "sources_list" ? new Promise(resolve => { done = resolve; }) : Promise.resolve({ ...knowledge, knowledge_id: p.knowledge_id }));
  const jump = vi.fn(); const host = render(<PinnedReferencePanel reference={reference} onClose={() => {}} onOpenReference={jump} />);
  fireEvent.click(await screen.findByRole("button", { name: "读取知识绑定的来源原件" }));
  host.rerender(<PinnedReferencePanel reference={{ kind: "knowledge", knowledge_id: "knowledge_v2" }} onClose={() => {}} onOpenReference={jump} />);
  await screen.findByText("知识 knowledge_v2"); await act(async () => done({ sources: [{ source_id: "source_real", sha256: "a".repeat(64) }] }));
  expect(jump).not.toHaveBeenCalled();
});
it("SIMULATED: duplicate clicks share one lookup and unmounted lookup cannot navigate", async () => {
  let done!: (value: unknown) => void;
  bridge.call.mockImplementation((op: string) => op === "sources_list" ? new Promise(resolve => { done = resolve; }) : Promise.resolve(knowledge));
  const jump = vi.fn(); const host = render(<PinnedReferencePanel reference={reference} onClose={() => {}} onOpenReference={jump} />);
  const button = await screen.findByRole("button", { name: "读取知识绑定的来源原件" }); fireEvent.click(button); fireEvent.click(button);
  expect(bridge.call.mock.calls.filter(([op]) => op === "sources_list")).toHaveLength(1); host.unmount();
  await act(async () => done({ sources: [{ source_id: "source_real", sha256: "a".repeat(64) }] })); expect(jump).not.toHaveBeenCalled();
});
