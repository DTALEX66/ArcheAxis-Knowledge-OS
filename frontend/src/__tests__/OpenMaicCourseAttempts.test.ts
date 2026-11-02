import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
import { cancelCourseAttempt, courseActivity, courseAnswerValues, freezeCourseAnswer, newCourseAttempt, readCourseHistory,
  startCourseAttempt, submitCourseAttempt } from "../presentation/importedCourseAttempts";
import { parseOpenMaicCourseV2 } from "../adapters/openmaicCourseV2";
import { fixture13Bytes } from "../test/fixtures/openmaicV2";

const document = { document_id: "doc_1", version: 1, content_sha256: "a".repeat(64) } as any;
const question = () => parseOpenMaicCourseV2(fixture13Bytes()).scenes[1].questions[0];
const activityReceipt = (activity: any) => ({ schema: "archeaxis.provider-learning-activity/v1", activity, duplicate: false,
  material_status: "current", question_binding: "client_declared_unverified", provider_identity: "adapter_declared_unverified", independent_mastery: "not_established" });
const startReceipt = (attempt: any) => ({ schema: "archeaxis.provider-learning-attempt/v1", activity_id: attempt.activity.activity_id,
  attempt_id: attempt.attemptId, state: "pending", origin_restore_epoch: "epoch_1", duplicate: false, material_status: "current" });
const resultReceipt = (attempt: any) => ({ schema: "archeaxis.provider-learning-result/v1", activity_id: attempt.activity.activity_id,
  attempt_id: attempt.attemptId, ...attempt.submission, duplicate: true, material_status: "current", question_binding: "client_declared_unverified",
  provider_result_verification: "unverified_client_report", independent_mastery: "not_established" });
const historyReceipt = (attempt: any) => ({ schema: "archeaxis.provider-learning-history/v1", activity: attempt.activity,
  question_binding: "client_declared_unverified", provider_identity: "adapter_declared_unverified",
  provider_result_verification: "unverified_client_report", independent_mastery: "not_established", material_status: "current", next_cursor: null,
  attempts: [{ attempt_id: attempt.attemptId, state: "submitted", origin_restore_epoch: "epoch_1",
    client_event_id: attempt.eventId, result: attempt.submission, client_cancel_id: null, created_at: "now", completed_at: "now" }] });
beforeEach(() => { vi.stubGlobal("crypto", webcrypto); bridge.call.mockReset(); });

