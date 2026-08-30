import { useEffect, useMemo, useState } from "react";
import { DataError, Loading } from "../components/RealData";
import {
  createBackup,
  getSetupStatus,
  initializeSetup,
  preflightSetup,
  resetRuntimeClient,
  retryDesktopBackend,
  type SetupMode,
  type SetupPreflightDto,
  type SetupRequestDto,
  type SetupStatusDto,
  verifyBackup,
} from "../api/workspace";
import { stateLabel, userErrorMessage } from "../presentation/labels";

const DOMAIN_LABELS: Record<string, string> = {
  source_archive: "源文件归档库",
  evidence_ledger: "证据账本库",
  human_learning_vault: "人类学习库",
  ai_asset_vault: "机器知识库",
};

const READINESS_LABELS: Record<string, string> = {
  workspace_exists: "工作区",
  manifest_valid: "工作区清单",
  legacy_db_migration: "旧数据迁移",
  paths_writable: "存储位置",
  capability_store_ready: "能力存储",
};

type WizardStage = "welcome" | "mode" | "paths" | "health" | "complete";

function defaultRoot(status: SetupStatusDto | null): string {
  return typeof status?.workspace_root === "string" ? status.workspace_root : "";
}

function errorMessage(error: unknown): string {
  return userErrorMessage(error instanceof Error ? error.message : error);
}

