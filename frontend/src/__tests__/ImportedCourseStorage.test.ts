import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
import { prepareCourseImport, saveCourseImport, reopenCourseImport, importedCourseEditor, CourseImportFailure } from "../presentation/importedCourseStorage";
import { fixtureBytes } from "../test/fixtures/openmaic";
import { sha256 } from "../presentation/exchangeProof";

let saved: any; let original: any;
beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto); bridge.call.mockReset(); saved = null;
});
async function setup() {
  const prepared = await prepareCourseImport(fixtureBytes(), "manifest.json");
  original = { source_id: "source1", name: "earlier-name.json", sha256: prepared.sha256,
    media_type: "application/json", content_base64: btoa(String.fromCharCode(...prepared.bytes)) };
  bridge.call.mockImplementation(async (op: string, payload: any) => {
    if (op === "source_import") return { source_id: "source1", sha256: prepared.sha256, duplicate: true };
    if (op === "source_original") return structuredClone(original);
    if (op === "document_create") {
      const body = payload.body;
      saved = { ...body, document_id: prepared.documentId, version: 1, content_sha256: "a".repeat(64), text_projection: "quiz", blocks: [], revision_basis: null };
      return structuredClone(saved);
    }
    if (op === "document_get") return structuredClone(saved);
    throw new Error(op);
  });
  return prepared;
}
describe("external course custody → Core document → explicit readback", () => {
  it("freezes identity, verifies CAS bytes, then saves and reads complete metadata; duplicate source name is allowed", async () => {
    const prepared = await setup();
    const stages: string[] = [];
    const result = await saveCourseImport(prepared, phase => stages.push(phase));
    expect(result.course.status).toBe("candidate");
    expect(result.course.grounding).toBe("external_unverified");
    expect(result.course.provenance.file_name).toBe("manifest.json");
    expect(result.course.scenes[0].questions[0].answer).toEqual(["source"]);
    expect(bridge.call.mock.calls.map(([op]) => op)).toEqual(["source_import", "source_original", "document_create", "document_get"]);
    expect(stages).toEqual(["original_confirmed", "document_submitted"]);
    expect((await prepareCourseImport(fixtureBytes(), "manifest.json")).requestId).toBe(prepared.requestId);
    expect((await reopenCourseImport(result.document.document_id)).course).toEqual(result.course);
    expect(bridge.call.mock.calls.some(([op]) => ["course_from_knowledge", "knowledge_review", "learning_review"].includes(op))).toBe(false);
  });
  it("rejects a changed frozen original before any write", async () => {
    const p = await setup(); p.bytes[0] ^= 1;
    await expect(saveCourseImport(p)).rejects.toThrow("冻结");
    expect(bridge.call).not.toHaveBeenCalled();
  });
  it("does not create a document after a mismatched custody receipt or original", async () => {
    const p = await setup(); original.content_base64 = btoa("changed");
    await expect(saveCourseImport(p)).rejects.toThrow();
    expect(bridge.call.mock.calls.some(([op]) => op === "document_create")).toBe(false);
    bridge.call.mockImplementation(async () => ({ source_id: "source1", sha256: "b".repeat(64), duplicate: false }));
    await expect(saveCourseImport(p)).rejects.toThrow();
  });
  it("reports source custody separately when document result is unknown and reuses the same creation body on retry", async () => {
    const p = await setup(), normal = bridge.call.getMockImplementation()!;
    let first = true;
    bridge.call.mockImplementation(async (op: string, payload: unknown) => {
      if (op === "document_create" && first) { first = false; throw new Error("lost response"); }
      return normal(op, payload);
    });
    const error = await saveCourseImport(p).catch(e => e);
    expect(error).toBeInstanceOf(CourseImportFailure);
    expect(error.originalConfirmed).toBe(true);
    expect(error.message).toContain("课程保存结果待核对");
    await saveCourseImport(p);
    const requests = bridge.call.mock.calls.filter(([op]) => op === "document_create");
    expect(requests[0][1]).toEqual(requests[1][1]);
  });
  it.each(["wrong document", "changed metadata", "changed hash", "changed projection"])("withholds success for %s readback", async mode => {
    const p = await setup(), normal = bridge.call.getMockImplementation()!;
    bridge.call.mockImplementation(async (op: string, payload: unknown) => {
      const result = await normal(op, payload);
      if (op === "document_get") {
        if (mode === "wrong document") result.document_id = "other";
        if (mode === "changed metadata") result.editor_json.attrs.archeaxis_imported_course.grounding = "verified";
        if (mode === "changed hash") result.content_sha256 = "b".repeat(64);
        if (mode === "changed projection") result.editor_json.content[0].content[0].text = "changed";
      }
      return result;
    });
    await expect(saveCourseImport(p)).rejects.toThrow("待核对");
  });
  it("reopening reparses the original and refuses fabricated typed answers even when a saved hash looks valid", async () => {
    const p = await setup(); await saveCourseImport(p);
    saved.editor_json.attrs.archeaxis_imported_course.scenes[0].questions[0].answer = ["guess"];
    await expect(reopenCourseImport(p.documentId)).rejects.toThrow();
    expect(await sha256(fixtureBytes())).toBe(p.sha256);
  });
  it("keeps 200 questions × 32 options intact within the actual Core block budget", async () => {
    const draft = (await setup()).draft;
    const question = draft.scenes[0].questions[0];
    draft.scenes[0].questions = Array.from({ length: 200 }, (_, index) => ({ ...question, id: `q${index}`,
      options: Array.from({ length: 32 }, (_, i) => ({ label: `L${i}`, value: `${i}` })), answer: ["0"] }));
    const candidate: any = { ...draft, schema: "archeaxis.imported-course/v1", status: "candidate", grounding: "external_unverified",
      human_review_required: true, provenance: { adapter: "openmaic-manifest/v1", upstream_commit: "6b83751a87896df99c47e98c20cea40cec09efb4",
        source_id: "source1", sha256: "a".repeat(64), file_name: "manifest.json", byte_length: 100 } };
    const editor = importedCourseEditor(candidate);
    expect(editor.content.length).toBeLessThan(5000);
    expect(editor.attrs.archeaxis_imported_course.scenes[0].questions).toHaveLength(200);
    expect(editor.attrs.archeaxis_imported_course.scenes[0].questions[199].options).toHaveLength(32);
  });
});
