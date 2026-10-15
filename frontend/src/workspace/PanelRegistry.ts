import { findUiPage } from "../presentation/uiPages";
import type { CoreWorkingStateSession } from "../presentation/coreWorkingState";
export function businessPanelId(page:string):string{
 if(["02","03","20"].includes(page))return "03";
 if(["13","14","22"].includes(page))return "13";
 if(["17","18"].includes(page))return "17";
 return findUiPage(page)?page:"01";
}
export function documentPanelId(objectId:string):string{if(!/^[A-Za-z0-9_-]{1,128}$/.test(objectId))throw new Error("文档对象身份无效");return `document.${objectId}`;}
export function documentObjectId(panelId:string):string|undefined{const value=panelId.startsWith("document.")?panelId.slice(9):undefined;return value&&/^[A-Za-z0-9_-]{1,128}$/.test(value)?value:undefined;}
export function presentationPanelId(panelId:string):string{return documentObjectId(panelId)?panelId:businessPanelId(panelId);}
/** One retained DOM presentation per business family; closing a Dock tab never disposes it. */
export class PanelRegistry {
 private hosts=new Map<string,HTMLDivElement>();
 private documents=new Map<string,{key:string;session:CoreWorkingStateSession}>();
 constructor(readonly workspaceId:string,readonly epoch:string){}
 key(page:string,objectId?:string):string{return `${this.workspaceId}:${this.epoch}:${presentationPanelId(page)}:${objectId??documentObjectId(page)??"workspace"}`;}
 host(page:string):HTMLDivElement{const id=presentationPanelId(page);let host=this.hosts.get(id);if(!host){host=document.createElement("div");host.className="dock-business-host";host.dataset.sessionKey=this.key(id);this.hosts.set(id,host);}return host;}
 park(page:string,parking:HTMLElement):void{parking.appendChild(this.host(page));}
 documentSession(objectId:string,session:CoreWorkingStateSession):{key:string;session:CoreWorkingStateSession}{let binding=this.documents.get(objectId);if(binding&&binding.session!==session)throw new Error("文档业务会话身份发生变化");if(!binding){binding={key:`${this.workspaceId}:${this.epoch}:document:${objectId}`,session};this.documents.set(objectId,binding);}return binding;}
}
