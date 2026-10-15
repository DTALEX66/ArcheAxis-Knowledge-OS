import { useEffect, useRef, useState } from "react";
import { assertCoreDto, type FileFormatQualificationDto } from "../api/generated/core-contract";

export type FormatQualificationCommand = (operation: "source_job_format_qualification", payload: Record<string, unknown>) => Promise<unknown>;
export type FormatIdentity = { sourceId: string; sourceRevision: string; jobId: string; attempt: number | null; jobState: string };
const labels = { store: "原件保管", preview: "预览", extract: "内容提取", edit: "原生编辑", export: "导出", roundtrip: "原格式往返" } as const;

export function readFormatQualification(value: unknown, identity: FormatIdentity): FileFormatQualificationDto {
  const dto = assertCoreDto<FileFormatQualificationDto>("FileFormatQualificationDto", value);
  if (!/^[a-f0-9]{64}$/.test(identity.sourceRevision) || dto.source_id !== identity.sourceId
    || dto.source_revision !== identity.sourceRevision || dto.job_id !== identity.jobId
    || dto.attempt !== identity.attempt || dto.job_state !== identity.jobState) throw new Error("资格回执身份或尝试已变化");
  return dto;
}

/** One explicit, bounded read. Caller remounts on source/revision/job/attempt/state changes. */
export function FormatQualificationPanel({ command, identity, error }: { command: FormatQualificationCommand; identity: FormatIdentity; error: string | null }) {
  const [receipt, setReceipt] = useState<FileFormatQualificationDto | null>(null);
  const [state, setState] = useState<"idle" | "reading" | "read" | "failed">("idle");
  const generation = useRef(0), inFlight = useRef(false);
  const identityKey = JSON.stringify(identity);
  const current = useRef(identityKey); current.current = identityKey;
  const [receiptIdentity, setReceiptIdentity] = useState("");
  useEffect(() => { ++generation.current; inFlight.current = false; setReceipt(null); setState("idle"); return () => { ++generation.current; }; }, [identityKey]);
  async function read() {
    if (inFlight.current) return;
    const epoch = ++generation.current, key = identityKey;
    inFlight.current = true; setReceipt(null); setState("reading");
    try {
      const value = await command("source_job_format_qualification", { source_id: identity.sourceId, job_id: identity.jobId });
      const result = readFormatQualification(value, identity);
      if (epoch !== generation.current || current.current !== key) return;
      setReceipt(result); setReceiptIdentity(key); setState("read");
    } catch {
      if (epoch === generation.current && current.current === key) setState("failed");
    } finally { if (epoch === generation.current) inFlight.current = false; }
  }
  const shown = receiptIdentity === identityKey ? receipt : null;
  return <section aria-label="文件六操作资格">
    <h3>文件操作资格</h3>
    <p>每项资格独立。转换成功不代表原生编辑或原格式往返无损；派生文档保存独立进行。</p>
    <button disabled={state === "reading" || !/^[a-f0-9]{64}$/.test(identity.sourceRevision)} onClick={() => void read()}>读取此文件操作回执</button>
    {state === "reading" ? <p role="status">正在读取此来源与任务的资格…</p> : null}
    {state === "failed" ? <p role="alert">资格读回未确认（UNVERIFIED）；请刷新任务状态后重新读取。</p> : null}
    <dl>{Object.entries(labels).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{shown?.operations[key as keyof typeof labels].status ?? "UNVERIFIED"}</dd></div>)}</dl>
    {error ? <p>本次任务失败原因：{error}</p> : null}
    {shown ? <>
      <p>损失登记：{shown.loss.status === "unknown" ? "未知 / UNVERIFIED" : shown.loss.status === "none_reported" ? "本次回执未报告损失，不代表无损" : "已报告损失"}；数量 {shown.loss.reported_count ?? "未知"}。</p>
      <details><summary>查看引擎、身份与输出证据</summary>
        <dl><dt>来源 / 修订</dt><dd>{shown.source_id} / {shown.source_revision}</dd><dt>任务 / attempt</dt><dd>{shown.job_id} / {shown.attempt ?? "未执行"}</dd><dt>Core / 资格版本</dt><dd>{shown.core_version} / {shown.qualification_version}</dd><dt>引擎 / 版本</dt><dd>{shown.engine || "UNVERIFIED"} / {shown.engine_version || "UNVERIFIED"}</dd><dt>损失回执引用</dt><dd>{shown.loss.receipt_ref ?? "UNVERIFIED"}</dd></dl>
        <ul>{Object.entries(labels).map(([key, label]) => <li key={key}>{label}：{shown.operations[key as keyof typeof labels].scope}</li>)}</ul>
        <ul>{shown.outputs.map((output, index) => <li key={index}>{output.kind ?? "未知类型"} · {output.schema ?? "未知schema"} · {output.byte_length ?? "未知"} bytes · SHA-256 {output.sha256 ?? "UNVERIFIED"}</li>)}</ul>
        {shown.outputs_capped ? <p>输出只展示有限窗口，资格不能推及未列证据。</p> : null}
        <p>{shown.evidence_scope}</p>
      </details>
    </> : <p>尚无匹配当前来源、修订与尝试的资格证据。</p>}
  </section>;
}
