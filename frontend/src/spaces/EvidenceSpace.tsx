import { useEffect, useState } from "react";
import { DataError, DataTable, Loading, Section } from "../components/RealData";
import { listEvidenceAnchors, type EvidenceAnchorDto } from "../api/runtime";

export function EvidenceSpace() {
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
        <DataTable
          columns={[
            { key: "anchor_id", label: "锚点 ID" },
            { key: "raw_sha256", label: "原件哈希（前 12）" },
            { key: "source_revision", label: "来源修订" },
          ]}
          rows={rows.map((r) => ({
            anchor_id: r.anchor_id.slice(0, 18),
            raw_sha256: r.raw_sha256.slice(0, 12),
            source_revision: r.source_revision.slice(0, 10),
          }))}
          empty="暂无证据锚点记录"
        />
      )}
    </Section>
  );
}
