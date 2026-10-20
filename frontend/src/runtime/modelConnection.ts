import type { ModelProfile } from "../api/generated/model-configuration-contract";

// Inventory-only diagnosis. No inference, configuration writes or credential lookup.
export async function readModelInventory(profile: Pick<ModelProfile, "endpoint" | "protocol">, signal: AbortSignal): Promise<string[]> {
  signal.throwIfAborted();
  const url = new URL(profile.endpoint);
  if (url.protocol !== "http:" || !["127.0.0.1", "[::1]"].includes(url.hostname) || url.username || url.password || url.search || url.hash) {
    throw new Error("连接诊断仅支持无凭据、无查询参数的 HTTP 数值 loopback 地址。");
  }
  const invoke=window.__TAURI__?.core?.invoke;
  if(invoke){
    let result:unknown;
    try {result=await invoke("model_inventory_read",{request:{endpoint:profile.endpoint,protocol:profile.protocol}});}
    catch(error){
      signal.throwIfAborted();
      const failure=error&&typeof error==="object"?error as Record<string,unknown>:{};
      if(failure.code==="HTTP_FAILURE"&&Number.isInteger(failure.status)&&Number(failure.status)>=100&&Number(failure.status)<=599)throw new Error(`目录读取失败：HTTP ${failure.status}`);
      throw new Error("本地目录读取未完成；请核对服务后重试，配置草稿保留。");
    }
    signal.throwIfAborted();
    const value=result&&typeof result==="object"?result as Record<string,unknown>:{};
    if(value.schema!=="archeaxis.local-model-inventory/v1"||value.inference_status!=="NOT_EXECUTED"||value.loaded_status!=="UNKNOWN"
      ||!Array.isArray(value.models)||value.models.length>256||value.models.some(name=>typeof name!=="string"||!name.trim()||new TextEncoder().encode(name).length>256||/[\u0000-\u001f\u007f-\u009f]/.test(name))){
      throw new Error("模型目录响应格式不正确；未确认模型清单。");
    }
    return value.models as string[];
  }
  const base = url.pathname.replace(/\/+$/, "");
  url.pathname = profile.protocol === "ollama" ? `${base}/api/tags` : `${base.endsWith("/v1") ? base : `${base}/v1`}/models`;
  const response = await fetch(url.href, { method: "GET", credentials: "omit", redirect: "error", signal });
  if (!response.ok) throw new Error(`目录读取失败：HTTP ${response.status}`);
  const data: unknown = await response.json();
  const key = profile.protocol === "ollama" ? "models" : "data";
  const identity = profile.protocol === "ollama" ? "name" : "id";
  const rows: unknown = data && typeof data === "object" ? (data as Record<string, unknown>)[key] : undefined;
  if (!Array.isArray(rows) || rows.some(row => !row || typeof row !== "object" || typeof row[identity] !== "string" || !row[identity].trim())) {
    throw new Error("响应格式不正确：模型目录及名称必须符合所选协议。");
  }
  return rows.map(row => row[identity] as string);
}

export async function diagnoseModelConnection(profile: ModelProfile, signal: AbortSignal): Promise<string> {
  const names = await readModelInventory(profile, signal);
  if (!profile.model.trim() || !names.includes(profile.model)) throw new Error("目录已读取，所选模型不在目录中；请核对模型名称。");
  return "目录读取成功，已找到所选模型；尚未验证推理或回答质量。";
}
