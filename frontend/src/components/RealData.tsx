// Minimal real-data view primitives (no mock mixing).
import type { ReactNode } from "react";
import { userErrorMessage } from "../presentation/labels";

export function Loading({ label }: { label: string }) {
  return <div className="space-card">加载中：{label}…</div>;
}

export function DataError({ label, message }: { label: string; message: string }) {
  return (
    <div className="space-card space-card-error">
      <strong>{label} 加载失败</strong>
      <div className="muted">{userErrorMessage(message)}</div>
    </div>
  );
}

export function DataTable<T>({
  columns,
  rows,
  empty,
}: {
  columns: { key: string; label: string }[];
  rows: T[];
  empty: string;
}) {
  if (rows.length === 0) {
    return <div className="space-card muted">{empty}</div>;
  }
  return (
    <table className="data-table">
      <thead>
        <tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            {columns.map((c) => (
              <td key={c.key}>{String((row as Record<string, unknown>)[c.key] ?? "—")}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-card">
      <h3>{title}</h3>
      {children}
    </section>
  );
}
