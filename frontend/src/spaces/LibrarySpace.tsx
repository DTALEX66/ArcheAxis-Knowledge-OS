import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { downloadLibraryAsset, listLibraryAssets, type LibraryAssetDto } from "../api/workspace";
import type { InspectionTarget } from "../components/Inspector";
import { stateLabel } from "../presentation/labels";

export function LibrarySpace({ onInspect }: { onInspect: (target: InspectionTarget) => void }) {
  const [assets, setAssets] = useState<LibraryAssetDto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    listLibraryAssets()
      .then((d) => { if (alive) setAssets(d.items); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  return (
    <Section title="原件库">
      <p className="muted">内容寻址的保留原件；界面不暴露本机路径。</p>
      {loading ? (
        <Loading label="原件库" />
      ) : error ? (
        <DataError label="原件库" message={error} />
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
                <td>{stateLabel(asset.conversion_state)}</td>
                <td><button type="button" onClick={() => onInspect({
                  title: asset.source_name,
                  source: "原件档案",
                  lifecycle: stateLabel(asset.conversion_state),
                  rawSha256: asset.raw_sha256,
                  detail: `保留策略：${asset.retention}`,
                })}>查看</button>{" "}<button type="button" onClick={async () => {
                  setMessage("正在读取原件…");
                  try {
                    const blob = await downloadLibraryAsset(asset.raw_sha256);
                    setMessage(`已按内容标识读回 ${blob.size} B：${asset.source_name}`);
                  } catch (e) {
                    setMessage(`原件读取失败：${e instanceof Error ? e.message : String(e)}`);
                  }
                }}>打开原件</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {message ? <p role="status" className="muted">{message}</p> : null}
    </Section>
  );
}
