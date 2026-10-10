import { useDiagnostics, clearDiagnostics, publishDiagnostic } from "../presentation/diagnostics";

/** Replaces an inline JSON dump: the operator still reaches the untouched payload, the reading surface does not carry it. */
export function RawReceiptButton({ label, payload }: { label: string; payload: unknown }) {
  return (
    <button type="button" className="raw-receipt" aria-label={`查看原始回执（诊断）：${label}`} onClick={() => publishDiagnostic(label, payload)}>
      查看原始回执（诊断）
    </button>
  );
}

/**
 * The one place raw backend payloads may appear. Reading surfaces keep human-readable
 * summaries and publish the untouched receipt here instead of printing it inline.
 */
export function DiagnosticConsole() {
  const entries = useDiagnostics();
  return (
    <section className="diagnostic-console" aria-label="诊断控制台">
      <header className="diagnostic-console-header">
        <h4>诊断控制台</h4>
        <span className="diagnostic-console-count">{entries.length} 条原始回执；主界面只显示人可读摘要</span>
        <button type="button" disabled={entries.length === 0} onClick={clearDiagnostics}>清空诊断</button>
      </header>
      {entries.length === 0
        ? <p className="diagnostic-console-empty">暂无原始回执。界面上的“查看原始回执”会把未改写的载荷记录到这里，同时输出到开发者控制台。</p>
        : (
          <ul className="diagnostic-console-list">
            {entries.map((entry) => (
              <li key={entry.sequence}>
                <details>
                  <summary>{entry.label} · {entry.at}</summary>
                  <pre>{JSON.stringify(entry.payload, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ul>
        )}
    </section>
  );
}
