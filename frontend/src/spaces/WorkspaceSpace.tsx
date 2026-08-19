import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { getStatus, type StatusDto } from "../api/runtime";

export function WorkspaceSpace() {
  const [status, setStatus] = useState<StatusDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getStatus()
      .then((s) => { if (alive) setStatus(s); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const rows = status ? Object.entries(status).slice(0, 12) : [];
  return (
    <Section title="工作区状态（Workspace）">
      <p className="muted">真实数据源：GET /api/status</p>
      {loading ? (
        <Loading label="工作区状态" />
      ) : error ? (
        <DataError label="Workspace" message={error} />
      ) : (
        <table className="data-table">
          <tbody>
            {rows.map(([k, v]) => (
              <tr key={k}><th>{k}</th><td>{String(v ?? "—")}</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </Section>
  );
}
