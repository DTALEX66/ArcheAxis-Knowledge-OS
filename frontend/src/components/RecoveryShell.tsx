import { useEffect, useRef, useState } from "react";
import {
  exitRecoveryApplication,
  getRecoveryLogTail,
} from "../api/runtime";
import type { RecoveryStatusDto } from "../runtime/recovery";

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
  logs: "Sanitized logs are unavailable.",
  "safe-mode": "Safe Mode is unavailable.",
  restore: "Backup restore failed; Core remains stopped.",
  retry: "Core retry failed. Review the sanitized status and try again.",
  reload: "Current Core reload failed. Review the sanitized status and try again.",
  exit: "Exit is unavailable. Use the window close control.",
};

const PROGRESS: Record<Operation, string> = {
  logs: "Loading sanitized logs…",
  "safe-mode": "Entering Safe Mode…",
  restore: "Restoring verified backup…",
  retry: "Retrying Core…",
  reload: "Reloading current Core…",
  exit: "Exiting application…",
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
  }, "Sanitized logs loaded.");

  const enterSafeMode = () => perform(
    "safe-mode",
    onEnterSafeMode,
    "Safe Mode is active; Core is stopped.",
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
        setError("Restore succeeded; status refresh unavailable.");
      } else {
        setSuccess("Backup restored. Retry Core when ready.");
      }
    } catch {
      if (mounted.current && operationEpoch.current === epoch) setError(ERRORS.restore);
    } finally {
      finish(epoch);
    }
  };

  const disabled = busy !== null || verificationPending;

  return (
    <div className="recovery-page">
      <header className="recovery-header">
        <span className="recovery-brand">ArcheAxis Knowledge</span>
        {status.external_dev ? <span className="dev-marker">DEV</span> : null}
      </header>
      <main className="recovery-shell" role="main" aria-label="Recovery Shell">
        <section className="recovery-card" aria-labelledby="recovery-title">
          <div className="recovery-heading">
            <div>
              <p className="recovery-kicker">Local desktop recovery</p>
              <h1 id="recovery-title">Recovery Shell</h1>
            </div>
            <span className="recovery-state" data-state={status.state}>{status.state}</span>
          </div>
          <p className="recovery-message" aria-live="polite">{status.message}</p>

          <div className="recovery-actions" aria-label="Recovery actions">
            <button type="button" disabled={disabled} onClick={() => void perform("retry", onRetry, "Core is ready.")}>Retry</button>
            <button type="button" disabled={disabled} onClick={() => void showLogs()}>Sanitized Logs</button>
            <button type="button" disabled={disabled || status.safe_mode} onClick={() => void enterSafeMode()}>Safe Mode</button>
            <button
              type="button"
              disabled={disabled || restoreLocked || !selectedBackup}
              onClick={() => setConfirmRestore(true)}
            >
              Restore Backup
            </button>
            {status.external_dev ? (
              <button
                type="button"
                disabled={disabled}
                onClick={() => void perform("reload", onReloadCurrentCore, "Current Core source reloaded.")}
              >
                Reload Current Core
              </button>
            ) : null}
            <button type="button" disabled={disabled} onClick={() => void perform("exit", exitRecoveryApplication, "Exiting…")}>Exit</button>
          </div>

          <div className="recovery-field">
            <label htmlFor="recovery-backup">Available backups</label>
            <select
              id="recovery-backup"
              value={selectedBackup}
              disabled={disabled || restoreLocked || status.backups.length === 0}
              onChange={(event) => {
                setSelectedBackup(event.target.value);
                setConfirmRestore(false);
              }}
            >
              {status.backups.length === 0 ? <option value="">No verified backups</option> : null}
              {status.backups.map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
          </div>

          {confirmRestore ? (
            <div className="recovery-confirm" role="group" aria-label="Confirm backup restore">
              <p>Restore the selected verified backup while Core remains stopped?</p>
              <button type="button" disabled={disabled || restoreLocked} onClick={() => void restore()}>Confirm Restore</button>
              <button type="button" disabled={disabled} onClick={() => setConfirmRestore(false)}>Cancel</button>
            </div>
          ) : null}

          {busy ? <p className="recovery-progress" role="status" aria-live="polite">{PROGRESS[busy]}</p> : null}
          <div ref={feedbackRef} tabIndex={-1} className="recovery-feedback">
            {error ? <p role="alert">{error}</p> : null}
            {success ? <p role="status" aria-live="polite">{success}</p> : null}
          </div>

          {logs !== null ? (
            <section className="recovery-logs" aria-labelledby="recovery-logs-title">
              <h2 id="recovery-logs-title">Sanitized Logs</h2>
              {logs.length === 0 ? <p>No sanitized diagnostics are available.</p> : (
                <ul>{logs.map((line, index) => <li key={`${index}-${line}`}>{line}</li>)}</ul>
              )}
            </section>
          ) : null}
        </section>
      </main>
    </div>
  );
}
