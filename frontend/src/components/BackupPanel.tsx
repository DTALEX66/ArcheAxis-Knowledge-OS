import { useEffect, useRef, useState } from "react";
import { previewWorkspaceRestore, confirmWorkspaceRestore } from "../api/workspaceRestore";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "./DiagnosticConsole";
function backup(value:unknown):Record<string,unknown>{
 if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("invalid backup");
 const item=value as Record<string,unknown>;
 if(typeof item.backup_id!=="string"||!/^[a-f0-9]{32}$/.test(item.backup_id)||item.filename!==`${item.backup_id}.sqlite`||typeof item.filename!=="string"||!/^[a-f0-9]{32}\.sqlite$/.test(item.filename)||typeof item.sha256!=="string"||!/^[a-f0-9]{64}$/.test(item.sha256)||!Number.isInteger(item.bytes)||(item.bytes as number)<=0||!(typeof item.schema_version==="string"||Number.isInteger(item.schema_version))||typeof item.sqlite_version!=="string"||!Array.isArray(item.source_sha_list)||item.source_sha_list.some(sha=>typeof sha!=="string"||!/^[a-f0-9]{64}$/.test(sha)))throw new Error("invalid backup metadata");
 return item;
}
export function BackupPanel({hasUnsavedDrafts=false}:{hasUnsavedDrafts?:boolean}){
 const busyRef=useRef(false);const draftDirty=useRef(false);const [unsaved,setUnsaved]=useState(false);
 useEffect(()=>{const listener=(event:Event)=>{draftDirty.current=(event as CustomEvent<boolean>).detail===true;setUnsaved(draftDirty.current);};window.addEventListener("archeaxis-draft-dirty",listener);return()=>window.removeEventListener("archeaxis-draft-dirty",listener);},[]);

 const [selected,setSelected]=useState<Record<string,unknown>|null>(null);const [preview,setPreview]=useState<Record<string,unknown>|null>(null);
 async function select(item:Record<string,unknown>){if(busyRef.current)return;busyRef.current=true;setBusy(true);setSelected(item);setPreview(null);try{setPreview(await previewWorkspaceRestore(String(item.backup_id),String(item.sha256)));setMessage("完整性、数据结构与 CAS 预检通过；尚未恢复。确认将替换整个工作区，当前库和 CAS 会先保全。");}catch{setMessage("恢复预检失败，当前工作区未改变。请核对备份是否损坏或版本不兼容。");}finally{busyRef.current=false;setBusy(false);}}
 async function restore(){if(draftDirty.current||hasUnsavedDrafts){setMessage("草稿尚未保存，请先保存或保留文字后恢复整个工作区。");return;}if(busyRef.current||!selected||!preview)return;busyRef.current=true;setBusy(true);window.dispatchEvent(new CustomEvent("workspace-restore-start"));let confirmed=false;let resultMessage="恢复或重启读回未确认，请保留当前回执并检查恢复状态；未显示为成功。";try{await confirmWorkspaceRestore(String(selected.backup_id),String(selected.sha256));confirmed=true;resultMessage="整个工作区已恢复，Core 已重启并读回。";setPreview(null);setSelected(null);window.dispatchEvent(new CustomEvent("archeaxis-workspace-restored"));setMessage("整个工作区已恢复，Core 已重启并读回。");}catch{setPreview(null);setMessage("恢复或重启读回未确认，请保留当前回执并检查恢复状态；未显示为成功。");}finally{busyRef.current=false;setBusy(false);window.dispatchEvent(new CustomEvent("workspace-invalidated",{detail:{confirmed,message:resultMessage}}));window.dispatchEvent(new CustomEvent("workspace-restore-finish"));}}

 const [items,setItems]=useState<Record<string,unknown>[]>([]);const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);
 async function create(){
  if(busyRef.current)return;busyRef.current=true;setBusy(true);
  try{const receipt=backup(await coreCommand("workspace_backup",{body:{}}));setItems(previous=>[receipt,...previous.filter(item=>item.backup_id!==receipt.backup_id)]);setMessage("一致备份已创建，下面是 Core 的实际产物回执。独立恢复尚需单独验证。");}
  catch{setMessage("备份未确认，请重试；不会将失败显示为成功。");}finally{busyRef.current=false;setBusy(false);}
 }
 async function refresh(){
  if(busyRef.current)return;busyRef.current=true;setBusy(true);
  try{const result=await coreCommand<unknown>("workspace_backups");if(!result||typeof result!=="object"||!("backups" in result)||!Array.isArray(result.backups))throw new Error("invalid backup list");setItems(result.backups.map(backup));setMessage("已读取产品自己的备份产物。");}
  catch{setMessage("备份列表读取失败，未替换已有回执。");}finally{busyRef.current=false;setBusy(false);}
 }
 return <section aria-label="一致备份"><h4>产品资料备份</h4><button disabled={busy} onClick={()=>void create()}>创建一致备份</button><button disabled={busy} onClick={()=>void refresh()}>刷新备份产物</button>{message?<p role="status">{message}</p>:null}{selected&&preview?<div role="group" aria-label="确认恢复整个工作区"><p>恢复目标：{String(selected.filename)} · 数据结构 {String(preview.schema_version)} · {String(preview.source_count)} 个来源。此操作与文档版本恢复不同。</p><p>恢复会保留资料与历史，但旧 AI 消费授权将暂停；恢复后需新建明确授权对象。</p>{unsaved||hasUnsavedDrafts?<p role="alert">草稿尚未保存，请先保存或保留文字。</p>:null}<button disabled={busy||unsaved||hasUnsavedDrafts} onClick={()=>void restore()}>确认恢复整个工作区</button><button disabled={busy} onClick={()=>{setSelected(null);setPreview(null);setMessage("已取消恢复，当前工作区未改变。");}}>取消恢复</button></div>:null}<ul>{items.map(item=><li key={String(item.backup_id)}><strong>{String(item.filename)}</strong><button disabled={busy} onClick={()=>void select(item)}>预检此备份</button><p>SHA-256 {String(item.sha256)} · {String(item.bytes)} 字节</p><p>数据结构版本 {String(item.schema_version)} · SQLite {String(item.sqlite_version)}</p><RawReceiptButton label="备份来源 SHA 与核验回执" payload={{source_sha_list:item.source_sha_list,verified:item.verified??"未提供"}} /></li>)}</ul></section>;
}
