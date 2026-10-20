import React from 'react';
import { DockviewReact, themeDark, type DockviewReadyEvent } from 'dockview-react';
import 'dockview-react/dist/styles/dockview.css';

/** Offline source recipe: actual object/session stores and layout persistence are supplied by FE06/BE02. */
export function DockviewIntegrationRecipe({onReady}: {onReady:(event:DockviewReadyEvent)=>void}) {
  return <div style={{height:'100%',minHeight:400}}><DockviewReact theme={themeDark} components={{materialReference:()=> <div style={{padding:24}}>材质与停靠参考；业务内容由正式对象服务提供。</div>}} onReady={onReady}/></div>;
}
