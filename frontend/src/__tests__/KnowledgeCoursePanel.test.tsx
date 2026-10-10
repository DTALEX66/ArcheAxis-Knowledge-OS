import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KnowledgeCoursePanel } from "../components/KnowledgeCoursePanel";
import { CanonicalKnowledgeSpace } from "../spaces/CanonicalKnowledgeSpace";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const courseId = `course-${"a".repeat(64)}`, artifactId = `lesson-${"b".repeat(64)}`;
const key = `course:${courseId}:artifact:${artifactId}`;
function course() { return { status: "candidate", human_review_required: true, stale: false,
  manifest: { schema: "archeaxis.course-manifest/v1", manifest_id: courseId, title: "证据课时", status: "candidate",
    knowledge_components: [{ component_id: "kc1", title: "证据要点", statement: "正文 <script>never execute</script>" }],
    learning_objectives: [{ objective_id: "obj1", statement: "解释证据并指出来源", knowledge_component_ids: ["kc1"] }],
    artifacts: [{ artifact_id: artifactId, artifact_type: "lesson", renderer: "native-lesson", knowledge_ids: ["kc1"], status: "candidate", derived_only: true, human_review_required: true }] },
  bindings: [{ knowledge_id: "k1", knowledge_version: "k1", component_id: "kc1", source_id: "s1", source_revision: "sha-source", stale: false }] }; }
function created() { return { course: course(), human_review_required: true, suggested_learning_item: {
  item_key: key, course_id: courseId, artifact_id: artifactId, knowledge_id: "k1", knowledge_version: "k1", source_id: "s1", source_revision: "sha-source" } }; }
function rendered() { return { course: course(), derived_only: true, canonical_bindings_verified: true, human_review_required: true,
  render: { derived_only: true, human_review_required: true, lesson: { path: "../never-write", content: "# 证据课时\nRAW_PROJECTION_METADATA", frontmatter: { manifest_id: courseId, artifact_id: artifactId } } } }; }
