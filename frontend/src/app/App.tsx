import { useCallback, useEffect, useRef, useState } from "react";
import { SpaceId, SPACES } from "../spaces/spaces";
import { StatusBar } from "../components/StatusBar";
import { SpaceRail } from "../components/SpaceRail";
import { ActivityDock } from "../components/ActivityDock";
import { Inspector, type InspectionTarget } from "../components/Inspector";
import { SpaceView, canonicalSurface } from "../spaces/SpaceView";
import { RecoveryShell } from "../components/RecoveryShell";
import { ContextNav } from "../components/ContextNav";
import { NavTrail, type ObjectTrailLevel } from "../components/NavTrail";
import { focusSpaceSection, spaceSectionsFor, type SpaceSectionDef } from "../presentation/spaceSections";
import { EFFECTIVE_NAVIGATION_ENTRIES, resolveNavigationHash } from "../presentation/navigation";
import {
  enterRecoverySafeMode,
  getRecoveryStatus,
  getStatus,
  resetRuntimeClient,
  restoreRecoveryBackup,
  retryDesktopBackend,
} from "../api/workspace";
import { runtimeProjectionMessage } from "../api/client";
import { verifyCanonicalCore } from "../api/core";
import {
  checkingRecoveryStatus,
  failedRecoveryStatus,
  isRecoveryReady,
  type RecoveryStatusDto,
} from "../runtime/recovery";

const DESKTOP_LIVENESS_INTERVAL_MS = 10_000;
const RECOVERY_BOOT_POLL_MS = 250;
const RECOVERY_BOOT_TIMEOUT_MS = 30_000;

