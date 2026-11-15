import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { AiAsset } from "../api/generated/ai-asset-contract";
import type { DocumentDto } from "../api/generated/core-contract";
import { PinnedReferencePanel } from "../components/PinnedReferencePanel";
import { KnowledgeCoursePanel } from "../components/KnowledgeCoursePanel";
import { CanonicalResearchSpace } from "../spaces/CanonicalResearchSpace";
import { CanonicalAiAssetsSpace } from "../spaces/CanonicalAiAssetsSpace";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
const fixed = { kind: "knowledge" as const, knowledge_id: "knowledge-old" };
const oldBody = "旧版本的知识内容";
const assetContent = "以旧知识为来源的经验";
const asset: AiAsset = { schema: "archeaxis.ai-asset/v1", kind: "experience", content: assetContent,
  purpose: "分析方法", scope: [], provenance: [fixed], expires_at: null, state: "candidate",
  members: [], conflicts: [], revises: null, review: null, source_payload: null };
const document = (id: string, attrs: unknown): DocumentDto => ({ document_id: id, title: id, version: 1,
  content_sha256: "a".repeat(64), source_id: null, source_revision: null, text_projection: "保留原记录", blocks: [],
  editor_json: { type: "doc", content: [], attrs } });
const research = document("research-saved", { archeaxis_research: { schema: "archeaxis.research/v1", question: "原研究问题",
  materials: [{ id: "m1", note: "保留原材料引用", reference: fixed }], hypotheses: [], methods: [], experiments: [],
  counterevidence: [], conclusions: [], unresolved: [] } });
const assetDocument = document("asset-saved", { archeaxis_ai_asset: asset });
const course = { status: "candidate", human_review_required: true, stale: true,
  manifest: { schema: "archeaxis.course-manifest/v1", manifest_id: "course-saved", title: "原课程", status: "candidate",
    knowledge_components: [{ component_id: "component-old", title: "原要点", statement: oldBody }],
    learning_objectives: [{ statement: "解释原知识", knowledge_component_ids: ["component-old"] }],
    artifacts: [{ artifact_id: "lesson-old", artifact_type: "lesson", renderer: "native-lesson", knowledge_ids: ["component-old"],
      status: "candidate", derived_only: true, human_review_required: true }] },
  bindings: [{ knowledge_id: fixed.knowledge_id, knowledge_version: fixed.knowledge_id, component_id: "component-old",
    source_id: "source-old", source_revision: "b".repeat(64), stale: true }] };
let phase: "current" | "superseded" | "not_current";
let previousScroll: typeof HTMLElement.prototype.scrollIntoView;
beforeEach(() => {
  previousScroll = HTMLElement.prototype.scrollIntoView;
  HTMLElement.prototype.scrollIntoView = vi.fn();
  phase = "current";
  bridge.call.mockReset();
  bridge.call.mockImplementation(async (op: string, payload: Record<string, unknown> = {}) => {
    if (op === "knowledge_qualification") return { knowledge_id: payload.id, exists: true,
      active: phase === "current", status: phase === "not_current" ? "deprecated" : "accepted", currentness: phase,
      superseded_by: phase === "superseded" ? "knowledge-next" : null, successor_count: phase === "superseded" ? 1 : 0, valid_to: null };
    if (op === "knowledge_get") return { knowledge_id: fixed.knowledge_id, body: oldBody, version: "old-version",
      status: "accepted", source_id: null, anchor_id: null };
    if (op === "documents_list") return { documents: [research], next_cursor: null, snapshot_count: 1 };
    if (op === "ai_assets_list") return { items: [assetDocument], next_cursor: null };
    if (op === "document_get") return structuredClone(payload.document_id === research.document_id ? research : assetDocument);
    if (op === "course_get") return structuredClone(course);
    throw new Error(`Unexpected operation ${op}`);
  });
});
afterEach(() => { HTMLElement.prototype.scrollIntoView = previousScroll; });

type Consumer = "资料固定引用" | "研究引用" | "课程绑定" | "AI资产来源";
async function mount(consumer: Consumer) {
  if (consumer === "资料固定引用") return render(<PinnedReferencePanel reference={fixed} onClose={() => {}}/>);
  if (consumer === "课程绑定") return render(<KnowledgeCoursePanel courseId="course-saved"/>);
  if (consumer === "研究引用") {
    const view = render(<CanonicalResearchSpace/>);
    fireEvent.click(screen.getByText("研究文档与版本", { selector: "summary" }));
    fireEvent.click(await screen.findByRole("button", { name: "research-saved · 版本 1" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "研究问题" })).toHaveValue("原研究问题"));
    fireEvent.click(within(screen.getByRole("navigation", { name: "研究内容导航" })).getByRole("button", { name: "证据对比 (1)" }));
    return view;
  }
  const view = render(<CanonicalAiAssetsSpace parseAsset={value => value as AiAsset} parseGrant={() => null} packetCommand={vi.fn()}/>);
  fireEvent.click(await screen.findByRole("button", { name: "asset-saved · v1" }));
  await waitFor(() => expect(screen.getByLabelText("资产内容")).toHaveValue(assetContent));
  return view;
}

// These are real consumer components with mock transport, not Core/installed restart evidence.
it.each<Consumer>(["资料固定引用", "研究引用", "课程绑定", "AI资产来源"])("%s keeps its old reference across revision and re-opening", async consumer => {
  const originals = structuredClone({ research, assetDocument, course });
  const view = await mount(consumer);
  const notice = await screen.findByLabelText("知识引用当前性");
  await within(notice).findByText(/^当前知识版本/);
  phase = "superseded";
  fireEvent.click(within(notice).getByRole("button", { name: "重新核对当前性" }));
  await within(notice).findByText("历史知识版本：已有后继修订，原引用保持不变。");
  expect(notice).toHaveAttribute("data-knowledge-id", fixed.knowledge_id);
  expect(within(notice).getByText(/原引用和旧评价保持原绑定/)).toBeInTheDocument();
  view.unmount();
  phase = "not_current";
  const reopened = await mount(consumer);
  await screen.findByText(/^知识引用已失效/);
  expect(screen.getByLabelText("知识引用当前性")).toHaveAttribute("data-knowledge-id", fixed.knowledge_id);
  expect({ research, assetDocument, course }).toEqual(originals);
  const reads = new Set(["knowledge_qualification", "knowledge_get", "documents_list", "ai_assets_list", "document_get", "course_get"]);
  expect(bridge.call.mock.calls.every(([op]) => reads.has(op))).toBe(true);
  expect(bridge.call.mock.calls.filter(([op]) => op === "knowledge_qualification").every(([, payload]) => payload.id === fixed.knowledge_id)).toBe(true);
  if (consumer === "课程绑定") {
    expect(screen.getByText(oldBody)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "由课程课时建立学习问题" })).not.toBeInTheDocument();
  }
  reopened.unmount();
});
