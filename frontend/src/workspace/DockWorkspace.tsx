import { useEffect,useLayoutEffect,useMemo,useRef,useState,type ComponentProps } from "react";
import { createPortal } from "react-dom";
import { DockviewReact,themeDark,type IDockviewPanelProps,type DockviewReadyEvent,type DockviewApi } from "dockview-react";
import "dockview-react/dist/styles/dockview.css";
import "./dock-workspace.css";
import { SpaceView } from "../spaces/SpaceView";
import { findUiPage,defaultUiPage } from "../presentation/uiPages";
import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import { PanelRegistry,businessPanelId,documentPanelId,documentObjectId,presentationPanelId } from "./PanelRegistry";
import { DocumentBusinessSessions,DocumentBusinessProvider } from "./documentSessions";
import { WorkspaceController,layoutPresets } from "./WorkspaceController";
import { desktopLayoutTransport } from "./layoutPort";
import { captureLayout,restoreLayout } from "./dockLayout";
type Props=ComponentProps<typeof SpaceView>;
export function DockWorkspace(props:Props){
 const working=useOptionalCoreWorkingState(),workspaceId=working?.server?.workspace_id??"unverified",epoch=working?.server?.restore_epoch??"initial";
 return <WorkspaceDockSession key={`${workspaceId}:${epoch}`} {...props} workspaceId={workspaceId} epoch={epoch}/>;
}
function WorkspaceDockSession(props:Props&{workspaceId:string;epoch:string}){
 const {workspaceId,epoch,...view}=props;
 const page=view.uiPageId??defaultUiPage(view.spaceId),id=businessPanelId(view.selectedCapabilityId?"17":page);
 const registry=useMemo(()=>new PanelRegistry(workspaceId,epoch),[workspaceId,epoch]);
 const documentSessions=useMemo(()=>new DocumentBusinessSessions(workspaceId,epoch),[workspaceId,epoch]);
 const working=useOptionalCoreWorkingState();
 if(view.initialDocumentId&&working){const binding=registry.documentSession(view.initialDocumentId,working.session);registry.host("03").dataset.objectSessionKey=binding.key;}
 const parking=useRef<HTMLDivElement>(null),api=useRef<DockviewApi|null>(null),hydrating=useRef(false),mounted=useRef(true);
 const [version,refresh]=useState(0),[ready,setReady]=useState(false),[locked,setLocked]=useState(false),[preset,setPreset]=useState<keyof typeof layoutPresets>("default"),[notice,setNotice]=useState("");
 const lockedRef=useRef(locked);lockedRef.current=locked;
 const presetRef=useRef(preset);presetRef.current=preset;
 const retained=useRef(new Map<string,Props>());retained.current.set(id,view);
 const controller=useMemo(()=>new WorkspaceController(desktopLayoutTransport(),()=>{if(mounted.current)refresh(v=>v+1);},{workspace_id:workspaceId,restore_epoch:epoch}),[]);
 const current=useRef(view);current.current=view;
 const components=useMemo(()=>({business:function BusinessSlot(panel:IDockviewPanelProps){const slot=useRef<HTMLDivElement>(null);const panelId=presentationPanelId(panel.api.id);useLayoutEffect(()=>{if(slot.current)slot.current.appendChild(registry.host(panelId));return()=>{if(parking.current)registry.park(panelId,parking.current);};},[panelId]);return <div className="dock-slot" ref={slot}/>;}}),[registry]);
 const ensure=(panelId:string)=>{if(!retained.current.has(panelId)){const objectId=documentObjectId(panelId),pageId=objectId?"03":panelId,definition=findUiPage(pageId);retained.current.set(panelId,{...current.current,uiPageId:pageId,spaceId:definition?.space??"workspace",selectedCapabilityId:null,initialDocumentId:objectId,navigation:undefined,onTrail:undefined});}registry.host(panelId);};
 const apply=(layout:typeof layoutPresets.default)=>{if(!api.current)return;layout.registered_panels.map(presentationPanelId).forEach(ensure);hydrating.current=true;try{restoreLayout(api.current,layout,{workspaceId,epoch});setPreset(layout.preset_id);setLocked(layout.schema_version===2?layout.locked??false:false);refresh(v=>v+1);}finally{hydrating.current=false;}};
 const open=(panelId:string,direction?:"right"|"below")=>{const dock=api.current;if(!dock)return;ensure(panelId);const existing=dock.getPanel(panelId);if(existing){existing.api.setActive();return;}dock.addPanel({id:panelId,component:"business",title:documentObjectId(panelId)?`文档 ${documentObjectId(panelId)}`:findUiPage(panelId)?.label??panelId,params:{pageId:documentObjectId(panelId)?"03":panelId},...(direction&&dock.activePanel?{position:{referencePanel:dock.activePanel.id,direction}}:{})});refresh(v=>v+1);};
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;controller.invalidate();};},[controller]);
 useEffect(()=>{if(ready)open(id);},[id,ready,page]);
 useEffect(()=>{if(!ready||workspaceId==="unverified")return;let alive=true;void controller.read().then(result=>{if(!alive)return;if(result.workspace_id!==workspaceId||result.restore_epoch!==epoch)throw new Error("布局属于其他工作区；保留当前视图");if([...Object.values(result.layout.floating_bounds),...(result.layout.schema_version===2?result.layout.floating_groups??[]:[]).map(g=>g.bounds)].some(b=>b.x+b.width>window.innerWidth||b.y+b.height>window.innerHeight))throw new Error("屏幕范围已变化；请确认布局恢复以调整浮动面板");if(!result.recovery_reason){apply(result.layout);const latest=current.current;open(businessPanelId(latest.selectedCapabilityId?"17":latest.uiPageId??defaultUiPage(latest.spaceId)));}}).catch(error=>{if(alive)setNotice(String(error.message??error));});return()=>{alive=false;};},[ready,workspaceId,epoch]);
 const onReady=(event:DockviewReadyEvent)=>{api.current=event.api;open(id);event.api.onDidLayoutChange(()=>{if(hydrating.current||!mounted.current)return;try{controller.stage(captureLayout(event.api,presetRef.current,{workspaceId,epoch,locked:lockedRef.current}));setNotice("");}catch(error){setNotice(String((error as Error).message));}});setReady(true);};
 const action=(operation:()=>void|Promise<unknown>)=>{try{Promise.resolve(operation()).catch(error=>setNotice(String(error.message??error)));}catch(error){setNotice(String((error as Error).message));}};
 const split=(direction:"right"|"below")=>{const candidate=id==="17"?"03":"17";open(candidate,direction);};
 const active=()=>api.current?.activePanel;
 return <section className="dock-workspace" aria-label="自由布局工作区" data-layout-version={version}>
  <div className="dock-toolbar" role="toolbar" aria-label="布局操作">
   <button onClick={()=>split("right")} disabled={locked}>左右分栏</button><button onClick={()=>split("below")} disabled={locked}>上下分栏</button>
   <button disabled={locked||!(view.initialDocumentId??working?.state.active_document)} onClick={()=>action(()=>open(documentPanelId(view.initialDocumentId??working!.state.active_document!),"right"))}>并排打开当前文档</button>
   <button onClick={()=>{const panel=active();if(panel)api.current?.removePanel(panel);}}>关闭当前视图</button>
   {[...retained.current.keys()].filter(panelId=>documentObjectId(panelId)).map(panelId=><button key={panelId} onClick={()=>open(panelId,"right")}>重开文档 {documentObjectId(panelId)}</button>)}
   <button disabled={locked} onClick={()=>action(()=>{const panel=active();if(panel)api.current?.addFloatingGroup(panel,{position:{left:24,top:24},width:600,height:440});})}>浮动当前面板</button>
   <button disabled={locked} onClick={()=>action(()=>{const panel=active(),target=api.current?.panels.find(p=>p.group!==panel?.group);if(panel&&target)panel.api.moveTo({group:target.group,position:"right"});})}>停靠当前面板</button>
   <button onClick={()=>{const panel=active();if(panel)panel.api.isMaximized()?panel.api.exitMaximized():panel.api.maximize();}}>缩放当前面板</button>
   <button aria-pressed={locked} onClick={()=>{const next=!locked;setLocked(next);api.current?.updateOptions({locked:next,disableDnd:next});}}>锁定布局</button>
   <select aria-label="布局预设" value={preset} disabled={locked} onChange={e=>action(()=>apply(layoutPresets[e.target.value as keyof typeof layoutPresets]))}>{Object.keys(layoutPresets).map(name=><option key={name}>{name}</option>)}</select>
   <button disabled={locked} onClick={()=>action(()=>apply(layoutPresets.default))}>重置视图布局</button>
   <button onClick={()=>action(async()=>{if(api.current)controller.stage(captureLayout(api.current,preset,{workspaceId,epoch,locked}));await controller.save();})}>保存布局</button>
   <button onClick={()=>action(async()=>{await controller.read();setNotice("已读回版本；当前视图保留。请明确应用读回布局。");})}>读回布局版本</button>
   <button disabled={locked} onClick={()=>action(()=>{if(controller.snapshot){apply(controller.snapshot.layout);setNotice("已应用读回布局；业务会话保留。");}})}>应用读回布局</button>
   <button disabled={locked} onClick={()=>action(async()=>{const recovered=await controller.recover(Math.max(320,window.innerWidth),Math.max(240,window.innerHeight));apply(recovered.layout);})}>确认布局恢复</button>
  </div>
  <p role="status">{notice||controller.status} · 关闭面板仅关闭视图；草稿与已提交任务保留。</p>
  <div className="dock-surface"><DockviewReact components={components} theme={themeDark} onReady={onReady} locked={locked} disableDnd={locked}/></div>
  <div hidden aria-hidden="true" ref={parking}/>
  {[...retained.current].map(([panelId,saved])=>createPortal(<DocumentBusinessProvider sessions={documentSessions} viewId={registry.key(panelId)} revealOwner={owner=>{const ownerPanel=[...retained.current.keys()].find(candidate=>registry.key(candidate)===owner);if(ownerPanel)open(ownerPanel);}}><SpaceView {...saved} onTrail={panelId===id?saved.onTrail:undefined}/></DocumentBusinessProvider>,registry.host(panelId),registry.key(panelId)))}
 </section>;
}
