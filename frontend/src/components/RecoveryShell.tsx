import { useEffect, useRef, useState } from "react";
import {
  exitRecoveryApplication,
  getRecoveryLogTail,
} from "../api/workspace";
import type { RecoveryStatusDto } from "../runtime/recovery";
import { stateLabel } from "../presentation/labels";
import { AaosStatusBadge } from "./AaosStatusBadge";

interface RecoveryShellProps {
  status: RecoveryStatusDto;
  hasUnsavedDrafts?: boolean;
  verificationPending: boolean;
  onEnterSafeMode: () => Promise<void>;
  onRetry: () => Promise<void>;
  onRestoreBackup: (
    name: string,
    onReceipt: () => void,
  ) => Promise<"refreshed" | "refresh-unavailable" | "not-started-status-refreshed" | "failed-status-refreshed" | "failed-status-unavailable">;
  onReloadCurrentCore: () => Promise<void>;
}

type Operation = "logs" | "safe-mode" | "restore" | "retry" | "reload" | "exit";

const ERRORS: Record<Operation, string> = {
  logs: "安全诊断日志不可用。",
  "safe-mode": "安全模式不可用。",
  restore: "备份恢复未完成；请核对本地核心状态和安全诊断。",
  retry: "本地核心重试失败，请检查安全诊断后重试。",
  reload: "当前核心重新加载失败，请检查安全诊断后重试。",
  exit: "无法从此处退出，请使用窗口关闭按钮。",
};

const PROGRESS: Record<Operation, string> = {
  logs: "正在加载安全诊断日志…",
  "safe-mode": "正在进入安全模式…",
  restore: "正在恢复已验证备份…",
  retry: "正在重试本地核心…",
  reload: "正在重新加载当前核心…",
  exit: "正在退出应用…",
};

const RECOVERY_MESSAGES: Record<RecoveryStatusDto["state"], string> = {
  booting: "正在启动本地核心，请稍候。",
  checking: "正在检查本地核心和工作区状态。",
  ready: "本地核心已就绪。",
  reconnecting: "连接已中断，正在恢复。",
  incompatible: "应用与本地服务暂时不能配合运行，请检查版本。",
  failed: "本地核心启动失败，可查看安全诊断或恢复备份。",
  stopped: "本地核心已停止。",
};