function readinessMessage(state: string): string {
  if (state === "ready" || state === "completed") return "检查通过";
  if (state === "pending") return "等待完成设置";
  if (state === "blocked") return "需要处理；请重新检查设置或存储权限";
  return "状态不可用";
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export function SettingsSpace() {
  const [data, setData] = useState<SetupStatusDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState<WizardStage>("welcome");
  const [mode, setMode] = useState<SetupMode>("quick");
  const [quickRoot, setQuickRoot] = useState("");
  const [domains, setDomains] = useState<Record<string, string>>({});
  const [preflight, setPreflight] = useState<SetupPreflightDto | null>(null);
  const [wizardBusy, setWizardBusy] = useState(false);
  const [wizardMessage, setWizardMessage] = useState<string | null>(null);
  const [backupName, setBackupName] = useState("");
  const [backupBusy, setBackupBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    getSetupStatus()
      .then((status) => {
        if (!alive) return;
        setData(status);
        setQuickRoot(defaultRoot(status));
        if (status.ready) setStage("complete");
      })
      .catch((requestError: Error) => { if (alive) setError(userErrorMessage(requestError.message)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const request = useMemo<SetupRequestDto>(() => {
    if (mode === "quick") return { mode, root: quickRoot.trim() };
    return { mode, domains };
  }, [domains, mode, quickRoot]);

  const readinessSteps = Array.isArray(data?.steps) ? data.steps : [];
  const selectedDomains = preflight?.domains ?? {};
  const health = preflight?.library_health ?? {};
  const canCheckHealth = mode === "quick"
    ? Boolean(quickRoot.trim())
    : Object.keys(DOMAIN_LABELS).every((domain) => Boolean(domains[domain]?.trim()));

  async function checkHealth() {
    setWizardBusy(true);
    setWizardMessage(null);
    try {
      setPreflight(await preflightSetup(request));
      setStage("health");
    } catch (requestError) {
      setWizardMessage(`路径检查失败：${errorMessage(requestError)}`);
    } finally {
      setWizardBusy(false);
    }
  }

  async function createWorkspace() {
    setWizardBusy(true);
    setWizardMessage(null);
    try {
      const result = await initializeSetup(request);
      const successMessage = result.workspace_id ? "工作区已创建并通过读回" : "工作区已创建";
      try {
        const freshStatus = await getSetupStatus();
        setData(freshStatus);
        if (freshStatus.ready !== true) {
          setStage("health");
          setWizardMessage("工作区写入已返回，但四库尚未达到就绪状态。");
          return;
        }
        setWizardMessage(successMessage);
        setStage("complete");
      } catch (refreshError) {
        setStage("health");
        setWizardMessage(`工作区写入已返回，但就绪状态读回失败：${errorMessage(refreshError)}`);
      }
    } catch (requestError) {
      setWizardMessage(`创建失败：${errorMessage(requestError)}`);
    } finally {
      setWizardBusy(false);
    }
  }

  return (
  <section className="settings-page" aria-labelledby="settings-title">
    <h1 id="settings-title">设置</h1>
    <p className="muted">配置工作区与四库位置，系统会在创建前检查路径可写性与可用空间。</p>
    {loading ? <Loading label="设置" /> : error ? <DataError label="设置" message={error} /> : <>
      {stage === "welcome" && (
        <div className="setup-card">
          <h4>欢迎使用星环知识</h4>
          <p className="muted" style={{ marginBottom: 16 }}>先选择四库的位置，系统会在创建前检查路径可写性与可用空间。</p>
          <button type="button" className="primary" onClick={() => setStage("mode")}>开始设置</button>
        </div>
      )}

      {stage === "mode" && (
        <div className="setup-card">
          <h4>选择路径模式</h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, margin: "16px 0" }}>
            <label className="mode-option">
              <input type="radio" checked={mode === "quick"} onChange={() => setMode("quick")} />
              <div>
                <div>快速设置</div>
                <div>四库位于同一根目录</div>
              </div>
            </label>
            <label className="mode-option">
              <input type="radio" checked={mode === "advanced"} onChange={() => setMode("advanced")} />
              <div>
                <div>高级设置</div>
                <div>分别选择四个库的位置</div>
              </div>
            </label>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" onClick={() => setStage("welcome")}>返回</button>
            <button type="button" className="primary" onClick={() => setStage("paths")}>继续</button>
          </div>
        </div>
      )}

      {stage === "paths" && (
        <div className="setup-card">
          <h4>{mode === "quick" ? "选择四库根路径" : "选择四个库路径"}</h4>
          {mode === "quick" ? (
            <div className="form-group">
              <label className="form-label" htmlFor="setup-root">四库根路径</label>
              <input
                id="setup-root"
                value={quickRoot}
                onChange={(event) => setQuickRoot(event.target.value)}
                placeholder="例如 D:/资料库"
              />
              <span className="form-hint">四个库将自动创建在此目录下</span>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {Object.entries(DOMAIN_LABELS).map(([domain, label]) => (
                <div className="form-group" key={domain}>
                  <label className="form-label" htmlFor={`setup-${domain}`}>
                    {label}
                  </label>
                  <input
                    id={`setup-${domain}`}
                    value={domains[domain] ?? ""}
                    onChange={(event) => setDomains((current) => ({ ...current, [domain]: event.target.value }))}
                    placeholder="绝对路径"
                  />
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <button type="button" onClick={() => setStage("mode")}>返回</button>
            <button
              type="button"
              className="primary"
              disabled={wizardBusy || !canCheckHealth}
              onClick={checkHealth}
            >
              {wizardBusy ? "检查中…" : "检查四库健康"}
            </button>
          </div>
        </div>
      )}

      {stage === "health" && (
        <div className="setup-card">
          <h4>四库健康检查</h4>
          {preflight?.ready === false && (
            <div className="error-card" style={{ marginBottom: 12 }}>
              健康检查未通过；修复不可写、空间不足或文件系统问题后才能创建工作区。
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {Object.entries(DOMAIN_LABELS).map(([domain, label]) => {
              const domainHealth = health[domain];
              const freeBytes = typeof domainHealth?.free_bytes === "number" ? domainHealth.free_bytes : null;
              const readonly = domainHealth?.readonly;
              return (
                <div key={domain} className="card" style={{ padding: 12 }}>
                  <div style={{ fontWeight: 590, marginBottom: 4, color: "var(--ax-fg)" }}>{label}</div>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>{selectedDomains[domain] ?? "—"}</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {freeBytes !== null && <span className="badge badge-info">{formatBytes(freeBytes)} 可用</span>}
                    {readonly === true && <span className="badge badge-warning">只读</span>}
                    {readonly === false && <span className="badge badge-success">可写</span>}
                    {domainHealth?.filesystem && <span className="badge badge-info">{domainHealth.filesystem}</span>}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <button type="button" onClick={() => setStage("paths")}>返回修改</button>
            <button
              type="button"
              className="primary"
              disabled={wizardBusy || preflight?.ready !== true}
              onClick={createWorkspace}
            >
              {wizardBusy ? "创建中…" : "创建工作区"}
            </button>
          </div>
        </div>
      )}

      {stage === "complete" && (
        <div className="setup-card">
          <h4>设置完成</h4>
          <p>{wizardMessage ?? "工作区四库状态已可读回。"}</p>
          {!data?.ready && (
            <button type="button" onClick={() => setStage("welcome")} style={{ marginTop: 12 }}>
              重新检查设置
            </button>
          )}
        </div>
      )}

      {wizardMessage && stage !== "complete" && <p className="muted" style={{ marginTop: 8 }}>{wizardMessage}</p>}

      <h2 style={{ marginTop: 32, marginBottom: 12, fontSize: 14 }}>当前就绪状态</h2>
      <div style={{ display: "grid", gap: 8 }}>
        {readinessSteps.map((step) => (
          <div key={step.id} className="card" style={{ padding: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <div style={{ fontWeight: 590, color: "var(--ax-fg)" }}>{READINESS_LABELS[step.id] ?? "设置检查"}</div>
              <div className="muted" style={{ fontSize: 12 }}>{readinessMessage(step.state)}</div>
            </div>
            <span className={`badge ${step.state === "ready" || step.state === "completed" ? "badge-success" : step.state === "pending" ? "badge-warning" : "badge-danger"}`}>
              {stateLabel(step.state)}
            </span>
          </div>
        ))}
      </div>

      <h2 style={{ marginTop: 32, marginBottom: 12, fontSize: 14 }}>备份管理</h2>
      <div className="card" style={{ padding: 16 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
            <label className="form-label" htmlFor="backup-name">备份名称</label>
            <input
              id="backup-name"
              value={backupName}
              onChange={(event) => setBackupName(event.target.value)}
              placeholder="例如 release-check"
            />
          </div>
          <button
            type="button"
            className="primary"
            disabled={backupBusy || !backupName.trim()}
            onClick={async () => {
              setBackupBusy(true);
              setWizardMessage("正在创建备份…");
              try {
                await createBackup(backupName.trim());
                const result = await verifyBackup(backupName.trim());
                if (result.valid !== true) throw new Error("backup verification projection is invalid");
                setWizardMessage("备份验证通过");
              } catch (requestError) {
                setWizardMessage(`备份失败：${errorMessage(requestError)}`);
              } finally {
                setBackupBusy(false);
              }
            }}
          >
            {backupBusy ? "创建中…" : "创建并验证备份"}
          </button>
        </div>
      </div>

      <h2 style={{ marginTop: 32, marginBottom: 12, fontSize: 14 }}>桌面后端</h2>
      <div className="card" style={{ padding: 16 }}>
        <button
          type="button"
          onClick={async () => {
            setWizardMessage("正在重试桌面后端…");
            try {
              await retryDesktopBackend();
              resetRuntimeClient();
              setData(await getSetupStatus());
              setWizardMessage("桌面后端已重新握手");
            } catch (requestError) {
              setWizardMessage(`恢复失败：${errorMessage(requestError)}`);
            }
          }}
        >
          重试桌面后端
        </button>
      </div>
    </>}
  </section>
  );
}
