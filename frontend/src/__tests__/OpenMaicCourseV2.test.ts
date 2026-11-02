import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
import { parseOpenMaicCourse, OPENMAIC_COMMIT } from "../adapters/openmaicCourse";
import { parseOpenMaicCourseV2 } from "../adapters/openmaicCourseV2";
import { importedCourseEditor, prepareCourseImport, preserveCourseOriginal, reopenCourseImport, saveCourseImport } from "../presentation/importedCourseStorage";
import { sha256 } from "../presentation/exchangeProof";
import { slideText, type ImportedCourse } from "../presentation/importedCourse";
import { openMaicFixture } from "../test/fixtures/openmaic";
import { fixture13Bytes, openMaic13Fixture } from "../test/fixtures/openmaicV2";

const bytes = (value: unknown) => new TextEncoder().encode(JSON.stringify(value));
beforeEach(() => { vi.stubGlobal("crypto", webcrypto); bridge.call.mockReset(); });

describe("OpenMAIC 1.3.0 manifest -> AAOS v2 candidate", () => {
  it("keeps upstream format 1 distinct from the AAOS schema, canvas geometry and quiz", async () => {
    const draft = parseOpenMaicCourseV2(fixture13Bytes());
    expect(draft.scenes.map(scene => scene.kind)).toEqual(["slide", "quiz"]);
    expect(draft.scenes[0].slide?.elements[0].left).toBe(100);
    expect(slideText(draft.scenes[0].slide!.elements[0].content)).toBe("核对原件 & 来源");
    expect(draft.scenes[1].questions[0].answer).toEqual(["source"]);
    const prepared = await prepareCourseImport(fixture13Bytes(), "manifest.json");
    expect(prepared.adapter).toBe("openmaic-1.3.0-manifest/v2");
    expect(JSON.parse(new TextDecoder().decode(prepared.bytes)).formatVersion).toBe(1);
  });
  it("accepts the exporter's 0.0.0 fallback without claiming the source version is established", async () => {
    const fallback = { ...openMaic13Fixture(), appVersion: "0.0.0" };
    const prepared = await prepareCourseImport(bytes(fallback), "manifest.json");
    expect(prepared.adapter).toBe("openmaic-1.3.0-manifest/v2");
    expect(prepared.draft.scenes[0].kind).toBe("slide");
    expect(prepared.draft.report.join(" ")).toContain("不证明课件来源");
    const future = { ...fallback, appVersion: "1.4.0" };
    expect(() => parseOpenMaicCourseV2(bytes(future))).toThrow("appVersion");
    await expect(prepareCourseImport(bytes(future), "manifest.json")).rejects.toThrow("scenes[0].type");
  });
  it.each([
    ["unknown upstream format", (v: any) => { v.formatVersion = 2; }, "formatVersion"],
    ["unknown content schema", (v: any) => { v.scenes[0].content.schemaVersion = 2; }, "schemaVersion"],
    ["unknown scene", (v: any) => { v.scenes[0].type = "interactive"; }, ".type"],
    ["unknown renderer", (v: any) => { v.scenes[0].content.canvas.elements[0].type = "future"; }, "elements[0].type"],
    ["media element", (v: any) => { v.scenes[0].content.canvas.elements[0].type = "image"; }, "elements[0].type"],
    ["inline media", (v: any) => { v.scenes[0].content.canvas.elements[0].content = '<img src="https://example.invalid/a">'; }, "elements[0].content"],
    ["embedded script", (v: any) => { v.scenes[0].content.canvas.elements[0].content = "<script>alert(1)</script>"; }, "elements[0].content"],
    ["external background", (v: any) => { v.scenes[0].content.canvas.background = { type: "image", image: { src: "https://example.invalid/a" } }; }, "background.type"],
    ["action", (v: any) => { v.scenes[0].actions = [{ type: "speech" }]; }, "actions"],
    ["media index", (v: any) => { v.mediaIndex = { x: { type: "image", missing: true } }; }, "mediaIndex"],
    ["duplicate scene", (v: any) => { v.scenes[1].order = 0; }, "scenes.order"],
    ["bad geometry", (v: any) => { v.scenes[0].content.canvas.elements[0].width = -1; }, "width"],
    ["CSS url", (v: any) => { v.scenes[0].content.canvas.theme.backgroundColor = "url(https://example.invalid)"; }, "backgroundColor"],
  ])("rejects %s without executing or truncating it", (_name, mutate, expectedPath) => {
    const value: any = openMaic13Fixture(); mutate(value);
    expect(() => parseOpenMaicCourseV2(bytes(value))).toThrow(expectedPath as string);
  });
  it("rejects oversized and invalid UTF-8 inputs", () => {
    expect(() => parseOpenMaicCourseV2(new Uint8Array(256 * 1024 + 1))).toThrow("256 KiB");
    expect(() => parseOpenMaicCourseV2(new Uint8Array([255]))).toThrow("UTF-8");
  });
});

