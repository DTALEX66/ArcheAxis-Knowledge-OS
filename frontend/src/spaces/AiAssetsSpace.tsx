import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { getMachineKnowledge, type MachineKnowledgeDto } from "../api/runtime";
import type { InspectionTarget } from "../components/Inspector";

export function AiAssetsSpace({ onInspect }: { onInspect: (target: InspectionTarget) => void }) {
  const [items, setItems] = useState<MachineKnowledgeDto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getMachineKnowledge()
      .then((d) => { if (alive) setItems(d.items); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  return (
    <Section title="AI 资产（AI Asset Vault）">
      <p className="muted">真实数据源：GET /workspace/api/runtime/knowledge（仅人工批准的机器知识）</p>
      {loading ? (
        <Loading label="AI 资产" />
      ) : error ? (
        <DataError label="AI Assets" message={error} />
      ) : items.length === 0 ? (
        <p className="muted">暂无已批准 AI 资产。</p>
      ) : (
        <table className="data-table">
          <thead><tr><th>标题</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.title}>
                <td>{item.title}</td><td>{item.lifecycle}</td>
                <td><button type="button" onClick={() => onInspect({
                  title: item.title,
                  source: "Machine Knowledge",
                  lifecycle: item.lifecycle,
                  detail: item.content.slice(0, 280),
                })}>查看</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Section>
  );
}
