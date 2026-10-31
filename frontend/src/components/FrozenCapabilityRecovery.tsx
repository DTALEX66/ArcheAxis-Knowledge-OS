import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { JobAdmissionRefusal } from "../api/client";
import { jobAdmissionRefusal } from "../api/jobAdmission";
import { readCapabilityDecision, readCapabilityPermission } from "../api/capabilitySettings";
import type { FolderAttempt } from "../presentation/folderIngestExecution";
import { capabilityOperationName } from "../presentation/capabilityCenter";
import { jobKindLabel } from "../presentation/labels";
import { RawReceiptButton } from "./DiagnosticConsole";

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
  const capabilityName=proof.capability==="text.extract"?jobKindLabel(proof.capability):capabilityOperationName(proof.capability);
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
      setMessage(actual ? "该能力已启用，并已重新核对工作区设置。本次处理记录保留；请另点原任务的重试按钮，不会自动执行。" : "该能力仍未启用，并已重新核对工作区设置。本次处理记录保留；如需继续，请先启用此能力。" );
    } catch {
      if (belongs()) { setNeedsRead(true); setMessage(writeSent ? "能力设置结果待确认，可能已保存。本次处理记录保留；请先核对设置，不会自动重发或执行。" : "能力设置结果待确认；未发送启用请求。本次处理记录保留，请先核对设置。" ); }
    } finally {
      flight.current = false;
      if (belongs()) { setBusy(false); callbacks.current.onBusyChange(false); }
    }
  }
  if (!valid) return null;
  return <section aria-label="处理能力恢复"><p>本地服务已确认本次处理请求未受理，当时“{capabilityName}”未启用。如需继续，请先启用，再手动重试原任务；启用仅改变当前工作区设置，不会自动执行。</p>
    <button disabled={disabled || busy || needsRead || enabled} onClick={()=>void decide(true)}>{`启用${capabilityName}`}</button>
    <button disabled={disabled || busy} onClick={()=>void decide(false)}>{`核对${capabilityName}设置`}</button>
    <RawReceiptButton label="未受理请求与能力记录" payload={{proof,attempt}}/>
    {message?<p role="status">{message}</p>:null}
  </section>;
}