describe("v1 and v2 persisted identities", () => {
  it("saves and reopens v2 only after original byte and Core Document readback", async () => {
    const prepared = await prepareCourseImport(fixture13Bytes(), "manifest.json");
    const original = { source_id: "source1", sha256: prepared.sha256,
      content_base64: btoa(Array.from(prepared.bytes, b => String.fromCharCode(b)).join("")) };
    let saved: any;
    bridge.call.mockImplementation(async (op: string, payload: any) => {
      if (op === "source_import") return { source_id: "source1", sha256: prepared.sha256, duplicate: false };
      if (op === "source_original") return structuredClone(original);
      if (op === "document_create") {
        saved = { ...payload.body, document_id: prepared.documentId, version: 1, content_sha256: "a".repeat(64), text_projection: "course" };
        return structuredClone(saved);
      }
      if (op === "document_get") return structuredClone(saved);
      throw new Error(op);
    });
    const result = await saveCourseImport(prepared);
    expect(result.course.schema).toBe("archeaxis.imported-course/v2");
    expect(result.course.provenance.adapter).toBe("openmaic-1.3.0-manifest/v2");
    expect((await reopenCourseImport(result.document.document_id)).course).toEqual(result.course);
    saved.editor_json.attrs.archeaxis_imported_course.scenes[0].slide.elements[0].content = "changed";
    await expect(reopenCourseImport(result.document.document_id)).rejects.toThrow();
  });
  it("reopens an old v1 document even when its source appVersion says 1.3.0", async () => {
    const raw = { ...openMaicFixture(), appVersion: "1.3.0" }, source = bytes(raw), hash = await sha256(source);
    const course: ImportedCourse = { ...parseOpenMaicCourse(source), schema: "archeaxis.imported-course/v1", status: "candidate",
      grounding: "external_unverified", human_review_required: true, provenance: { adapter: "openmaic-manifest/v1",
        upstream_commit: OPENMAIC_COMMIT, file_name: "manifest.json", source_id: "source1", sha256: hash, byte_length: source.length } };
    const saved = { document_id: "old", version: 1, source_id: "source1", source_revision: hash,
      content_sha256: "a".repeat(64), text_projection: "quiz", title: `外部课程候选 · ${course.title}`, editor_json: importedCourseEditor(course) };
    bridge.call.mockImplementation(async (op: string) => op === "document_get" ? structuredClone(saved)
      : { source_id: "source1", sha256: hash, content_base64: btoa(Array.from(source, b => String.fromCharCode(b)).join("")) });
    expect((await reopenCourseImport("old")).course).toEqual(course);
    expect((await prepareCourseImport(source, "manifest.json")).adapter).toBe("openmaic-1.3.0-manifest/v2");
  });
  it("preserves unsupported bytes only through Core source custody, and refuses a bad readback hash", async () => {
    const source = fixture13Bytes(), hash = await sha256(source);
    const original = { source_id: "source1", sha256: hash, content_base64: btoa(Array.from(source, b => String.fromCharCode(b)).join("")) };
    bridge.call.mockImplementation(async (op: string) => op === "source_import"
      ? { source_id: "source1", sha256: hash, duplicate: false } : structuredClone(original));
    expect(await preserveCourseOriginal(source, "manifest.json")).toEqual({ sourceId: "source1", sha256: hash });
    expect(bridge.call.mock.calls.map(([op]) => op)).toEqual(["source_import", "source_original"]);
    original.content_base64 = btoa("wrong bytes");
    await expect(preserveCourseOriginal(source, "manifest.json")).rejects.toThrow();
  });
});
