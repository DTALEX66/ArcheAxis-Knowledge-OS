// Actual 2026-10-26 missing-resource Core receipt shape. Only identity and local
// path are rebound for isolated UI fixtures; this is not another runtime claim.
export function asrModelFailure(identity: { job_id: string; request_id: string; attempt: number },
  message = "ASR model directory not found: C:/registered/asr (set --model-dir; product-local location consulted: C:/app/runtime/models/asr)") {
  return { schema: "archeaxis.worker-response/v1", type: "job_result", ...identity, protocol_minor: 0,
    status: "failed", outputs: [], measurements: {}, warnings: [],
    error: { code: "AAK-WORKER-003", message, retryable: false } };
}
