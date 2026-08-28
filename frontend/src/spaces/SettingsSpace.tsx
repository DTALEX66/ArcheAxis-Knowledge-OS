import { useEffect, useMemo, useState } from "react";
import { DataError, Loading, Section } from "../components/RealData";
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
      setWizardMessage(successMessage);
      setStage("complete");
      try {
        setData(await getSetupStatus());
      } catch (refreshError) {
        setWizardMessage(`${successMessage}；状态刷新失败：${errorMessage(refreshError)}`);
      }
    } catch (requestError) {
      setWizardMessage(`创建失败：${errorMessage(requestError)}`);
    } finally {
      setWizardBusy(false);
    }
  }

  return (
    <Section title="设置与四库管理">
      <p className="muted">设置工作区位置，并在写入前完成路径和空间检查。</p>
      {loading ? <Loading label="设置" /> : error ? <DataError label="设置" message={error} /> : <>
        {stage === "welcome" && <div>
          <h4>欢迎使用星环知识平台</h4>
          <p>先选择四库的位置，系统会在创建前检查路径可写性与可用空间。</p>
          <button type="button" className="btn-primary" onClick={() => setStage("mode")}>开始设置</button>
        </div>}

        {stage === "mode" && <div>
          <h4>选择路径模式</h4>
          <label><input type="radio" checked={mode === "quick"} onChange={() => setMode("quick")} /> 快速设置：四库位于同一根目录</label>
          <label><input type="radio" checked={mode === "advanced"} onChange={() => setMode("advanced")} /> 高级设置：分别选择四个库的位置</label>
          <div className="command-row"><button type="button" onClick={() => setStage("paths")}>继续</button></div>
        </div>}

        {stage === "paths" && <div>
          <h4>{mode === "quick" ? "选择四库根路径" : "选择四个库路径"}</h4>
          {mode === "quick" ? <label htmlFor="setup-root">四库根路径
            <input id="setup-root" value={quickRoot} onChange={(event) => setQuickRoot(event.target.value)} placeholder="例如 D:\\ArcheAxis" />
          </label> : Object.entries(DOMAIN_LABELS).map(([domain, label]) => <label key={domain} htmlFor={`setup-${domain}`}>{label}
            <input id={`setup-${domain}`} value={domains[domain] ?? ""} onChange={(event) => setDomains((current) => ({ ...current, [domain]: event.target.value }))} placeholder="绝对路径" />
          </label>)}
          <div className="command-row">
            <button type="button" onClick={() => setStage("mode")}>返回</button>
            <button type="button" className="btn-primary" disabled={wizardBusy || !canCheckHealth} onClick={checkHealth}>{wizardBusy ? "检查中…" : "检查四库健康"}</button>
          </div>
        </div>}

        {stage === "health" && <div>
          <h4>四库健康检查</h4>
          {preflight?.ready === false ? <p role="status" className="muted">健康检查未通过；修复不可写、空间不足或文件系统问题后才能创建工作区。</p> : null}
          {Object.entries(DOMAIN_LABELS).map(([domain, label]) => {
            const domainHealth = health[domain];
            const healthDetails = [
              typeof domainHealth?.free_bytes === "number" ? `${domainHealth.free_bytes} bytes 可用` : null,
              domainHealth?.readonly === true ? "只读" : domainHealth?.readonly === false ? "可写" : null,
              domainHealth?.filesystem,
              domainHealth?.removable,
            ].filter(Boolean).join(" · ");
            return <div className="row" key={domain}>
              <div className="row-main"><b>{label}</b><span>{selectedDomains[domain] ?? "—"}</span></div>
              <span>{healthDetails || "未返回健康信息"}</span>
            </div>;
          })}
          <div className="command-row">
            <button type="button" onClick={() => setStage("paths")}>返回修改</button>
            <button type="button" className="btn-primary" disabled={wizardBusy || preflight?.ready !== true} onClick={createWorkspace}>{wizardBusy ? "创建中…" : "创建工作区"}</button>
          </div>
        </div>}

        {stage === "complete" && <div>
          <h4>设置完成</h4>
          <p>{wizardMessage ?? "工作区四库状态已可读回。"}</p>
          {!data?.ready && <button type="button" onClick={() => setStage("welcome")}>重新检查设置</button>}
        </div>}

        {wizardMessage && stage !== "complete" ? <p className="muted">{wizardMessage}</p> : null}
        <h4>当前就绪状态</h4>
        {readinessSteps.map((step) => <div className="row" key={step.id}>
          <div className="row-main"><b>{READINESS_LABELS[step.id] ?? "设置检查"}</b><span>{readinessMessage(step.state)}</span></div><span>{stateLabel(step.state)}</span>
        </div>)}
        <div className="command-row">
          <label htmlFor="backup-name">备份名称</label>
          <input id="backup-name" value={backupName} onChange={(event) => setBackupName(event.target.value)} placeholder="例如 release-check" />
          <button type="button" disabled={backupBusy || !backupName.trim()} onClick={async () => {
            setBackupBusy(true); setWizardMessage("正在创建备份…");
            try { await createBackup(backupName.trim()); const result = await verifyBackup(backupName.trim()); setWizardMessage(result.valid === false ? "备份验证失败" : "备份验证通过"); }
            catch (requestError) { setWizardMessage(`备份失败：${errorMessage(requestError)}`); }
            finally { setBackupBusy(false); }
          }}>创建并验证备份</button>
        </div>
        <div className="command-row"><button type="button" onClick={async () => {
          setWizardMessage("正在重试桌面后端…");
          try { await retryDesktopBackend(); resetRuntimeClient(); setData(await getSetupStatus()); setWizardMessage("桌面后端已重新握手"); }
          catch (requestError) { setWizardMessage(`恢复失败：${errorMessage(requestError)}`); }
        }}>重试桌面后端</button></div>
      </>}
    </Section>
  );
}
