import { useEffect, useRef, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import {
  downloadLibraryAsset,
  downloadPdfAsset,
  getConvertedContent,
  listEvidenceAnchors,
  listLibraryAssets,
  type ConvertedContentDto,
  type EvidenceAnchorDto,
  type LibraryAssetDto,
} from "../api/workspace";
import type { InspectionTarget } from "../components/Inspector";
import { stateLabel, userErrorMessage } from "../presentation/labels";
import { formatLabel } from "./IntakeSpace";

export function LibrarySpace({ onInspect }: { onInspect: (target: InspectionTarget) => void }) {
  const [assets, setAssets] = useState<LibraryAssetDto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [opened, setOpened] = useState<LibraryAssetDto | null>(null);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [textPreview, setTextPreview] = useState<string | null>(null);
  const [converted, setConverted] = useState<ConvertedContentDto | null>(null);
  const [anchors, setAnchors] = useState<EvidenceAnchorDto[]>([]);
  const reader = useRef({ generation: 0, objectUrl: null as string | null, mounted: true });

  useEffect(() => {
    let alive = true;
    listLibraryAssets()
      .then((d) => { if (alive) setAssets(d.items); })
      .catch((e: Error) => { if (alive) setError(userErrorMessage(e.message)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    reader.current.mounted = true;
    return () => {
      reader.current.mounted = false;
      reader.current.generation += 1;
      if (reader.current.objectUrl) URL.revokeObjectURL(reader.current.objectUrl);
      reader.current.objectUrl = null;
    };
  }, []);

  function closeReader() {
    reader.current.generation += 1;
    if (reader.current.objectUrl) URL.revokeObjectURL(reader.current.objectUrl);
    reader.current.objectUrl = null;
    setObjectUrl(null);
    setOpened(null);
    setAnchors([]);
    setTextPreview(null);
    setConverted(null);
  }

  async function openAsset(asset: LibraryAssetDto) {
    const generation = ++reader.current.generation;
    const isCurrent = () => reader.current.mounted && reader.current.generation === generation;
    setMessage("正在读取原件…");
    setAnchors([]);
    setTextPreview(null);
    setConverted(null);
    try {
      const pdf = asset.mime_type === "application/pdf" || /\.pdf$/i.test(asset.source_name);
      const blob = pdf
        ? await downloadPdfAsset(asset.raw_sha256)
        : await downloadLibraryAsset(asset.raw_sha256);
      if (!isCurrent()) return;
      const nextUrl = URL.createObjectURL(blob);
      if (!isCurrent()) {
        URL.revokeObjectURL(nextUrl);
        return;
      }
      if (reader.current.objectUrl) URL.revokeObjectURL(reader.current.objectUrl);
      reader.current.objectUrl = nextUrl;
      setObjectUrl(nextUrl);
      setOpened(asset);
      if (pdf) {
        const matching: EvidenceAnchorDto[] = [];
        let cursor: string | undefined;
        const seen = new Set<string>();
        do {
          const page = await listEvidenceAnchors(100, cursor);
          if (!isCurrent()) return;
          matching.push(...page.items.filter((anchor) => anchor.raw_sha256 === asset.raw_sha256));
          cursor = page.next_cursor ?? undefined;
          if (cursor && seen.has(cursor)) break;
          if (cursor) seen.add(cursor);
        } while (cursor);
        if (isCurrent()) setAnchors(matching);
      } else if (blob.type.startsWith("text/") || /\.(md|txt|json|csv)$/i.test(asset.source_name)) {
        const preview = (await blob.text()).slice(0, 20_000);
        if (!isCurrent()) return;
        setTextPreview(preview);
      }
      if (isCurrent()) setMessage(`已打开原件：${asset.source_name}`);
    } catch (e) {
      if (!isCurrent()) return;
      closeReader();
      setMessage(userErrorMessage(e instanceof Error ? e.message : e));
    }
  }

  async function openConverted(asset: LibraryAssetDto) {
    const generation = ++reader.current.generation;
    const isCurrent = () => reader.current.mounted && reader.current.generation === generation;
    setMessage("正在读取转换文本…");
    setAnchors([]);
    setTextPreview(null);
    setConverted(null);
    try {
      const body = await getConvertedContent(asset.raw_sha256);
      if (!isCurrent()) return;
      setOpened(asset);
      setConverted(body);
      setMessage(`已加载转换文本：${body.engine} · ${body.block_count} 块`);
    } catch (e) {
      if (!isCurrent()) return;
      setMessage(userErrorMessage(e instanceof Error ? e.message : e));
    }
  }

  return (
    <Section title="资料库">
      <p className="muted">内容寻址的保留原件与多格式转换结果；界面不暴露本机路径。</p>
      {loading ? (
        <Loading label="资料库" />
      ) : error ? (
        <DataError label="资料库" message={error} />
      ) : assets.length === 0 ? (
        <p className="muted">暂无保留原件。通过「导入」空间的网页、文件或批量导入添加资料后会出现在这里。</p>
      ) : (
        <table className="data-table">
          <thead><tr><th>原件</th><th>格式</th><th>转换</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {assets.map((asset) => (
              <tr key={asset.raw_sha256}>
                <td>{asset.source_name}<small className="table-sub">{asset.size_bytes} B</small></td>
                <td>{formatLabel(asset.format)}</td>
                <td>{asset.engine ?? "—"}{asset.converted_char_count != null ? <small className="table-sub">{asset.converted_char_count} 字符</small> : null}</td>
                <td>
                  {asset.conversion_state === "requires_attention"
                    ? <span title={asset.error_reason ?? undefined}>需关注</span>
                    : "已保留"}
                  {asset.error_reason ? <small className="table-sub error-reason">{asset.error_reason}</small> : null}
                </td>
                <td>
                  <button type="button" onClick={() => onInspect({
                    title: asset.source_name,
                    source: "原件档案",
                    lifecycle: stateLabel(asset.conversion_state),
                    rawSha256: asset.raw_sha256,
                    detail: `保留策略：${asset.retention}${asset.engine ? `；转换引擎：${asset.engine}` : ""}`,
                  })}>查看</button>{" "}
                  {asset.engine ? <button type="button" onClick={() => void openConverted(asset)}>转换文本</button> : null}{" "}
                  <button type="button" onClick={() => void openAsset(asset)}>打开原件</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {opened && (objectUrl || converted) ? <section className="library-reader" aria-label="原件阅读器">
        <header><div><span className="archive-eyebrow">当前原件</span><h4>{opened.source_name}</h4></div><button type="button" onClick={closeReader}>关闭阅读器</button></header>
        <div className="library-reader-grid">
          <div className="library-document">
            {converted ? <div className="converted-document">
              <p className="muted">转换引擎：{converted.engine} · {converted.block_count} 块</p>
              <pre>{converted.content}</pre>
            </div>
              : opened.mime_type === "application/pdf" || /\.pdf$/i.test(opened.source_name)
                ? <iframe title="PDF 原件阅读器" src={objectUrl ?? undefined} sandbox="" />
                : textPreview !== null ? <pre>{textPreview}</pre> : <p>该格式已保留，可通过系统关联应用继续查看。</p>}
          </div>
          <aside aria-label="原件证据锚点">
            <h4>证据锚点</h4>
            {anchors.length === 0 ? <p className="muted">当前原件暂无页级锚点</p> : <ol>{anchors.map((anchor, index) => <li key={anchor.anchor_id}>证据锚点 {index + 1}{typeof anchor.locator.page === "number" ? ` · 第 ${anchor.locator.page} 页` : ""}</li>)}</ol>}
          </aside>
        </div>
      </section> : null}
      {message ? <p role="status" className="muted">{message}</p> : null}
    </Section>
  );
}
