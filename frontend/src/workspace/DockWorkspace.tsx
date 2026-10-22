import { useCallback,useContext,useEffect,useLayoutEffect,useMemo,useRef,useState,useSyncExternalStore,type ComponentProps } from "react";
import { createPortal } from "react-dom";
import { DockviewReact,DockviewDefaultTab,themeDark,type IDockviewPanelProps,type IDockviewPanelHeaderProps,type IDockviewHeaderActionsProps,type DockviewReadyEvent,type DockviewApi } from "dockview-react";
import "dockview-react/dist/styles/dockview.css";
import "./dock-workspace.css";
import { SpaceView } from "../spaces/SpaceView";
import { StitchResearchOutlet } from "../components/StitchWorkspaceChrome";
import { findUiPage,defaultUiPage } from "../presentation/uiPages";
import { useOptionalCoreWorkingState } from "../presentation/useCoreWorkingState";
import type {SourceJourneyTarget} from "../presentation/sourceJourney";
import { PanelRegistry,businessPanelId,documentPanelId,documentObjectId,presentationPanelId } from "./PanelRegistry";
import { DocumentBusinessSessions,DocumentBusinessProvider } from "./documentSessions";
import { WorkspaceController,layoutPresets } from "./WorkspaceController";
import { desktopLayoutTransport } from "./layoutPort";
import { captureLayout,restoreLayout,layoutFitsSurface,tabbedLayout } from "./dockLayout";
type ViewProps=ComponentProps<typeof SpaceView>;
export type DockNavigationTarget=Pick<ViewProps,"uiPageId"|"spaceId"|"initialDocumentId"|"selectedCapabilityId">&{panelId:string};
type Props=ViewProps&{activePanelId?:string;navigationRevision?:number;onActivateView?:(target:DockNavigationTarget)=>boolean};
function AccessibleDockTab(props:IDockviewPanelHeaderProps){
 const middleDown=useRef(false);
 // 标签内部只保留标签内容；关闭操作放在 tablist 的同级区域。
 return <DockviewDefaultTab {...props} hideClose onPointerDown={event=>{middleDown.current=event.button===1;if(middleDown.current)event.preventDefault();}} onPointerUp={event=>{if(middleDown.current&&event.button===1)props.api.close();middleDown.current=false;}} onPointerCancel={()=>{middleDown.current=false;}} onPointerLeave={()=>{middleDown.current=false;}}/>;
}
function DockGroupActions({activePanel}:IDockviewHeaderActionsProps){
 const title=useSyncExternalStore(useCallback((notify:()=>void)=>{const subscription=activePanel?.api.onDidTitleChange(()=>notify());return()=>subscription?.dispose();},[activePanel]),()=>activePanel?.title??"",()=>activePanel?.title??"");
 return <button type="button" className="dock-group-close" disabled={!activePanel} aria-label={`关闭视图 ${title}`} title="关闭此组当前视图；保留草稿" onClick={event=>{
  const workspace=event.currentTarget.closest(".dock-workspace");
  activePanel?.api.close();
  queueMicrotask(()=>{if(document.activeElement===document.body||!document.activeElement?.isConnected){
   const tabs=[...workspace?.querySelectorAll<HTMLElement>('[role="tab"][aria-selected="true"]')??[]];
   (tabs.find(tab=>tab.getClientRects().length>0)??workspace?.querySelector<HTMLElement>(".dock-layout-options summary"))?.focus();
  }});
 }}>×</button>;
}
export function DockWorkspace(props:Props){
 const working=useOptionalCoreWorkingState(),workspaceId=working?.server?.workspace_id??"unverified",epoch=working?.server?.restore_epoch??"initial";
 return <WorkspaceDockSession key={`${workspaceId}:${epoch}`} {...props} workspaceId={workspaceId} epoch={epoch}/>;
}
function WorkspaceDockSession(props:Props&{workspaceId:string;epoch:string}){
 const researchOutlet=useContext(StitchResearchOutlet);
 const {workspaceId,epoch,activePanelId,navigationRevision=0,onActivateView,...view}=props;
 const page=view.uiPageId??defaultUiPage(view.spaceId),id=activePanelId??businessPanelId(view.selectedCapabilityId?"17":page);
 const registry=useMemo(()=>new PanelRegistry(workspaceId,epoch),[workspaceId,epoch]);
 const documentSessions=useMemo(()=>new DocumentBusinessSessions(workspaceId,epoch),[workspaceId,epoch]);
 const working=useOptionalCoreWorkingState();
 if(view.initialDocumentId&&working&&businessPanelId(page)==="03"){const binding=registry.documentSession(view.initialDocumentId,working.session);registry.host(id).dataset.objectSessionKey=binding.key;}
 const parking=useRef<HTMLDivElement>(null),api=useRef<DockviewApi|null>(null),hydrating=useRef(false),mounted=useRef(true);
 const surface=useRef<HTMLDivElement>(null),surfaceSize=useRef({width:0,height:0}),responsiveLayout=useRef<typeof layoutPresets.default|null>(null);
 const [compactFallback,setCompactFallback]=useState(false);
 const [version,refresh]=useState(0),[ready,setReady]=useState(false),[locked,setLocked]=useState(false),[preset,setPreset]=useState<keyof typeof layoutPresets>("default"),[notice,setNotice]=useState("");
 const lockedRef=useRef(locked);lockedRef.current=locked;
 const presetRef=useRef(preset);presetRef.current=preset;
 const retained=useRef(new Map<string,ViewProps>());retained.current.set(id,view);
 const acceptance=useRef(onActivateView);acceptance.current=onActivateView;
 const controlled=useRef(0),acceptedPanel=useRef(id),interaction=useRef(0);
 const rollbackPending=useRef(false);
 const quiet=(operation:()=>void)=>{controlled.current++;try{operation();}finally{controlled.current--;}};
 const activations=useRef(new Map<string,number>());
 const controller=useMemo(()=>new WorkspaceController(desktopLayoutTransport(),()=>{if(mounted.current)refresh(v=>v+1);},{workspace_id:workspaceId,restore_epoch:epoch}),[]);
 const current=useRef(view);current.current=view;
 const [sourceTarget,setSourceTarget]=useState<SourceJourneyTarget>();
 const [pendingSource,setPendingSource]=useState<{target:SourceJourneyTarget;documentId?:string}>();
 const changeSource=useCallback((target?:SourceJourneyTarget)=>{
  if(target)setPendingSource({target,documentId:current.current.initialDocumentId});
  else {setPendingSource(undefined);setSourceTarget(undefined);}
 },[]);
 // App navigation guards run synchronously in the requesting event. Commit only
 // after the accepted page change; a refused request must not alter a hidden reader
 // or survive to a later, unrelated visit to page 03.
 useEffect(()=>{if(pendingSource){if(page==="03"&&pendingSource.documentId===view.initialDocumentId)setSourceTarget(pendingSource.target);setPendingSource(undefined);}},[pendingSource,page,view.initialDocumentId]);
 useLayoutEffect(()=>{setPendingSource(undefined);setSourceTarget(undefined);},[view.initialDocumentId]);
 useEffect(()=>{const clear=(event:Event)=>{if((event as CustomEvent<{confirmed?:boolean}>).detail?.confirmed)changeSource(undefined);};window.addEventListener("workspace-invalidated",clear);return()=>window.removeEventListener("workspace-invalidated",clear);},[changeSource]);
 const components=useMemo(()=>({business:function BusinessSlot(panel:IDockviewPanelProps){const slot=useRef<HTMLDivElement>(null);const panelId=presentationPanelId(panel.api.id);useLayoutEffect(()=>{const container=slot.current;if(container)container.appendChild(registry.host(panelId));const activate=()=>{activations.current.set(panelId,(activations.current.get(panelId)??0)+1);refresh(v=>v+1);};const visibility=panel.api.onDidVisibilityChange(event=>{if(event.isVisible)activate();else refresh(v=>v+1);});if(panel.api.isVisible)activate();return()=>{visibility.dispose();if(parking.current&&registry.host(panelId).parentElement===container)registry.park(panelId,parking.current);};},[panelId]);return <div className="dock-slot" ref={slot}/>;}}),[registry]);
 const ensure=(panelId:string)=>{if(!retained.current.has(panelId)){const objectId=documentObjectId(panelId),pageId=objectId?"03":panelId,definition=findUiPage(pageId);retained.current.set(panelId,{...current.current,uiPageId:pageId,spaceId:definition?.space??"workspace",selectedCapabilityId:null,initialDocumentId:objectId,navigation:undefined,onTrail:undefined});}registry.host(panelId);};
 // 宿主身份只决定保留的业务会话；标签使用该宿主最后获准展示的页面。
 const titleFor=(panelId:string)=>{const objectId=documentObjectId(panelId);if(objectId)return `文档 ${objectId}`;const saved=retained.current.get(panelId);return findUiPage(saved?.selectedCapabilityId?"17":saved?.uiPageId??panelId)?.label??panelId;};
 const updateTitles=()=>{if(!api.current)return;quiet(()=>{for(const panel of api.current!.panels){const title=titleFor(panel.id);if(panel.title!==title)panel.api.setTitle(title);}});};
 const expandedPreference=()=>{
  const saved=responsiveLayout.current,dock=api.current;
  // Close/add events may still be coalesced when the next resize/save arrives.
  if(saved&&dock&&(saved.registered_panels.length!==dock.panels.length||saved.registered_panels.some(id=>!dock.getPanel(id)))){responsiveLayout.current=null;setCompactFallback(false);}
  return responsiveLayout.current;
 };
 const apply=(layout:typeof layoutPresets.default,notify=true)=>{
  if(!api.current)return;layout.registered_panels.map(presentationPanelId).forEach(ensure);
  const {width,height}=surfaceSize.current,active=api.current.activePanel?.id;
  const compact=width>0&&height>0&&!layoutFitsSurface(layout,width,height)&&tabbedLayout(layout)!==layout;
  hydrating.current=true;try{restoreLayout(api.current,compact?tabbedLayout(layout,active):layout,{workspaceId,epoch});responsiveLayout.current=compact?layout:null;setCompactFallback(compact);updateTitles();setPreset(layout.preset_id);setLocked(layout.schema_version===2?layout.locked??false:false);refresh(v=>v+1);}finally{hydrating.current=false;}if(notify)synchronize();
 };
 const fitWorkspace=()=>{
  const dock=api.current,{width,height}=surfaceSize.current;if(!dock||hydrating.current||width<=0||height<=0)return;
  const previous=expandedPreference(),active=dock.activePanel?.id;
  const layout=previous??captureLayout(dock,presetRef.current,{workspaceId,epoch,locked:lockedRef.current});
  if(!previous&&tabbedLayout(layout)===layout)return;
  if(previous?!layoutFitsSurface(previous,width,height):layoutFitsSurface(layout,width,height))return;
  apply(layout,false);if(active)open(active,undefined,false);
 };
 const fitCurrent=useRef(fitWorkspace);fitCurrent.current=fitWorkspace;
 useEffect(()=>{if(!ready||!surface.current)return;const observer=new ResizeObserver(entries=>{
  const entry=entries[0];if(!entry)return;surfaceSize.current={width:entry.contentRect.width,height:entry.contentRect.height};
  try{fitCurrent.current();}catch(error){setNotice(String((error as Error).message));}
 });observer.observe(surface.current);return()=>observer.disconnect();},[ready]);
 const open=(panelId:string,direction?:"right"|"below",notify=true)=>{
  const dock=api.current;if(!dock)return;ensure(panelId);
   const existing=dock.getPanel(panelId);if(existing){const title=titleFor(panelId),changed=existing.title!==title;quiet(()=>{if(changed)existing.api.setTitle(title);if(direction){const target=dock.activeGroup===existing.group&&existing.group.panels.length===1?dock.groups.find(group=>group!==existing.group):dock.activeGroup;if(target){const options={group:target,position:direction==="below"?"bottom" as const:"right" as const};if(target!==existing.group)existing.group.api.moveTo(options);else existing.api.moveTo(options);}}existing.api.setActive();});if(changed||direction)refresh(v=>v+1);if(notify)synchronize();else acceptedPanel.current=panelId;return;}
  // 布局刚恢复时 activeGroup 可能尚未建立；已有组仍是默认标签归宿。
  // 只有明确的分栏操作才创建相邻组，不让普通导航意外压窄阅读区。
  const group=dock.activeGroup??dock.groups[0];
   quiet(()=>{dock.addPanel({id:panelId,component:"business",title:titleFor(panelId),params:{pageId:documentObjectId(panelId)?"03":panelId},...(group?{position:{referenceGroup:group,direction:direction??"within"}}:{})});});
  refresh(v=>v+1);
   if(notify)synchronize();else acceptedPanel.current=panelId;
 };
 // 只采纳已存在视图的上下文；不能把激活反馈重新解释成打开普通页面。
 const synchronize=()=>{
  const panel=api.current?.activePanel;if(!panel||hydrating.current||controlled.current||rollbackPending.current||!mounted.current)return;
  if(panel.id===acceptedPanel.current)return;
  const saved=retained.current.get(panel.id);if(!saved)return;
  interaction.current++;
  const previous=acceptedPanel.current;
  const accepted=acceptance.current?.({panelId:panel.id,uiPageId:saved.uiPageId,spaceId:saved.spaceId,initialDocumentId:saved.initialDocumentId,selectedCapabilityId:saved.selectedCapabilityId})!==false;
  if(accepted)acceptedPanel.current=panel.id;
  else{
   // 原生关闭已移除标签时恢复同一保留宿主；不会丢弃草稿或重新挂载业务。
   rollbackPending.current=true;
   queueMicrotask(()=>{rollbackPending.current=false;if(!mounted.current||acceptedPanel.current!==previous)return;open(previous,undefined,false);setNotice("视图切换未获确认，已恢复原视图；草稿保留。");});
  }
  refresh(v=>v+1);
 };
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;controller.invalidate();};},[controller]);
 useEffect(()=>{if(ready)open(id,undefined,false);},[id,ready,page,navigationRevision]);
 useEffect(()=>{if(!ready||workspaceId==="unverified")return;let alive=true;const started=interaction.current;void controller.read().then(result=>{if(!alive)return;if(result.workspace_id!==workspaceId||result.restore_epoch!==epoch)throw new Error("布局属于其他工作区；保留当前视图");if([...Object.values(result.layout.floating_bounds),...(result.layout.schema_version===2?result.layout.floating_groups??[]:[]).map(g=>g.bounds)].some(b=>b.x+b.width>window.innerWidth||b.y+b.height>window.innerHeight))throw new Error("屏幕范围已变化；请确认布局恢复以调整浮动面板");if(!result.recovery_reason){if(started!==interaction.current){setNotice("已读取已保存的布局；保留当前视图。需要时可选择“应用已保存布局”。");return;}apply(result.layout,false);const latest=current.current;open(businessPanelId(latest.selectedCapabilityId?"17":latest.uiPageId??defaultUiPage(latest.spaceId)),undefined,false);}}).catch(error=>{if(alive)setNotice(String(error.message??error));});return()=>{alive=false;};},[ready,workspaceId,epoch]);
 const onReady=(event:DockviewReadyEvent)=>{api.current=event.api;open(id,undefined,false);event.api.onDidActivePanelChange(()=>synchronize());event.api.onDidRemovePanel(()=>{if(!hydrating.current&&!controlled.current)interaction.current++;refresh(v=>v+1);});event.api.onDidLayoutChange(()=>{if(hydrating.current||!mounted.current)return;try{
  const layout=captureLayout(event.api,presetRef.current,{workspaceId,epoch,locked:lockedRef.current});
  // Tab selection is presentation only. A deliberate panel addition/close replaces
  // the temporary projection, so growing the window cannot resurrect closed tabs.
  controller.stage(expandedPreference()??layout);setNotice("");
 }catch(error){setNotice(String((error as Error).message));}});setReady(true);};
 const action=(operation:()=>void|Promise<unknown>)=>{interaction.current++;try{Promise.resolve(operation()).catch(error=>setNotice(String(error.message??error)));}catch(error){setNotice(String((error as Error).message));}};
 const split=(direction:"right"|"below")=>action(()=>{const candidate=id==="17"?"03":"17";open(candidate,responsiveLayout.current?undefined:direction);fitCurrent.current();});
 const active=()=>api.current?.activePanel;
 // Navigation already exposes these singleton pages. Keep tabs for every real
 // multi-group, floating or object view; compacting never closes a business host.
 const compactReader=page==="03"&&api.current?.groups.length===1&&api.current.groups[0].api.location.type==="grid"&&api.current.panels.every(panel=>panel.id==="01"||panel.id==="03");
 return <section className="dock-workspace" aria-label="自由布局工作区" data-layout-version={version} data-panel-count={api.current?.panels.length??1} data-compact-reader={compactReader||undefined} data-responsive-tabs={compactFallback||undefined}>
  <details className="dock-layout-options"><summary>布局与面板</summary><div className="dock-toolbar" role="toolbar" aria-label="布局操作">
   <button onClick={()=>split("right")} disabled={locked}>左右分栏</button><button onClick={()=>split("below")} disabled={locked}>上下分栏</button>
   <button disabled={locked||!(view.initialDocumentId??working?.state.active_document)} onClick={()=>action(()=>open(documentPanelId(view.initialDocumentId??working!.state.active_document!),"right"))}>并排打开当前文档</button>
   <button onClick={()=>{const panel=active();if(panel)api.current?.removePanel(panel);}}>关闭当前视图</button>
   {[...retained.current.keys()].filter(panelId=>documentObjectId(panelId)).map(panelId=><button key={panelId} onClick={()=>open(panelId,"right")}>重开文档 {documentObjectId(panelId)}</button>)}
   <button disabled={locked||compactFallback} onClick={()=>action(()=>{const panel=active();if(panel)api.current?.addFloatingGroup(panel,{position:{left:24,top:24},width:600,height:440});fitCurrent.current();})}>浮动当前面板</button>
   <button disabled={locked} onClick={()=>action(()=>{const panel=active(),target=api.current?.panels.find(p=>p.group!==panel?.group);if(panel&&target)panel.api.moveTo({group:target.group,position:"right"});})}>停靠当前面板</button>
   <button onClick={()=>{interaction.current++;const panel=active();if(panel)panel.api.isMaximized()?panel.api.exitMaximized():panel.api.maximize();}}>缩放当前面板</button>
   <button aria-pressed={locked} onClick={()=>{interaction.current++;const next=!locked;setLocked(next);const expanded=expandedPreference();if(expanded?.schema_version===2)responsiveLayout.current={...expanded,locked:next};api.current?.updateOptions({locked:next,disableDnd:next||compactFallback});}}>锁定布局</button>
   <select aria-label="布局预设" value={preset} disabled={locked} onChange={e=>action(()=>apply(layoutPresets[e.target.value as keyof typeof layoutPresets]))}>{Object.keys(layoutPresets).map(name=><option key={name}>{name}</option>)}</select>
   <button disabled={locked} onClick={()=>action(()=>apply(layoutPresets.default))}>重置视图布局</button>
   <button onClick={()=>action(async()=>{if(api.current)controller.stage(expandedPreference()??captureLayout(api.current,preset,{workspaceId,epoch,locked}));await controller.save();})}>保存布局</button>
   <button onClick={()=>action(async()=>{await controller.read();setNotice("已读取已保存的布局；当前视图保留。请确认是否应用。");})}>读取已保存布局</button>
   <button disabled={locked} onClick={()=>action(()=>{if(controller.snapshot){apply(controller.snapshot.layout);setNotice("已应用保存的布局；草稿和任务保留。");}})}>应用已保存布局</button>
   <button disabled={locked} onClick={()=>action(async()=>{const recovered=await controller.recover(Math.max(320,window.innerWidth),Math.max(240,window.innerHeight));apply(recovered.layout);})}>确认布局恢复</button>
  </div><p role="status">{controller.status} · 关闭面板仅关闭视图；草稿与已提交任务保留。</p></details>
  {notice?<p role="alert">{notice}</p>:null}
  {compactFallback?<p role="status">当前面板空间不足，已改为标签视图；空间足够时恢复分栏，已保存布局与草稿保留。</p>:null}
  {controller.snapshot?.recovery_reason?<p role="alert">布局需要确认恢复。请展开“布局与面板”核对并确认恢复。</p>:null}
  <div className="dock-surface" ref={surface}><DockviewReact components={components} defaultTabComponent={AccessibleDockTab} rightHeaderActionsComponent={DockGroupActions} theme={themeDark} onReady={onReady} locked={locked} disableDnd={locked||compactFallback}/></div>
  <div hidden aria-hidden="true" ref={parking}/>
  {[...retained.current].map(([panelId,saved])=>createPortal(<DocumentBusinessProvider sessions={documentSessions} viewId={registry.key(panelId)} revealOwner={owner=>{const ownerPanel=[...retained.current.keys()].find(candidate=>registry.key(candidate)===owner);if(ownerPanel)open(ownerPanel);}}><StitchResearchOutlet.Provider value={researchOutlet && !(panelId===id && api.current?.activePanel?.id===panelId && api.current.getPanel(panelId)?.api.isVisible) ? {...researchOutlet,host:null} : researchOutlet}><SpaceView {...saved} sourceJourney={{target:panelId==="03"?sourceTarget:undefined,onChange:changeSource}} activationRevision={activations.current.get(panelId)??0} onTrail={panelId===id?saved.onTrail:undefined}/></StitchResearchOutlet.Provider></DocumentBusinessProvider>,registry.host(panelId),registry.key(panelId)))}
 </section>;
}
