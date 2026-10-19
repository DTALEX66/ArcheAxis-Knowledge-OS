import React, { type ButtonHTMLAttributes, type ReactNode } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import * as Tabs from '@radix-ui/react-tabs';
import './materials.css';

/** Material wrappers only. Host readiness and business state come from admitted services. */
export type ReadinessVisual = 'ready' | 'unavailable' | 'attention';
export function GlassSurface({children,label,blur=false}:{children:ReactNode;label?:string;blur?:boolean}) {
  return <section className="ax-surface" data-blur={blur?'on':'off'} aria-label={label}>{children}</section>;
}
export const ActionButton = React.forwardRef<HTMLButtonElement,ButtonHTMLAttributes<HTMLButtonElement>&{variant?:'default'|'primary'|'ghost'}>(function ActionButton({variant='default',...props},ref) {
  return <button {...props} ref={ref} type={props.type??'button'} className={`ax-button ${props.className??''}`} data-variant={variant}/>;
});
export function StatusLight({state,text}:{state:ReadinessVisual;text:string}) {
  return <span className="ax-status" data-state={state}>{text}</span>;
}
export function NavigationItem({label,status,icon,active=false,onSelect}:{label:string;status:{state:ReadinessVisual;text:string};icon?:ReactNode;active?:boolean;onSelect:()=>void}) {
  return <button type="button" className="ax-nav-item" aria-current={active?'page':undefined} onClick={onSelect}><span aria-hidden="true">{icon}</span><span>{label}</span><StatusLight {...status}/></button>;
}
export function ContextChip({title,onRemove}:{title:string;onRemove?:()=>void}) {
  return <span className="ax-chip">{title}{onRemove?<button type="button" className="ax-button" data-variant="ghost" aria-label={`移除上下文 ${title}`} onClick={onRemove}>×</button>:null}</span>;
}
export function EmptyState({title,description,action}:{title:string;description:string;action?:ReactNode}) {
  return <section className="ax-empty"><strong>{title}</strong><p className="ax-muted">{description}</p>{action}</section>;
}
export function ConversationBubble({role,children}:{role:'user'|'assistant';children:ReactNode}) {
  return <article className="ax-message" data-role={role} aria-label={role==='user'?'我的消息':'小栖的消息'}>{children}</article>;
}
export function MaterialDialog({title,description,trigger,children}:{title:string;description:string;trigger:React.ReactElement;children:ReactNode}) {
  return <Dialog.Root><Dialog.Trigger asChild>{trigger}</Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="ax-dialog-overlay"/><Dialog.Content className="ax-dialog-content"><Dialog.Title>{title}</Dialog.Title><Dialog.Description className="ax-muted">{description}</Dialog.Description>{children}<Dialog.Close asChild><ActionButton>关闭</ActionButton></Dialog.Close></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
export function MaterialTabs({items,defaultValue}:{items:{id:string;label:string;content:ReactNode}[];defaultValue:string}) {
  return <Tabs.Root defaultValue={defaultValue}><Tabs.List className="ax-tabs-list" aria-label="功能区域">{items.map(item=><Tabs.Trigger key={item.id} className="ax-tab" value={item.id}>{item.label}</Tabs.Trigger>)}</Tabs.List>{items.map(item=><Tabs.Content key={item.id} value={item.id}>{item.content}</Tabs.Content>)}</Tabs.Root>;
}

