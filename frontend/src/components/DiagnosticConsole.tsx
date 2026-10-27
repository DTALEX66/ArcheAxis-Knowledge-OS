import {coreCommand} from "../api/core";
import {assertUiWorkingState} from "../api/generated/ui-working-state-contract";
import type {WorkingRead} from "../presentation/coreWorkingState";
import { useCallback, useLayoutEffect, useReducer, useRef } from "react";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import { localDateTime } from "../presentation/display";
import type {FailureLogSnapshot} from "../api/generated/core-contract";
import { useDiagnosticState, clearDiagnostics, publishDiagnostic, diagnosticCategories, openDiagnostics, closeDiagnostics, restoreDiagnosticFocus, resetDiagnostics, suspendDiagnostics, resumeDiagnostics, connectDiagnosticPersistence, reloadDiagnosticPersistence, setDiagnosticFilter, type DiagnosticCategory } from "../presentation/diagnostics";

function connectLog(workspace_id:string,restore_epoch:string) {
  connectDiagnosticPersistence({workspace_id,restore_epoch},{read:body=>coreCommand<FailureLogSnapshot>("operation_failure_log_read",{body}),append:body=>coreCommand<FailureLogSnapshot>("operation_failure_log_append",{body}),clear:body=>coreCommand<FailureLogSnapshot>("operation_failure_log_clear",{body})});
}

/** Replaces an inline JSON dump: the operator still reaches the untouched payload, the reading surface does not carry it. */
export function RawReceiptButton({ label, payload, visibleLabel, category = "operation" }: { label: string; payload: unknown; visibleLabel?: string; category?: DiagnosticCategory }) {
  const {suspended}=useDiagnosticState();
  const text = suspended ? "请先核对工作状态" : visibleLabel ?? "状态与诊断";
  // The visible and accessible names describe the same shared destination.
  const display = suspended ? text : visibleLabel ?? "状态与诊断";
  return (
    <button type="button" className="raw-receipt" data-diagnostic-label={label} aria-label={`${text}：${label}`} disabled={suspended} title={suspended?"正在恢复或工作状态尚未确认，请先核对工作状态。":"查看处理状态与详细记录"} onClick={event => publishDiagnostic(label, payload, category, event.currentTarget)}>
        {display}
    </button>
  );
}

/**
 * The one place raw backend payloads may appear. Reading surfaces keep human-readable
 * summaries and publish the untouched receipt here instead of printing it inline.
 */
