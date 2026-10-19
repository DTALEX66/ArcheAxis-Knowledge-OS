import { describe, expect, it } from "vitest";
import { parseOpenMaicCourse } from "../adapters/openmaicCourse";
import { referenceFeedback } from "../presentation/importedCourse";
import { fixtureBytes, openMaicFixture } from "../test/fixtures/openmaic";

const bytes = (v: unknown) => new TextEncoder().encode(JSON.stringify(v));
describe("OpenMAIC fixed export → external unverified quiz candidate", () => {
  it("accepts the real manifest shape without invented scene IDs, preserving question and reference text", () => {
    const course = parseOpenMaicCourse(fixtureBytes());
    expect(course.title).toBe("证据与来源");
    expect(course.scenes[0].questions[0].question).toContain("<script>never()</script>");
    expect(course.scenes[0].questions[0].answer).toEqual(["source"]);
    expect(course.report).toContain("参考答案由外部课件提供，尚未核验。");
  });
  it.each([
    ["version", (v: any) => v.formatVersion = 2, "formatVersion"],
    ["unknown top field", (v: any) => v.future = true, "future"],
    ["slide canvas", (v: any) => v.scenes[0].type = "slide", "scenes[0].type"],
    ["mismatch", (v: any) => v.scenes[0].content.type = "slide", "content.type"],
    ["action", (v: any) => v.scenes[0].actions = [{ type: "speech" }], "actions"],
    ["whiteboard", (v: any) => v.scenes[0].whiteboards = [{}], "whiteboards"],
    ["media", (v: any) => v.mediaIndex = { a: {} }, "mediaIndex"],
    ["video", (v: any) => v.stage.videoManifest = { a: {} }, "videoManifest"],
    ["agents", (v: any) => v.scenes[0].multiAgent = { enabled: true, agentIndices: [] }, "multiAgent"],
    ["duplicate question", (v: any) => v.scenes[0].content.questions.push(v.scenes[0].content.questions[0]), "questions"],
    ["unknown question", (v: any) => v.scenes[0].content.questions[0].future = 1, "future"],
    ["unknown answer", (v: any) => v.scenes[0].content.questions[0].answer = ["missing"], "answer"],
    ["duplicate option", (v: any) => v.scenes[0].content.questions[0].options[1].value = "source", "options"],
    ["bad points", (v: any) => v.scenes[0].content.questions[0].points = -1, "points"],
  ])("refuses %s with a concrete JSON path instead of dropping it", (_label, mutate, path) => {
    const value = openMaicFixture(); mutate(value);
    expect(() => parseOpenMaicCourse(bytes(value))).toThrow(path as string);
  });
  it("preserves absent references and short answers without equating them with correctness or mastery", () => {
    const value: any = openMaicFixture();
    value.scenes[0].content.questions.push({ id: "q2", type: "short_answer", question: "解释", hasAnswer: false, commentPrompt: "not executed" });
    const question = parseOpenMaicCourse(bytes(value)).scenes[0].questions[1];
    expect(question.answer).toBeUndefined();
    expect(question.commentPrompt).toBe("not executed");
    expect(referenceFeedback(question, [])).toBe("no_reference");
    expect(referenceFeedback({ ...question, hasAnswer: true, answer: ["解释"] }, ["解释"])).toBe("review_required");
  });
  it("compares multiple-choice sets against provided references only; no partial answer turns correct", () => {
    const q: any = { ...parseOpenMaicCourse(fixtureBytes()).scenes[0].questions[0], type: "multiple", answer: ["source", "guess"] };
    expect(referenceFeedback(q, ["guess", "source"])).toBe("matches_reference");
    expect(referenceFeedback(q, ["source"])).toBe("differs_from_reference");
    expect(referenceFeedback(q, ["source", "source", "guess"])).toBe("invalid_response");
  });
  it("limits bytes, scene count and duplicate order; never truncates", () => {
    expect(() => parseOpenMaicCourse(new Uint8Array(256 * 1024 + 1))).toThrow("256 KiB");
    const value: any = openMaicFixture(); value.scenes = Array.from({ length: 65 }, (_, order) => ({ ...value.scenes[0], order }));
    expect(() => parseOpenMaicCourse(bytes(value))).toThrow("scenes");
    value.scenes = [value.scenes[0], value.scenes[0]];
    expect(() => parseOpenMaicCourse(bytes(value))).toThrow("order");
    expect(() => parseOpenMaicCourse(new Uint8Array([255]))).toThrow("UTF-8");
  });
});
