import { useEffect, useState } from "react";

export interface DiagnosticEntry {
  label: string;
  payload: unknown;
  at: string;
  sequence: number;
}

const LIMIT = 50;
const entries: DiagnosticEntry[] = [];
const listeners = new Set<(value: DiagnosticEntry[]) => void>();
let sequence = 0;

function snapshot(): DiagnosticEntry[] {
  return [...entries];
}

/**
 * Raw backend payloads belong in a diagnostic channel, not in the reading surface.
 * A component that wants the operator to still reach the exact receipt publishes it here:
 * it is always mirrored to the developer console, and it stays reachable in the activity
 * dock's diagnostic list instead of being printed as an undifferentiated JSON block
 * next to the document.
 */
export function publishDiagnostic(label: string, payload: unknown): void {
  sequence += 1;
  const entry: DiagnosticEntry = { label, payload, at: new Date().toISOString(), sequence };
  entries.unshift(entry);
  if (entries.length > LIMIT) entries.length = LIMIT;
  // eslint-disable-next-line no-console
  console.debug("[archeaxis-diagnostic]", label, payload);
  for (const listener of listeners) listener(snapshot());
}

export function clearDiagnostics(): void {
  entries.length = 0;
  for (const listener of listeners) listener(snapshot());
}

export function useDiagnostics(): DiagnosticEntry[] {
  const [value, setValue] = useState<DiagnosticEntry[]>(snapshot);
  useEffect(() => {
    listeners.add(setValue);
    setValue(snapshot());
    return () => { listeners.delete(setValue); };
  }, []);
  return value;
}