// AXW-UI-802: composite left navigation, central task area, on-demand inspector,
// and activity dock. Capability entries share one generated navigation projection.
export function App() {
  const desktop = Boolean(window.__TAURI__?.core?.invoke);
  const [initialNavigation] = useState(() => resolveNavigationHash(window.location.hash));
  const [activeSpace, setActiveSpace] = useState<SpaceId>(initialNavigation?.spaceId ?? (desktop ? "library" : "workspace"));
  const [selectedCapabilityId, setSelectedCapabilityId] = useState<string | null>(initialNavigation?.capabilityId ?? null);
  const [sectionNavigation, setSectionNavigation] = useState<{ spaceId: SpaceId; section: string; sequence: number }>({ spaceId: "library", section: "sources", sequence: 0 });
  const [objectTrail, setObjectTrail] = useState<readonly ObjectTrailLevel[]>([]);
  const [sectionNotice, setSectionNotice] = useState<string | null>(null);
  const [inspectionTarget, setInspectionTarget] = useState<InspectionTarget | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [learningFocus, setLearningFocus] = useState(false);
  const [desktopReady, setDesktopReady] = useState(!desktop);
  const [verificationPending, setVerificationPending] = useState(desktop);
  const [recoveryStatus, setRecoveryStatus] = useState<RecoveryStatusDto | null>(
    desktop ? checkingRecoveryStatus() : null,
  );
  const operation = useRef({ epoch: 0, mounted: true });
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const draftDirty = useRef(false);
  const navigationHash = useRef(window.location.hash);
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

  useEffect(() => {
    const listener = (event: Event) => { draftDirty.current = (event as CustomEvent<boolean>).detail === true; };
    window.addEventListener("archeaxis-draft-dirty", listener);
    return () => window.removeEventListener("archeaxis-draft-dirty", listener);
  }, []);

  useEffect(() => {
    const protectDocumentClose = (event: BeforeUnloadEvent) => {
      if (!draftDirty.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", protectDocumentClose);
    return () => window.removeEventListener("beforeunload", protectDocumentClose);
  }, []);

  useEffect(() => {
    const listener = (event: Event) => {
      const focused = (event as CustomEvent<boolean>).detail === true;
      setLearningFocus(focused);
      if (focused) setInspectorOpen(false);
    };
    window.addEventListener("archeaxis-learning-focus", listener);
    return () => window.removeEventListener("archeaxis-learning-focus", listener);
  }, []);

  const navigate = useCallback((id: SpaceId) => {
    if (draftDirty.current && !window.confirm("草稿尚未保存，请先保留文字。仍要离开吗？")) return false;
    setActiveSpace(id);
    if(id!=="learning"&&learningFocus){setLearningFocus(false);window.dispatchEvent(new CustomEvent("archeaxis-learning-focus",{detail:false}));}
    setSelectedCapabilityId(null);
    setInspectionTarget(null);
    setObjectTrail([]);
    setSectionNotice(null);
    const nextHash = `#space=${encodeURIComponent(id)}`;
    if (window.location.hash !== nextHash) window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${nextHash}`);
    navigationHash.current = nextHash;
    return true;
  }, [learningFocus]);

  const openCapability = useCallback((id: string) => {
    const entry = EFFECTIVE_NAVIGATION_ENTRIES.find((item) => item.entry_id === id && item.capability);
    if (!entry?.capability) return;
    if (draftDirty.current && !window.confirm("草稿尚未保存，请先保留文字。仍要离开吗？")) return;
    setActiveSpace("settings");
    if(learningFocus){setLearningFocus(false);window.dispatchEvent(new CustomEvent("archeaxis-learning-focus",{detail:false}));}
    setSelectedCapabilityId(id);
    setInspectionTarget(null);
    setObjectTrail([]);
    setSectionNotice(null);
    const nextHash = `#capability/${encodeURIComponent(id)}`;
    if (window.location.hash !== nextHash) window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${nextHash}`);
    navigationHash.current = nextHash;
  }, [learningFocus]);

  useEffect(() => {
    const onHashChange = () => {
      if (draftDirty.current && !window.confirm("草稿尚未保存，请先保留文字。仍要离开吗？")) {
        window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${navigationHash.current}`);
        return;
      }
      const target = resolveNavigationHash(window.location.hash);
      if (!target) return;
      if(target.spaceId!=="learning"&&learningFocus){setLearningFocus(false);window.dispatchEvent(new CustomEvent("archeaxis-learning-focus",{detail:false}));}
      navigationHash.current = window.location.hash;
      setActiveSpace(target.spaceId);
      setSelectedCapabilityId(target.capabilityId);
      setInspectionTarget(null);
      setObjectTrail([]);
      setSectionNotice(null);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [learningFocus]);

  const inspect = useCallback((target: InspectionTarget) => {
    setInspectionTarget(target);
    setInspectorOpen(true);
  }, []);

  const surface = canonicalSurface(activeSpace, desktop);
  const sections = spaceSectionsFor(activeSpace, surface);
  const activeSection = sectionNavigation.spaceId === activeSpace
    ? sectionNavigation.section
    : sections.find((section) => section.state === "ready")?.id;

  const focusRegion = useCallback((region: string) => {
    if (focusSpaceSection(region)) { setSectionNotice(null); return; }
    // A tab-mounted region only exists after the surface re-renders, so retry once
    // before telling the user the group has nothing open.
    globalThis.setTimeout(() => {
      if (!focusSpaceSection(region)) setSectionNotice("这个分组当前没有可打开的区域；请先在当前视图选择具体对象。");
    }, 0);
  }, []);

  const activateSection = useCallback((section: SpaceSectionDef) => {
    if (section.state !== "ready") return;
    if (section.goto) {
      const target = section.goto;
      if (!navigate(target.space)) return;
      setSectionNavigation((previous) => ({ spaceId: target.space, section: target.section, sequence: previous.sequence + 1 }));
      const region = spaceSectionsFor(target.space, canonicalSurface(target.space, desktop))
        .find((item) => item.id === target.section)?.region;
      if (region) focusRegion(region);
      return;
    }
    setSectionNavigation((previous) => ({ spaceId: activeSpace, section: section.id, sequence: previous.sequence + 1 }));
    if (section.region) focusRegion(section.region);
  }, [activeSpace, desktop, focusRegion, navigate]);

  const toggleInspector = useCallback(() => setInspectorOpen((value) => !value), []);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if (commandPaletteOpen || event.repeat || event.isComposing || event.getModifierState("AltGraph")) return;
      if (event.ctrlKey && event.altKey && !event.metaKey && !event.shiftKey && event.key.toLowerCase() === "i") {
        event.preventDefault(); toggleInspector();
      }
    };
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, [commandPaletteOpen, toggleInspector]);

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
      if (desktop) await verifyCanonicalCore();
      else await getStatus();
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
  }, [desktop, isCurrent]);

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
        await verifyCanonicalCore();
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

  const currentSpaceLabel = SPACES.find((space) => space.id === activeSpace)?.label ?? "";
  const firstReadyRegion = sections.find((section) => section.state === "ready" && section.region)?.region;
  const trailLevels: readonly ObjectTrailLevel[] = objectTrail.length === 0 ? [] : [
    { id: `space:${activeSpace}`, label: currentSpaceLabel, ...(firstReadyRegion ? { region: firstReadyRegion } : {}) },
    ...objectTrail,
  ];

  return (
    <div className="app-shell">
      <StatusBar
        activeSpace={activeSpace}
        backendState={!desktop
          ? "web"
          : verificationPending ? "checking" : desktopReady ? "available" : "unavailable"}
        externalDev={recoveryStatus?.external_dev === true}
        onNavigate={navigate}
        onOpenCapability={openCapability}
        selectedCapabilityId={selectedCapabilityId}
        onCommandPaletteOpenChange={setCommandPaletteOpen}
        inspectorOpen={inspectorOpen}
        onToggleInspector={toggleInspector}
      />
      <div className="app-body">
        {!learningFocus && <aside className="navigation-sidebar" aria-label="产品导航">
          <SpaceRail active={activeSpace} onNavigate={navigate} onOpenCapability={openCapability} activeCapabilityId={selectedCapabilityId} spaces={SPACES} />
          {!selectedCapabilityId && <ContextNav active={activeSpace} onNavigate={navigate} sections={sections} activeSection={activeSection} onSection={activateSection} />}
        </aside>}
        <main className="app-center" role="main" aria-label="当前空间内容">
          <NavTrail levels={trailLevels} onJump={focusRegion} />
          {sectionNotice ? <p className="nav-trail-notice" role="status">{sectionNotice}</p> : null}
          <SpaceView spaceId={activeSpace} onInspect={inspect} onNavigate={navigate} onOpenCapability={openCapability} navigation={sectionNavigation} selectedCapabilityId={selectedCapabilityId} onTrail={setObjectTrail} />
        </main>
        {inspectorOpen && !selectedCapabilityId && !learningFocus ? <Inspector target={inspectionTarget} onClose={() => setInspectorOpen(false)} /> : null}
      </div>
      {!learningFocus && <ActivityDock onInspect={inspect} commandPaletteOpen={commandPaletteOpen} />}
    </div>
  );
}