function setup() {
  bridge.call.mockImplementation(async (op: string) => {
    if (op === "course_from_knowledge") return created();
    if (op === "course_get") return course();
    if (op === "course_render") return rendered();
    if (op === "assessment_create") return { item_key: key, knowledge_id: "k1", knowledge_version: "k1", assessment_id: "assessment-1", question: "说明证据" };
    if (op === "learning_reference") return { item_key: key };
    throw new Error(op);
  });
}
describe("knowledge → course → lesson → existing learning queue", () => {
  beforeEach(() => { bridge.call.mockReset(); setup(); });
  it("reads the Core course and text projection before binding the exact long learning key", async () => {
    const onLearning = vi.fn(); render(<KnowledgeCoursePanel knowledgeId="k1" onLearning={onLearning} />);
    const user = userEvent.setup(); await user.click(screen.getByRole("button", { name: "从当前知识生成课程与课时" }));
    expect(await screen.findByLabelText("课程候选课时")).toHaveTextContent("<script>never execute</script>");
    expect(document.querySelector("script")).toBeNull();
    expect(bridge.call.mock.calls.slice(0, 3).map(([op]) => op)).toEqual(["course_from_knowledge", "course_get", "course_render"]);
    await user.click(screen.getByRole("button", { name: "由课程课时建立学习问题" }));
    await waitFor(() => expect(onLearning).toHaveBeenCalledOnce());
    expect(bridge.call).toHaveBeenCalledWith("assessment_create", { item_key: key, body: { knowledge_id: "k1" } });
    expect(bridge.call).toHaveBeenCalledWith("learning_reference", { item_key: key, body: { knowledge_id: "k1" } });
    const writes = bridge.call.mock.calls.filter(([op]) => ["learning_reference", "assessment_create"].includes(op)).map(([op]) => op);
    expect(writes).toEqual(["learning_reference", "assessment_create"]);
    expect(bridge.call.mock.calls.some(([op]) => ["knowledge_review", "learning_review"].includes(op))).toBe(false);
  });
  it.each(["stale", "wrong_knowledge", "review_boundary", "wrong_item_key"])("withholds course for %s creation reply", async failure => {
    const result = created();
    if (failure === "stale") result.course.stale = true;
    if (failure === "wrong_knowledge") result.course.bindings[0].knowledge_id = "k2";
    if (failure === "review_boundary") result.human_review_required = false;
    if (failure === "wrong_item_key") result.suggested_learning_item.item_key = "arbitrary:colon";
    bridge.call.mockResolvedValue(result);
    render(<KnowledgeCoursePanel knowledgeId="k1" />);
    await userEvent.setup().click(screen.getByRole("button", { name: "从当前知识生成课程与课时" }));
    await screen.findByText(/课程未能读取/);
    expect(screen.queryByLabelText("课程候选课时")).not.toBeInTheDocument();
    expect(bridge.call).toHaveBeenCalledTimes(1);
  });
  it("rejects a mismatched rendered artifact and never offers a learning write", async () => {
    const wrong = rendered(); wrong.render.lesson.frontmatter.artifact_id = "lesson-other";
    bridge.call.mockImplementation(async (op: string) => op === "course_from_knowledge" ? created() : op === "course_get" ? course() : wrong);
    render(<KnowledgeCoursePanel knowledgeId="k1" />);
    await userEvent.setup().click(screen.getByRole("button", { name: "从当前知识生成课程与课时" }));
    await screen.findByText(/课程未能读取/);
    expect(screen.queryByRole("button", { name: "由课程课时建立学习问题" })).not.toBeInTheDocument();
  });
  it("keeps projection metadata in the diagnostic receipt while presenting teaching content", async () => {
    const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
    try {
      render(<KnowledgeCoursePanel knowledgeId="k1" />); const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "从当前知识生成课程与课时" }));
      const article = await screen.findByLabelText("课程候选课时");
      expect(article).toHaveTextContent("证据要点");
      expect(article).toHaveTextContent("解释证据并指出来源");
      expect(article).not.toHaveTextContent("RAW_PROJECTION_METADATA");
      expect(article).not.toHaveTextContent(courseId);
      await user.click(screen.getByRole("button", { name: "查看原始回执（诊断）：课程课时渲染回执" }));
      expect(debug.mock.calls.some(args => args.some(arg => arg && typeof arg === "object" && JSON.stringify(arg).includes("RAW_PROJECTION_METADATA")))).toBe(true);
    } finally { debug.mockRestore(); }
  });
  it("rejects teaching content that changes between the course read and render", async () => {
    const changed = rendered(); changed.course.manifest.knowledge_components[0].statement = "替换正文";
    bridge.call.mockImplementation(async (op: string) => op === "course_from_knowledge" ? created() : op === "course_get" ? course() : changed);
    render(<KnowledgeCoursePanel knowledgeId="k1" />);
    await userEvent.setup().click(screen.getByRole("button", { name: "从当前知识生成课程与课时" }));
    await screen.findByText(/课程未能读取/);
    expect(screen.queryByLabelText("课程候选课时")).not.toBeInTheDocument();
  });
  it("rechecks staleness before assessment and preserves a refusal as no review result", async () => {
    render(<KnowledgeCoursePanel knowledgeId="k1" />); const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "从当前知识生成课程与课时" }));
    await screen.findByLabelText("课程候选课时");
    const stale = course(); stale.stale = true; stale.bindings[0].stale = true; bridge.call.mockResolvedValue(stale);
    await user.click(screen.getByRole("button", { name: "由课程课时建立学习问题" }));
    await screen.findByText(/未记录复习成绩/);
    expect(bridge.call.mock.calls.some(([op]) => op === "assessment_create")).toBe(false);
    expect(screen.getByLabelText("课程候选课时")).toHaveTextContent("历史课程");
    expect(screen.queryByRole("button", {name: "由课程课时建立学习问题"})).not.toBeInTheDocument();
  });
  it("mounts the course entry for accepted knowledge while retaining the original knowledge review hash", async () => {
    bridge.call.mockImplementation(async (op: string) => {
      if (op === "search") return { items: [{ knowledge_id: "k1", head: "知识", status: "accepted" }], transforms: [] };
      if (op === "knowledge_get") return { knowledge_id: "k1", body: "知识正文", version: "review-receipt-hash", status: "accepted", title: "知识" };
      if (op === "knowledge_qualification") return {};
      if (op === "course_from_knowledge") return created(); if (op === "course_get") return course(); if (op === "course_render") return rendered();
      throw new Error(op);
    });
    render(<CanonicalKnowledgeSpace />); const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "搜索" })); await user.click(await screen.findByRole("button", { name: "知识" }));
    await user.click(await screen.findByRole("button", { name: "从当前知识生成课程与课时" }));
    await screen.findByLabelText("课程候选课时"); expect(screen.getByText(/版本 review-receipt-hash/)).toBeInTheDocument();
  });
  it("establishes the knowledge reference required by Core before the original study entry creates an assessment", async () => {
    let referenced = false;
    const onLearning = vi.fn();
    bridge.call.mockImplementation(async (op: string, payload: Record<string, unknown>) => {
      if (op === "search") return { items: [{ knowledge_id: "k1", head: "知识" }], transforms: [] };
      if (op === "knowledge_get") return { knowledge_id: "k1", body: "正文", version: "review-hash", status: "accepted", title: "知识" };
      if (op === "knowledge_qualification") return {};
      if (op === "learning_reference") { referenced = true; return {}; }
      if (op === "assessment_create") {
        if (!referenced) throw new Error("assessment knowledge must be referenced by the learning item");
        return { item_key: payload.item_key, assessment_id: "a1", question: "说明正文" };
      }
      throw new Error(op);
    });
    render(<CanonicalKnowledgeSpace onLearning={onLearning} />); const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "搜索" })); await user.click(await screen.findByRole("button", { name: "知识" }));
    await user.click(await screen.findByRole("button", { name: "由当前知识建立学习问题" }));
    await waitFor(() => expect(onLearning).toHaveBeenCalledOnce());
  });
});


