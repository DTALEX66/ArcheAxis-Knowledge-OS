import { useEffect, useState } from "react";
import { coreCommand } from "../api/core";
import { coreFailureReason } from "../presentation/labels";

export function VersionSourcePanel() {
  const [version, setVersion] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let alive = true;
    setError(null);
    coreCommand<Record<string, unknown>>("system_version").then(value => {
      if (value.runtime !== "archeaxis-api" || typeof value.contract !== "string"
        || !Number.isInteger(value.schema_version) || typeof value.sqlite_version !== "string") throw new Error("version identity invalid");
      if (alive) setVersion(value);
    }).catch(reason => { if (alive) { setVersion(null); setError(coreFailureReason(reason) ?? "版本读取失败"); } });
    return () => { alive = false; };
  }, [retry]);
  return <section className="ui-reliability-panel" aria-label="版本与来源" data-section="runtime" tabIndex={-1}>
    <h2>当前运行身份</h2>
    {error ? <p role="alert">{error}</p> : version ? <dl>
      <dt>Core</dt><dd>{String(version.runtime)}</dd>
      <dt>接口合同</dt><dd>{String(version.contract)}</dd>
      <dt>数据结构</dt><dd>{String(version.schema_version)}</dd>
      <dt>SQLite</dt><dd>{String(version.sqlite_version)}</dd>
    </dl> : <p role="status">正在读取当前 Core…</p>}
    <button type="button" onClick={() => setRetry(value => value + 1)}>重新读取运行身份</button>
    <p>安装包来源与构建 SHA：UNKNOWN。当前运行接口没有提供可验证的安装与构建回执。</p>
    <p>下方原件、来源引用与文档版本来自当前工作区。历史版本是只读记录；恢复文档版本会创建新版本。</p>
  </section>;
}
