import { CoreWorkingStateSession, type WorkingRead } from "../presentation/coreWorkingState";
import { CoreWorkingStateProvider, useCoreWorkingState } from "../presentation/useCoreWorkingState";
import { coreCommand } from "../api/core";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { PinnedReferencePanel } from "../components/PinnedReferencePanel";
import type { ObjectReference } from "../api/generated/research-contract";
import { findUiPage } from "../presentation/uiPages";
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
function createWorkingSession() {
  return new CoreWorkingStateSession({
    read:()=>coreCommand<WorkingRead>("ui_state_read"),
    write:body=>coreCommand<WorkingRead>("ui_state_write",{body}),
    clearJob:body=>coreCommand<WorkingRead>("ui_state_clear_job",{body}),
    clearSaved:body=>coreCommand<WorkingRead>("ui_state_clear_saved",{body}),
    recover:body=>coreCommand<WorkingRead>("ui_state_recover",{body}),
  });
}
export function App() {
  const [session,setSession]=useState(createWorkingSession);
  useEffect(()=>{
    // Only a confirmed workspace replacement owns a new session. CAS/permission
    // refusals and ambiguous restore receipts retain the App-owned local drafts.
    const reset=(event:Event)=>{if((event as CustomEvent<{confirmed?:boolean}>).detail?.confirmed===true)setSession(createWorkingSession());};
    window.addEventListener("workspace-invalidated",reset);
    return()=>window.removeEventListener("workspace-invalidated",reset);
  },[]);
  return <CoreWorkingStateProvider session={session}><AppBody /></CoreWorkingStateProvider>;
}
function AppBody() {
  const working=useCoreWorkingState();
  const hydratedSession=useRef<CoreWorkingStateSession|null>(null);
  const [workingEntered,setWorkingEntered]=useState(false);
  const desktop = Boolean(window.__TAURI__?.core?.invoke);
  const [initialNavigation] = useState(() => resolveNavigationHash(window.location.hash));
  const [activeSpace, setActiveSpace] = useState<SpaceId>(initialNavigation?.spaceId ?? "workspace");
  const [navigationOpen,setNavigationOpen] = useState(false);
  const [uiPageId,setUiPageId] = useState<string|undefined>(initialNavigation?.capabilityId ? "18" : initialNavigation?.pageId ?? (initialNavigation ? undefined : "01"));
  const [openedDocumentId,setOpenedDocumentId] = useState<string|undefined>();
  const [initialLearningItemKey, setInitialLearningItemKey] = useState<string|undefined>();
  const composing = useRef(false);
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
  const [searchedObject,setSearchedObject]=useState<ObjectReference|null>(null);
  const [searchedContentSha,setSearchedContentSha]=useState<string>();
  const draftDirty = useRef(false);
  const draftOwners = useRef(new Set<string>());
  const [unsavedDrafts, setUnsavedDrafts] = useState(false);
  const [workspaceRestoring, setWorkspaceRestoring] = useState(false);
  const restoringRef = useRef(false);
  const [restoreNotice, setRestoreNotice] = useState<{confirmed:boolean;message:string}|null>(null);
  const [workspaceEpoch, setWorkspaceEpoch] = useState(0);
  const navigationHash = useRef(window.location.hash);
  const liveness = useRef<{
    generation: number;
    timeout: ReturnType<typeof globalThis.setTimeout> | null;
  }>({ generation: 0, timeout: null });

  useEffect(() => {
    const start = () => { composing.current = true; };
    const end = () => { composing.current = false; };
    window.addEventListener("compositionstart", start, true);
    window.addEventListener("compositionend", end, true);
    return () => {
      window.removeEventListener("compositionstart", start, true);
      window.removeEventListener("compositionend", end, true);
      composing.current = false;
    };
  }, []);

  useEffect(() => {
    operation.current.mounted = true;
    return () => {
      operation.current.mounted = false;
      operation.current.epoch += 1;
    };
  }, []);

  useEffect(() => {
    const listener = (event: Event) => {
      const value = (event as CustomEvent<unknown>).detail;
      const item = value && typeof value === "object" ? value as { owner?: unknown; dirty?: unknown } : null;
      const owner = item && typeof item.owner === "string" ? item.owner : "legacy";
      if (item ? item.dirty === true : value === true) draftOwners.current.add(owner); else draftOwners.current.delete(owner);
      draftDirty.current = draftOwners.current.size > 0; setUnsavedDrafts(draftDirty.current);
    };
    window.addEventListener("archeaxis-draft-dirty", listener);
    return () => window.removeEventListener("archeaxis-draft-dirty", listener);
  }, []);

  useEffect(() => {
    const lock = () => {
      restoringRef.current = true;
      setRestoreNotice(null); setNavigationOpen(false); setInspectorOpen(false);
      liveness.current.generation += 1;
      if (liveness.current.timeout !== null) globalThis.clearTimeout(liveness.current.timeout);
      for (const area of document.querySelectorAll(".app-body, .status-bar, .activity-dock, .ui-navigation-trigger, .aaos-dialog-overlay, .aaos-dialog-content")) area.setAttribute("inert", "");
      setWorkspaceRestoring(true);
    };
    const unlock = () => {
      restoringRef.current = false;
      for (const area of document.querySelectorAll(".app-body, .status-bar, .activity-dock, .ui-navigation-trigger, .aaos-dialog-overlay, .aaos-dialog-content")) area.removeAttribute("inert");
      setWorkspaceRestoring(false);
    };
    const invalidate = (event:Event) => {
      const detail=(event as CustomEvent<{confirmed?:boolean;message?:string}>).detail;
      setRestoreNotice({confirmed:detail?.confirmed===true,message:typeof detail?.message==="string"?detail.message:"恢复结果尚未确认，旧视图已失效，请核对当前工作区。"});
      composing.current = false;
      resetRuntimeClient();
      // Every mounted data view and editor belongs to the replaced workspace.
      draftOwners.current.clear(); draftDirty.current = false; setUnsavedDrafts(false);
      setWorkspaceEpoch(value => value + 1);
      setUiPageId("01"); setActiveSpace("workspace"); setOpenedDocumentId(undefined); setInitialLearningItemKey(undefined);
      setSelectedCapabilityId(null); setInspectionTarget(null); setObjectTrail([]);
      setSearchedObject(null);
      setLearningFocus(false); setNavigationOpen(false);
      const hash = "#page=01";
      window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${hash}`);
      navigationHash.current = hash;
    };
    // Capture before portal/CommandPalette/window listeners, even in the same
    // dispatch turn before React has applied the restoring state render.
    const blockInteraction=(event:Event)=>{if(!restoringRef.current)return;event.preventDefault();event.stopImmediatePropagation();};
    const blockedEvents=["keydown","pointerdown","click","beforeinput","input","submit"];
    for(const name of blockedEvents)window.addEventListener(name,blockInteraction,true);
    window.addEventListener("workspace-restore-start", lock);
    window.addEventListener("workspace-restore-finish", unlock);
    window.addEventListener("workspace-invalidated", invalidate);
    return () => {
      for(const name of blockedEvents)window.removeEventListener(name,blockInteraction,true);
      unlock();
      window.removeEventListener("workspace-restore-start", lock);
      window.removeEventListener("workspace-restore-finish", unlock);
      window.removeEventListener("workspace-invalidated", invalidate);
    };
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
    if (restoringRef.current || composing.current) return false;
    if (draftDirty.current && !window.confirm("草稿尚未保存，请先保留文字。仍要离开吗？")) return false;
    setNavigationOpen(false);
    setUiPageId(id === "workspace" ? "01" : undefined);
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
  }, [learningFocus, workspaceRestoring]);

  const openPage = useCallback((id:string) => {
    const page=findUiPage(id);
    if (!page || restoringRef.current || composing.current) return;
    if (uiPageId === id && activeSpace === page.space && !selectedCapabilityId) { setNavigationOpen(false); return; }
    if (!navigate(page.space)) return;
    setUiPageId(id);
    const hash=`#page=${encodeURIComponent(id)}`;
    window.history.replaceState(null,"",`${window.location.pathname}${window.location.search}${hash}`);
    navigationHash.current=hash;
  },[navigate, uiPageId, activeSpace, selectedCapabilityId]);
  const openDocument = useCallback((id:string) => {
    if(!navigate("library"))return;
    setUiPageId("03");setOpenedDocumentId(id);
    const hash = "#page=03";
    window.history.replaceState(null,"",`${window.location.pathname}${window.location.search}${hash}`);
    navigationHash.current = hash;
  },[navigate]);
  const openReviewItem = useCallback((itemKey: string) => {
    if (!itemKey || !navigate("learning")) return;
    setUiPageId("06"); setInitialLearningItemKey(itemKey);
    const hash = "#page=06";
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${hash}`);
    navigationHash.current = hash;
  }, [navigate]);
  const openCapability = useCallback((id: string) => {
    if(restoringRef.current || composing.current)return;
    const entry = EFFECTIVE_NAVIGATION_ENTRIES.find((item) => item.entry_id === id && item.capability);
    if (!entry?.capability) return;
    if (draftDirty.current && !window.confirm("草稿尚未保存，请先保留文字。仍要离开吗？")) return;
    setNavigationOpen(false);
    setUiPageId("18");
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
      if(restoringRef.current || composing.current){window.history.replaceState(null,"",`${window.location.pathname}${window.location.search}${navigationHash.current}`);return;}
      if (draftDirty.current && !window.confirm("草稿尚未保存，请先保留文字。仍要离开吗？")) {
        window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${navigationHash.current}`);
        return;
      }
      const target = resolveNavigationHash(window.location.hash);
      if (!target) return;
      if(target.spaceId!=="learning"&&learningFocus){setLearningFocus(false);window.dispatchEvent(new CustomEvent("archeaxis-learning-focus",{detail:false}));}
      navigationHash.current = window.location.hash;
      setUiPageId(target.capabilityId ? "18" : target.pageId);
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
    if(restoringRef.current)return;
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
    if(restoringRef.current)return;
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

  const toggleInspector = useCallback(() => {if(!restoringRef.current)setInspectorOpen((value) => !value);}, []);
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if (restoringRef.current || commandPaletteOpen || event.repeat || event.isComposing || event.getModifierState("AltGraph")) return;
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
    if (!desktop || !desktopReady || verificationPending || workspaceRestoring) return;

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
  }, [desktop, desktopReady, verificationPending, workspaceRestoring]);

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

  useEffect(()=>{
    if(!desktop||!desktopReady||verificationPending||workspaceRestoring)return;
    let alive=true;
    setWorkingEntered(false);
    void working.session.load().then(read=>{
      if(!alive||read.recovery_requires_confirmation)return;
      const snapshot=working.session.getSnapshot();
      if(snapshot.status==="blocked")return;
      if(hydratedSession.current!==working.session) {
        hydratedSession.current=working.session;
        const page=findUiPage(snapshot.state.page_id??"");
        if(page){setUiPageId(page.id);setActiveSpace(page.space);setSelectedCapabilityId(null);}
        setOpenedDocumentId(snapshot.state.active_document??undefined);
      }
      setWorkingEntered(true);
    }).catch(()=>{});
    return()=>{alive=false;};
  },[desktop,desktopReady,verificationPending,workspaceRestoring,working.session]);
  useEffect(()=>{
    if(!desktop)return;
    // Scene CAS status also includes page/opened-object bookkeeping. Only actual
    // content drafts or a frozen create request own the content navigation guard.
    const dirty=Object.keys(working.state.drafts).length>0||Boolean(working.state.pending_original)||Object.keys(working.state.pending_jobs??{}).length>0;
    if(dirty)draftOwners.current.add("core-working-state");else draftOwners.current.delete("core-working-state");
    draftDirty.current=draftOwners.current.size>0;setUnsavedDrafts(draftDirty.current);
  },[desktop,working.state,working.status,workspaceEpoch]);
  useEffect(()=>{
    if(!desktop||!workingEntered||working.status==="blocked"||working.status==="recovery")return;
    if(working.state.page_id!==(uiPageId??null))working.session.rememberScene(uiPageId??null);
  },[desktop,workingEntered,uiPageId,working.session,working.state.page_id,working.status]);
  useEffect(()=>{
    if(!desktop||working.status!=="unsaved"||workspaceRestoring)return;
    const timer=window.setTimeout(()=>{void working.session.flush().catch(()=>{});},250);
    return()=>window.clearTimeout(timer);
  },[desktop,working.state,working.status,workspaceRestoring,working.session]);
  async function rereadWorkingState() {
    try {
      const read=await working.session.load();
      const view=working.session.getSnapshot();
      if(!read.recovery_requires_confirmation&&view.status!=="blocked") {
        if(hydratedSession.current!==working.session){const page=findUiPage(view.state.page_id??"");if(page){setUiPageId(page.id);setActiveSpace(page.space);}setOpenedDocumentId(view.state.active_document??undefined);hydratedSession.current=working.session;}
        setWorkingEntered(true);
      }
    }catch{/* Session retains the exact local draft and displays the refusal. */}
  }
  async function decideWorkingRecovery(action:"preserve"|"discard") {
    try {
      await working.session.recover(action);
      const view=working.session.getSnapshot();
      if(view.status!=="ready")return;
      const page=findUiPage(view.state.page_id??"");
      if(page){setUiPageId(page.id);setActiveSpace(page.space);}
      setOpenedDocumentId(view.state.active_document??undefined);
      hydratedSession.current=working.session;setWorkingEntered(true);
    }catch{/* Explicit choice may still be refused; no candidate replaces local input. */}
  }
  const workingNotice=desktop?<section aria-label="工作草稿保全" role={working.error?"alert":"status"}>
    <p>{working.status==="ready"?"工作状态已由 Core 保全；正文保存以各文档版本回执为准。":working.status==="saving"?"正在保全工作草稿…":working.status==="loading"?"正在读取工作草稿；编辑入口等待身份核对。":"工作草稿仍保留，持久化尚未全部确认。"}</p>
    {working.error?<p>{working.error}</p>:null}
    {["blocked","loading","unsaved"].includes(working.status)?<><button onClick={()=>void rereadWorkingState()}>核对工作状态</button><button disabled={working.status!=="unsaved"} onClick={()=>void working.session.flush().catch(()=>{})}>仅重试草稿保全</button></>:null}
    {working.server?.recovery_requires_confirmation?<><p>恢复候选含 {Object.keys(working.server.recovery_candidates?.drafts??{}).length} 份独立草稿及 {Object.keys(working.server.recovery_candidates?.pending_jobs??{}).length} 个冻结执行请求。正文尚未套用；请明确选择。</p><pre>{Object.keys(working.server.recovery_candidates?.drafts??{}).join("\n")}</pre><button onClick={()=>void decideWorkingRecovery("preserve")}>保留恢复候选</button><button onClick={()=>void decideWorkingRecovery("discard")}>丢弃恢复候选</button></>:null}
  </section>:null;

  if (!desktopReady && recoveryStatus) {
    return (
      <>
      {restoreNotice ? <p role={restoreNotice.confirmed ? "status" : "alert"} className="workspace-restore-notice">{restoreNotice.message}</p> : null}
      <RecoveryShell
        status={recoveryStatus}
        verificationPending={verificationPending}
        onEnterSafeMode={enterSafeMode}
        onRetry={retry}
        onRestoreBackup={restoreBackup}
        onReloadCurrentCore={reloadCurrentCore}
      />
      </>
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
      {restoreNotice?<p role={restoreNotice.confirmed?"status":"alert"} className="workspace-restore-notice">{restoreNotice.message}</p>:null}
      {workspaceRestoring ? <div role="status" className="workspace-restore-overlay">正在恢复工作区并重启本地 Core，请等待读回完成…</div> : null}
      {workingNotice}
      <StatusBar
        activeSpace={activeSpace}
        backendState={!desktop
          ? "web"
          : verificationPending ? "checking" : desktopReady ? "available" : "unavailable"}
        externalDev={recoveryStatus?.external_dev === true}
        onPage={openPage} onNavigate={navigate}
        onOpenCapability={openCapability}
        selectedCapabilityId={selectedCapabilityId}
        onCommandPaletteOpenChange={setCommandPaletteOpen}
        onOpenObject={(reference,sha)=>{if(!restoringRef.current){setSearchedObject(reference);setSearchedContentSha(sha);}}}
        inspectorOpen={inspectorOpen}
        onToggleInspector={toggleInspector}
      />
      {!learningFocus && <AaosDialog title="产品导航" description="选择页面；Esc关闭并返回导航按钮。" open={navigationOpen} onOpenChange={setNavigationOpen} trigger={<button className="ui-navigation-trigger" aria-label="打开产品导航">☰ 导航</button>} contentClassName="ui-navigation-drawer"><button onClick={()=>setNavigationOpen(false)}>关闭导航</button><SpaceRail active={activeSpace} onNavigate={navigate} onOpenCapability={openCapability} activeCapabilityId={selectedCapabilityId} spaces={SPACES} pageId={uiPageId} onPage={openPage}/></AaosDialog>}
      <div className="app-body" key={`workspace:${workspaceEpoch}`} aria-busy={workspaceRestoring}>
        {!learningFocus && <aside className="navigation-sidebar" aria-label="产品导航">
          <SpaceRail active={activeSpace} onNavigate={navigate} onOpenCapability={openCapability} activeCapabilityId={selectedCapabilityId} spaces={SPACES} pageId={uiPageId} onPage={openPage} />
          {!selectedCapabilityId && ["02","03","16","17","19","20"].includes(uiPageId ?? "03") && <ContextNav active={activeSpace} onNavigate={navigate} sections={sections} activeSection={activeSection} onSection={activateSection} />}
        </aside>}
        <main className="app-center" role="main" aria-label="当前空间内容">
          {searchedObject?<PinnedReferencePanel reference={searchedObject} expectedDocumentSha={searchedContentSha} onClose={()=>setSearchedObject(null)} onOpenReference={reference=>{setSearchedObject(reference);setSearchedContentSha(undefined);}}/>:null}
          <NavTrail levels={trailLevels} onJump={focusRegion} />
          {sectionNotice ? <p className="nav-trail-notice" role="status">{sectionNotice}</p> : null}
          <div className="ui-page-heading" role="group" aria-label="当前页面"><div><h1>{findUiPage(uiPageId ?? "")?.label ?? currentSpaceLabel}</h1><p>个人空间 · 本地知识与 Human–AI 双向学习</p></div><small>UI / {uiPageId ?? "兼容入口"}</small></div>
          {(!desktop||workingEntered)?<SpaceView initialLearningItemKey={initialLearningItemKey} onReviewItem={openReviewItem} onOpenPage={openPage} hasUnsavedDrafts={unsavedDrafts} uiPageId={uiPageId} initialDocumentId={openedDocumentId} onOpenDocument={openDocument} spaceId={activeSpace} onInspect={inspect} onNavigate={navigate} onOpenCapability={openCapability} navigation={sectionNavigation} selectedCapabilityId={selectedCapabilityId} onTrail={setObjectTrail} />:<p role="status">工作状态尚未核对；请使用上方读回或明确恢复入口。</p>}
        </main>
        {inspectorOpen && !selectedCapabilityId && !learningFocus ? <Inspector target={inspectionTarget} onClose={() => setInspectorOpen(false)} /> : null}
      </div>
      {!learningFocus && <ActivityDock key={`activity:${workspaceEpoch}`} onInspect={inspect} commandPaletteOpen={commandPaletteOpen} />}
    </div>
  );
}
