import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { getHome, type ActivityItemDto } from "../api/runtime";

interface HomeDto {
  release?: Record<string, unknown>;
  counts?: Record<string, unknown>;
  capabilities?: Record<string, unknown>;
  components?: Record<string, unknown>;
  recent_activity?: ActivityItemDto[];
}

export function WorkspaceSpace() {
  const [status, setStatus] = useState<HomeDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getHome()
      .then((s) => { if (alive) setStatus(s as HomeDto); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  return (
    <Section title="工作区状态（Workspace）">
      <p className="muted">真实数据源：GET /api/v1/home（发布、组件、能力、计数与近期活动）</p>
      {loading ? (
        <Loading label="工作区状态" />
      ) : error ? (
        <DataError label="Workspace" message={error} />
      ) : (
        <>
          <div className="summary-grid">
            <article><h4>发布</h4>{Object.entries(status?.release ?? {}).map(([key, value]) => <p key={key}><strong>{key}</strong> {String(value)}</p>)}</article>
            <article><h4>计数</h4>{Object.entries(status?.counts ?? {}).map(([key, value]) => <p key={key}><strong>{key}</strong> {String(value)}</p>)}</article>
            <article><h4>组件</h4>{Object.entries(status?.components ?? {}).map(([key, value]) => <p key={key}><strong>{key}</strong> {String(value)}</p>)}</article>
          </div>
          <h4>可用能力</h4>
          <ul className="tag-list">{Object.entries(status?.capabilities ?? {}).map(([capability, state]) => <li key={capability}>{capability} · {String(state)}</li>)}</ul>
          <h4>近期活动</h4>
          {(status?.recent_activity ?? []).length === 0 ? <p className="muted">暂无活动</p> : <ul className="action-list">{status?.recent_activity?.map((item) => <li key={item.public_ref}>{item.label} · {item.state}</li>)}</ul>}
        </>
      )}
    </Section>
  );
}
