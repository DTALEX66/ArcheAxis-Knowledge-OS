import type { BoundedJobCommand, JobStatus } from "../components/BoundedJobPanel";

// Batch-specific finite adapter, using the existing bounded command/status contract.
// No worker, scheduler, database or general runtime is implemented in the browser.
export const FOLDER_EXECUTION_BUDGET_MS = 90_000;
export type JobState = "queued" | "pending" | "running" | "leased" | "starting" | "succeeded" | "failed" | "cancelled" | "rejected";
export type FolderAttempt = Readonly<{ job_id: string; request_id: string; body: Readonly<{ deadline_ms: number; split: boolean; words: boolean }> }>;
const STATES: readonly string[] = ["queued", "pending", "running", "leased", "starting", "succeeded", "failed", "cancelled", "rejected"];
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Core 回执结构无效");
  return value as Record<string, unknown>;
}
export function jobState(value: unknown): JobState {
  if (typeof value !== "string" || !STATES.includes(value)) throw new Error("Core 作业状态未知");
  return value as JobState;
}
export function terminalJobState(state: string): boolean {
  return ["succeeded", "failed", "cancelled", "rejected"].includes(state);
}
export function freezeFolderAttempt(job_id: string): FolderAttempt {
  return Object.freeze({ job_id, request_id: `folder_run_${crypto.randomUUID()}`, body: Object.freeze({ deadline_ms: FOLDER_EXECUTION_BUDGET_MS, split: false, words: false }) });
}
export function folderExecutionAck(value: unknown, attempt: FolderAttempt): JobState {
  const receipt = object(value);
  if (receipt.job_id !== attempt.job_id || receipt.request_id !== attempt.request_id || typeof receipt.replayed !== "boolean") throw new Error("执行回执身份不匹配");
  return jobState(receipt.state);
}
export function folderCancelAck(value: unknown, attempt: FolderAttempt): void {
  const receipt = object(value);
  if (receipt.job_id !== attempt.job_id || receipt.request_id !== attempt.request_id || typeof receipt.cancel_requested !== "boolean") throw new Error("取消回执身份不匹配");
  if (receipt.state !== undefined) jobState(receipt.state);
}
export function folderJobStatus(value: unknown, job: string, source: string, expected?: FolderAttempt): JobStatus {
  const receipt = object(value);
  const state = jobState(receipt.state);
  if (receipt.job_id !== job || receipt.input_ref !== source
    || !(receipt.attempt === null || (Number.isSafeInteger(receipt.attempt) && Number(receipt.attempt) > 0))
    || !(receipt.request_id === null || typeof receipt.request_id === "string" && receipt.request_id.length > 0)
    || !(receipt.error === null || typeof receipt.error === "string")) throw new Error("状态回执身份不匹配");
  if (expected && (receipt.request_id !== expected.request_id || receipt.attempt === null)) throw new Error("尚未读回冻结执行身份；不能认领另一个尝试");
  if (expected && !Array.isArray(receipt.attempts)) throw new Error("冻结请求的尝试历史缺失");
  if (receipt.attempts !== undefined) {
    if (!Array.isArray(receipt.attempts)) throw new Error("尝试历史结构无效");
    const matches = receipt.attempts.filter(raw => raw && typeof raw === "object" && (raw as Record<string, unknown>).attempt === receipt.attempt);
    if (expected && matches.length !== 1) throw new Error("当前尝试历史缺失或身份重复");
    const current = matches[0];
    if (current) {
      const item = object(current);
      if (item.request_id !== receipt.request_id || item.state !== state) throw new Error("当前尝试历史身份不匹配");
      if (expected) {
        const budget = object(item.budget);
        if (budget.deadline_ms !== expected.body.deadline_ms || budget.split !== expected.body.split || budget.words !== expected.body.words) throw new Error("冻结执行预算不匹配");
      }
    } else if (expected) throw new Error("当前尝试历史缺失");
  }
  return receipt as JobStatus;
}
export function freshAttemptEligible(status: JobStatus): boolean {
  if (!["failed", "cancelled"].includes(status.state) || !Array.isArray(status.attempts)) return false;
  const raw = status.attempts.find(value => value && typeof value === "object" && (value as Record<string, unknown>).attempt === status.attempt);
  if (!raw || typeof raw !== "object") return false;
  const item = raw as Record<string, unknown>, continuation = item.continuation;
  return item.request_id === status.request_id && item.state === status.state && !!continuation && typeof continuation === "object"
    && (continuation as Record<string, unknown>).new_attempt_eligible_state === true;
}
export async function readFolderStatus(command: BoundedJobCommand, job: string, source: string, expected?: FolderAttempt): Promise<JobStatus> {
  return folderJobStatus(await command("job_execution_status", { job_id: job }), job, source, expected);
}
export async function pollFolderAttempt(command: BoundedJobCommand, attempt: FolderAttempt, source: string,
  current: () => boolean, onRead: (status: JobStatus) => void, wait: (ms: number) => Promise<void>, pollMs = 300): Promise<JobStatus> {
  const deadline = Date.now() + attempt.body.deadline_ms + 5_000;
  while (current() && Date.now() < deadline) {
    const status = await readFolderStatus(command, attempt.job_id, source, attempt);
    if (!current()) throw new Error("当前页面已退出，原任务仍由 Core 管理");
    onRead(status);
    if (terminalJobState(status.state)) return status;
    await wait(pollMs);
  }
  throw new Error("执行终态未确认；保留冻结请求，不能自动产生新尝试");
}