export function RecoveryShell({
  status,
  hasUnsavedDrafts = false,
  verificationPending,
  onEnterSafeMode,
  onRetry,
  onRestoreBackup,
  onReloadCurrentCore,
}: RecoveryShellProps) {
  const [busy, setBusy] = useState<Operation | null>(null);
  const [logs, setLogs] = useState<string[] | null>(null);
  const [selectedBackup, setSelectedBackup] = useState(status.backups[0] ?? "");
  const [confirmRestore, setConfirmRestore] = useState(false);
  const [restoreLocked, setRestoreLocked] = useState(false);
  const [restoreUnconfirmed, setRestoreUnconfirmed] = useState(false);
  const [restoreStatusUnknown, setRestoreStatusUnknown] = useState(false);
  const [restoreNotStarted, setRestoreNotStarted] = useState(false);
  const restoreStarted = useRef(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const feedbackRef = useRef<HTMLDivElement>(null);
  const mounted = useRef(true);
  const operationEpoch = useRef(0);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      operationEpoch.current += 1;
    };
  }, []);

  useEffect(() => {
    if (!status.backups.includes(selectedBackup)) {
      setSelectedBackup(status.backups[0] ?? "");
      setConfirmRestore(false);
    }
  }, [selectedBackup, status.backups]);

  const finish = (epoch: number) => {
    if (!mounted.current || operationEpoch.current !== epoch) return;
    setBusy(null);
    globalThis.setTimeout(() => {
      if (mounted.current && operationEpoch.current === epoch) feedbackRef.current?.focus();
    }, 0);
  };

  const perform = async (
    operation: Operation,
    action: (epoch: number) => Promise<void>,
    message: string,
  ) => {
    const epoch = ++operationEpoch.current;
    setBusy(operation);
    setError("");
    setSuccess("");
    try {
      await action(epoch);
      if (mounted.current && operationEpoch.current === epoch) setSuccess(message);
    } catch {
      if (mounted.current && operationEpoch.current === epoch) setError(ERRORS[operation]);
    } finally {
      finish(epoch);
    }
  };

  const showLogs = () => perform("logs", async (epoch) => {
    const result = await getRecoveryLogTail();
    if (mounted.current && operationEpoch.current === epoch) setLogs(result.lines);
  }, "安全诊断日志已加载。");

  const enterSafeMode = () => perform(
    "safe-mode",
    onEnterSafeMode,
    "安全模式已启用；本地核心已停止。",
  );

  const restore = async () => {
    if (restoreStarted.current) return;
    if (hasUnsavedDrafts) {
      setError("草稿尚未保存，请先保存或保留文字后恢复备份。");
      return;
    }
    if (!selectedBackup || !status.backups.includes(selectedBackup)) {
      setError(ERRORS.restore);
      return;
    }
    const epoch = ++operationEpoch.current;
    restoreStarted.current = true;
    setBusy("restore");
    // A failed or lost receipt can follow a partial restore. Do not repeat it
    // or reopen the workspace without an independently confirmed outcome.
    setConfirmRestore(false);
    setRestoreLocked(true);
    setRestoreUnconfirmed(true);
    setRestoreStatusUnknown(false);
    setRestoreNotStarted(false);
    setError("");
    setSuccess("");
    try {
      const result = await onRestoreBackup(selectedBackup, () => {
        if (!mounted.current || operationEpoch.current !== epoch) return;
        setConfirmRestore(false);
        setRestoreLocked(true);
      });
      if (!mounted.current || operationEpoch.current !== epoch) return;
      if (result === "refresh-unavailable") {
        setRestoreStatusUnknown(true);
        setError("备份已恢复，但状态刷新不可用。");
      } else if (result === "not-started-status-refreshed") {
        // This one fixed host code means no restore side effect occurred.
        // Permit a later explicit action, but never retry or reopen by itself.
        restoreStarted.current = false;
        setRestoreLocked(false);
        setRestoreUnconfirmed(false);
        setRestoreNotStarted(true);
        setError("未找到本地核心；本次恢复未执行。修复应用后可手动重试。");
      } else if (result === "failed-status-unavailable") {
        setRestoreStatusUnknown(true);
        setError("备份恢复未完成；本地核心状态无法确认。请保留草稿并查看安全诊断，再重新打开应用核对。");
      } else if (result === "failed-status-refreshed") {
        setError(ERRORS.restore);
      } else {
        setRestoreUnconfirmed(false);
        setSuccess("备份已恢复；准备好后可重试本地核心。");
      }
    } catch {
      if (mounted.current && operationEpoch.current === epoch) {
        setRestoreStatusUnknown(true);
        setError("备份恢复未完成；本地核心状态无法确认。请保留草稿并查看安全诊断，再重新打开应用核对。");
      }
    } finally {
      finish(epoch);
    }
  };

  const disabled = busy !== null || verificationPending;
  const unverifiedReady = (restoreUnconfirmed || restoreNotStarted) && status.state === "ready";
  const primaryMessage = restoreStatusUnknown ? "本地核心状态无法确认。" : unverifiedReady
    ? "宿主报告本地核心可用；工作区尚未重新验证。"
    : status.safe_mode
    ? "安全模式已启用；本地核心保持停止。"
    : RECOVERY_MESSAGES[status.state];
  const diagnostic = status.message === "CORE_UNAVAILABLE"
    ? "未找到本地核心，请修复应用后重试。"
    : /[\u3400-\u9fff]/.test(status.message) && status.message !== primaryMessage
    ? status.message
    : "";

  return (
    <div className="recovery-page">
      <header className="recovery-header">
        <span className="recovery-brand">星环知识系统</span>
        {status.external_dev ? <span className="dev-marker">开发</span> : null}
      </header>
      <main className="recovery-shell" role="main" aria-label="恢复工作台">
        <section className="recovery-card" aria-labelledby="recovery-title">
          <div className="recovery-heading">
            <div>
              <p className="recovery-kicker">本地桌面恢复</p>
              <h1 id="recovery-title">恢复工作台</h1>
            </div>
            <AaosStatusBadge tone={unverifiedReady || restoreStatusUnknown ? "warning" : status.state === "ready" ? "success" : status.state === "failed" ? "danger" : "warning"}>
              {unverifiedReady || restoreStatusUnknown ? "待确认" : stateLabel(status.state)}
            </AaosStatusBadge>
          </div>
          <p className="recovery-message" aria-live="polite">{primaryMessage}</p>
          {diagnostic ? <p className="recovery-diagnostic">诊断：{diagnostic}</p> : null}
          {hasUnsavedDrafts ? <p role="alert">草稿尚未保存，请先保存或保留文字后恢复备份。</p> : null}

          <div className="recovery-actions" aria-label="恢复操作">
            <button type="button" className="primary" disabled={disabled || restoreUnconfirmed} onClick={() => void perform("retry", onRetry, "本地核心已就绪。")}>重试启动</button>
            <button type="button" disabled={disabled} onClick={() => void showLogs()}>安全诊断</button>
            <button type="button" disabled={disabled || restoreUnconfirmed || status.safe_mode} onClick={() => void enterSafeMode()}>安全模式</button>
            <button
              type="button"
              disabled={disabled || restoreLocked || !selectedBackup || hasUnsavedDrafts}
              onClick={() => setConfirmRestore(true)}
            >
              恢复备份
            </button>
            {status.external_dev ? (
              <button
                type="button"
                disabled={disabled || restoreUnconfirmed}
                onClick={() => void perform("reload", onReloadCurrentCore, "当前核心已重新加载。")}
              >
                重新加载当前核心
              </button>
            ) : null}
            <button type="button" disabled={disabled} onClick={() => void perform("exit", exitRecoveryApplication, "正在退出…")}>退出</button>
          </div>

          <div className="recovery-field">
            <label htmlFor="recovery-backup">可用备份</label>
            <select
              id="recovery-backup"
              value={selectedBackup}
              disabled={disabled || restoreLocked || status.backups.length === 0}
              onChange={(event) => {
                setSelectedBackup(event.target.value);
                setConfirmRestore(false);
              }}
            >
              {status.backups.length === 0 ? <option value="">没有已验证备份</option> : null}
              {status.backups.map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
          </div>

          {confirmRestore ? (
            <div className="recovery-confirm" role="group" aria-label="确认恢复备份">
              <p>在本地核心保持停止时恢复所选已验证备份？</p>
              <button type="button" className="danger" disabled={disabled || restoreLocked || hasUnsavedDrafts} onClick={() => void restore()}>确认恢复</button>
              <button type="button" disabled={disabled} onClick={() => setConfirmRestore(false)}>取消</button>
            </div>
          ) : null}

          {busy ? <p className="recovery-progress" role="status" aria-live="polite">{PROGRESS[busy]}</p> : null}
          <div ref={feedbackRef} tabIndex={-1} className="recovery-feedback">
            {error ? <p role="alert" className="error-card">{error}</p> : null}
            {success ? <p role="status" aria-live="polite" className="badge badge-success">{success}</p> : null}
          </div>

          {logs !== null ? (
            <section className="recovery-logs" aria-labelledby="recovery-logs-title">
              <h2 id="recovery-logs-title">安全诊断日志</h2>
              {logs.length === 0 ? <p>没有可用的安全诊断信息。</p> : (
                <ul>{logs.map((line, index) => <li key={`${index}-${line}`}>{line}</li>)}</ul>
              )}
            </section>
          ) : null}
        </section>
      </main>
    </div>
  );
}
