import { useEffect, useRef, useState } from "react";
import {
  exitRecoveryApplication,
  getRecoveryLogTail,
} from "../api/workspace";
import type { RecoveryStatusDto } from "../runtime/recovery";
import { stateLabel } from "../presentation/labels";

interface RecoveryShellProps {
  status: RecoveryStatusDto;
  verificationPending: boolean;
  onEnterSafeMode: () => Promise<void>;
  onRetry: () => Promise<void>;
  onRestoreBackup: (
    name: string,
    onReceipt: () => void,
  ) => Promise<"refreshed" | "refresh-unavailable">;
  onReloadCurrentCore: () => Promise<void>;
}

type Operation = "logs" | "safe-mode" | "restore" | "retry" | "reload" | "exit";

const ERRORS: Record<Operation, string> = {
  logs: "安全诊断日志不可用。",
  "safe-mode": "安全模式不可用。",
  restore: "备份恢复失败；本地核心仍保持停止。",
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
  incompatible: "本地核心与当前桌面版本不兼容。",
  failed: "本地核心启动失败，可查看安全诊断或恢复备份。",
  stopped: "本地核心已停止。",
};

export function RecoveryShell({
  status,
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
    if (!selectedBackup || !status.backups.includes(selectedBackup)) {
      setError(ERRORS.restore);
      return;
    }
    const epoch = ++operationEpoch.current;
    setBusy("restore");
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
        setError("备份已恢复，但状态刷新不可用。");
      } else {
        setSuccess("备份已恢复；准备好后可重试本地核心。");
      }
    } catch {
      if (mounted.current && operationEpoch.current === epoch) setError(ERRORS.restore);
    } finally {
      finish(epoch);
    }
  };

  const disabled = busy !== null || verificationPending;
  const primaryMessage = status.safe_mode
    ? "安全模式已启用；本地核心保持停止。"
    : RECOVERY_MESSAGES[status.state];
  const diagnostic = /[\u3400-\u9fff]/.test(status.message) && status.message !== primaryMessage
    ? status.message
    : "";

  return (
    <div className="recovery-page">
      <header className="recovery-header">
        <span className="recovery-brand">星环知识</span>
        {status.external_dev ? <span className="dev-marker">开发</span> : null}
      </header>
      <main className="recovery-shell" role="main" aria-label="恢复工作台">
        <section className="recovery-card" aria-labelledby="recovery-title">
          <div className="recovery-heading">
            <div>
              <p className="recovery-kicker">本地桌面恢复</p>
              <h1 id="recovery-title">恢复工作台</h1>
            </div>
            <span className={`badge ${status.state === "ready" ? "badge-success" : status.state === "failed" ? "badge-danger" : "badge-warning"}`}>
              {stateLabel(status.state)}
            </span>
          </div>
          <p className="recovery-message" aria-live="polite">{primaryMessage}</p>
          {diagnostic ? <p className="recovery-diagnostic">诊断：{diagnostic}</p> : null}

          <div className="recovery-actions" aria-label="恢复操作">
            <button type="button" className="primary" disabled={disabled} onClick={() => void perform("retry", onRetry, "本地核心已就绪。")}>重试</button>
            <button type="button" disabled={disabled} onClick={() => void showLogs()}>安全诊断</button>
            <button type="button" disabled={disabled || status.safe_mode} onClick={() => void enterSafeMode()}>安全模式</button>
            <button
              type="button"
              disabled={disabled || restoreLocked || !selectedBackup}
              onClick={() => setConfirmRestore(true)}
            >
              恢复备份
            </button>
            {status.external_dev ? (
              <button
                type="button"
                disabled={disabled}
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
              <button type="button" className="danger" disabled={disabled || restoreLocked} onClick={() => void restore()}>确认恢复</button>
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
