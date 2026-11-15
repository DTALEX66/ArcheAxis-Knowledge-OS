import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import type { DocumentDto } from "../api/generated/core-contract";
import { sceneView, readSceneCandidate, ScenePosition } from "../presentation/openMaicSceneReader";
import { OpenMaicScenePanel } from "../components/OpenMaicScenePanel";
import { openMaic13Fixture } from "../test/fixtures/openmaicV2";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../presentation/useCoreWorkingState", () => ({ useOptionalCoreWorkingState: () => ({ status: "ready", server: { workspace_id: "workspace_1", restore_epoch: "epoch_1", recovery_requires_confirmation: false } }) }));
const source = { document_id: "material_1", version: 1, content_sha256: "c".repeat(64) };
const makeDoc = (id: string, version: number, editor: unknown): DocumentDto => ({ document_id: id, version, content_sha256: String(version).repeat(64),
  title: "候选课件", editor_json: editor, text_projection: "候选课件", blocks: [], source_id: null, source_revision: null });
function fixture() {
  const scene = { ...openMaic13Fixture().scenes[0], actions: [
    { id: "a1", type: "speech", text: "先区分来源和证据" }, { id: "a2", type: "spotlight", elementId: "text1" },
    { id: "a3", type: "laser", elementId: "text1" }, { id: "a4", type: "wb_open" },
  ] };
  const renderReport = { schema: "archeaxis.openmaic-scene-render/v1", scene_type: "slide", renderer: "openmaic-canvas-text", playable: true };
  const saved = { schema: "archeaxis.openmaic-scene-document/v2", human_review_required: true, rendering_authorized: false,
    request_frame: JSON.stringify({ source }), render: renderReport,
    worker_document: { status: "CANDIDATE", human_review_required: true, active_content_executed: false, rendering_authorized: false, scene } };
  const doc = makeDoc("scene_1", 1, { type: "doc", attrs: { archeaxis_openmaic_scene_candidate: saved }, content: [] });
  const row = { document_id: doc.document_id, document_version: doc.version, document_content_sha256: doc.content_sha256,
    status: "recorded", contract_version: saved.schema, scene_type: "slide", renderer: renderReport.renderer, playability: "playable" };
  const pack = { schema: "archeaxis.openmaic-course-package-projection/v1", document_count: 1, renderer_executed: false,
    rendering_authorized: false, human_review_required: true, scenes: [row] };
  return { doc, row, saved, scene, pack };
}
beforeEach(() => { bridge.call.mockReset(); });