export function DiagnosticConsole() {
  const {entries, filter, selected, persistence, persistenceFailure} = useDiagnosticState();
  const visible = entries.filter(entry => filter === "all" || entry.category === filter);
  return (
    <section className="diagnostic-console" aria-label="诊断控制台">
      <header className="diagnostic-console-header">
        <h4>问题与运行记录</h4>
        <span className="diagnostic-console-count">当前工作区共 {entries.length} 条记录</span>
        <button type="button" disabled={(entries.length === 0&&persistence!=="corrupt")||persistence==="loading"||persistence==="clearing"} onClick={()=>void clearDiagnostics()}>清空诊断</button>
      </header>
      <label>诊断分类<select value={filter} onChange={event => setDiagnosticFilter(event.target.value as DiagnosticCategory | "all")}><option value="all">全部</option>{Object.entries(diagnosticCategories).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
      {persistence==="unavailable"||persistence==="corrupt"?<button type="button" onClick={reloadDiagnosticPersistence}>重新读取问题记录</button>:null}
      <p>{persistence==="ready"?"已保存的问题摘要关闭后仍可查看，最多50条；备份也会保留这些记录。标为“本次会话”的记录和手动详细回执关闭后不保留。":persistence==="loading"?"正在读取此工作区的问题记录。":persistence==="clearing"?"正在清空问题记录，请稍候。":persistence==="corrupt"?"已保存的问题记录暂时无法读取；文档和草稿不受影响。可明确清空这些记录后重新开始。":persistence==="unavailable"?(persistenceFailure==="clear"?"清空结果尚未确认，原记录仍显示。请先重新读取记录，再决定是否清空。":persistenceFailure==="append"?"问题摘要暂未确认保存，当前会话的记录仍可查看。未保存的记录关闭后可能丢失，请先重新读取记录。":"暂时无法读取已保存的问题记录。当前会话的记录仍可查看，关闭后可能丢失。 "):"简要问题记录暂存于当前会话，关闭应用后不保留。"}</p>
      {entries.length === 0
        ? <p className="diagnostic-console-empty">暂无诊断记录。操作失败会自动记下简要信息；各页面的“状态与诊断”可补充详细记录。</p>
        : visible.length === 0 ? <p>此分类暂无记录。</p>
        : (
          <ul className="diagnostic-console-list">
            {visible.map((entry) => (
              <li key={entry.sequence}>
                {entry.summary ? <p>{entry.label}：{entry.summary}{entry.occurrences && entry.occurrences > 1 ? `（共发生${entry.occurrences}次）` : ""}</p> : null}
                <details key={`${entry.sequence}:${filter}`} open={entry.sequence === selected || undefined}>
                  <summary>{entry.automatic ? "查看技术信息" : entry.label} · {diagnosticCategories[entry.category]} · {localDateTime(entry.at)}{entry.historical?" · 恢复前记录":""}{entry.persisted?" · 已保存":entry.automatic?" · 本次会话（未确认保存）":""}</summary>
                  <pre>{JSON.stringify(entry.payload, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ul>
        )}
    </section>
  );
}

export function DiagnosticCenterTrigger() {
  const {suspended} = useDiagnosticState();
  return <><button type="button" className="diagnostic-center-trigger" aria-label="运行诊断" data-diagnostic-trigger="true" disabled={suspended} onClick={event => openDiagnostics(event.currentTarget)}>运行诊断</button>{suspended?<button type="button" onClick={() => window.dispatchEvent(new Event("diagnostic-workspace-check"))}>重新检查诊断连接</button>:null}</>;
}

/** One App-owned surface, independent of page, activity expansion or recovery UI. */
export function DiagnosticCenter() {
  const {open} = useDiagnosticState();
  useLayoutEffect(() => {
    if (!open) return;
    // This App-owned portal can open above a picker owned by another tree.
    // Handle its focused Escape before a lower Radix document listener can
    // dismiss that picker during the portal's layer-registration effects.
    const dismissFocusedDiagnostic = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || !(event.target instanceof Element) || !event.target.closest('.aaos-dialog-content')?.classList.contains("diagnostic-center")) return;
      event.stopPropagation();
      if (event.isComposing || event.defaultPrevented) return;
      event.preventDefault();
      closeDiagnostics();
    };
    window.addEventListener("keydown", dismissFocusedDiagnostic, true);
    return () => window.removeEventListener("keydown", dismissFocusedDiagnostic, true);
  }, [open]);
  const working = useOptionalCoreWorkingState();
  const identity = useRef<{session: unknown; workspace: string; restore: string} | null>(null);
  const latest = useRef(working); latest.current = working;
  const barrier = useRef({restoring:false, awaitingRead:false, epoch:0});
  const [readbackRevision, recheckIdentity] = useReducer(value => value + 1, 0);
  const verify = useCallback(async () => {
    const expected = latest.current, gate = barrier.current;
    if (!expected?.server || gate.restoring || ["blocked", "loading", "recovery"].includes(expected.status) || expected.server.recovery_requires_confirmation) return;
    const attempt = ++gate.epoch;
    try {
      // Deliberately bypass session.load(): that may reuse a pre-restore readFlight.
      const fresh = assertUiWorkingState<WorkingRead>("Read", await coreCommand("ui_state_read"));
      const current = latest.current;
      if (attempt !== gate.epoch || gate.restoring || current?.session !== expected.session || !current.server || ["blocked", "loading", "recovery"].includes(current.status) || current.server.recovery_requires_confirmation || fresh.recovery_requires_confirmation || fresh.workspace_id !== current.server.workspace_id || fresh.restore_epoch !== current.server.restore_epoch) return;
      const previous = identity.current;
      if (!previous || previous.session !== current.session || previous.workspace !== fresh.workspace_id || previous.restore !== fresh.restore_epoch) resetDiagnostics();
      identity.current = {session:current.session, workspace:fresh.workspace_id, restore:fresh.restore_epoch};
      gate.awaitingRead = false; resumeDiagnostics();connectLog(fresh.workspace_id,fresh.restore_epoch);
    } catch { /* Keep quarantine; an ordinary CAS ACK cannot release this barrier. */ }
  }, []);
  useLayoutEffect(() => {
    if (!working) return;
    const gate = barrier.current;
    if (gate.restoring || !working.server || ["blocked", "loading", "recovery"].includes(working.status) || working.server.recovery_requires_confirmation) {suspendDiagnostics(); return;}
    if (gate.awaitingRead) {suspendDiagnostics(); void verify(); return;}
    const next = {session: working.session, workspace: working.server.workspace_id, restore: working.server.restore_epoch};
    const previous = identity.current;
    if (!previous || previous.session !== next.session || previous.workspace !== next.workspace || previous.restore !== next.restore) resetDiagnostics();
    identity.current = next; resumeDiagnostics();connectLog(next.workspace,next.restore);
  }, [working?.session, working?.server?.workspace_id, working?.server?.restore_epoch, working?.status, readbackRevision, verify]);
  useLayoutEffect(() => {
    const pause = () => {barrier.current.epoch++; barrier.current.awaitingRead = true; suspendDiagnostics();};
    const start = () => {barrier.current.restoring = true; pause();};
    const finish = () => {barrier.current.restoring = false; barrier.current.awaitingRead = true; recheckIdentity();};
    const check = () => {if (barrier.current.awaitingRead) void verify();};
    const invalidate = (event: Event) => {
      if ((event as CustomEvent<{confirmed?: boolean}>).detail?.confirmed === true) {identity.current = null; resetDiagnostics();}
      pause();
    };
    window.addEventListener("workspace-invalidated", invalidate);
    window.addEventListener("workspace-restore-start", start);
    window.addEventListener("workspace-restore-finish", finish);
    window.addEventListener("diagnostic-workspace-check", check);
    return () => {barrier.current.epoch++; window.removeEventListener("workspace-invalidated", invalidate); window.removeEventListener("workspace-restore-start", start); window.removeEventListener("workspace-restore-finish", finish); window.removeEventListener("diagnostic-workspace-check", check); resetDiagnostics();};
  }, [verify]);
  return <AaosDialog title="运行诊断" description="集中查看连接状态、错误原因、技术详情和执行记录。简要问题记录保存在各自工作区；手动详细回执仅保留在当前会话。" open={open} onOpenChange={value => {if (!value) closeDiagnostics();}} onCloseAutoFocus={event => {event.preventDefault(); restoreDiagnosticFocus();}} contentClassName="diagnostic-center">
    <button type="button" aria-label="关闭运行诊断" onClick={closeDiagnostics}>关闭运行诊断</button>
    <DiagnosticConsole />
  </AaosDialog>;
}
