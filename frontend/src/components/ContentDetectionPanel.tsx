import { useState } from "react";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "./DiagnosticConsole";

type Verdict = { label: string; group: string; score: number; inputSha256: string; modelSha256: string; model: string };

function verdictFrom(loss: unknown): Verdict {
  if (!loss || typeof loss !== "object" || Array.isArray(loss)) throw new Error("invalid loss report");
  const params = (loss as Record<string, unknown>).params;
  const structure = params && typeof params === "object"
    ? (params as Record<string, unknown>).worker_structure : undefined;
  if (!structure || typeof structure !== "object" || Array.isArray(structure)) throw new Error("missing judgement");
  const item = structure as Record<string, unknown>;
  if (item.state !== "detected" || typeof item.label !== "string" || typeof item.group !== "string"
    || typeof item.input_sha256 !== "string" || typeof item.model_score !== "number"
    || !item.model || typeof item.model !== "object" || Array.isArray(item.model)
    || typeof (item.model as Record<string, unknown>).model_sha256 !== "string") {
    throw new Error("missing judgement");
  }
  return {
    label: item.label,
    group: item.group,
    score: item.model_score,
    inputSha256: item.input_sha256,
    modelSha256: String((item.model as Record<string, unknown>).model_sha256),
    model: `${String((item.model as Record<string, unknown>).name ?? "model")}-${String((item.model as Record<string, unknown>).revision ?? "unknown")}`,
  };
}

export function ContentDetectionPanel({ sourceId, name }: { sourceId: string; name: string }) {
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function detect() {
    if (busy) return;
    setBusy(true);
    const jobId = `detect_${crypto.randomUUID()}`;
    try {
      await coreCommand("job_enqueue", { body: { job_id: jobId, kind: "detect", input_ref: sourceId } });
      await coreCommand("job_execute", { job_id: jobId, body: { deadline_ms: 300000 } });
      const state = await coreCommand<unknown>("jobs_get", { job_id: jobId });
      if (!state || typeof state !== "object" || (state as Record<string, unknown>).state !== "succeeded") {
        throw new Error("not settled");
      }
      const raw = await coreCommand<unknown>("job_output", { job_id: jobId, kind: "loss_report" });
      if (!raw || typeof raw !== "object" || typeof (raw as Record<string, unknown>).content !== "string") {
        throw new Error("invalid output");
      }
      setVerdict(verdictFrom(JSON.parse((raw as { content: string }).content)));
      setMessage("");
    }
    catch {
      // A refusal is the answer: the type of these bytes is still unknown to the product, and a
      // failed model call must not be rendered as a verdict of "unknown".
      setVerdict(null);
      setMessage("内容判定未完成或被拒绝；这份字节的类型仍按未知处理，原件未改动。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="内容类型判定">
      <h4>这份文件说不出自己的类型</h4>
      <p>{name} 的扩展名无法命名类型，因此没有可执行的转换通路；原件已按字节保管。</p>
      <button disabled={busy} onClick={() => void detect()}>按字节判定内容类型（模型判定）</button>
      {message ? <p role="status">{message}</p> : null}
      {verdict ? (
        <>
          <p role="status">模型判定：{verdict.label} · 组 {verdict.group} · 分值 {verdict.score.toFixed(4)}</p>
          <p>这是 {verdict.model} 对本次读取字节的判定，不是文件自我声明的类型，也不是已转换正文；分值不是准确率，判定也不改变原件的保管身份。</p>
          <RawReceiptButton label="判定回执与字节摘要" payload={{ input_sha256: verdict.inputSha256, model_sha256: verdict.modelSha256, model: verdict.model }} />
        </>
      ) : null}
    </section>
  );
}
