import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CanonicalLearningJourneySpace } from "../spaces/CanonicalLearningJourneySpace";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
const journal = vi.hoisted(() => ({ value: null as null | {state:{pending_reviews:Record<string,{item_key:string}>}} }));
vi.mock("../presentation/useCoreWorkingState", () => ({useOptionalCoreWorkingState:()=>journal.value}));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../spaces/CanonicalLearningSpace", () => ({ CanonicalLearningSpace: ({ initialItemKey }: { initialItemKey?: string }) => <div>真实练习入口 {initialItemKey}</div> }));
vi.mock("../components/KnowledgeCoursePanel", () => ({ KnowledgeCoursePanel: ({ courseId, knowledgeId, onLearning }: { courseId?: string; knowledgeId?: string; onLearning: (key: string) => void }) => <div>课程读回 {courseId ?? knowledgeId}<button onClick={() => onLearning("real-course-item")}>练习当前课时</button></div> }));
const row = (id: string, stale = false) => ({ manifest_id: id, title: `课程${id}`, stale, status: "candidate", human_review_required: true });
beforeEach(() => {
  journal.value = null;
  bridge.call.mockReset(); bridge.call.mockImplementation(async (operation: string) => {
    if (operation === "course_list") return { items: [row("c1")], next_cursor: null };
    if (operation === "search") return { items: [{ knowledge_id: "k1", head: "真实知识" }] };
    if (operation === "knowledge_get") return { knowledge_id: "k1", status: "accepted" };
    throw new Error(operation);
  });
});
it("offers an actionable first step without disabled practice controls before an item is selected",async()=>{
 const onOpenPage=vi.fn();render(<CanonicalLearningJourneySpace pageId="06" onOpenPage={onOpenPage}/>);
 await waitFor(()=>expect(screen.getByRole("button",{name:"选择已有课程"})).toBeEnabled());
 expect(screen.queryByRole("button",{name:"练习此学习项目"})).toBeNull();
 expect(screen.queryByRole("button",{name:"复习此学习项目"})).toBeNull();
 await userEvent.click(screen.getByRole("button",{name:"选择已有课程"}));
 expect(screen.getByRole("button",{name:"课程c1"})).toBeVisible();
});
it("routes an empty library to real source selection instead of inventing a course or mastery",async()=>{
 bridge.call.mockResolvedValue({items:[],next_cursor:null});
 render(<CanonicalLearningJourneySpace pageId="06"/>);
 await userEvent.click(screen.getByRole("button",{name:"从已有知识开始"}));
 expect(screen.getByRole("region",{name:"课程来源选择"})).toBeVisible();
 expect(bridge.call.mock.calls.some(([op])=>op==="course_from_knowledge"||op==="learning_review")).toBe(false);
});
it("recovers the persisted pending review on the restored feedback scene without submitting", async () => {
  journal.value={state:{pending_reviews:{e1:{item_key:"persisted-item"}}}};
  render(<CanonicalLearningJourneySpace pageId="12" />);
  expect(await screen.findByText(/真实练习入口 persisted-item/)).toBeInTheDocument();
  expect(bridge.call.mock.calls.some(([op])=>op==="learning_review")).toBe(false);
});
it("does not choose between multiple pending learning identities", async () => {
  journal.value={state:{pending_reviews:{e1:{item_key:"first"},e2:{item_key:"second"}}}};
  render(<CanonicalLearningJourneySpace pageId="12" />);
  await userEvent.click(within(screen.getByRole("navigation",{name:"学习内容导航"})).getByRole("button",{name:"课程与课时"}));
  await screen.findByRole("button",{name:"课程c1"});
  expect(screen.queryByText(/真实练习入口/)).not.toBeInTheDocument();
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
  await userEvent.click(screen.getByRole("button",{name:"课程来源"}));
  await userEvent.click(screen.getByRole("button", { name: "搜索知识" }));
  await userEvent.click(await screen.findByRole("button", { name: "真实知识" }));
  await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("knowledge_get", { id: "k1" }));
  expect(screen.getByText(/课程读回 k1/)).toBeInTheDocument();
});
it("does not treat rejected knowledge as a usable course source", async () => {
  const original = bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation((op: string, payload: unknown) => op === "knowledge_get" ? Promise.resolve({ knowledge_id: "k1", status: "rejected" }) : original(op, payload));
  render(<CanonicalLearningJourneySpace />);
  await userEvent.click(screen.getByRole("button",{name:"课程来源"}));
  await userEvent.click(screen.getByRole("button", { name: "搜索知识" }));
  await userEvent.click(await screen.findByRole("button", { name: "真实知识" }));
  expect(await screen.findByText(/此知识暂不能用于生成课程/)).toBeInTheDocument();
  expect(screen.queryByText(/课程读回 k1/)).not.toBeInTheDocument();
});

it("keeps one Stitch learning content slot visible and retains the actual course and practice nodes",async()=>{
 render(<CanonicalLearningJourneySpace pageId="07"/>);const nav=screen.getByRole("navigation",{name:"学习内容导航"});
 await userEvent.click(await screen.findByRole("button",{name:"课程c1"}));const course=screen.getByText(/课程读回 c1/);const courseSlot=screen.getByRole("region",{name:"课程内容槽"});
 await userEvent.click(screen.getByRole("button",{name:"练习当前课时"}));const practice=screen.getByText(/真实练习入口 real-course-item/);
 expect(practice).toBeVisible();expect(screen.getByRole("region",{name:"练习内容槽"})).toHaveFocus();expect(course).toBeInTheDocument();expect(course).not.toBeVisible();expect(screen.queryByRole("region",{name:"课程内容槽"})).not.toBeInTheDocument();
 await userEvent.click(within(nav).getByRole("button",{name:"课程与课时"}));expect(screen.getByRole("region",{name:"课程内容槽"})).toBe(courseSlot);expect(course).toBeVisible();expect(practice).not.toBeVisible();
 await userEvent.click(within(nav).getByRole("button",{name:"学习路径"}));expect(screen.getByText(/真实练习入口 real-course-item/)).toBe(practice);expect(practice).toBeVisible();
 expect(bridge.call.mock.calls.some(([op])=>op==="learning_review"||op==="course_from_knowledge")).toBe(false);
});
it("keeps source search input across content navigation and never invents a course selection",async()=>{
 render(<CanonicalLearningJourneySpace pageId="06"/>);const nav=screen.getByRole("navigation",{name:"学习内容导航"});
 await userEvent.click(within(nav).getByRole("button",{name:"课程来源"}));expect(within(nav).getByRole("button",{name:"课程来源"})).toHaveFocus();const input=screen.getByRole("textbox",{name:"查找课程来源知识"});await userEvent.type(input,"真实来源问题");
 await userEvent.click(within(nav).getByRole("button",{name:"课程与课时"}));expect(input).toBeInTheDocument();expect(input).not.toBeVisible();
 await userEvent.click(within(nav).getByRole("button",{name:"课程来源"}));expect(screen.getByRole("textbox",{name:"查找课程来源知识"})).toBe(input);expect(input).toHaveValue("真实来源问题");expect(screen.queryByText(/课程读回/)).not.toBeInTheDocument();
});
