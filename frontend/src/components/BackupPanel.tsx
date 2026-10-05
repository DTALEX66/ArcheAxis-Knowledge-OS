import { useState } from "react";
import { coreCommand } from "../api/core";
function backup(value:unknown):Record<string,unknown>{
 if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("invalid backup");
 const item=value as Record<string,unknown>;
 if(typeof item.backup_id!=="string"||typeof item.filename!=="string"||!/^[a-f0-9]{32}\.sqlite$/.test(item.filename)||typeof item.sha256!=="string"||!/^[a-f0-9]{64}$/.test(item.sha256)||!Number.isInteger(item.bytes)||(item.bytes as number)<=0||!(typeof item.schema_version==="string"||Number.isInteger(item.schema_version))||typeof item.sqlite_version!=="string"||!Array.isArray(item.source_sha_list)||item.source_sha_list.some(sha=>typeof sha!=="string"||!/^[a-f0-9]{64}$/.test(sha)))throw new Error("invalid backup metadata");
 return item;
}
export function BackupPanel(){
 const [items,setItems]=useState<Record<string,unknown>[]>([]);const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);
 async function create(){
  if(busy)return;setBusy(true);
  try{const receipt=backup(await coreCommand("workspace_backup",{body:{}}));setItems(previous=>[receipt,...previous.filter(item=>item.backup_id!==receipt.backup_id)]);setMessage("一致备份已创建，下面是 Core 的实际产物回执。独立恢复尚需单独验证。");}
  catch{setMessage("备份未确认，请重试；不会将失败显示为成功。");}finally{setBusy(false);}
 }
 async function refresh(){
  if(busy)return;setBusy(true);
  try{const result=await coreCommand<unknown>("workspace_backups");if(!result||typeof result!=="object"||!("backups" in result)||!Array.isArray(result.backups))throw new Error("invalid backup list");setItems(result.backups.map(backup));setMessage("已读取产品自己的备份产物。");}
  catch{setMessage("备份列表读取失败，未替换已有回执。");}finally{setBusy(false);}
 }
 return <section aria-label="一致备份"><h4>产品资料备份</h4><button disabled={busy} onClick={()=>void create()}>创建一致备份</button><button disabled={busy} onClick={()=>void refresh()}>刷新备份产物</button>{message?<p role="status">{message}</p>:null}<ul>{items.map(item=><li key={String(item.backup_id)}><strong>{String(item.filename)}</strong><p>SHA-256 {String(item.sha256)} · {String(item.bytes)} 字节</p><p>数据结构版本 {String(item.schema_version)} · SQLite {String(item.sqlite_version)}</p><details><summary>来源 SHA 与核验回执</summary><pre>{JSON.stringify({source_sha_list:item.source_sha_list,verified:item.verified??"未提供"},null,2)}</pre></details></li>)}</ul></section>;
}
