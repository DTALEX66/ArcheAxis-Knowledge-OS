import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { getHome } from "../api/runtime";

export function LibrarySpace() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getHome()
      .then((d) => { if (alive) setData(d); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const entries = data ? Object.entries(data).slice(0, 20) : [];
  return (
    <Section title="原件库（Source Archive）">
      <p className="muted">真实数据源：GET /api/v1/home（v1 只读投影）</p>
      {loading ? (
        <Loading label="原件库" />
      ) : error ? (
        <DataError label="Library" message={error} />
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
