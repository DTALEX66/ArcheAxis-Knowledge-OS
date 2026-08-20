export interface InspectionTarget {
  title: string;
  source: string;
  lifecycle: string;
  rawSha256?: string;
  detail?: string;
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
