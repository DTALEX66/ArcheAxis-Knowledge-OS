import { coreCommand } from "../api/core";
import type { DocumentDto } from "../api/generated/core-contract";
import { object, sameValue, sha256 } from "./exchangeProof";
import type { ImportedQuestion } from "./importedCourse";

type Activity = { activity_id: string; material: { document_id: string; version: number; content_sha256: string };
  provider: { id: "openmaic"; version: "1.3.0" }; question: { question_id: string; question_version: string }; grant: null };
type Submission = { client_event_id: string; answer: string; provider_correct: null; self_report: false; rating: null };
export type CourseAttempt = { activity: Activity; attemptId: string; eventId: string; cancelId: string; submission?: Submission };
export type CourseHistoryRow = { attemptId: string; state: "pending" | "submitted" | "cancelled";
  answer: string | null; clientEventId: string | null; selfReport: boolean | null; rating: string | null;
  createdAt: string; completedAt: string | null };
export type MaterialStatus = "current" | "historical" | "unavailable";
export type CourseHistoryPage = { rows: CourseHistoryRow[]; nextCursor: string | null; materialStatus: MaterialStatus };

function validToken(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9_-]{1,128}$/.test(value);
}
function invalid(): never { throw new Error("Core 作答回执或版本身份不一致；结果未确认，请保留原请求。"); }
function materialStatus(value: unknown): MaterialStatus {
  if (value !== "current" && value !== "historical" && value !== "unavailable") invalid();
  return value;
}
const hash = (value: unknown) => sha256(new TextEncoder().encode(JSON.stringify(value)));

/** Stable identity, including the actual saved Core document version and content SHA. */
export async function courseActivity(document: DocumentDto, order: number, question: ImportedQuestion): Promise<Activity> {
  if (!validToken(document.document_id) || !Number.isSafeInteger(document.version) || document.version < 1
    || !/^[a-f0-9]{64}$/.test(document.content_sha256) || !Number.isSafeInteger(order) || order < 0) invalid();
  const questionId = `q_${await hash(["openmaic-question-id/v1", order, question.id])}`;
  const questionVersion = await hash(["openmaic-question-content/v1", question]);
  const material = { document_id: document.document_id, version: document.version, content_sha256: document.content_sha256 };
  return { activity_id: `openmaic_${await hash(["openmaic-activity/v1", material, questionId, questionVersion])}`,
    material, provider: { id: "openmaic", version: "1.3.0" },
    question: { question_id: questionId, question_version: questionVersion }, grant: null };
}
export function newCourseAttempt(activity: Activity): CourseAttempt {
  return { activity, attemptId: `attempt_${crypto.randomUUID()}`, eventId: `event_${crypto.randomUUID()}`,
    cancelId: `cancel_${crypto.randomUUID()}` };
}
function activityReceipt(value: unknown, activity: Activity) {
  const receipt = object(value);
  if (receipt.schema !== "archeaxis.provider-learning-activity/v1" || !sameValue(receipt.activity, activity)
    || typeof receipt.duplicate !== "boolean" || receipt.question_binding !== "client_declared_unverified"
    || receipt.provider_identity !== "adapter_declared_unverified" || receipt.independent_mastery !== "not_established") invalid();
  materialStatus(receipt.material_status);
}
/** `current` stops a late response from starting another operation after unmount/reselection. */
export async function startCourseAttempt(attempt: CourseAttempt, current: () => boolean): Promise<MaterialStatus | null> {
  activityReceipt(await coreCommand("learning_provider_activity_create", { body: attempt.activity }), attempt.activity);
  if (!current()) return null;
  const receipt = object(await coreCommand("learning_provider_attempt_start", { activity_id: attempt.activity.activity_id,
    body: { attempt_id: attempt.attemptId } }));
  if (receipt.schema !== "archeaxis.provider-learning-attempt/v1" || receipt.activity_id !== attempt.activity.activity_id
    || receipt.attempt_id !== attempt.attemptId || receipt.state !== "pending" || typeof receipt.origin_restore_epoch !== "string"
    || typeof receipt.duplicate !== "boolean") invalid();
  const status = materialStatus(receipt.material_status);
  return current() ? status : null;
}

function checkedValues(question: ImportedQuestion, selected: string[]): string[] {
  if (!Array.isArray(selected) || !selected.length || selected.some(v => typeof v !== "string" || !v.trim() || v.includes("\u0000"))
    || new Set(selected).size !== selected.length) throw new Error("请先填写有效答案。");
  if (question.type === "short_answer") {
    if (selected.length !== 1) throw new Error("短答只能保存一份文字答案。");
    return selected;
  }
  if ((question.type === "single" && selected.length !== 1) || selected.some(value => !question.options?.some(option => option.value === value)))
    throw new Error("请选择有效选项后保存。");
  return [...selected].sort();
}
export function freezeCourseAnswer(attempt: CourseAttempt, question: ImportedQuestion, selected: string[]): CourseAttempt {
  if (attempt.submission) return attempt;
  const values = checkedValues(question, selected);
  const answer = JSON.stringify({ schema: "archeaxis.openmaic-response/v1", question_type: question.type, values });
  if (new TextEncoder().encode(answer).length > 20_000) throw new Error("答案超过 Core 限额；未提交。");
  return { ...attempt, submission: { client_event_id: attempt.eventId, answer, provider_correct: null, self_report: false, rating: null } };
}
/** Parse only our bounded response shape; a different producer's answer stays uninterpreted. */
export function courseAnswerValues(answer: string, question: ImportedQuestion): string[] | null {
  try {
    const value = object(JSON.parse(answer));
    if (value.schema !== "archeaxis.openmaic-response/v1" || value.question_type !== question.type
      || Object.keys(value).length !== 3 || !Array.isArray(value.values)) return null;
    return checkedValues(question, value.values as string[]);
  } catch { return null; }
}