describe("version-bound OpenMAIC Core attempt", () => {
  it("binds activity to the saved version and question; version claims remain client-declared", async () => {
    const a = await courseActivity(document, 1, question());
    expect(await courseActivity(document, 1, question())).toEqual(a);
    expect((await courseActivity({ ...document, version: 2 }, 1, question())).activity_id).not.toBe(a.activity_id);
    expect((await courseActivity(document, 2, question())).question.question_id).not.toBe(a.question.question_id);
    expect((await courseActivity(document, 1, { ...question(), question: "changed" })).question.question_version).not.toBe(a.question.question_version);
    expect(a.provider).toEqual({ id: "openmaic", version: "1.3.0" });
    expect(a.grant).toBeNull();
  });
  it("retries an uncertain submission using exactly the same answer/event and requires Core history readback", async () => {
    const attempt = freezeCourseAnswer(newCourseAttempt(await courseActivity(document, 1, question())), question(), ["source"]);
    let first = true;
    bridge.call.mockImplementation(async (op: string) => {
      if (op === "learning_provider_activity_create") return activityReceipt(attempt.activity);
      if (op === "learning_provider_attempt_start") return startReceipt(attempt);
      if (op === "learning_provider_attempt_submit") {
        if (first) { first = false; throw new Error("lost response"); }
        return resultReceipt(attempt);
      }
      if (op === "learning_provider_activity_get") return historyReceipt(attempt);
      throw new Error(op);
    });
    expect(await startCourseAttempt(attempt, () => true)).toBe("current");
    await expect(submitCourseAttempt(attempt, () => true)).rejects.toThrow("lost response");
    expect(await submitCourseAttempt(attempt, () => true)).toBe("current");
    const requests = bridge.call.mock.calls.filter(([op]) => op === "learning_provider_attempt_submit");
    expect(requests[0][1]).toEqual(requests[1][1]);
    expect(requests[1][1].body).toMatchObject({ provider_correct: null, self_report: false, rating: null, client_event_id: attempt.eventId });
    expect(courseAnswerValues(attempt.submission!.answer, question())).toEqual(["source"]);
    expect(bridge.call.mock.calls.at(-1)?.[1].after_attempt_id).toBe(attempt.attemptId.slice(0, -1));
  });
  it("does not accept an altered answer, provider grade or wrong activity in readback", async () => {
    const attempt = freezeCourseAnswer(newCourseAttempt(await courseActivity(document, 1, question())), question(), ["source"]);
    bridge.call.mockImplementation(async (op: string) => op === "learning_provider_attempt_submit" ? resultReceipt(attempt)
      : { ...historyReceipt(attempt), attempts: [{ ...historyReceipt(attempt).attempts[0], result: { ...attempt.submission, provider_correct: true } }] });
    await expect(submitCourseAttempt(attempt, () => true)).rejects.toThrow("未确认");
    bridge.call.mockResolvedValue({ ...historyReceipt(attempt), activity: { ...attempt.activity, material: { ...attempt.activity.material, version: 2 } } });
    await expect(readCourseHistory(attempt.activity)).rejects.toThrow("未确认");
  });
  it("reports a historical material version and rejects an unknown material status", async () => {
    const attempt = newCourseAttempt(await courseActivity(document, 1, question()));
    bridge.call.mockResolvedValueOnce({ ...historyReceipt(attempt), attempts: [], material_status: "historical" });
    expect((await readCourseHistory(attempt.activity)).materialStatus).toBe("historical");
    bridge.call.mockResolvedValueOnce({ ...historyReceipt(attempt), attempts: [], material_status: "unknown" });
    await expect(readCourseHistory(attempt.activity)).rejects.toThrow("未确认");
  });
  it("stops after a late activity or submission response when the caller is no longer current", async () => {
    const attempt = freezeCourseAnswer(newCourseAttempt(await courseActivity(document, 1, question())), question(), ["source"]);
    bridge.call.mockResolvedValueOnce(activityReceipt(attempt.activity));
    expect(await startCourseAttempt(attempt, () => false)).toBeNull();
    expect(bridge.call.mock.calls.map(([op]) => op)).toEqual(["learning_provider_activity_create"]);
    bridge.call.mockReset(); bridge.call.mockResolvedValueOnce(resultReceipt(attempt));
    expect(await submitCourseAttempt(attempt, () => false)).toBeNull();
    expect(bridge.call.mock.calls.map(([op]) => op)).toEqual(["learning_provider_attempt_submit"]);
  });
  it("verifies cancellation identity and refuses invalid or oversized answers", async () => {
    const attempt = newCourseAttempt(await courseActivity(document, 1, question()));
    bridge.call.mockResolvedValue({ schema: "archeaxis.provider-learning-cancel/v1", activity_id: attempt.activity.activity_id,
      attempt_id: attempt.attemptId, client_cancel_id: attempt.cancelId, state: "cancelled", duplicate: false, provider_stop_state: "unknown" });
    await cancelCourseAttempt(attempt);
    expect(() => freezeCourseAnswer(attempt, question(), [])).toThrow();
    const short = { id: "q", type: "short_answer" as const, question: "Explain" };
    expect(() => freezeCourseAnswer(attempt, short, ["中".repeat(7000)])).toThrow("限额");
    expect(courseAnswerValues('{"schema":"unknown","values":[]}', question())).toBeNull();
  });
});
