import { useSyncExternalStore } from "react";

export interface DiagnosticEntry {
  label: string;
  payload: unknown;
  at: string;
  sequence: number;
  category: DiagnosticCategory;
}
export const diagnosticCategories = {runtime: "运行与连接", operation: "操作与回执", data: "对象与来源"} as const;
export type DiagnosticCategory = keyof typeof diagnosticCategories;
type DiagnosticState = {entries: DiagnosticEntry[]; open: boolean; filter: DiagnosticCategory | "all"; selected: number | null; suspended: boolean};
const LIMIT = 50;
let state: DiagnosticState = {entries: [], open: false, filter: "all", selected: null, suspended: false};
const listeners = new Set<() => void>();
let sequence = 0;
let opener: HTMLElement | null = null;
function update(patch: Partial<DiagnosticState>) {
  state = {...state, ...patch};
  for (const listener of listeners) listener();
}
const subscribe = (listener: () => void) => {listeners.add(listener); return () => {listeners.delete(listener);};};
const snapshot = () => state;

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
export function resetDiagnostics(): void {opener = null; update({entries: [], open: false, filter: "all", selected: null, suspended: false});}
export function suspendDiagnostics(): void {update({open: false, suspended: true});}
export function resumeDiagnostics(): void {update({suspended: false});}
export function useDiagnosticState(): DiagnosticState {return useSyncExternalStore(subscribe, snapshot, snapshot);}
export function useDiagnostics(): DiagnosticEntry[] {return useDiagnosticState().entries;}
