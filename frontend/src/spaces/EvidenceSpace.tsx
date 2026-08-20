import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { listEvidenceAnchors, type EvidenceAnchorDto } from "../api/runtime";
import type { InspectionTarget } from "../components/Inspector";

export function EvidenceSpace({ onInspect }: { onInspect: (target: InspectionTarget) => void }) {
  const [rows, setRows] = useState<EvidenceAnchorDto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    listEvidenceAnchors(50)
      .then((d) => { if (alive) setRows(d.items); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  return (
    <Section title="证据账本（Evidence & Knowledge Ledger）">
      <p className="muted">真实数据源：GET /api/evidence/anchors（证据锚定记录）</p>
      {loading ? (
        <Loading label="证据账本" />
      ) : error ? (
        <DataError label="Evidence" message={error} />
      ) : (
        rows.length === 0 ? <p className="muted">暂无证据锚点记录</p> : (
          <table className="data-table">
            <thead><tr><th>锚点 ID</th><th>原件哈希</th><th>来源修订</th><th>操作</th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.anchor_id}>
                  <td>{row.anchor_id.slice(0, 18)}</td>
                  <td>{row.raw_sha256.slice(0, 12)}</td>
                  <td>{row.source_revision.slice(0, 10)}</td>
                  <td><button type="button" onClick={() => onInspect({
                    title: `证据锚点 ${row.anchor_id.slice(0, 12)}`,
                    source: row.source_revision,
                    lifecycle: "anchored",
                    rawSha256: row.raw_sha256,
                    detail: `定位信息：${JSON.stringify(row.locator)}`,
                  })}>查看</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </Section>
  );
}
