import { Orientation, type DockviewApi, type SerializedDockview } from "dockview";
import { assertLayoutDto, type LayoutDock, type LayoutLayout } from "../api/generated/layout-contract";
import { businessPanelId,documentObjectId,presentationPanelId } from "./PanelRegistry";
import { findUiPage } from "../presentation/uiPages";
type Node={type:"leaf"|"branch";size?:number;data:any};
const axis=(orientation:Orientation):"horizontal"|"vertical"=>orientation===Orientation.HORIZONTAL?"horizontal":"vertical";
const other=(orientation:Orientation)=>orientation===Orientation.HORIZONTAL?Orientation.VERTICAL:Orientation.HORIZONTAL;
/** Only the finite Core tree is persisted, never arbitrary Dockview components or params. */
export function captureLayout(api:DockviewApi,preset_id:LayoutLayout["preset_id"],identity?:{workspaceId:string;epoch:string;locked:boolean}):LayoutLayout{
 const json=api.toJSON();
 if(Object.entries(json.panels).some(([id,panel])=>(!findUiPage(id)&&!documentObjectId(id))||panel.contentComponent!=="business"))throw new Error("布局含未知面板组件；当前视图保留");
 if(json.popoutGroups?.length||json.edgeGroups)throw new Error("此布局包含暂不支持保存的窗口；当前视图已保留");
 const walk=(node:Node,orientation:Orientation):LayoutDock=>{
  if(node.type==="leaf"){const panels=(node.data.views as string[]).map(presentationPanelId);if(!panels.length)throw new Error("空布局不能保存；请重新打开页面");return {kind:"tabs",panels,active:presentationPanelId(node.data.activeView??panels[0])};}
  const children=node.data as Node[];if(!children.length)return {kind:"empty"};
  const fold=(index:number):LayoutDock=>{const first=walk(children[index],other(orientation));if(index===children.length-1)return first;const total=children.slice(index).reduce((sum,n)=>sum+(n.size??1),0);return {kind:"split",axis:axis(orientation),ratio:Math.max(0.1,Math.min(0.9,(children[index].size??1)/total)),first,second:fold(index+1)};};
  return fold(0);
 };
 const dock_tree=walk(json.grid.root,json.grid.orientation),floating_bounds:LayoutLayout["floating_bounds"]={};
 const floating_groups=(json.floatingGroups??[]).map(group=>{if(!group.data||group.grid)throw new Error("嵌套浮动网格暂不可保存");const p=group.position;return {tree:{kind:"tabs" as const,panels:group.data.views.map(presentationPanelId),active:presentationPanelId(group.data.activeView??group.data.views[0])},bounds:{x:Math.max(0,"left" in p?p.left:api.width-p.right-p.width),y:Math.max(0,"top" in p?p.top:api.height-p.bottom-p.height),width:p.width,height:p.height}};});
 const ids=api.panels.map(p=>presentationPanelId(p.id));
 const instance_bindings:Record<string,{page_id:"03";object_id:string;session_key:string}>={};
 for(const id of ids){const object_id=documentObjectId(id);if(object_id){if(!identity||identity.workspaceId==="unverified")throw new Error("对象布局需真实工作区身份");instance_bindings[id]={page_id:"03",object_id,session_key:`${identity.workspaceId}:${identity.epoch}:document:${object_id}`};}}
 const layout={schema_version:2,preset_id,registered_panels:ids,dock_tree,floating_bounds,instance_bindings,floating_groups,locked:identity?.locked??false};
 try{return assertLayoutDto<LayoutLayout>("Layout",layout);}catch{throw new Error("暂时无法保存此布局；请停靠面板或调整大小后再试");}
}
export function restoreLayout(api:DockviewApi,layout:LayoutLayout,identity?:{workspaceId:string;epoch:string}):void{
 assertLayoutDto("Layout",layout);
 if(layout.schema_version===2){for(const [id,b] of Object.entries(layout.instance_bindings??{})){if(id!==`document.${b.object_id}`||b.page_id!=="03"||!identity||b.session_key!==`${identity.workspaceId}:${identity.epoch}:document:${b.object_id}`)throw new Error("布局业务会话身份不一致；请明确恢复");}}
 // Normalize singleton business families before hydration. Multiple legacy IDs
 // sharing a family cannot silently create concurrent document/model writers.
 const normalized=layout.registered_panels.map(presentationPanelId);
 if(new Set(normalized).size!==normalized.length)throw new Error("旧布局存在重复业务宿主；请明确恢复为默认布局");
 let sequence=0;
 const panels:SerializedDockview["panels"]={};
 const leaf=(ids:string[],active:string,size:number):Node=>({type:"leaf",size,data:{id:`restored_${++sequence}`,views:ids.map(presentationPanelId),activeView:presentationPanelId(active)}});
 const walk=(tree:LayoutDock,parent:Orientation,size:number):Node=>{
  if(tree.kind==="empty")return {type:"branch",size,data:[]};
  if(tree.kind==="tabs")return leaf(tree.panels,tree.active,size);
  const own=tree.axis==="horizontal"?Orientation.HORIZONTAL:Orientation.VERTICAL;
  const node:Node={type:"branch",size,data:[walk(tree.first,other(own),size*tree.ratio),walk(tree.second,other(own),size*(1-tree.ratio))]};
  return own===parent?node:{type:"branch",size,data:[node]};
 };
 for(const id of normalized)panels[id]={id,contentComponent:"business",title:findUiPage(id)?.label??id,params:{pageId:documentObjectId(id)?"03":id}};
 const orientation=layout.dock_tree.kind==="split"&&layout.dock_tree.axis==="vertical"?Orientation.VERTICAL:Orientation.HORIZONTAL;
 const built=walk(layout.dock_tree,orientation,1000);
 const root=built.type==="branch"?built:{type:"branch" as const,size:1000,data:[built]};
 const floatingGroups=Object.entries(layout.floating_bounds).map(([id,b])=>({data:{id:`float_${++sequence}`,views:[businessPanelId(id)],activeView:businessPanelId(id)},position:{left:b.x,top:b.y,width:b.width,height:b.height}}));
 if(layout.schema_version===2){for(const group of layout.floating_groups??[]){if(group.tree.kind!=="tabs")throw new Error("嵌套浮动树需显式恢复");floatingGroups.push({data:{id:`float_${++sequence}`,views:group.tree.panels.map(presentationPanelId),activeView:presentationPanelId(group.tree.active)},position:{left:group.bounds.x,top:group.bounds.y,width:group.bounds.width,height:group.bounds.height}});}}
 api.fromJSON({grid:{root:root as SerializedDockview["grid"]["root"],orientation,width:1000,height:700},panels,floatingGroups});
}
