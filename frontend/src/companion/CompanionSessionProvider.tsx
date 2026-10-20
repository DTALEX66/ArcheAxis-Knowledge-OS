import {createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode} from "react";
import {useOptionalCoreWorkingState} from "../presentation/useCoreWorkingState";
import {assertUiWorkingState} from "../api/generated/ui-working-state-contract";
import type {WorkingRead} from "../presentation/coreWorkingState";
import {coreCommand} from "../api/core";
import {CompanionSession} from "./CompanionSession";

const Context = createContext<CompanionSession | null>(null);
const IdentityCheck = createContext<(() => Promise<void>) | null>(null);
/** Views can disappear without ending a Core request. Scope changes replace presentation state. */
export function CompanionSessionProvider({children, session: supplied}: {children: ReactNode; session?: CompanionSession}) {
  const working = useOptionalCoreWorkingState();
  const session = useMemo(() => supplied ?? new CompanionSession(), [supplied, working?.session, working?.server?.workspace_id, working?.server?.restore_epoch]);
  const barrier = useRef({restoring: false, awaitingRead: false, epoch: 0});
  const [, updateBarrier] = useState(0);
  useEffect(() => () => {session.detach();}, [session]);
  const verify = useCallback(async () => {
    const expected = working?.server;
    if (!expected || barrier.current.restoring || ["loading", "blocked", "recovery"].includes(working.status)) return;
    const epoch = ++barrier.current.epoch;
    try {
      const read = assertUiWorkingState<WorkingRead>("Read", await coreCommand("ui_state_read"));
      if (epoch !== barrier.current.epoch || barrier.current.restoring || read.recovery_requires_confirmation || read.workspace_id !== expected.workspace_id || read.restore_epoch !== expected.restore_epoch) return;
      barrier.current.awaitingRead = false;
      session.resume(); void session.initialize(); updateBarrier(v => v + 1);
    } catch {/* Preserve the barrier and original request until an explicit fresh read succeeds. */}
  }, [session, working?.server, working?.status]);
  useEffect(() => {
    const pause = () => {barrier.current.awaitingRead = true; ++barrier.current.epoch; session.pause(); updateBarrier(v => v + 1);};
    const start = () => {barrier.current.restoring = true; pause();};
    const finish = () => {barrier.current.restoring = false; void verify();};
    window.addEventListener("workspace-restore-start", start);
    window.addEventListener("workspace-invalidated", pause);
    window.addEventListener("workspace-restore-finish", finish);
    return () => {
      ++barrier.current.epoch;
      window.removeEventListener("workspace-restore-start", start); window.removeEventListener("workspace-invalidated", pause); window.removeEventListener("workspace-restore-finish", finish);
    };
  }, [session, verify]);
  useEffect(() => {
    const desktop = Boolean(window.__TAURI__?.core?.invoke);
    // Browser hosts also establish the Core workspace identity; presentation never invents one.
    if (!desktop && working && !working.server) {session.pause(); void working.session.load().catch(() => {}); return;}
    const identityReady = !working || Boolean(working.server && !working.server.recovery_requires_confirmation && !["loading", "blocked", "recovery"].includes(working.status));
    if (!identityReady || barrier.current.restoring || barrier.current.awaitingRead) {
      session.pause();
      if (identityReady && !barrier.current.restoring && barrier.current.awaitingRead) void verify();
    } else {session.resume(); void session.initialize();}
  }, [session, working?.session, working?.server, working?.status, verify]);
  return <Context.Provider value={session}><IdentityCheck.Provider value={verify}>{children}</IdentityCheck.Provider></Context.Provider>;
}
export function useOptionalCompanionSession() {return useContext(Context);}
export function useCompanionIdentityVerification() {return useContext(IdentityCheck);}
export function useStandaloneCompanionSession() {
  const [session] = useState(() => new CompanionSession());
  useEffect(() => {session.resume(); void session.initialize(); return () => {session.detach();};}, [session]);
  return session;
}
