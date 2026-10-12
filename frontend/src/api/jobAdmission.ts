import { ApiError, type JobAdmissionRefusal } from "./client";

type Attempt = { job_id: string; request_id: string; body: { deadline_ms: number; split: boolean; words: boolean } };
export function jobAdmissionRefusal(value: unknown, attempt: Attempt): JobAdmissionRefusal | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return;
  const r = value as Record<string, unknown>, b = r.budget as Record<string, unknown> | undefined;
  if (r.schema !== "archeaxis.job-admission-refusal/v1" || r.code !== "AAK-CAP-001"
    || r.job_id !== attempt.job_id || r.request_id !== attempt.request_id
    || !b || b.deadline_ms !== attempt.body.deadline_ms || b.split !== attempt.body.split || b.words !== attempt.body.words
    || r.admission_state !== "NOT_ADMITTED" || r.request_consumed !== false || r.active_execution !== false
    || r.enabled !== false || r.same_request_retry_allowed !== true
    || ![r.input_ref, r.kind, r.capability].every(v => typeof v === "string" && v.length > 0 && v.length <= 200)) return;
  return r as JobAdmissionRefusal;
}
export function recoverableJobRefusal(error: unknown, attempt: Attempt, source: string, kind?: string): boolean {
  if (!(error instanceof ApiError) || error.status !== 409) return false;
  const r = jobAdmissionRefusal(error.jobAdmission, attempt);
  return !!r && r.input_ref === source && (kind === undefined || r.kind === kind);
}
