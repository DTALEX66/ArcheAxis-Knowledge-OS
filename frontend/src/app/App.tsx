import { useCallback, useEffect, useRef, useState } from "react";
import { SpaceId, SPACES } from "../spaces/spaces";
import { StatusBar } from "../components/StatusBar";
import { SpaceRail } from "../components/SpaceRail";
import { ActivityDock } from "../components/ActivityDock";
import { Inspector, type InspectionTarget } from "../components/Inspector";
import { SpaceView } from "../spaces/SpaceView";
import { RecoveryShell } from "../components/RecoveryShell";
import { ContextNav } from "../components/ContextNav";
import {
  enterRecoverySafeMode,
  getRecoveryStatus,
  getStatus,
  resetRuntimeClient,
  restoreRecoveryBackup,
  retryDesktopBackend,
} from "../api/workspace";
import { runtimeProjectionMessage } from "../api/client";
import {
  checkingRecoveryStatus,
  failedRecoveryStatus,
  isRecoveryReady,
  type RecoveryStatusDto,
} from "../runtime/recovery";

const DESKTOP_LIVENESS_INTERVAL_MS = 10_000;
const RECOVERY_BOOT_POLL_MS = 250;
const RECOVERY_BOOT_TIMEOUT_MS = 30_000;

// AXW-UI-802: six-space shell following task pack §15.3 fixed structure:
// top status bar | left rail (six spaces) | context subnav | center view |
// right inspector | bottom activity dock.
export function App() {
  const desktop = Boolean(window.__TAURI__?.core?.invoke);
  const [activeSpace, setActiveSpace] = useState<SpaceId>("workspace");
  const [inspectionTarget, setInspectionTarget] = useState<InspectionTarget | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [desktopReady, setDesktopReady] = useState(!desktop);
  const [verificationPending, setVerificationPending] = useState(desktop);
  const [recoveryStatus, setRecoveryStatus] = useState<RecoveryStatusDto | null>(
    desktop ? checkingRecoveryStatus() : null,
  );
  const operation = useRef({ epoch: 0, mounted: true });
  const liveness = useRef<{
    generation: number;
    timeout: ReturnType<typeof globalThis.setTimeout> | null;
  }>({ generation: 0, timeout: null });

  useEffect(() => {
    operation.current.mounted = true;
    return () => {
      operation.current.mounted = false;
      operation.current.epoch += 1;
    };
  }, []);

  const navigate = useCallback((id: SpaceId) => {
    setActiveSpace(id);
    setInspectionTarget(null);
  }, []);

  const inspect = useCallback((target: InspectionTarget) => {
    setInspectionTarget(target);
    setInspectorOpen(true);
  }, []);

  const beginOperation = useCallback(() => {
    liveness.current.generation += 1;
    if (liveness.current.timeout !== null) {
      globalThis.clearTimeout(liveness.current.timeout);
      liveness.current.timeout = null;
    }
    operation.current.epoch += 1;
    setVerificationPending(true);
    return operation.current.epoch;
  }, []);

  const isCurrent = useCallback((epoch: number) => (
    operation.current.mounted && operation.current.epoch === epoch
  ), []);

  const finishOperation = useCallback((epoch: number) => {
    if (isCurrent(epoch)) setVerificationPending(false);
  }, [isCurrent]);

  const verifyReadyStatus = useCallback(async (status: RecoveryStatusDto, epoch: number) => {
    if (!isCurrent(epoch)) return false;
    setRecoveryStatus(status);
    setDesktopReady(false);
    if (!isRecoveryReady(status)) {
      return false;
    }
    try {
      await getStatus();
      if (!isCurrent(epoch)) return false;
      setDesktopReady(true);
      return true;
    } catch (error) {
      if (!isCurrent(epoch)) return false;
      setDesktopReady(false);
      const message = runtimeProjectionMessage(error);
      setRecoveryStatus(failedRecoveryStatus(message, status));
      try {
        const freshStatus = await getRecoveryStatus();
        if (!isCurrent(epoch)) return false;
        setRecoveryStatus(failedRecoveryStatus(message, freshStatus));
      } catch {
        if (!isCurrent(epoch)) return false;
        setRecoveryStatus(failedRecoveryStatus(message, status));
      }
      return false;
    }
  }, [isCurrent]);

  useEffect(() => {
    if (!desktop) return;
    const epoch = beginOperation();
    void (async () => {
      try {
        let status = await getRecoveryStatus();
        const bootDeadline = Date.now() + RECOVERY_BOOT_TIMEOUT_MS;
        if (!isCurrent(epoch)) return;
        while (status.state === "booting") {
          if (Date.now() >= bootDeadline) {
            setDesktopReady(false);
            setRecoveryStatus({
              ...status,
              state: "failed",
              backend_available: false,
              message: "本地核心启动超时；可查看安全诊断或重试。",
            });
            return;
          }
          setRecoveryStatus(status);
          setDesktopReady(false);
          const remaining = bootDeadline - Date.now();
          await new Promise((resolve) => globalThis.setTimeout(
            resolve,
            Math.min(RECOVERY_BOOT_POLL_MS, remaining),
          ));
          if (!isCurrent(epoch)) return;
          status = await getRecoveryStatus();
          if (!isCurrent(epoch)) return;
        }
        await verifyReadyStatus(status, epoch);
      } catch {
        if (isCurrent(epoch)) {
          setDesktopReady(false);
          setRecoveryStatus(failedRecoveryStatus("桌面恢复状态不可用。"));
        }
      } finally {
        finishOperation(epoch);
      }
    })();
  }, [beginOperation, desktop, finishOperation, isCurrent, verifyReadyStatus]);

  useEffect(() => {
    if (!desktop || !desktopReady || verificationPending) return;

    const generation = ++liveness.current.generation;
    const epoch = operation.current.epoch;
    const loopIsCurrent = () => (
      operation.current.mounted
      && operation.current.epoch === epoch
      && liveness.current.generation === generation
    );
    const claimRecovery = (fallback: RecoveryStatusDto, pending: boolean) => {
      if (!loopIsCurrent()) return null;
      const recoveryEpoch = ++operation.current.epoch;
      const recoveryGeneration = ++liveness.current.generation;
      if (liveness.current.timeout !== null) {
        globalThis.clearTimeout(liveness.current.timeout);
        liveness.current.timeout = null;
      }
      setDesktopReady(false);
      setVerificationPending(pending);
      setRecoveryStatus(fallback);
      return { epoch: recoveryEpoch, generation: recoveryGeneration };
    };
    const recoveryIsCurrent = (claim: { epoch: number; generation: number }) => (
      operation.current.mounted
      && operation.current.epoch === claim.epoch
      && liveness.current.generation === claim.generation
    );
    const schedule = () => {
      if (!loopIsCurrent()) return;
      liveness.current.timeout = globalThis.setTimeout(() => {
        liveness.current.timeout = null;
        void check();
      }, DESKTOP_LIVENESS_INTERVAL_MS);
    };
    const recoverHandshakeFailure = async (status: RecoveryStatusDto, error: unknown) => {
      const claim = claimRecovery(
        failedRecoveryStatus(runtimeProjectionMessage(error), status),
        true,
      );
      if (!claim) return;
      try {
        const freshStatus = await getRecoveryStatus();
        if (!recoveryIsCurrent(claim)) return;
        setRecoveryStatus(failedRecoveryStatus(runtimeProjectionMessage(error), freshStatus));
      } catch {
        if (!recoveryIsCurrent(claim)) return;
      } finally {
        if (recoveryIsCurrent(claim)) setVerificationPending(false);
      }
    };
    const check = async () => {
      let status: RecoveryStatusDto;
      try {
        status = await getRecoveryStatus();
      } catch {
        if (!loopIsCurrent()) return;
        claimRecovery(failedRecoveryStatus("桌面恢复状态不可用。"), false);
        return;
      }
      if (!loopIsCurrent()) return;
      if (!isRecoveryReady(status)) {
        claimRecovery(status, false);
        return;
      }
      try {
        await getStatus();
      } catch (error) {
        if (!loopIsCurrent()) return;
        await recoverHandshakeFailure(status, error);
        return;
      }
      if (!loopIsCurrent()) return;
      schedule();
    };

    schedule();
    return () => {
      if (liveness.current.timeout !== null) {
        globalThis.clearTimeout(liveness.current.timeout);
        liveness.current.timeout = null;
      }
      if (liveness.current.generation === generation) {
        liveness.current.generation += 1;
      }
    };
  }, [desktop, desktopReady, verificationPending]);

  const runRetry = useCallback(async (epoch: number) => {
    let retryFailed = false;
    try {
      await retryDesktopBackend();
    } catch {
      retryFailed = true;
    }
    if (!isCurrent(epoch)) return false;
    resetRuntimeClient();
    const status = await getRecoveryStatus();
    if (!isCurrent(epoch)) return false;
    const ready = await verifyReadyStatus(status, epoch);
    return !retryFailed && ready;
  }, [isCurrent, verifyReadyStatus]);

  const retry = useCallback(async () => {
    const epoch = beginOperation();
    setDesktopReady(false);
    try {
      const ready = await runRetry(epoch);
      if (isCurrent(epoch) && !ready) throw new Error("本地核心重试未完成");
    } finally {
      finishOperation(epoch);
    }
  }, [beginOperation, finishOperation, isCurrent, runRetry]);

  const enterSafeMode = useCallback(async () => {
    const epoch = beginOperation();
    setDesktopReady(false);
    try {
      const status = await enterRecoverySafeMode();
      if (!isCurrent(epoch)) return;
      setRecoveryStatus(status);
    } finally {
      finishOperation(epoch);
    }
  }, [beginOperation, finishOperation, isCurrent]);

  const reloadCurrentCore = useCallback(async () => {
    const epoch = beginOperation();
    setDesktopReady(false);
    try {
      const status = await enterRecoverySafeMode();
      if (!isCurrent(epoch)) return;
      setRecoveryStatus(status);
      resetRuntimeClient();
      const ready = await runRetry(epoch);
      if (isCurrent(epoch) && !ready) throw new Error("当前核心重新加载未完成");
    } finally {
      finishOperation(epoch);
    }
  }, [beginOperation, finishOperation, isCurrent, runRetry]);

  const restoreBackup = useCallback(async (
    name: string,
    onReceipt: () => void,
  ): Promise<"refreshed" | "refresh-unavailable"> => {
    const epoch = beginOperation();
    setDesktopReady(false);
    try {
      await restoreRecoveryBackup(name);
      if (!isCurrent(epoch)) return "refresh-unavailable";
      onReceipt();
      try {
        const status = await getRecoveryStatus();
        if (!isCurrent(epoch)) return "refresh-unavailable";
        await verifyReadyStatus(status, epoch);
        if (!isCurrent(epoch)) return "refresh-unavailable";
        return "refreshed";
      } catch {
        if (!isCurrent(epoch)) return "refresh-unavailable";
        setRecoveryStatus({
          state: "stopped",
          safe_mode: true,
          backend_available: false,
          message: "备份已恢复，但状态刷新不可用。",
          backups: [],
          external_dev: recoveryStatus?.external_dev === true,
        });
        return "refresh-unavailable";
      }
    } finally {
      finishOperation(epoch);
    }
  }, [beginOperation, finishOperation, isCurrent, recoveryStatus?.external_dev, verifyReadyStatus]);

  if (!desktopReady && recoveryStatus) {
    return (
      <RecoveryShell
        status={recoveryStatus}
        verificationPending={verificationPending}
        onEnterSafeMode={enterSafeMode}
        onRetry={retry}
        onRestoreBackup={restoreBackup}
        onReloadCurrentCore={reloadCurrentCore}
      />
    );
  }

  return (
    <div className="app-shell">
      <StatusBar
        activeSpace={activeSpace}
        backendState={!desktop
          ? "web"
          : verificationPending ? "checking" : desktopReady ? "available" : "unavailable"}
        externalDev={recoveryStatus?.external_dev === true}
        onNavigate={navigate}
        inspectorOpen={inspectorOpen}
        onToggleInspector={() => setInspectorOpen((value) => !value)}
      />
      <div className="app-body">
        <SpaceRail active={activeSpace} onNavigate={navigate} spaces={SPACES} />
        <ContextNav active={activeSpace} onNavigate={navigate} />
        <main className="app-center" role="main" aria-label="当前空间内容">
          <SpaceView spaceId={activeSpace} onInspect={inspect} onNavigate={navigate} />
        </main>
        {inspectorOpen ? <Inspector target={inspectionTarget} onClose={() => setInspectorOpen(false)} /> : null}
      </div>
      <ActivityDock onInspect={inspect} />
    </div>
  );
}
