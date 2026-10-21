import { coreCommand } from "../api/core";

export type Definition = {version:number;sha256:string;snapshot:{template_id:"T3";version:number;name:string;kind:"first-party-data-only";fields:Record<string,string>;paragraphs:string[]}};
export type DefinitionPin = Definition & {application_epoch:number};
export type TemplateState = {capability:"template.T3";enabled:boolean;installed:boolean;state_epoch:number;definition:Definition;available_definitions:Definition[]};
export type TemplateAction = "enable"|"disable"|"update"|"rollback"|"install"|"uninstall";
export function readableDefinition(value:unknown):value is Definition {
  if(!value||typeof value!=="object")return false;
  const pin=value as Definition, snapshot=pin.snapshot;
  return Number.isSafeInteger(pin.version)&&pin.version>0&&typeof pin.sha256==="string"&&/^[a-f0-9]{64}$/.test(pin.sha256)
    && !!snapshot&&snapshot.template_id==="T3"&&snapshot.version===pin.version&&snapshot.kind==="first-party-data-only"
    &&typeof snapshot.name==="string"&&!!snapshot.fields&&typeof snapshot.fields==="object"&&!Array.isArray(snapshot.fields)
    &&Object.values(snapshot.fields).every(v=>typeof v==="string")&&Array.isArray(snapshot.paragraphs)&&snapshot.paragraphs.every(v=>typeof v==="string");
}
export function readTemplateState(value:unknown):TemplateState {
  const state=value as TemplateState;
  if(!state||state.capability!=="template.T3"||typeof state.enabled!=="boolean"||typeof state.installed!=="boolean"
    ||!Number.isSafeInteger(state.state_epoch)||state.state_epoch<0||!readableDefinition(state.definition)
    ||!Array.isArray(state.available_definitions)||!state.available_definitions.every(readableDefinition)
    ||new Set(state.available_definitions.map(d=>d.version)).size!==state.available_definitions.length
    ||!state.available_definitions.some(d=>d.version===state.definition.version&&d.sha256===state.definition.sha256))throw new Error("模板定义状态未能完整读回；保留原对象。");
  return state;
}
export async function changeTemplate(state:TemplateState,action:TemplateAction,target=state.definition):Promise<TemplateState> {
  const result=await coreCommand<{capability:unknown}>("capability_template_change",{expected_epoch:state.state_epoch,action,version:target.version,sha256:target.sha256});
  const next=readTemplateState(result.capability);
  const installed=action==="uninstall"?false:action==="install"?true:state.installed;
  const enabled=action==="enable"||action==="install"?true:action==="disable"||action==="uninstall"?false:state.enabled;
  if(next.state_epoch!==state.state_epoch+1||next.definition.version!==target.version||next.definition.sha256!==target.sha256||next.installed!==installed||next.enabled!==enabled)throw new Error("模板变更结果未确认；请重新读取后操作。");
  return next;
}
