import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { getMachineKnowledge } from "../api/runtime";

export function AiAssetsSpace() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getMachineKnowledge()
      .then((d) => { if (alive) setData(d); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const entries = data ? Object.entries(data).slice(0, 20) : [];
  return (
    <Section title="AI 资产（AI Asset Vault）">
      <p className="muted">真实数据源：GET /api/runtime/knowledge（机器知识单元）</p>
      {loading ? (
        <Loading label="AI 资产" />
      ) : error ? (
        <DataError label="AI Assets" message={error} />
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