it("reads generated scene DSL directly and keeps unsupported actions visible", () => {
  const f = fixture(), view = sceneView(f.doc, f.row);
  expect(view.slide?.elements).toHaveLength(1);
  expect(view.steps.map(s => s.kind)).toEqual(["speech", "spotlight", "laser", "unsupported"]);
  expect(view.steps[1].elementId).toBe("text1");
  expect(view.questions).toEqual([]);
});
it("refuses a projection bound to another scene version or fingerprint", () => {
  const f = fixture();
  for (const delta of [{ document_id: "other" }, { document_version: 2 }, { document_content_sha256: "f".repeat(64) }, { contract_version: "future" }]) {
    expect(() => sceneView(f.doc, { ...f.row, ...delta })).toThrow();
  }
});
it("does not execute interactive HTML or pretend an unsupported canvas rendered", () => {
  const f = fixture();
  Object.assign(f.scene, { type: "interactive", content: { type: "interactive", html: "<script>window.SHOULD_NOT_RUN = true</script><iframe src='https://example.invalid'></iframe>" } });
  Object.assign(f.saved.render, { playable: false, renderer: null, scene_type: "interactive" });
  const view = sceneView(f.doc, { ...f.row, playability: "not_playable", renderer: null, scene_type: "interactive" });
  expect(view.fallback).toContain("尚无受支持"); expect(view.slide).toBeUndefined();
  expect(view).not.toHaveProperty("html"); expect(document.querySelector("iframe")).toBeNull();
  const unsupported = fixture();
  (unsupported.scene.content as { canvas: { elements: unknown[] } }).canvas.elements = [{ type: "image", src: "https://example.invalid/private" }];
  expect(sceneView(unsupported.doc, unsupported.row).fallback).toContain("不能完整读取");
});
it("reads the exact projected version and reports newer material without rebinding", async () => {
  const f = fixture();
  bridge.call.mockImplementation(async op => op === "course_openmaic_package_projection" ? f.pack
    : op === "document_version" ? f.doc : { ...makeDoc(source.document_id, 2, {}), content_sha256: "d".repeat(64) });
  const view = await readSceneCandidate("scene_1");
  expect(view.source).toEqual(source); expect(view.sourceStatus).toBe("historical");
  expect(bridge.call).toHaveBeenCalledWith("document_version", { document_id: "scene_1", version: 1 });
  expect(bridge.call.mock.calls.every(([op]) => ["course_openmaic_package_projection", "document_version", "document_get"].includes(op))).toBe(true);
});
it("keeps source availability unknown and refuses forged package authority", async () => {
  const f = fixture();
  bridge.call.mockImplementation(async op => { if (op === "course_openmaic_package_projection") return f.pack;
    if (op === "document_version") return f.doc; throw new Error("offline"); });
  expect((await readSceneCandidate("scene_1")).sourceStatus).toBe("unavailable");
  bridge.call.mockResolvedValueOnce({ ...f.pack, renderer_executed: true });
  await expect(readSceneCandidate("scene_1")).rejects.toThrow();
});
it("saves create then expected-version draft and resumes without writing on open", async () => {
  const f = fixture(), scene = sceneView(f.doc, f.row); let persisted: DocumentDto | undefined;
  bridge.call.mockImplementation(async (op, p) => {
    if (op === "document_get") { if (!persisted) throw new ApiError(404, "missing"); return structuredClone(persisted); }
    if (op === "document_create") persisted = makeDoc((await ScenePosition.open(scene, "workspace_1")).documentId, 1, p.body.editor_json);
    if (op === "document_draft") { expect(p.body.expected_version).toBe(1); expect(p.body.base_version).toBeUndefined(); persisted = makeDoc(p.document_id, 2, p.body.editor_json); }
    return structuredClone(persisted);
  });
  const position = await ScenePosition.open(scene, "workspace_1"); expect(await position.read()).toBe(0);
  await position.save(1); await position.save(2);
  const writes = bridge.call.mock.calls.filter(([op]) => op === "document_create" || op === "document_draft").length;
  const reopened = await ScenePosition.open(scene, "workspace_1"); expect(await reopened.read()).toBe(2);
  expect(bridge.call.mock.calls.filter(([op]) => op === "document_create" || op === "document_draft")).toHaveLength(writes);
});
it("preserves unknown position writes and only clears them on exact readback", async () => {
  const f = fixture(), scene = sceneView(f.doc, f.row); const position = await ScenePosition.open(scene, "workspace_1");
  let saved: DocumentDto | undefined;
  bridge.call.mockImplementation(async (op, p) => {
    if (op === "document_create") { saved = makeDoc(position.documentId, 1, p.body.editor_json); throw new Error("lost ack"); }
    return structuredClone(saved);
  });
  await expect(position.save(1)).rejects.toThrow("lost ack"); expect(position.unresolved).toBe(true);
  await expect(position.save(2)).rejects.toThrow("尚未确认");
  const exact = structuredClone(saved!); saved!.version = 2;
  await expect(position.read()).rejects.toThrow("未确认"); expect(position.unresolved).toBe(true);
  saved = exact; expect(await position.read()).toBe(1); expect(position.unresolved).toBe(false);
  expect(bridge.call.mock.calls.filter(([op]) => op === "document_create")).toHaveLength(1);
});
it("the product panel opens real documents-list shape and navigates from the default step", async () => {
  const f = fixture();
  bridge.call.mockImplementation(async (op, p) => {
    if (op === "documents_list") return { documents: [f.doc], next_cursor: null, snapshot_count: 1 };
    if (op === "course_openmaic_package_projection") return f.pack;
    if (op === "document_version") return f.doc;
    if (op === "document_get" && p.document_id === source.document_id) return { ...makeDoc(source.document_id, 1, {}), content_sha256: source.content_sha256 };
    throw new ApiError(404, "missing");
  });
  render(<OpenMaicScenePanel />);
  fireEvent.click(screen.getByRole("button", { name: "浏览生成场景文档" }));
  fireEvent.click(await screen.findByRole("button", { name: "打开场景 候选课件" }));
  expect(await screen.findByText("先区分来源和证据")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "下一步讲解" }));
  expect(screen.getByText("聚焦课件元素 text1")).toBeVisible();
  expect(document.querySelector('[data-focused="true"]')).not.toBeNull();
  expect(bridge.call.mock.calls.some(([op]) => /generate|scene_create/.test(op))).toBe(false);
});

