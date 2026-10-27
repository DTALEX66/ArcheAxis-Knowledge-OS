import { useSyncExternalStore } from "react";
import { coreFailureReason } from "./labels";

export interface DiagnosticEntry {
  label: string;
  payload: unknown;
  at: string;
  sequence: number;
  category: DiagnosticCategory;
  summary?: string;
  occurrences?: number;
  automatic?: boolean;
}
export const diagnosticCategories = {runtime: "运行与连接", operation: "操作与回执", data: "对象与来源"} as const;
export type DiagnosticCategory = keyof typeof diagnosticCategories;
type DiagnosticState = {entries: DiagnosticEntry[]; open: boolean; filter: DiagnosticCategory | "all"; selected: number | null; suspended: boolean};
const LIMIT = 50;
let state: DiagnosticState = {entries: [], open: false, filter: "all", selected: null, suspended: false};
const listeners = new Set<() => void>();
let sequence = 0;
let opener: HTMLElement | null = null;
let observationEpoch = 0;
function update(patch: Partial<DiagnosticState>) {
  state = {...state, ...patch};
  for (const listener of listeners) listener();
}
const subscribe = (listener: () => void) => {listeners.add(listener); return () => {listeners.delete(listener);};};
const snapshot = () => state;

/** A request started in another workspace/recovery generation cannot publish here. */
export function beginDiagnosticObservation(): number | null {
  return state.suspended ? null : observationEpoch;
}

const operationLabels: Record<string, string> = {
  sources_list: "读取资料列表", source_get: "打开原件", source_original: "读取原件",
  documents_list: "读取文档列表", document_get: "打开文档", document_create: "新建文档",
  document_draft: "保存文档", document_restore: "恢复文档版本", search: "搜索内容",
  learning_items: "读取学习队列", learning_state: "读取学习记录", learning_review: "保存复习记录",
  machine_answer: "获取 AI 回答", machine_retest: "复测 AI 回答", machine_tasks_list: "读取 AI 任务",
  job_execute: "处理文件", job_execution_status: "查询文件处理进度", job_execution_cancel: "取消文件处理",
  model_configuration_get: "读取模型连接", model_configuration_put: "保存模型连接",
  workspace_backups: "读取备份列表", ui_state_read: "读取工作进度", ui_state_write: "保存工作进度",
  local_request: "连接本地服务", local_write: "保存本地内容",
};

/**
 * Automatic failures are bounded, session-local metadata. Never collect request
 * bodies, arbitrary exception messages, paths, credentials or stacks. Recording
 * does not open a dialog, move focus, retry a request or change its exception.
 */
export function recordDiagnosticFailure(operation: string, error: unknown, observed: number | null): void {
  try {
    if (observed === null || observed !== observationEpoch || state.suspended) return;
    const safeOperation = /^[a-z_]{1,80}$/.test(operation) ? operation : "unknown_operation";
    const value = error && typeof error === "object" ? error as {status?: unknown; code?: unknown} : null;
    const status = typeof value?.status === "number" && Number.isInteger(value.status) && value.status >= 0 && value.status <= 599 ? value.status : null;
    const code = typeof value?.code === "string" && ["offline", "backend_starting", "migrating", "incompatible", "unauthorized", "unavailable"].includes(value.code) ? value.code : "unknown";
    const summary = coreFailureReason(error) ?? "这次操作的结果尚未确认，请查看当前页面的处理状态后再决定是否重试。";
    const label = operationLabels[safeOperation] ?? "功能操作";
    const now = new Date();
    const payload = {operation: safeOperation, status, code, summary};
    const previous = state.entries.find(entry => entry.automatic && entry.label === label && JSON.stringify(entry.payload) === JSON.stringify(payload) && now.getTime() - Date.parse(entry.at) < 30_000);
    const entry: DiagnosticEntry = {label, payload, summary, automatic: true, occurrences: (previous?.occurrences ?? 0) + 1, category: "operation", at: now.toISOString(), sequence: previous?.sequence ?? ++sequence};
    update({entries: [entry, ...state.entries.filter(item => item !== previous)].slice(0, LIMIT)});
  } catch { /* Logging must never replace the original business result or error. */ }
}

/**
 * Raw backend payloads belong in a diagnostic channel, not in the reading surface.
 * Session-local observations only: never persist or mirror full receipts to console.
 * Publications are explicit user clicks, not asynchronous completion handlers.
 */
export function publishDiagnostic(label: string, payload: unknown, category: DiagnosticCategory = "operation", trigger?: HTMLElement): void {
  if (state.suspended) return;
  const entry: DiagnosticEntry = {label, payload, category, at: new Date().toISOString(), sequence: ++sequence};
  opener = trigger ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
  update({entries: [entry, ...state.entries].slice(0, LIMIT), open: true, filter: category, selected: entry.sequence});
}
export function openDiagnostics(trigger: HTMLElement): void {
  if (state.suspended) return;
  opener = trigger;
  update({open: true});
}
export function closeDiagnostics(): void {update({open: false});}
export function restoreDiagnosticFocus(): void {
  const usable = (element: HTMLElement | null): element is HTMLElement => {
    if (!element?.isConnected || element.closest('[hidden],[inert],[aria-hidden="true"]') || element.matches(':disabled')) return false;
    for (let node: HTMLElement | null = element; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden") return false;
    }
    return true;
  };
  const target = usable(opener) ? opener : document.querySelector<HTMLElement>('[data-diagnostic-trigger="true"]');
  if (!state.suspended && usable(target)) target.focus();
  opener = null;
}
export function setDiagnosticFilter(filter: DiagnosticState["filter"]): void {update({filter});}
export function clearDiagnostics(): void {update({entries: [], selected: null, filter: "all"});}
export function resetDiagnostics(): void {observationEpoch++; opener = null; update({entries: [], open: false, filter: "all", selected: null, suspended: false});}
export function suspendDiagnostics(): void {if (!state.suspended) observationEpoch++; update({open: false, suspended: true});}
export function resumeDiagnostics(): void {update({suspended: false});}
export function useDiagnosticState(): DiagnosticState {return useSyncExternalStore(subscribe, snapshot, snapshot);}
export function useDiagnostics(): DiagnosticEntry[] {return useDiagnosticState().entries;}
