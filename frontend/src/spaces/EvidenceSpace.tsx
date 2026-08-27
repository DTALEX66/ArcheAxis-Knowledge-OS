import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import {
  approveResearchCandidate,
  getEvidenceBundleInspection,
  listEvidenceAnchors,
  listEvidenceBundles,
  listResearchCandidates,
  type EvidenceAnchorDto,
  type EvidenceBundleSummaryDto,
  type ResearchCandidateDto,
} from "../api/workspace";
import type { InspectionTarget } from "../components/Inspector";
import { stateLabel, userErrorMessage } from "../presentation/labels";

export function EvidenceSpace({ onInspect }: { onInspect: (target: InspectionTarget) => void }) {
  const [rows, setRows] = useState<EvidenceAnchorDto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [anchorCursor, setAnchorCursor] = useState<string | null>(null);
  const [anchorHistory, setAnchorHistory] = useState<Array<string | null>>([]);
  const [nextAnchorCursor, setNextAnchorCursor] = useState<string | null>(null);
  const [anchorPageLoading, setAnchorPageLoading] = useState(false);
  const [bundles, setBundles] = useState<EvidenceBundleSummaryDto[]>([]);
  const [candidates, setCandidates] = useState<ResearchCandidateDto[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  async function refreshCandidates() {
    const data = await listResearchCandidates();
    setCandidates(data.items);
  }

  async function loadAnchorPage(
    cursor: string | null,
    history: Array<string | null>,
  ) {
    setAnchorPageLoading(true);
    try {
      const data = await listEvidenceAnchors(50, cursor ?? undefined);
      setRows(data.items);
      setAnchorCursor(cursor);
      setAnchorHistory(history);
      setNextAnchorCursor(data.next_cursor);
      setError(null);
    } catch (e) {
      setMessage(userErrorMessage(e instanceof Error ? e.message : e));
    } finally {
      setAnchorPageLoading(false);
    }
  }

  useEffect(() => {
    let alive = true;
    listEvidenceAnchors(50)
      .then((d) => {
        if (!alive) return;
        setRows(d.items);
        setNextAnchorCursor(d.next_cursor);
      })
      .catch((e: Error) => { if (alive) setError(userErrorMessage(e.message)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    refreshCandidates().catch((e: Error) => setMessage(userErrorMessage(e.message)));
  }, []);

  useEffect(() => {
    let alive = true;
    listEvidenceBundles(50)
      .then((data) => { if (alive) setBundles(data.items); })
      .catch((e: Error) => { if (alive) setMessage(userErrorMessage(e.message)); });
    return () => { alive = false; };
  }, []);

  async function inspectBundle(bundleId: string) {
    try {
      const bundle = await getEvidenceBundleInspection(bundleId);
      onInspect({
        title: "受治理证据束",
        source: "关联主张",
        lifecycle: stateLabel(bundle.latest_review?.decision ?? "unreviewed"),
        detail: `证据束指纹：${bundle.fingerprint}；条目数：${bundle.entries.length}`,
        conflict: bundle.conflict,
        rights: bundle.rights,
        scopes: bundle.scopes,
        review: bundle.latest_review,
        versionHistory: bundle.version_history.map((version) => ({
          versionId: version.version_id,
          lifecycle: version.lifecycle_status,
          conflictStatus: version.conflict?.status,
        })),
      });
    } catch (e) {
      setMessage(userErrorMessage(e instanceof Error ? e.message : e));
    }
  }

  return (
    <Section title="证据账本">
      <p className="muted">证据锚点与受治理证据束的只读投影。</p>
      {loading ? (
        <Loading label="证据账本" />
      ) : error ? (
        <DataError label="证据账本" message={error} />
      ) : (
        rows.length === 0 ? <p className="muted">暂无证据锚点记录</p> : (
          <table className="data-table">
            <thead><tr><th>证据锚点</th><th>原件指纹</th><th>锚点状态</th><th>操作</th></tr></thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.anchor_id}>
                  <td>锚点 {index + 1}</td>
                  <td>{row.raw_sha256.slice(0, 12)}</td>
                  <td>已锚定</td>
                  <td><button type="button" onClick={() => onInspect({
                    title: "证据锚点",
                    source: "已保留原件版本",
                    lifecycle: stateLabel("anchored"),
                    rawSha256: row.raw_sha256,
                    detail: `定位信息：${JSON.stringify(row.locator)}`,
                  })}>查看</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
      {!loading && !error ? (
        <p className="muted">
          <button
            type="button"
            disabled={anchorPageLoading || anchorHistory.length === 0}
            onClick={() => {
              const previousCursor = anchorHistory[anchorHistory.length - 1] ?? null;
              void loadAnchorPage(previousCursor, anchorHistory.slice(0, -1));
            }}
          >上一页</button>{" "}
          <button
            type="button"
            disabled={anchorPageLoading || !nextAnchorCursor}
            onClick={() => {
              if (!nextAnchorCursor) return;
              void loadAnchorPage(nextAnchorCursor, [...anchorHistory, anchorCursor]);
            }}
          >下一页</button>
        </p>
      ) : null}
      <h4>受治理证据束</h4>
      {bundles.length === 0 ? <p className="muted">暂无可查看的证据束</p> : (
        <ul className="action-list">{bundles.map((bundle, index) => (
          <li key={bundle.bundle_id}>
            <span>证据束 {index + 1} · {stateLabel(bundle.review_decision ?? "unreviewed")}</span>{" "}
            <button type="button" onClick={() => { void inspectBundle(bundle.bundle_id); }}>查看证据束</button>
          </li>
        ))}</ul>
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
              setMessage(userErrorMessage(e instanceof Error ? e.message : e));
            }
          }}>批准入账</button></li>
        ))}</ul>
      )}
      {message ? <p role="status" className="muted">{message}</p> : null}
    </Section>
  );
}
