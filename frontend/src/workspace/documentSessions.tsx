import {createContext,useContext,useEffect,useSyncExternalStore,type ReactNode} from "react";
/** Runtime business ownership. Draft content remains in CoreWorkingStateSession. */
export class DocumentBusinessSessions {
 private records=new Map<string,{key:string;owner:string|null;inFlight:boolean;releaseAfterWrite:boolean}>();
 private listeners=new Set<()=>void>();private revision=0;
 constructor(readonly workspaceId:string,readonly restoreEpoch:string){}
 subscribe=(listener:()=>void)=>{this.listeners.add(listener);return()=>{this.listeners.delete(listener);};};
 snapshot=()=>this.revision;
 private publish(){++this.revision;for(const listener of this.listeners)listener();}
 session(objectId:string){let session=this.records.get(objectId);if(!session){session={key:`${this.workspaceId}:${this.restoreEpoch}:document:${objectId}`,owner:null,inFlight:false,releaseAfterWrite:false};this.records.set(objectId,session);}return session;}
 acquire(objectId:string,viewId:string):boolean{const session=this.session(objectId);if(session.owner&&session.owner!==viewId)return false;session.releaseAfterWrite=false;if(!session.owner){session.owner=viewId;this.publish();}return true;}
 release(objectId:string,viewId:string):void{const session=this.session(objectId);if(session.owner!==viewId)return;if(session.inFlight)session.releaseAfterWrite=true;else{session.owner=null;this.publish();}}
 async write<T>(objectId:string,viewId:string,action:()=>Promise<T>):Promise<T>{const session=this.session(objectId);if(session.owner!==viewId)throw new Error("同一文档已有写入视图；此视图只读，草稿保留");if(session.inFlight)throw new Error("同一文档已有保存进行中");session.inFlight=true;this.publish();try{return await action();}finally{session.inFlight=false;if(session.releaseAfterWrite){session.owner=null;session.releaseAfterWrite=false;}this.publish();}}
}
const Context=createContext<{sessions:DocumentBusinessSessions;viewId:string;revealOwner?:(viewId:string)=>void}|null>(null);
const subscribeEmpty=()=>()=>{};const snapshotEmpty=()=>0;
export function DocumentBusinessProvider({sessions,viewId,revealOwner,children}:{sessions:DocumentBusinessSessions;viewId:string;revealOwner?:(viewId:string)=>void;children:ReactNode}){return <Context.Provider value={{sessions,viewId,revealOwner}}>{children}</Context.Provider>;}
export function useDocumentWriteLease(objectId:string|undefined){
 const context=useContext(Context);const revision=useSyncExternalStore(context?.sessions.subscribe??subscribeEmpty,context?.sessions.snapshot??snapshotEmpty,snapshotEmpty);
 useEffect(()=>{if(!objectId||!context)return;context.sessions.acquire(objectId,context.viewId);return()=>context.sessions.release(objectId,context.viewId);},[objectId,context?.sessions,context?.viewId]);
 const session=objectId&&context?context.sessions.session(objectId):null;
 // Subscribe while another owner leaves this object; the retained readonly view
 // can acquire a now-free lease, never steal a live owner's draft or write.
 useEffect(()=>{if(objectId&&context&&session?.owner===null)context.sessions.acquire(objectId,context.viewId);},[revision,objectId,context?.sessions,context?.viewId]);
 return {ownerId:context?.viewId,sessionKey:session?.key,canWrite:!context||!objectId||session?.owner===context.viewId,canRevealOwner:!!context?.revealOwner&&!!session?.owner,revealOwner:()=>{if(session?.owner)context?.revealOwner?.(session.owner);},
  write:<T,>(action:()=>Promise<T>)=>objectId&&context?context.sessions.write(objectId,context.viewId,action):action()};
}
