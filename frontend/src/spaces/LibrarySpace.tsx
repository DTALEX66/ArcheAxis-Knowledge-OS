import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { listLibraryAssets, type LibraryAssetDto } from "../api/runtime";
import type { InspectionTarget } from "../components/Inspector";

export function LibrarySpace({ onInspect }: { onInspect: (target: InspectionTarget) => void }) {
  const [assets, setAssets] = useState<LibraryAssetDto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    listLibraryAssets()
      .then((d) => { if (alive) setAssets(d.items); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  return (
    <Section title="原件库（Source Archive）">
      <p className="muted">真实数据源：GET /workspace/api/library（内容寻址原件；不暴露本机路径）</p>
      {loading ? (
        <Loading label="原件库" />
      ) : error ? (
        <DataError label="Library" message={error} />
      ) : assets.length === 0 ? (
        <p className="muted">暂无保留原件。通过本地导入添加资料后会出现在这里。</p>
      ) : (
        <table className="data-table">
          <thead><tr><th>原件</th><th>大小</th><th>转换</th><th>操作</th></tr></thead>
          <tbody>
            {assets.map((asset) => (
              <tr key={asset.raw_sha256}>
                <td>{asset.source_name}</td>
                <td>{asset.size_bytes} B</td>
                <td>{asset.conversion_state}</td>
                <td><button type="button" onClick={() => onInspect({
                  title: asset.source_name,
                  source: "Source Archive",
                  lifecycle: asset.conversion_state,
                  rawSha256: asset.raw_sha256,
                  detail: `保留策略：${asset.retention}`,
                })}>查看</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Section>
  );
}
