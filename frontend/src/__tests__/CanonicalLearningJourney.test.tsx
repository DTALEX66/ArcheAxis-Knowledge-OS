import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalLearningJourneySpace } from "../spaces/CanonicalLearningJourneySpace";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../spaces/CanonicalLearningSpace", () => ({ CanonicalLearningSpace: ({ initialItemKey }: { initialItemKey?: string }) => <div>真实练习入口 {initialItemKey}</div> }));
vi.mock("../components/KnowledgeCoursePanel", () => ({ KnowledgeCoursePanel: ({ courseId, knowledgeId, onLearning }: { courseId?: string; knowledgeId?: string; onLearning: (key: string) => void }) => <div>课程读回 {courseId ?? knowledgeId}<button onClick={() => onLearning("real-course-item")}>练习当前课时</button></div> }));
const row = (id: string, stale = false) => ({ manifest_id: id, title: `课程${id}`, stale, status: "candidate", human_review_required: true });
beforeEach(() => {
  bridge.call.mockReset(); bridge.call.mockImplementation(async (operation: string) => {
    if (operation === "course_list") return { items: [row("c1")], next_cursor: null };
    if (operation === "search") return { items: [{ knowledge_id: "k1", head: "真实知识" }] };
    if (operation === "knowledge_get") return { knowledge_id: "k1", status: "accepted" };
    throw new Error(operation);
  });
});
it("opens a persisted course without regenerating it and sends the actual assessment key to review", async () => {
  const onOpenPage = vi.fn(); render(<CanonicalLearningJourneySpace pageId="07" onOpenPage={onOpenPage} />);
  await userEvent.click(await screen.findByRole("button", { name: "课程c1" }));
  expect(screen.getByText(/课程读回 c1/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "练习当前课时" }));
  expect(screen.getByText(/真实练习入口 real-course-item/)).toBeInTheDocument();
  expect(onOpenPage).toHaveBeenLastCalledWith("06");
  expect(bridge.call).not.toHaveBeenCalledWith("course_from_knowledge", expect.anything());
});
it("keeps stale historical courses discoverable without fabricated progress", async () => {
  bridge.call.mockResolvedValue({ items: [row("old", true)], next_cursor: null });
  render(<CanonicalLearningJourneySpace pageId="07" />);
  expect(await screen.findByText(/来源已变化 · 历史只读/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "课程old" }));
  expect(screen.getByText(/课程读回 old/)).toBeInTheDocument();
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
});
it("uses Core's cursor for more courses and keeps the existing selection", async () => {
  bridge.call.mockImplementation(async (_operation: string, payload: { cursor?: string }) => payload.cursor
    ? { items: [row("c2")], next_cursor: null } : { items: [row("c1")], next_cursor: "c1" });
  render(<CanonicalLearningJourneySpace pageId="07" />);
  await userEvent.click(await screen.findByRole("button", { name: "课程c1" }));
  await userEvent.click(screen.getByRole("button", { name: "读取更多课程" }));
  expect(await screen.findByRole("button", { name: "课程c2" })).toBeInTheDocument();
  expect(screen.getByText(/课程读回 c1/)).toBeInTheDocument();
  expect(bridge.call).toHaveBeenCalledWith("course_list", { cursor: "c1" });
});
it("shows an unavailable Core as a read failure instead of empty or demo courses", async () => {
  bridge.call.mockRejectedValue(new Error("no Core")); render(<CanonicalLearningJourneySpace pageId="07" />);
  expect(await screen.findByText(/课程列表读取失败/)).toBeInTheDocument();
  expect(screen.queryByText(/尚无已保存课程/)).not.toBeInTheDocument();
  expect(screen.queryByText(/课程读回/)).not.toBeInTheDocument();
});
it("rechecks source knowledge before offering candidate creation", async () => {
  render(<CanonicalLearningJourneySpace pageId="06" />);
  await userEvent.click(screen.getByRole("button", { name: "搜索知识" }));
  await userEvent.click(await screen.findByRole("button", { name: "真实知识" }));
  await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("knowledge_get", { id: "k1" }));
  expect(screen.getByText(/课程读回 k1/)).toBeInTheDocument();
});
it("does not treat rejected knowledge as a usable course source", async () => {
  const original = bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation((op: string, payload: unknown) => op === "knowledge_get" ? Promise.resolve({ knowledge_id: "k1", status: "rejected" }) : original(op, payload));
  render(<CanonicalLearningJourneySpace />);
  await userEvent.click(screen.getByRole("button", { name: "搜索知识" }));
  await userEvent.click(await screen.findByRole("button", { name: "真实知识" }));
  expect(await screen.findByText(/此知识暂不能用于生成课程/)).toBeInTheDocument();
  expect(screen.queryByText(/课程读回 k1/)).not.toBeInTheDocument();
});
