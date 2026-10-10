// Version 2 finite recovery commands. No paths, tokens, endpoints or SQL in UI.
function identity(backupId:string,sha:string) {if(!/^[a-f0-9]{32}$/.test(backupId)||!/^[a-f0-9]{64}$/.test(sha))throw new Error("无效备份标识");}
export async function previewWorkspaceRestore(backupId:string,sha:string) {
 identity(backupId,sha);const invoke=window.__TAURI__?.core?.invoke;if(!invoke)throw new Error("本地核心未连接");
 const value=await invoke("workspace_restore_preview",{backupId,expectedSha256:sha});
 if(!value||typeof value!=="object")throw new Error("恢复预检合同无效");
 const r=value as Record<string,unknown>;
 if(r.schema!=="archeaxis.workspace-restore-preview/v2"||r.backup_id!==backupId||r.sha256!==sha||r.verified!==true||r.compatible!==true||typeof r.schema_version!=="string"||!Number.isInteger(r.source_count))throw new Error("恢复预检未通过");
 return r;
}
export async function confirmWorkspaceRestore(backupId:string,sha:string) {
 identity(backupId,sha);const invoke=window.__TAURI__?.core?.invoke;if(!invoke)throw new Error("本地核心未连接");
 const value=await invoke("workspace_restore_confirm",{backupId,expectedSha256:sha});
 if(!value||typeof value!=="object")throw new Error("恢复完成合同无效");
 const r=value as Record<string,unknown>;const readback=r.readback as Record<string,unknown>|undefined;
 if(r.schema!=="archeaxis.workspace-restore-result/v2"||r.backup_id!==backupId||r.restored!==true||r.restarted!==true||readback?.runtime!=="archeaxis-api")throw new Error("恢复或重启读回未确认");
 return r;
}
