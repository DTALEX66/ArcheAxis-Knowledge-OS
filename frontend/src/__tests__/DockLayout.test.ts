import {afterEach,beforeEach,describe,expect,it,vi} from "vitest";
import { createDockview } from "dockview";
import { captureLayout,restoreLayout } from "../workspace/dockLayout";
import {layoutPresets} from "../workspace/WorkspaceController";
import type {LayoutLayout} from "../api/generated/layout-contract";
function dock(){const element=document.createElement("div");document.body.appendChild(element);const api=createDockview(element,{createComponent:()=>({element:document.createElement("div"),init(){}})});api.layout(1000,700);return {api,dispose:()=>{api.dispose();element.remove();}};}
// Explicit synthetic viewport geometry, only for serialization behavior.
beforeEach(()=>{vi.spyOn(HTMLElement.prototype,"getBoundingClientRect").mockImplementation(function(this:HTMLElement){const x=parseFloat(this.style.left)||0,y=parseFloat(this.style.top)||0,width=this.style.width.endsWith("%")?1000:parseFloat(this.style.width)||1000,height=this.style.height.endsWith("%")?700:parseFloat(this.style.height)||700;return {x,y,left:x,top:y,right:x+width,bottom:y+height,width,height,toJSON(){return {};}};});});
afterEach(()=>vi.restoreAllMocks());
describe("real Dockview finite layout serialization",()=>{
 it("preserves the full active object presentation in a docked tab group",()=>{
  const d=dock(),identity={workspaceId:"workspace",epoch:"initial",locked:false};try{
   d.api.addPanel({id:"03",component:"business"});d.api.addPanel({id:"document.doc_a",component:"business",position:{referencePanel:"03",direction:"within"}});
   const saved=captureLayout(d.api,"reading",identity);expect(saved.dock_tree).toEqual({kind:"tabs",panels:["03","document.doc_a"],active:"document.doc_a"});
   // 合同保存组内活动标签；恢复初期全局 activeGroup 可以尚未指定。
   restoreLayout(d.api,saved,identity);expect(d.api.getPanel("document.doc_a")!.group.activePanel?.id).toBe("document.doc_a");expect(captureLayout(d.api,"reading",identity)).toEqual(saved);
  }finally{d.dispose();}
 });
 it("persists empty, all-floating grouped tabs, stable object bindings and lock in v2",()=>{
  const d=dock(),identity={workspaceId:"workspace",epoch:"initial",locked:true};try{
   expect(captureLayout(d.api,"default",identity).dock_tree).toEqual({kind:"empty"});
   d.api.addPanel({id:"document.doc_a",component:"business"});d.api.addPanel({id:"03",component:"business",position:{referencePanel:"document.doc_a",direction:"within"}});
   d.api.addFloatingGroup(d.api.getPanel("03")!.group,{position:{left:30,top:40},width:600,height:400});
   const saved=captureLayout(d.api,"reading",identity);expect(saved.schema_version).toBe(2);if(saved.schema_version!==2)throw new Error("schema");
   expect(saved.locked).toBe(true);expect(saved.dock_tree).toEqual({kind:"empty"});expect(saved.floating_groups![0].tree).toMatchObject({kind:"tabs",panels:["document.doc_a","03"]});expect(saved.instance_bindings!["document.doc_a"].session_key).toBe("workspace:initial:document:doc_a");
   expect(()=>restoreLayout(d.api,saved,{workspaceId:"foreign",epoch:"initial"})).toThrow("身份");restoreLayout(d.api,saved,identity);expect(captureLayout(d.api,"reading",identity)).toEqual(saved);
  }finally{d.dispose();}
 });
 it("restores each actual preset and captures its finite tree and ratio without persisting business params",()=>{
  for(const preset of Object.values(layoutPresets)){const d=dock();try{restoreLayout(d.api,preset);const saved=captureLayout(d.api,preset.preset_id);expect(saved.registered_panels.sort()).toEqual([...preset.registered_panels].sort());expect(saved.dock_tree).toEqual(preset.dock_tree);expect(JSON.stringify(saved)).not.toContain("params");}finally{d.dispose();}}
 });
 it("roundtrips single-panel floating bounds, redocking and close without unknown components",()=>{
  const d=dock();try{restoreLayout(d.api,layoutPresets.reading);const p=d.api.getPanel("17")!;d.api.addFloatingGroup(p,{position:{left:24,top:24},width:600,height:440});const saved=captureLayout(d.api,"reading");expect((saved.schema_version===2?saved.floating_groups![0].bounds:null)).toEqual({x:24,y:24,width:600,height:440});expect(saved.dock_tree).toEqual({kind:"tabs",panels:["03"],active:"03"});restoreLayout(d.api,saved);expect(captureLayout(d.api,"reading")).toEqual(saved);d.api.getPanel("17")!.api.moveTo({group:d.api.getPanel("03")!.group,position:"right"});expect(captureLayout(d.api,"reading").schema_version).toBe(2);}finally{d.dispose();}
 });
 it("rejects duplicated canonical business families before native layout replacement",()=>{
  const d=dock();try{restoreLayout(d.api,layoutPresets.default);const invalid:LayoutLayout={...layoutPresets.default,registered_panels:["02","03"],dock_tree:{kind:"tabs",panels:["02","03"],active:"03"}};expect(()=>restoreLayout(d.api,invalid)).toThrow("重复");expect(d.api.panels.map(p=>p.id)).toEqual(["01"]);}finally{d.dispose();}
 });
 it("roundtrips nested orthogonal splits and refuses unknown components",()=>{
  const layout:LayoutLayout={schema_version:1,preset_id:"research",registered_panels:["03","05","17"],dock_tree:{kind:"split",axis:"horizontal",ratio:0.5,first:{kind:"split",axis:"vertical",ratio:0.6,first:{kind:"tabs",panels:["03"],active:"03"},second:{kind:"tabs",panels:["05"],active:"05"}},second:{kind:"tabs",panels:["17"],active:"17"}},floating_bounds:{}};
  const d=dock();try{restoreLayout(d.api,layout);expect(captureLayout(d.api,"research").dock_tree).toEqual(layout.dock_tree);d.api.addPanel({id:"unknown",component:"arbitrary"});expect(()=>captureLayout(d.api,"research")).toThrow("未知");}finally{d.dispose();}
 });
});
