import { createContext, useContext, useSyncExternalStore, type ReactNode } from "react";
import { CoreWorkingStateSession, type WorkingView } from "./coreWorkingState";
const Context=createContext<CoreWorkingStateSession|null>(null);
const unavailable:WorkingView={state:{drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null},server:null,status:"loading",error:null};
const snapshot=()=>unavailable;
const subscribe=()=>()=>{};
export function CoreWorkingStateProvider({session,children}:{session:CoreWorkingStateSession;children:ReactNode}) {
  return <Context.Provider value={session}>{children}</Context.Provider>;
}
export function useCoreWorkingState() {
  const value=useOptionalCoreWorkingState();
  if(!value)throw new Error("工作状态需要 App 生命周期 provider。");
  return value;
}
export function useOptionalCoreWorkingState() {
  const session=useContext(Context);
  const view=useSyncExternalStore(session?.subscribe??subscribe,session?.getSnapshot??snapshot,session?.getSnapshot??snapshot);
  return session?{session,...view}:null;
}
