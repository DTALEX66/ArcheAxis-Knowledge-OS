import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import {
  createBackup,
  getSetupStatus,
  initializeSetup,
  resetRuntimeClient,
  retryDesktopBackend,
  verifyBackup,
} from "../api/workspace";

export function SettingsSpace() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [initializing, setInitializing] = useState(false);
  const [initMsg, setInitMsg] = useState<string | null>(null);
  const [backupName, setBackupName] = useState("");
  const [backupBusy, setBackupBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    getSetupStatus()
      .then((d) => { if (alive) setData(d); })
      .catch((e: Error) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const entries = data ? Object.entries(data).slice(0, 16) : [];
  return (
    <Section title="设置与四库管理（Settings）">
      <p className="muted">真实数据源：GET /api/v1/setup/status（首次启动向导状态）</p>
      {loading ? (
        <Loading label="设置" />
      ) : error ? (
        <DataError label="Settings" message={error} />
      ) : (
        <>
          <button
            type="button"
            className="btn-primary"
            disabled={initializing}
            onClick={async () => {
              setInitializing(true);
              setInitMsg("初始化中…");
              try {
                const result = await initializeSetup();
                setInitMsg(`初始化完成：workspace_id=${String(result.workspace_id ?? "—")}`);
                setData(await getSetupStatus());
              } catch (e) {
                setInitMsg("初始化失败：" + (e instanceof Error ? e.message : String(e)));
              } finally {
                setInitializing(false);
              }
            }}
          >
            {initializing ? "初始化中…" : "初始化四库工作区"}
          </button>
          {initMsg ? <p className="muted">{initMsg}</p> : null}
          <div className="command-row">
            <label htmlFor="backup-name">备份名称</label>
            <input id="backup-name" value={backupName} onChange={(event) => setBackupName(event.target.value)} placeholder="例如 release-check" />
            <button type="button" disabled={backupBusy || !backupName.trim()} onClick={async () => {
              setBackupBusy(true);
              setInitMsg("正在创建备份…");
              try {
                await createBackup(backupName.trim());
                const result = await verifyBackup(backupName.trim());
                setInitMsg(result.valid === false ? "备份验证失败" : "备份验证通过");
              } catch (e) {
                setInitMsg(`备份失败：${e instanceof Error ? e.message : String(e)}`);
              } finally {
                setBackupBusy(false);
              }
            }}>创建并验证备份</button>
          </div>
          <div className="command-row">
            <button type="button" onClick={async () => {
              setInitMsg("正在重试桌面后端…");
              try {
                await retryDesktopBackend();
                resetRuntimeClient();
                setData(await getSetupStatus());
                setInitMsg("桌面后端已重新握手");
              } catch (e) {
                setInitMsg(`恢复失败：${e instanceof Error ? e.message : String(e)}`);
              }
            }}>重试桌面后端</button>
          </div>
          <table className="data-table">
            <tbody>
              {entries.map(([k, v]) => (
                <tr key={k}><th>{k}</th><td>{String(v ?? "—")}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </Section>
  );
}
