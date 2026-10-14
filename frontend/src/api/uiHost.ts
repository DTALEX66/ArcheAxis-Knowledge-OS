// Finite v2 native host calls. A request ID is correlation only; no automatic retry.
import { coreCommand } from "./core";
import { ApiError } from "./client";
import { assertCoreDto, type MachineConfigurationDto, type MachineInventoryDto } from "./generated/core-contract";
import { UI_HOST_CONTRACT_DIGEST, assertUiHostRequest, assertUiHostResponse, type UiHostOperation, type UiHostRequest } from "./generated/ui-host-contract";

export async function uiHostRead(operation: UiHostOperation): Promise<Record<string, unknown>> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new ApiError(0, "请在本地桌面应用打开此内容。", "offline");
  const identity = await coreCommand<{workspace_id:string;restore_epoch:string}>("ui_state_read");
  const request: UiHostRequest = { schema:"archeaxis.ui-host-request/v2", contract_digest:UI_HOST_CONTRACT_DIGEST,
    request_id:crypto.randomUUID(), workspace_id:identity.workspace_id, restore_epoch:identity.restore_epoch, operation, input:{} };
  assertUiHostRequest(request);
  const reply:unknown = await invoke("ui_host_command", {request});
  assertUiHostResponse(reply, request);
  if(reply.outcome!=="READ_OK") throw new ApiError(reply.core_status??503, `宿主接口未完成：${reply.reason_code}。`, reply.outcome==="REJECTED"?"unauthorized":"unavailable");
  const body = reply.result_ref!;
  if(operation==="model.configuration.read") return assertCoreDto<MachineConfigurationDto>("MachineConfigurationDto",body);
  if(operation==="model.inventory.read") return assertCoreDto<MachineInventoryDto>("MachineInventoryDto",body);
  if(operation==="capability.catalog.read") {
    if(body.schema!=="archeaxis.capabilities/v1"||!Array.isArray(body.capabilities)||body.capabilities.some(row=>!row||typeof row!=="object"||typeof row.capability!=="string"))throw new Error("HOST_CATALOG_INVALID");
    return body;
  }
  throw new Error("HOST_READ_NOT_ADMITTED");
}
export const readHostCapabilityCatalog = () => uiHostRead("capability.catalog.read");
export const readHostModelInventory = () => uiHostRead("model.inventory.read");
export const readHostModelConfiguration = () => uiHostRead("model.configuration.read");