describe("persisted course selection and immutable history", () => {
  beforeEach(() => { bridge.call.mockReset(); setup(); });
  it("opens a saved course without regeneration and delivers the exact existing learning key", async () => {
    const onLearning=vi.fn(), onCreated=vi.fn();
    render(<KnowledgeCoursePanel courseId={courseId} onLearning={onLearning} onCourseCreated={onCreated}/>);
    await screen.findByLabelText("课程候选课时");
    expect(bridge.call.mock.calls.slice(0,2).map(([op])=>op)).toEqual(["course_get","course_render"]);
    await userEvent.setup().click(screen.getByRole("button", {name:"由课程课时建立学习问题"}));
    await waitFor(()=>expect(onLearning).toHaveBeenCalledWith(key));
    expect(onCreated).not.toHaveBeenCalled();
    expect(bridge.call.mock.calls.some(([op])=>op==="course_from_knowledge")).toBe(false);
  });
  it("keeps stale source/body/objectives readable without render or learning writes", async () => {
    const saved=course();saved.stale=true;saved.bindings[0].stale=true;
    bridge.call.mockResolvedValue(saved);
    render(<KnowledgeCoursePanel courseId={courseId}/>);
    const article=await screen.findByLabelText("课程候选课时");
    expect(article).toHaveTextContent("历史课程");
    expect(article).toHaveTextContent("正文 <script>never execute</script>");
    expect(article).toHaveTextContent("解释证据并指出来源");
    expect(article).toHaveTextContent("sha-source");
    expect(screen.queryByRole("button",{name:"由课程课时建立学习问题"})).not.toBeInTheDocument();
    expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["course_get"]);
    expect(document.querySelector("script")).toBeNull();
  });
  it("refuses a different stored course rather than showing another object's content", async () => {
    render(<KnowledgeCoursePanel courseId="course-other"/>);
    await screen.findByText(/课程未能读取/);
    expect(screen.queryByLabelText("课程候选课时")).not.toBeInTheDocument();
    expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["course_get"]);
  });
  it("ignores late course reads after the catalog selection changes", async () => {
    let resolveOld!:(value:unknown)=>void;
    const old=new Promise(resolve=>{resolveOld=resolve;});
    const secondId=`course-${"c".repeat(64)}`, second=course();second.manifest.manifest_id=secondId;second.manifest.title="第二课程";
    const projected=rendered();projected.course=second;projected.render.lesson.frontmatter.manifest_id=secondId;
    bridge.call.mockImplementation(async (op:string,payload:{course_id?:string})=>{
      if(op==="course_get")return payload.course_id===courseId?old:second;
      if(op==="course_render")return projected;
      throw new Error(op);
    });
    const view=render(<KnowledgeCoursePanel courseId={courseId}/>);
    view.rerender(<KnowledgeCoursePanel courseId={secondId}/>);
    expect(await screen.findByLabelText("课程候选课时")).toHaveTextContent("第二课程");
    resolveOld(course());
    await waitFor(()=>expect(screen.getByLabelText("课程候选课时")).toHaveTextContent("第二课程"));
    expect(bridge.call.mock.calls.filter(([op])=>op==="course_render")).toHaveLength(1);
  });
  it("ignores late generation from a replaced knowledge selection", async () => {
    let finish!:(value:unknown)=>void;
    bridge.call.mockImplementation(async(op:string)=>op==="course_from_knowledge"?new Promise(resolve=>{finish=resolve;}):course());
    const onCreated=vi.fn(), view=render(<KnowledgeCoursePanel knowledgeId="k1" onCourseCreated={onCreated}/>);
    await userEvent.setup().click(screen.getByRole("button",{name:"从当前知识生成课程与课时"}));
    view.rerender(<KnowledgeCoursePanel knowledgeId="k2" onCourseCreated={onCreated}/>);
    finish(created());
    await waitFor(()=>expect(screen.getByRole("button",{name:"从当前知识生成课程与课时"})).toBeEnabled());
    expect(onCreated).not.toHaveBeenCalled();
    expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["course_from_knowledge"]);
    expect(screen.queryByLabelText("课程候选课时")).not.toBeInTheDocument();
  });
  it("returns the Core-created course ID only after identity-checked read and render", async()=>{
    const onCreated=vi.fn();render(<KnowledgeCoursePanel knowledgeId="k1" onCourseCreated={onCreated}/>);
    await userEvent.setup().click(screen.getByRole("button",{name:"从当前知识生成课程与课时"}));
    await waitFor(()=>expect(onCreated).toHaveBeenCalledWith(courseId));
    expect(bridge.call.mock.calls.map(([op])=>op)).toEqual(["course_from_knowledge","course_get","course_render"]);
  });
});
