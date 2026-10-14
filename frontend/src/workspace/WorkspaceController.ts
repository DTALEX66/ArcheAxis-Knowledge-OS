import { assertLayoutDto, type LayoutDock, type LayoutLayout, type LayoutSnapshot } from "../api/generated/layout-contract";
import type { LayoutTransport } from "./layoutPort";
export const layoutPresets:Record<LayoutLayout["preset_id"],LayoutLayout>={
 default:{schema_version:1,preset_id:"default",registered_panels:["01"],dock_tree:{kind:"tabs",panels:["01"],active:"01"},floating_bounds:{}},
 reading:{schema_version:1,preset_id:"reading",registered_panels:["03","17"],dock_tree:{kind:"split",axis:"horizontal",ratio:0.7,first:{kind:"tabs",panels:["03"],active:"03"},second:{kind:"tabs",panels:["17"],active:"17"}},floating_bounds:{}},
 research:{schema_version:1,preset_id:"research",registered_panels:["05","03"],dock_tree:{kind:"split",axis:"horizontal",ratio:0.5,first:{kind:"tabs",panels:["05"],active:"05"},second:{kind:"tabs",panels:["03"],active:"03"}},floating_bounds:{}},
 learning:{schema_version:1,preset_id:"learning",registered_panels:["06","13"],dock_tree:{kind:"split",axis:"vertical",ratio:0.65,first:{kind:"tabs",panels:["06"],active:"06"},second:{kind:"tabs",panels:["13"],active:"13"}},floating_bounds:{}},
};
/** Layout owns preferences only; no document/AI writes, clear, cancel, or draft mutation. */
export class WorkspaceController {
 snapshot:LayoutSnapshot|null=null; pending:LayoutLayout|null=null; status="布局尚未读回";
 private generation=0;private saving=false;
 constructor(private transport:LayoutTransport,private changed:()=>void=()=>{},private identity?:{workspace_id:string;restore_epoch:string}){}
 async read():Promise<LayoutSnapshot>{const generation=++this.generation;const result=await this.transport.read();if(generation!==this.generation)throw new Error("布局读回已失效");if(this.identity&&(result.workspace_id!==this.identity.workspace_id||result.restore_epoch!==this.identity.restore_epoch))throw new Error("布局读回身份与当前工作区不一致");this.snapshot=result;this.status=result.recovery_reason?`布局需要确认恢复：${result.recovery_reason}`:"布局已读回";this.changed();return result;}
 stage(layout:LayoutLayout):void{this.pending=assertLayoutDto<LayoutLayout>("Layout",structuredClone(layout));this.status="当前布局未保存";this.changed();}
 async save():Promise<void>{if(this.saving)throw new Error("布局正在保存");if(!this.snapshot||!this.pending)throw new Error("请先读回布局");if(this.snapshot.recovery_reason)throw new Error("请先明确恢复布局");const base=this.snapshot,sent=this.pending,generation=this.generation;this.saving=true;
  try{const result=await this.transport.write(base,sent);if(generation!==this.generation||result.workspace_id!==base.workspace_id||result.restore_epoch!==base.restore_epoch||result.device_id!==base.device_id||result.revision!==base.revision+1)throw new Error("布局回执身份或版本变化；当前布局保留");this.snapshot=result;if(this.pending===sent)this.pending=null;this.status="布局已保存";}
  catch(error){this.status=error instanceof Error?error.message:"布局保存未确认";throw error;}finally{this.saving=false;this.changed();}
 }
 async recover(width:number,height:number):Promise<LayoutSnapshot>{if(!this.snapshot||this.saving)throw new Error("请先读回布局");const base=this.snapshot,generation=++this.generation;const result=await this.transport.recover(base,width,height);if(generation!==this.generation||result.workspace_id!==base.workspace_id||result.device_id!==base.device_id||result.restore_epoch!==base.restore_epoch||result.revision!==base.revision+1)throw new Error("布局恢复回执未确认");this.snapshot=result;this.status="布局恢复已读回；资料和会话保留";this.changed();return result;}
 invalidate():void{++this.generation;this.snapshot=null;this.status="工作区已变化；布局需要重新读回";this.changed();}
}
export function panelsIn(tree:LayoutDock):string[]{return tree.kind==="empty"?[]:tree.kind==="tabs"?tree.panels:[...panelsIn(tree.first),...panelsIn(tree.second)];}
