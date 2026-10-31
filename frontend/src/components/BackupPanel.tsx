import { useEffect, useRef, useState } from "react";
import { previewWorkspaceRestore, confirmWorkspaceRestore } from "../api/workspaceRestore";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "./DiagnosticConsole";
import { updateDraftOwners } from "../workspace/draftProtection";
import { assertCoreDto, type BackupsListDto, type UnavailableBackupDto } from "../api/generated/core-contract";
function backup(value:unknown):Record<string,unknown>{
 if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("invalid backup");
 const item=value as Record<string,unknown>;
 if(typeof item.backup_id!=="string"||!/^[a-f0-9]{32}$/.test(item.backup_id)||item.filename!==`${item.backup_id}.sqlite`||typeof item.filename!=="string"||!/^[a-f0-9]{32}\.sqlite$/.test(item.filename)||typeof item.sha256!=="string"||!/^[a-f0-9]{64}$/.test(item.sha256)||!Number.isInteger(item.bytes)||(item.bytes as number)<=0||!(typeof item.schema_version==="string"||Number.isInteger(item.schema_version))||typeof item.sqlite_version!=="string"||!Array.isArray(item.source_sha_list)||item.source_sha_list.some(sha=>typeof sha!=="string"||!/^[a-f0-9]{64}$/.test(sha)))throw new Error("invalid backup metadata");
 return item;
}
export function BackupPanel({hasUnsavedDrafts=false}:{hasUnsavedDrafts?:boolean}){
 const busyRef=useRef(false);const draftDirty=useRef(false);const draftOwners=useRef(new Set<string>());const [unsaved,setUnsaved]=useState(false);
 useEffect(()=>{const listener=(event:Event)=>{draftDirty.current=updateDraftOwners(draftOwners.current,(event as CustomEvent<unknown>).detail);setUnsaved(draftDirty.current);};window.addEventListener("archeaxis-draft-dirty",listener);return()=>window.removeEventListener("archeaxis-draft-dirty",listener);},[]);

 const [selected,setSelected]=useState<Record<string,unknown>|null>(null);const [preview,setPreview]=useState<Record<string,unknown>|null>(null);
 async function select(item:Record<string,unknown>){if(busyRef.current)return;busyRef.current=true;setBusy(true);setSelected(item);setPreview(null);try{setPreview(await previewWorkspaceRestore(String(item.backup_id),String(item.sha256)));setMessage("备份检查通过，尚未恢复。确认后将替换整个工作区；当前资料和原件会先另行保留。");}catch{setMessage("备份检查失败，当前工作区未改变。请检查备份是否损坏或版本不兼容。");}finally{busyRef.current=false;setBusy(false);}}
 async function restore(){if(draftDirty.current||hasUnsavedDrafts){setMessage("草稿尚未保存，请先保存或保留文字后恢复整个工作区。");return;}if(busyRef.current||!selected||!preview)return;busyRef.current=true;setBusy(true);window.dispatchEvent(new CustomEvent("workspace-restore-start"));let confirmed=false;let resultMessage="恢复结果暂未确认，请保留当前内容并检查恢复状态。";try{await confirmWorkspaceRestore(String(selected.backup_id),String(selected.sha256));confirmed=true;resultMessage="整个工作区已恢复，并已重新打开确认。";setPreview(null);setSelected(null);window.dispatchEvent(new CustomEvent("archeaxis-workspace-restored"));setMessage("整个工作区已恢复，并已重新打开确认。");}catch{setPreview(null);setMessage("恢复结果暂未确认，请保留当前内容并检查恢复状态。");}finally{busyRef.current=false;setBusy(false);window.dispatchEvent(new CustomEvent("workspace-invalidated",{detail:{confirmed,message:resultMessage}}));window.dispatchEvent(new CustomEvent("workspace-restore-finish"));}}

 const [items,setItems]=useState<Record<string,unknown>[]>([]);const [unavailable,setUnavailable]=useState<UnavailableBackupDto[]>([]);const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);
 async function create(){
  if(busyRef.current)return;busyRef.current=true;setBusy(true);
  try{const receipt=backup(await coreCommand("workspace_backup",{body:{}}));setItems(previous=>[receipt,...previous.filter(item=>item.backup_id!==receipt.backup_id)]);setMessage("备份已创建，可在下方列表找到。需要恢复时，请先检查备份并确认替换范围。");}
  catch{setMessage("备份未确认，请重试；不会将失败显示为成功。");}finally{busyRef.current=false;setBusy(false);}
 }
 async function refresh(){
  if(busyRef.current)return;busyRef.current=true;setBusy(true);
  try{
   const result=assertCoreDto<BackupsListDto>("BackupsListDto",await coreCommand("workspace_backups"));
   const next=result.backups.map(backup);
   const invalid=result.unavailable_backups??[];
   if(selected&&!next.some(item=>item.backup_id===selected.backup_id&&item.sha256===selected.sha256)){
    setSelected(null);setPreview(null);
   }
   setItems(next);setUnavailable(invalid);setMessage("备份列表已刷新。");
  }
  catch{setMessage("备份列表读取失败，原列表仍保留。");}finally{busyRef.current=false;setBusy(false);}
 }
 return <section aria-label="一致备份"><h3>产品资料备份</h3><button disabled={busy} onClick={()=>void create()}>创建备份</button><button disabled={busy} onClick={()=>void refresh()}>刷新备份列表</button>{message?<p role="status">{message}</p>:null}{selected&&preview?<div role="group" aria-label="确认恢复整个工作区"><p>恢复目标：{String(selected.filename)} · {String(preview.source_count)} 个来源。此操作会替换整个工作区，不是恢复单篇文档的旧版本。</p><p>当前资料和原件会先另行保留。恢复后，原 AI 使用授权将失效，需要重新明确授权。</p>{unsaved||hasUnsavedDrafts?<p role="alert">草稿尚未保存，请先保存或保留文字。</p>:null}<button disabled={busy||unsaved||hasUnsavedDrafts} onClick={()=>void restore()}>确认恢复整个工作区</button><button disabled={busy} onClick={()=>{setSelected(null);setPreview(null);setMessage("已取消恢复，当前工作区未改变。");}}>取消恢复</button></div>:null}<ul>{items.map(item=><li key={String(item.backup_id)}><strong>{String(item.filename)}</strong><button disabled={busy} onClick={()=>void select(item)}>检查此备份</button><p>大小：{String(item.bytes)} 字节</p><RawReceiptButton label="备份详细信息" category="data" payload={{backup:item,...(selected?.backup_id===item.backup_id&&preview?{restore_preview:preview}:{})}} /></li>)}</ul>
  {unavailable.length?<section aria-label="无法核验的备份"><p role="status">有 {unavailable.length} 份备份无法核验，已保留。</p><ul>{unavailable.map(item=><li key={item.backup_id}><strong>{item.filename}</strong><p>备份内容未通过检查；文件已保留，暂不能恢复。</p><button disabled>此备份无法恢复</button><RawReceiptButton label="无法核验的备份详情" payload={item}/></li>)}</ul></section>:null}
 </section>;
}
