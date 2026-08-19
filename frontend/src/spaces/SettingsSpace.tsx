import { useEffect, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
import { getSetupStatus, initializeSetup } from "../api/runtime";

export function SettingsSpace() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [initializing, setInitializing] = useState(false);
  const [initMsg, setInitMsg] = useState<string | null>(null);

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
