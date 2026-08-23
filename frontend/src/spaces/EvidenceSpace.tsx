import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import {
  approveResearchCandidate,
  listEvidenceAnchors,
  listResearchCandidates,
  type EvidenceAnchorDto,
  type ResearchCandidateDto,
} from "../api/runtime";
import type { InspectionTarget } from "../components/Inspector";

export function EvidenceSpace({ onInspect }: { onInspect: (target: InspectionTarget) => void }) {
  const [rows, setRows] = useState<EvidenceAnchorDto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [candidates, setCandidates] = useState<ResearchCandidateDto[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  async function refreshCandidates() {
    const data = await listResearchCandidates();
    setCandidates(data.items);
  }

  useEffect(() => {
    let alive = true;
    listEvidenceAnchors(50)
      .then((d) => { if (alive) setRows(d.items); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    refreshCandidates().catch((e: Error) => setMessage(`审核队列不可用：${e.message}`));
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
      <h4>待审核研究资料</h4>
      {candidates.length === 0 ? <p className="muted">暂无待审核资料</p> : (
        <ul className="action-list">{candidates.map((candidate) => (
          <li key={candidate.source}><span>{candidate.source}</span>{" "}<button type="button" onClick={async () => {
            try {
              await approveResearchCandidate(candidate.source);
              setMessage("已批准并写入证据治理账本");
              await refreshCandidates();
            } catch (e) {
              setMessage(`批准失败：${e instanceof Error ? e.message : String(e)}`);
            }
          }}>批准入账</button></li>
        ))}</ul>
      )}
      {message ? <p role="status" className="muted">{message}</p> : null}
    </Section>
  );
}
