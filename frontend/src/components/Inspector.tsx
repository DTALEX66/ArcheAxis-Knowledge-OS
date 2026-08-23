export interface InspectionTarget {
  title: string;
  source: string;
  lifecycle: string;
  rawSha256?: string;
  detail?: string;
  version?: string;
  evidenceSource?: string;
  updatedAt?: string;
  conflict?: boolean;
  rights?: string[];
  scopes?: string[];
  review?: {
    decision: string;
    reviewer_id: string;
    reviewed_at: string;
    rationale: string;
  } | null;
  versionHistory?: Array<{
    versionId: string;
    lifecycle: string;
    conflictStatus?: string;
  }>;
}

// Right inspector: source/evidence/conflict/version (task pack §15.3).
export function Inspector({ target }: { target: InspectionTarget | null }) {
  if (target) {
    return (
      <aside className="inspector" aria-label="检查器">
        <h2 className="inspector-title">检查器</h2>
        <dl className="inspector-details">
          <dt>条目</dt><dd>{target.title}</dd>
          <dt>来源</dt><dd>{target.source}</dd>
          <dt>状态</dt><dd>{target.lifecycle}</dd>
          {target.rawSha256 ? <><dt>原件哈希</dt><dd>{target.rawSha256}</dd></> : null}
          {target.version ? <><dt>版本</dt><dd>{target.version}</dd></> : null}
          {target.evidenceSource ? <><dt>证据来源</dt><dd>{target.evidenceSource}</dd></> : null}
          {target.updatedAt ? <><dt>更新时间</dt><dd>{target.updatedAt}</dd></> : null}
          {target.conflict !== undefined ? <><dt>证据冲突</dt><dd>{target.conflict ? "存在支持/反驳冲突" : "未发现支持/反驳冲突"}</dd></> : null}
          {target.rights?.length ? <><dt>权利标记</dt><dd>{target.rights.join("、")}</dd></> : null}
          {target.scopes?.length ? <><dt>适用范围</dt><dd>{target.scopes.join("、")}</dd></> : null}
          {target.review ? <><dt>人工复核</dt><dd>{target.review.decision} · {target.review.reviewer_id} · {target.review.reviewed_at}<br />{target.review.rationale}</dd></> : null}
          {target.versionHistory?.length ? <><dt>关联版本</dt><dd>{target.versionHistory.map((version) => (
            <div key={version.versionId}>{version.versionId} · {version.lifecycle}{version.conflictStatus ? ` · 冲突 ${version.conflictStatus}` : ""}</div>
          ))}</dd></> : null}
          {target.detail ? <><dt>说明</dt><dd>{target.detail}</dd></> : null}
        </dl>
      </aside>
    );
  }
  return (
    <aside className="inspector" aria-label="检查器">
      <div className="inspector-empty">选择条目以查看来源、证据与版本</div>
    </aside>
  );
}