it("a failed position read does not block the lesson or trap read-only navigation", async () => {
  const f = fixture();
  bridge.call.mockImplementation(async (op, p) => {
    if (op === "documents_list") return { documents: [f.doc], next_cursor: null, snapshot_count: 1 };
    if (op === "course_openmaic_package_projection") return f.pack;
    if (op === "document_version") return f.doc;
    if (p.document_id === source.document_id) return { ...makeDoc(source.document_id, 1, {}), content_sha256: source.content_sha256 };
    throw new ApiError(500, "position unavailable");
  });
  render(<OpenMaicScenePanel />); fireEvent.click(screen.getByRole("button", { name: "浏览生成场景文档" }));
  fireEvent.click(await screen.findByRole("button", { name: "打开场景 候选课件" }));
  expect(await screen.findByText("先区分来源和证据")).toBeVisible();
  expect(screen.getByRole("button", { name: "保存阅读位置" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "下一步讲解" }));
  expect(screen.getByRole("button", { name: "打开场景 候选课件" })).not.toBeDisabled();
});

it("a learner answer prevents changing scenes and publishes unsaved-work protection", async () => {
  const f = fixture();
  Object.assign(f.scene, { type: "quiz", content: { type: "quiz", questions: [{ id: "short1", type: "short_answer", question: "你的依据是什么？" }] }, actions: [] });
  Object.assign(f.saved.render, { scene_type: "quiz", renderer: "openmaic-quiz-objective" });
  Object.assign(f.row, { scene_type: "quiz", renderer: "openmaic-quiz-objective" });
  bridge.call.mockImplementation(async (op, p) => {
    if (op === "documents_list") return { documents: [f.doc], next_cursor: null, snapshot_count: 1 };
    if (op === "course_openmaic_package_projection") return f.pack;
    if (op === "document_version") return f.doc;
    if (p.document_id === source.document_id) return { ...makeDoc(source.document_id, 1, {}), content_sha256: source.content_sha256 };
    throw new ApiError(404, "missing");
  });
  const observed: boolean[] = [], listener = (event: Event) => { observed.push((event as CustomEvent).detail.dirty); };
  window.addEventListener("archeaxis-draft-dirty", listener);
  try {
    render(<OpenMaicScenePanel />); fireEvent.click(screen.getByRole("button", { name: "浏览生成场景文档" }));
    fireEvent.click(await screen.findByRole("button", { name: "打开场景 候选课件" }));
    fireEvent.change(await screen.findByRole("textbox", { name: "你的回答" }), { target: { value: "尚未保存的解释" } });
    expect(screen.getByRole("button", { name: "打开场景 候选课件" })).toBeDisabled();
    expect(observed.at(-1)).toBe(true);
    expect(bridge.call.mock.calls.some(([op]) => op === "learning_provider_attempt_submit")).toBe(false);
  } finally { window.removeEventListener("archeaxis-draft-dirty", listener); }
});
