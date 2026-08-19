import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { getSetupStatus } from "../api/runtime";

export function SettingsSpace() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getSetupStatus()
      .then((d) => { if (alive) setData(d); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const entries = data ? Object.entries(data).slice(0, 16) : [];
  return (
    <Section title="设置与四库管理（Settings）">
      <p className="muted">真实数据源：GET /api/v1/setup/status（首次启动向导状态）</p>
      {loading ? (
        <Loading label="设置" />
      ) : error ? (
        <DataError label="Settings" message={error} />
      ) : (
        <table className="data-table">
          <tbody>
            {entries.map(([k, v]) => (
              <tr key={k}><th>{k}</th><td>{String(v ?? "—")}</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </Section>
  );
}
