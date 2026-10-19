import { assertLayoutDto, type LayoutLayout, type LayoutSnapshot } from "../api/generated/layout-contract";
export type LayoutTransport = {read:()=>Promise<LayoutSnapshot>; write:(base:LayoutSnapshot,layout:LayoutLayout)=>Promise<LayoutSnapshot>; recover:(base:LayoutSnapshot,width:number,height:number)=>Promise<LayoutSnapshot>};
// Fixed, product-owned finite Core routes. No browser persistence or generic transport.
async function command(operation:"layout_read"|"layout_write"|"layout_recover",payload:Record<string,unknown>):Promise<LayoutSnapshot>{
 const invoke=window.__TAURI__?.core?.invoke;if(!invoke)throw new Error("请在桌面应用中保存布局；当前视图仍保留。");
 const raw=await invoke("core_command",{request:{operation,payload}}) as {status:number;body:unknown};
 if(!raw||raw.status<200||raw.status>=300)throw new Error(raw?.status===409?"布局版本冲突；当前视图保留，请重新读取后再决定。":"布局保存未确认；当前视图保留。");
 return assertLayoutDto<LayoutSnapshot>("Snapshot",raw.body);
}
let temporaryDevice:string|undefined;
function deviceId():string{try{const existing=window.localStorage.getItem("aaos.layout.device-id");if(existing&&/^[A-Za-z0-9_-]{1,64}$/.test(existing))return existing;const id=crypto.randomUUID();window.localStorage.setItem("aaos.layout.device-id",id);return id;}catch{return temporaryDevice??=crypto.randomUUID();}}
export function desktopLayoutTransport():LayoutTransport{
 const device_id=deviceId();
 return {read:()=>command("layout_read",{device_id}),write:(base,layout)=>command("layout_write",{body:{workspace_id:base.workspace_id,restore_epoch:base.restore_epoch,device_id,expected_revision:base.revision,layout:assertLayoutDto("Layout",layout)}}),recover:(base,viewport_width,viewport_height)=>command("layout_recover",{body:{workspace_id:base.workspace_id,restore_epoch:base.restore_epoch,device_id,expected_revision:base.revision,viewport_width,viewport_height}})};
}
