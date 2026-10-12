import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { JobAdmissionRefusal } from "../api/client";
import { jobAdmissionRefusal } from "../api/jobAdmission";
import { readCapabilityDecision, readCapabilityPermission } from "../api/capabilitySettings";
import type { FolderAttempt } from "../presentation/folderIngestExecution";

/** Remain beside the frozen request: enabling never navigates, clears it or executes it. */
export function FrozenCapabilityRecovery({proof,attempt,source,kind,disabled,current,onBusyChange}: {
  proof: JobAdmissionRefusal; attempt: FolderAttempt; source: string; kind?: string;
  disabled: boolean; current: () => boolean; onBusyChange: (busy: boolean) => void;
}) {
  const bound = jobAdmissionRefusal(proof, attempt);
  const valid = !!bound && bound.input_ref === source && (kind === undefined || bound.kind === kind);
  const identity = JSON.stringify([attempt.job_id,attempt.request_id,attempt.body,source,kind,proof.capability]);
  const identityRef = useRef(identity); identityRef.current = identity;
  const mounted = useRef(true), flight = useRef(false), callbacks = useRef({current,onBusyChange});
  callbacks.current = {current,onBusyChange};
  const [busy,setBusy] = useState(false), [message,setMessage] = useState("");
  const [needsRead,setNeedsRead] = useState(false), [enabled,setEnabled] = useState(false);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  const belongs = () => mounted.current && identityRef.current === identity && callbacks.current.current();
  async function decide(write: boolean) {
    if (!valid || disabled || flight.current || !belongs() || write && (needsRead || enabled)) return;
    flight.current = true; setBusy(true); callbacks.current.onBusyChange(true); setMessage("");
    let writeSent = false;
    try {
      const before = readCapabilityPermission(await coreCommand("capabilities_list"), proof.capability);
      if (!belongs()) return;
      if (write && !before) {
        writeSent = true;
        readCapabilityDecision(await coreCommand("capability_set_enabled", {capability:proof.capability,enabled:true}), proof.capability, true);
        if (!belongs()) return;
        if (!readCapabilityPermission(await coreCommand("capabilities_list"), proof.capability)) throw new Error("enable readback not confirmed");
        if (!belongs()) return;
      }
      const actual = write ? true : before;
      setEnabled(actual); setNeedsRead(false);
      setMessage(actual ? "该能力已启用，工作区设置已读回。原冻结请求保留；请另点同请求重试。" : "该能力仍禁用，工作区设置已读回。原冻结请求保留，可显式启用。" );
    } catch {
      if (belongs()) { setNeedsRead(true); setMessage(writeSent ? "能力设置 UNKNOWN，可能已写入；原冻结请求保留。请先核对能力设置，不自动重发或执行。" : "能力设置 UNKNOWN；未发送启用请求。原冻结请求保留，请重新核对能力设置。" ); }
    } finally {
      flight.current = false;
      if (belongs()) { setBusy(false); callbacks.current.onBusyChange(false); }
    }
  }
  if (!valid) return null;
  return <section aria-label="冻结请求的能力恢复"><p>Core 已证明原请求未受理；拒绝时 {proof.capability} 已禁用。启用只改变该工作区能力设置，不会自动执行。</p>
    <button disabled={disabled || busy || needsRead || enabled} onClick={()=>void decide(true)}>启用 {proof.capability}</button>
    <button disabled={disabled || busy} onClick={()=>void decide(false)}>核对 {proof.capability} 设置</button>
    {message?<p role="status">{message}</p>:null}
  </section>;
}
