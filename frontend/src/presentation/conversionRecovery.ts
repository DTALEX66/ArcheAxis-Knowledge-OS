export type ConversionRecovery = {
  reason: "asr_model_missing" | "asr_model_incomplete";
  title: string;
  summary: string;
};

const record = (value: unknown): Record<string, unknown> | null =>
  value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;

/** Explain only a known error bound to the displayed failed job and attempt. */
export function conversionRecovery(status: unknown): ConversionRecovery | null {
  const row = record(status);
  if (!row || row.state !== "failed" || typeof row.job_id !== "string" || !row.job_id
    || !Number.isSafeInteger(row.attempt) || Number(row.attempt) < 1 || typeof row.error !== "string") return null;
  try {
    const response = record(JSON.parse(row.error));
    const error = record(response?.error);
    if (!response || response.schema !== "archeaxis.worker-response/v1" || response.type !== "job_result"
      || response.status !== "failed" || response.job_id !== row.job_id || response.attempt !== row.attempt
      || typeof response.request_id !== "string" || !response.request_id
      || row.request_id === null || row.request_id !== undefined && response.request_id !== row.request_id
      || !error || error.code !== "AAK-WORKER-003" || typeof error.message !== "string" || typeof error.retryable !== "boolean") return null;
    if (error.message.startsWith("ASR model directory not found: ")) return {
      reason: "asr_model_missing", title: "缺少语音转写模型", summary: "缺少语音转写模型，本次转写未完成。",
    };
    if (error.message.startsWith("ASR model directory has no model.bin: ")) return {
      reason: "asr_model_incomplete", title: "语音转写模型不完整", summary: "语音转写模型文件不完整，本次转写未完成。",
    };
  } catch { /* Unknown/malformed errors keep the existing neutral diagnosis. */ }
  return null;
}
