import { useEffect, useRef, useState } from "react";
import { assertCoreDto, type FileFormatQualificationDto } from "../api/generated/core-contract";
import { RawReceiptButton } from "./DiagnosticConsole";

export type FormatQualificationCommand = (operation: "source_job_format_qualification", payload: Record<string, unknown>) => Promise<unknown>;
export type FormatIdentity = { sourceId: string; sourceRevision: string; jobId: string; attempt: number | null; jobState: string };
const labels = { store: "原件保管", preview: "预览", extract: "内容提取", edit: "原生编辑", export: "导出", roundtrip: "原格式往返" } as const;
const qualificationStatus = { RECORDED: "已记录", AVAILABLE: "已声明可用", QUALIFIED: "已核实", FAILED: "处理失败", CANCELLED: "已取消", NOT_EXECUTED: "尚未执行", UNVERIFIED: "尚未核实" } as const;
function qualificationScope(scope: string): string {
  if (scope.startsWith("ORIGINAL_CAS_REFERENCE")) return "仅记录原件引用，未重新审计完整性";
  if (scope.startsWith("DERIVED_TEXT_PROJECTION")) return "仅限派生文字预览，原格式视觉效果未核实";
  if (scope.startsWith("DECLARED_JOB_CAPABILITY_ONLY")) return "仅限本次内容提取，质量与损失需另行核对";
  if (scope.startsWith("SOURCE_NATIVE_EDIT")) return "原格式编辑未核实；普通文档编辑独立进行";
  if (scope.startsWith("ORIGINAL_BYTES_ONLY")) return "仅限导出原文件字节";
  if (scope.startsWith("NATIVE_FORMAT_EDIT_EXPORT_REIMPORT")) return "原格式编辑后回导尚未核实";
  return "适用范围尚未核实，请查看详细信息";
}

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
    <button disabled={state === "reading" || !/^[a-f0-9]{64}$/.test(identity.sourceRevision)} onClick={() => void read()}>查看此文件操作结果</button>
    {state === "reading" ? <p role="status">正在读取此来源与任务的资格…</p> : null}
    {state === "failed" ? <p role="alert">暂时无法确认文件操作结果；请刷新任务状态后重试。</p> : null}
    <dl>{Object.entries(labels).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{qualificationStatus[shown?.operations[key as keyof typeof labels].status ?? "UNVERIFIED"]}；{shown ? qualificationScope(shown.operations[key as keyof typeof labels].scope) : "尚无本次证据"}</dd></div>)}</dl>
    {error ? <p>本次任务失败原因：{error}</p> : null}
    {shown ? <>
      <p>损失登记：{shown.loss.status === "unknown" ? "尚未核实" : shown.loss.status === "none_reported" ? "本次回执未报告损失，不代表无损" : "已报告损失"}；数量 {shown.loss.reported_count ?? "未知"}。</p>
      {shown.outputs_capped ? <p>结果只覆盖已显示的部分内容；其余尚未核实。</p> : null}<p>{shown.evidence_scope.startsWith("PERSISTED_CORE_EXECUTION") ? "结论仅限本次已保存的任务，不代表其他文件、已安装界面或人工验收。" : "适用范围尚未核实，请查看详细信息。"}</p><RawReceiptButton label="文件操作资格与输出详细信息" category="data" payload={shown}/>
    </> : <p>尚无匹配当前来源、修订与尝试的资格证据。</p>}
  </section>;
}
