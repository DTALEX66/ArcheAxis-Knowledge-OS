import { useState } from "react";
import { DataError, Section } from "../components/RealData";
import { exportExchange, verifyExchange, type ExchangeExportDto } from "../api/workspace";
import { userErrorMessage } from "../presentation/labels";

export function ExchangeSpace() {
  const [exportName, setExportName] = useState("exchange");
  const [verifyName, setVerifyName] = useState("exchange");
  const [exported, setExported] = useState<ExchangeExportDto | null>(null);
  const [verified, setVerified] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState<"export" | "verify" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function runExport() {
    const name = exportName.trim() || "exchange";
    setBusy("export");
    setError(null);
    setMessage(null);
    try {
      const result = await exportExchange(name, false);
      setExported(result);
      setMessage(`已导出 ${result.item_count} 项知识交换包`);
    } catch (e) {
      setMessage(null);
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    } finally {
      setBusy(null);
    }
  }

  async function runVerify() {
    const name = verifyName.trim() || "exchange";
    setBusy("verify");
    setError(null);
    setMessage(null);
    try {
      const result = await verifyExchange(name);
      setVerified(result);
      setMessage("交换包验证通过：清单与全部文件哈希一致。");
    } catch (e) {
      setMessage(null);
      setError(userErrorMessage(e instanceof Error ? e.message : e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Section title="交换">
      <p className="muted">把原件、证据、学习与机器知识导出为开放交换目录（清单+哈希），并可随时验证完整性。</p>

      <h4>导出知识交换包</h4>
      <div className="intake-row">
        <label className="visually-hidden" htmlFor="exchange-name">交换包名称</label>
        <input id="exchange-name" value={exportName} onChange={(event) => setExportName(event.target.value)} placeholder="exchange" aria-label="交换包名称" />
        <button type="button" onClick={() => void runExport()} disabled={busy !== null}>{busy === "export" ? "正在导出…" : "导出"}</button>
      </div>
      {exported ? <dl className="receipt-grid" aria-label="导出回执">
        <div><dt>交换包</dt><dd>{exportName}</dd></div>
        <div><dt>项目数</dt><dd>{exported.item_count}</dd></div>
        <div><dt>清单哈希</dt><dd className="mono">{exported.manifest_sha256.slice(0, 16)}…</dd></div>
        <div><dt>保存位置</dt><dd className="mono">{exported.destination}</dd></div>
      </dl> : null}

      <h4>验证交换包</h4>
      <div className="intake-row">
        <label className="visually-hidden" htmlFor="exchange-verify-name">验证交换包名称</label>
        <input id="exchange-verify-name" value={verifyName} onChange={(event) => setVerifyName(event.target.value)} placeholder="exchange" aria-label="验证交换包名称" />
        <button type="button" onClick={() => void runVerify()} disabled={busy !== null}>{busy === "verify" ? "正在验证…" : "验证"}</button>
      </div>
      {verified ? <p role="status" className="muted">验证结果：{verified.valid === true ? "通过" : "未通过"}{typeof verified.verified_items === "number" ? ` · ${verified.verified_items} 项` : ""}</p> : null}

      {error ? <DataError label="交换" message={error} /> : null}
      {message ? <p role="status" className="muted">{message}</p> : null}
    </Section>
  );
}
