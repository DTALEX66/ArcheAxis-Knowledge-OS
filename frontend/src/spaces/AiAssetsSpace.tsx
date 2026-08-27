import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import {
  approveMachineKnowledge,
  deprecateMachineKnowledge,
  getMachineKnowledge,
  listMachineKnowledgeCandidates,
  type MachineKnowledgeCandidateDto,
  type MachineKnowledgeDto,
} from "../api/workspace";
import type { InspectionTarget } from "../components/Inspector";
import { stateLabel } from "../presentation/labels";

export function AiAssetsSpace({ onInspect }: { onInspect: (target: InspectionTarget) => void }) {
  const [items, setItems] = useState<MachineKnowledgeDto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [candidates, setCandidates] = useState<MachineKnowledgeCandidateDto[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    const [approved, governed] = await Promise.all([
      getMachineKnowledge(), listMachineKnowledgeCandidates(),
    ]);
    setItems(approved.items);
    setCandidates(governed.items.filter((item) => item.lifecycle === "candidate"));
  }

  useEffect(() => {
    let alive = true;
    Promise.all([getMachineKnowledge(), listMachineKnowledgeCandidates()])
      .then(([approved, governed]) => { if (alive) {
        setItems(approved.items);
        setCandidates(governed.items.filter((item) => item.lifecycle === "candidate"));
      } })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  return (
    <Section title="机器知识">
      <p className="muted">只显示经过人工治理、允许供机器使用的内容。</p>
      {loading ? (
        <Loading label="机器知识" />
      ) : error ? (
        <DataError label="机器知识" message={error} />
      ) : items.length === 0 ? (
        <p className="muted">暂无已批准的机器知识。</p>
      ) : (
        <table className="data-table">
          <thead><tr><th>标题</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.title}>
                <td>{item.title}</td><td>{stateLabel(item.lifecycle)}</td>
                <td><button type="button" onClick={() => onInspect({
                  title: item.title,
                  source: "机器知识",
                  lifecycle: stateLabel(item.lifecycle),
                  detail: item.content.slice(0, 280),
                })}>查看</button>{" "}<button type="button" aria-label={`弃用 ${item.title}`} onClick={async () => {
                  try { await deprecateMachineKnowledge(item.title); setMessage("机器知识已弃用"); await refresh(); }
                  catch (e) { setMessage(`弃用失败：${e instanceof Error ? e.message : String(e)}`); }
                }}>弃用</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <h4>待治理候选</h4>
      {candidates.length === 0 ? <p className="muted">暂无候选</p> : (
        <ul className="action-list">{candidates.map((item) => (
          <li key={item.title}><span>{item.title} · v{item.version} · 证据已记录</span>{" "}<button type="button" aria-label={`批准 ${item.title}`} onClick={async () => {
            try { await approveMachineKnowledge(item.title); setMessage("机器知识已批准"); await refresh(); }
            catch (e) { setMessage(`批准失败：${e instanceof Error ? e.message : String(e)}`); }
          }}>批准</button></li>
        ))}</ul>
      )}
      {message ? <p role="status" className="muted">{message}</p> : null}
    </Section>
  );
}
