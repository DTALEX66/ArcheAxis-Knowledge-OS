// Recheck finite measurement fields at the UI boundary; never retain provider text.
export type MachineFailureDiagnostics = Record<string, unknown>;
export function readMachineFailureDiagnostics(value: unknown): MachineFailureDiagnostics | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const raw=value as Record<string,unknown>, out:MachineFailureDiagnostics={};
  for (const key of ["requested_model","observed_model"]) {
    const v=raw[key];
    if (v===null || typeof v==="string" && /^[A-Za-z0-9_.:/@+-]{1,256}$/.test(v)) out[key]=v;
  }
  for (const [key,choices] of Object.entries({finish_reason:["stop","length","tool_calls","function_call","content_filter","error"],answer_source:["content","reasoning_content","response","none"],request_stage:["service_discovery","model_request","response_deadline","worker_deadline"],request_phase:["http_open","body_read","json_parse","response_validation"],error_type:["HTTPError","URLError","TimeoutError","ConnectionError","OSError","ValueError","TypeError","KeyError","IndexError","JSONDecodeError"]})) {
    const v=raw[key]; if(typeof v==="string" && choices.includes(v)) out[key]=v;
  }
  for(const key of ["max_tokens","timeout_s"]) {
    const v=raw[key];if(typeof v==="number" && Number.isSafeInteger(v) && v>0)out[key]=v;
  }
  for(const key of ["prompt_utf8_bytes","serialized_request_bytes","response_bytes"]) {
    const v=raw[key];if(typeof v==="number" && Number.isSafeInteger(v) && v>=0)out[key]=v;
  }
  for(const key of ["elapsed_s","discovery_elapsed_s","http_open_elapsed_s","body_read_elapsed_s","json_parse_elapsed_s"]) {
    const elapsed=raw[key];
    if(typeof elapsed==="number" && Number.isFinite(elapsed) && elapsed>=0 && elapsed<=Number.MAX_SAFE_INTEGER)out[key]=elapsed;
  }
  const status=raw.http_status;
  if(typeof status==="number" && Number.isInteger(status) && status>=100 && status<=599)out.http_status=status;
  const usage=raw.usage;
  if(usage && typeof usage==="object" && !Array.isArray(usage)) {
    const safe:Record<string,number>={};
    for(const key of ["input_tokens","output_tokens","total_tokens"]) {
      const v=(usage as Record<string,unknown>)[key];if(typeof v==="number" && Number.isSafeInteger(v) && v>=0)safe[key]=v;
    }
    if(Object.keys(safe).length)out.usage=safe;
  }
  return Object.keys(out).length?out:undefined;
}

/** 只解释有明确失败终态的有限原因；不从任意服务端文本猜测结果。 */
export function modelTimeoutMessage(reason: unknown): string | undefined {
  return typeof reason==="string" && ["MODEL_CALL_TIMEOUT","WORKER_TIMEOUT","material_model_timeout","conversation_model_timeout"].includes(reason)
    ? "模型调用超时，未生成可用回答；原请求已保留，没有自动重试。" : undefined;
}
