import { useState } from "react";
import { DataError, Section } from "../components/RealData";
import { exportExchange, importExchange, verifyExchange, type ExchangeExportDto, type ExchangeImportDto } from "../api/workspace";
import { failureMessage } from "../presentation/labels";

export function ExchangeSpace() {
  const [exportName, setExportName] = useState("exchange");
  const [verifyName, setVerifyName] = useState("exchange");
  const [importName, setImportName] = useState("exchange");
  const [workspaceName, setWorkspaceName] = useState("");
  const [exported, setExported] = useState<ExchangeExportDto | null>(null);
  const [verified, setVerified] = useState<Record<string, unknown> | null>(null);
  const [imported, setImported] = useState<ExchangeImportDto | null>(null);
  const [busy, setBusy] = useState<"export" | "verify" | "import" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function runExport() {
    const name = exportName.trim() || "exchange";
    setBusy("export");
    setError(null);
    setMessage("正在导出交换包…");
    try {
      const result = await exportExchange(name, false);
      setExported(result);
      setMessage(`已导出 ${result.item_count} 项知识交换包`);
    } catch (e) {
      setMessage(null);
      setError(failureMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function runVerify() {
    const name = verifyName.trim() || "exchange";
    setBusy("verify");
    setError(null);
    setMessage("正在验证交换包…");
    try {
      const result = await verifyExchange(name);
      setVerified(result);
      setMessage("交换包验证通过：清单与全部文件哈希一致。");
    } catch (e) {
      setMessage(null);
      setError(failureMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function runImport() {
    const name = importName.trim() || "exchange";
    const wsName = workspaceName.trim();
    if (!wsName) {
      setError(null);
      setMessage("请输入新工作区名称。");
      return;
    }
    setBusy("import");
    setError(null);
    setMessage("正在从交换包创建工作区…");
    try {
      const result = await importExchange(name, wsName);
      setImported(result);
      setMessage(`已从交换包创建工作区「${wsName}」：${result.item_count} 项。原始工作区未受影响。`);
    } catch (e) {
      setMessage(null);
      setError(failureMessage(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Section title="交换">
      <p className="muted">把原件、证据、学习与机器知识导出为开放交换目录（清单+哈希），并可随时验证完整性或从交换包创建新工作区。</p>

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
      {/* Persisted verify receipt, deliberately NOT a live region: the same verify action is already
          announced once by the single outcome region below, so a second one would read the result twice. */}
      {verified ? <p className="muted">验证结果：{verified.valid === true ? "通过" : "未通过"}{typeof verified.verified_items === "number" ? ` · ${verified.verified_items} 项` : ""}</p> : null}

      <h4>从交换包创建新工作区</h4>
      <p className="muted">将已验证的交换包导入为一个全新的独立四库工作区（原始工作区不会被修改）。</p>
      <div className="intake-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <label>交换包名称<input value={importName} onChange={(event) => setImportName(event.target.value)} placeholder="exchange" aria-label="导入交换包名称" /></label>
        <label>新工作区名称<input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} placeholder="imported-workspace" aria-label="新工作区名称" /></label>
      </div>
      <div className="intake-row">
        <button type="button" onClick={() => void runImport()} disabled={busy !== null}>{busy === "import" ? "正在导入…" : "创建工作区"}</button>
      </div>
      {imported ? <dl className="receipt-grid" aria-label="导入回执">
        <div><dt>新工作区</dt><dd className="mono">{imported.workspace_path}</dd></div>
        <div><dt>项目数</dt><dd>{imported.item_count}</dd></div>
        <div><dt>来源</dt><dd>{imported.source}</dd></div>
      </dl> : null}

      {/* One announce path per broadcast event. Loading, success and failure of export / verify /
          import all resolve into this single live region: on failure the outcome is the error card and
          on success or in-progress it is the message, and the two are never live at the same time.
          Before this, an Exchange failure produced no announcement at all while the persisted verify
          receipt announced the same success a second time. */}
      {error || message ? <div role="status">
        {error ? <DataError label="交换" message={error} /> : null}
        {message ? <p className="muted">{message}</p> : null}
      </div> : null}
    </Section>
  );
}