export async function readCourseHistory(activity: Activity, cursor?: string): Promise<CourseHistoryPage> {
  if (cursor !== undefined && !validToken(cursor)) invalid();
  const response = object(await coreCommand("learning_provider_activity_get", { activity_id: activity.activity_id,
    ...(cursor ? { after_attempt_id: cursor } : {}) }));
  if (response.schema !== "archeaxis.provider-learning-history/v1" || !sameValue(response.activity, activity)
    || response.question_binding !== "client_declared_unverified" || response.provider_identity !== "adapter_declared_unverified"
    || response.provider_result_verification !== "unverified_client_report" || response.independent_mastery !== "not_established"
    || !Array.isArray(response.attempts) || response.attempts.length > 100
    || !(response.next_cursor === null || validToken(response.next_cursor))) invalid();
  const rows = response.attempts.map(item => {
    const row = object(item);
    if (!validToken(row.attempt_id) || !["pending", "submitted", "cancelled"].includes(row.state as string)
      || typeof row.origin_restore_epoch !== "string" || typeof row.created_at !== "string"
      || !(row.completed_at === null || typeof row.completed_at === "string")
      || !(row.client_event_id === null || validToken(row.client_event_id))) invalid();
    let answer: string | null = null, selfReport: boolean | null = null, rating: string | null = null;
    if (row.state === "submitted") {
      const result = object(row.result);
      if (result.client_event_id !== row.client_event_id || !validToken(result.client_event_id)
        || typeof result.answer !== "string" || result.provider_correct !== null || typeof result.self_report !== "boolean"
        || !(result.rating === null || typeof result.rating === "string")) invalid();
      answer = result.answer;
      selfReport = result.self_report as boolean;
      rating = result.rating as string | null;
    } else if (row.result !== null || row.client_event_id !== null) invalid();
    return { attemptId: row.attempt_id as string, state: row.state as CourseHistoryRow["state"], answer,
      clientEventId: row.client_event_id as string | null, selfReport, rating, createdAt: row.created_at as string,
      completedAt: row.completed_at as string | null };
  });
  if (rows.some((row, index) => (index === 0 && cursor !== undefined && row.attemptId <= cursor)
      || (index > 0 && row.attemptId <= rows[index - 1].attemptId))
    || (response.next_cursor !== null && (rows.length !== 100 || response.next_cursor !== rows[rows.length - 1].attemptId))) invalid();
  return { rows, nextCursor: response.next_cursor as string | null, materialStatus: materialStatus(response.material_status) };
}
export async function submitCourseAttempt(attempt: CourseAttempt, current: () => boolean): Promise<MaterialStatus | null> {
  const submission = attempt.submission;
  if (!submission) throw new Error("请先冻结本次答案。");
  const receipt = object(await coreCommand("learning_provider_attempt_submit", { activity_id: attempt.activity.activity_id,
    attempt_id: attempt.attemptId, body: submission }));
  if (receipt.schema !== "archeaxis.provider-learning-result/v1" || receipt.activity_id !== attempt.activity.activity_id
    || receipt.attempt_id !== attempt.attemptId || receipt.client_event_id !== submission.client_event_id
    || receipt.answer !== submission.answer || receipt.provider_correct !== null || receipt.self_report !== false || receipt.rating !== null
    || typeof receipt.duplicate !== "boolean" || receipt.question_binding !== "client_declared_unverified"
    || receipt.provider_result_verification !== "unverified_client_report" || receipt.independent_mastery !== "not_established") invalid();
  materialStatus(receipt.material_status);
  if (!current()) return null;
  // Start just before the random ID lexicographically; paginate instead of assuming a single page.
  let cursor: string | undefined = attempt.attemptId.slice(0, -1);
  for (let page = 0; page < 8; page++) {
    const history = await readCourseHistory(attempt.activity, cursor);
    if (!current()) return null;
    const found = history.rows.find(row => row.attemptId === attempt.attemptId);
    if (found) {
      if (found.state !== "submitted" || found.clientEventId !== submission.client_event_id || found.answer !== submission.answer
        || found.selfReport !== false || found.rating !== null) invalid();
      return history.materialStatus;
    }
    if (history.rows.some(row => row.attemptId > attempt.attemptId) || !history.nextCursor) break;
    cursor = history.nextCursor;
  }
  return invalid();
}
export async function cancelCourseAttempt(attempt: CourseAttempt): Promise<void> {
  const receipt = object(await coreCommand("learning_provider_attempt_cancel", { activity_id: attempt.activity.activity_id,
    attempt_id: attempt.attemptId, body: { client_cancel_id: attempt.cancelId } }));
  if (receipt.schema !== "archeaxis.provider-learning-cancel/v1" || receipt.activity_id !== attempt.activity.activity_id
    || receipt.attempt_id !== attempt.attemptId || receipt.client_cancel_id !== attempt.cancelId
    || receipt.state !== "cancelled" || typeof receipt.duplicate !== "boolean" || receipt.provider_stop_state !== "unknown") invalid();
}
