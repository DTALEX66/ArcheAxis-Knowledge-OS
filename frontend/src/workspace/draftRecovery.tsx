import { createContext, useContext, useLayoutEffect, useRef, useState, type ReactNode } from "react";

export type RecoveryDraft = { label: string; text: string };
type Source = () => RecoveryDraft[];

/** Explicit content sources only: no DOM, settings, diagnostics or persistence. */
export class DraftRecoveryRegistry {
  private sources = new Map<string, { label: string; read: Source }>();
  register(owner: string, label: string, read: Source) {
    const source = { label, read }; this.sources.set(owner, source);
    return () => { if (this.sources.get(owner) === source) this.sources.delete(owner); };
  }
  read(): RecoveryDraft[] {
    return [...this.sources.values()].flatMap(source => {
      try { return source.read(); }
      catch { return [{ label: source.label, text: "此页原稿读取失败；原页面仍保留，请重试查看。" }]; }
    });
  }
}

const Context = createContext<DraftRecoveryRegistry | null>(null);
export function DraftRecoveryScope({ children }: { children: ReactNode }) {
  const [registry] = useState(() => new DraftRecoveryRegistry());
  return <Context.Provider value={registry}>{children}</Context.Provider>;
}
export function useDraftRecoveryRegistry() { return useContext(Context); }
export function useDraftRecoverySource(owner: string, label: string, read: Source) {
  const registry = useDraftRecoveryRegistry(), latest = useRef(read); latest.current = read;
  useLayoutEffect(() => registry?.register(owner, label, () => latest.current()), [registry, owner, label]);
}
