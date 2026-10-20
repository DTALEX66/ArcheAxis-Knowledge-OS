import { useEffect, useId, useRef, useState } from "react";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { applyMemory, exportMemory, memoryAttempt, readMemoryProfile, type MemoryAttempt, type MemoryCommand } from "../api/characterMemory";
import type { CharacterProfile } from "../api/generated/core-contract";
import { sameValue } from "../presentation/exchangeProof";

/** Human-controlled product memory; no chat extraction, model call or second knowledge store. */
export function CharacterMemoryPanel() {
  const [profile,setProfile]=useState<CharacterProfile|null>(null);
  const [preferences,setPreferences]=useState(""), [goals,setGoals]=useState("");
  const [memoryText,setMemoryText]=useState(""), [provenance,setProvenance]=useState(""), [editing,setEditing]=useState<string|null>(null);
  const [pending,setPending]=useState<MemoryAttempt|null>(null), [observed,setObserved]=useState<CharacterProfile|null>(null);
  const [busy,setBusy]=useState(false), [message,setMessage]=useState(""), [failed,setFailed]=useState(false);
  const [forgetTarget,setForgetTarget]=useState<string|null>(null), [forgetOpen,setForgetOpen]=useState(false);
  const mounted=useRef(false), epoch=useRef(0), lock=useRef<number|null>(null), initialized=useRef(false), serial=useRef(0), sentSerial=useRef(0);
  const owner=useId();
  const forgetOrigin=useRef<HTMLButtonElement|null>(null);
  const selected=profile?.memories.find(row=>row.id===editing);
  const memoryDirty=editing?memoryText!==selected?.text||provenance!==selected?.provenance:!!memoryText||!!provenance;
  const dirty=!!pending||!!profile&&(preferences!==profile.preferences||goals!==profile.learning_goals)||memoryDirty;
  function note(text:string,error=false){setMessage(text);setFailed(error);}
  useEffect(()=>{window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner,dirty}}));},[owner,dirty]);
  useEffect(()=>{mounted.current=true;void refresh();return()=>{mounted.current=false;epoch.current++;lock.current=null;window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner,dirty:false}}));};},[]);
  async function task(work:(request:number)=>Promise<void>){
    if(lock.current!==null)return;const request=++epoch.current;lock.current=request;setBusy(true);
    try{await work(request);}catch{if(mounted.current&&request===epoch.current)note("操作未确认；当前文字保留，不自动重发或把失败当作空记忆。",true);}
    finally{if(lock.current===request)lock.current=null;if(mounted.current&&request===epoch.current)setBusy(false);}
  }
  const current=(request:number)=>mounted.current&&request===epoch.current;
  async function refresh(){await task(async request=>{
    const value=await readMemoryProfile();if(!current(request))return;
    setProfile(value);
    if(!initialized.current){initialized.current=true;setPreferences(value.preferences);setGoals(value.learning_goals);}
    note("已读取当前档案与获准记忆；刷新保留本地编辑，不从聊天自动提取记忆。");
  });}
  function finish(attempt:MemoryAttempt,value:CharacterProfile){
    setProfile(value);setPending(null);setObserved(null);
    if(serial.current===sentSerial.current){
      if(attempt.body.command.operation==="profile"){setPreferences(value.preferences);setGoals(value.learning_goals);}
      if(["remember","correct"].includes(attempt.body.command.operation)){setEditing(null);setMemoryText("");setProvenance("");}
    }
    note(attempt.forgotten.length?"遗忘已在当前记忆存储中读回；原聊天与备份未改动，不声明安全擦除。":"档案或记忆变更已保存并读回；事实来源与权限保持独立。");
  }
  async function write(command:MemoryCommand){
    if(!profile||pending||lock.current)return;
    let attempt:MemoryAttempt;
    try{attempt=memoryAttempt(profile,command);}catch{note("输入超出记忆允许范围或来源未填写；当前文字保留，不执行写入。",true);return;}
    sentSerial.current=serial.current;setPending(attempt);setObserved(null);setForgetOpen(false);
    await task(async request=>{
      await applyMemory(attempt);if(!current(request))return;
      const value=await readMemoryProfile();if(!current(request))return;
      if(!sameValue(value,attempt.expected))throw new Error("MEMORY_READBACK_MISMATCH");
      finish(attempt,value);
    });
  }
  async function reconcile(){if(!pending)return;const attempt=pending;await task(async request=>{
    const value=await readMemoryProfile();if(!current(request))return;
    if(sameValue(value,attempt.expected)){finish(attempt,value);return;}
    if(sameValue(value,attempt.base)){setProfile(value);setPending(null);setObserved(null);note("当前存储仍与原基线一致；原操作未确认，文字保留，可重新审阅后显式提交。",true);return;}
    setObserved(value);note("当前存储与原提交不一致；原操作结果仍未确认。请核对当前版本，保留原文字，不自动覆盖。",true);
  });}
  function adoptObserved(){
    if(!observed||!pending||lock.current)return;
    if(observed.workspace_id!==pending.base.workspace_id||observed.restore_epoch!==pending.base.restore_epoch){note("工作区或恢复身份已改变；原文字保留，不能采用为原工作区的写入基线。",true);return;}
    setProfile(observed);setPending(null);setObserved(null);note("已采用读回的当前版本，原操作结果仍未确认；本地文字保留，请核对后决定下一次提交。",true);
  }
  function editMemory(id:string){
    if(!profile||pending||lock.current)return;
    if(memoryDirty&&id!==editing){note("此条本地编辑尚未保存；请先保存或取消编辑，原文字保留。",true);return;}
    const row=profile.memories.find(item=>item.id===id);if(!row)return;
    setEditing(id);setMemoryText(row.text);setProvenance(row.provenance);serial.current++;
  }
  async function download(){if(!profile)return;const identity=profile;await task(async request=>{
    const value=await exportMemory();if(!current(request))return;
    if(value.profile.workspace_id!==identity.workspace_id||value.profile.restore_epoch!==identity.restore_epoch)throw new Error("MEMORY_EXPORT_IDENTITY_CHANGED");
    const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:"application/json"}));
    try{const link=document.createElement("a");link.href=url;link.download=`archeaxis-memory-v${value.profile.revision}.json`;link.click();}finally{URL.revokeObjectURL(url);}
    note(`当前记忆已导出到本地 JSON · v${value.profile.revision}；没有上传或修改原聊天。`);
  });}
  const disabled=busy||!!pending||!profile;
  return <section className="ui-content-panel" aria-label="角色档案与获准记忆">
    <h2>角色档案与获准记忆</h2><p>由你明确保存偏好、学习目标和有来源的记忆。启用后才用于陪伴风格；记忆不授予权限，也不成为已核验知识。</p>
    <button disabled={busy||!!pending} onClick={()=>void refresh()}>读取当前档案与记忆</button>
    {message?<p role={failed?"alert":"status"}>{message}</p>:null}
    {profile?<><p>当前存储 v{profile.revision} · {profile.enabled?"记忆已启用":"记忆已停用"} · {profile.memories.length} 条获准记忆</p>
      <details><summary>核对当前已存储档案</summary><p style={{whiteSpace:"pre-wrap"}}>偏好：{profile.preferences||"未填写"}</p><p style={{whiteSpace:"pre-wrap"}}>学习目标：{profile.learning_goals||"未填写"}</p></details>
      <button disabled={disabled} onClick={()=>void write({operation:profile.enabled?"disable":"enable"})}>{profile.enabled?"停用陪伴记忆":"明确启用陪伴记忆"}</button>
      <button disabled={busy} onClick={()=>void download()}>导出当前记忆 JSON</button>
      <form onSubmit={event=>{event.preventDefault();void write({operation:"profile",preferences,learning_goals:goals});}} aria-label="编辑角色档案"><fieldset disabled={disabled}>
        <label>角色偏好<textarea value={preferences} onChange={event=>{serial.current++;setPreferences(event.target.value);}}/></label>
        <label>学习目标<textarea value={goals} onChange={event=>{serial.current++;setGoals(event.target.value);}}/></label>
        <button type="submit">保存并核对档案</button>
      </fieldset></form>
      <ul>{profile.memories.map(row=><li key={row.id}><article aria-label={`获准记忆 ${row.id}`}><p style={{whiteSpace:"pre-wrap"}}>{row.text}</p><p>来源：{row.provenance}</p><small>{row.id}</small><button disabled={disabled} onClick={()=>editMemory(row.id)}>纠正此条</button><button disabled={disabled} onClick={event=>{forgetOrigin.current=event.currentTarget;setForgetTarget(row.id);setForgetOpen(true);}}>审阅遗忘此条</button></article></li>)}</ul>
      <form aria-label="编辑获准记忆" onSubmit={event=>{event.preventDefault();void write({operation:editing?"correct":"remember",memory:{id:editing??`memory_${crypto.randomUUID()}`,text:memoryText,provenance}});}}><fieldset disabled={disabled}>
        <legend>{editing?`纠正 ${editing}${selected?"":"（当前存储中已不存在）"}`:"明确记住一条"}</legend>
        <label>记忆内容<textarea value={memoryText} onChange={event=>{serial.current++;setMemoryText(event.target.value);}}/></label><label>记忆来源<input value={provenance} onChange={event=>{serial.current++;setProvenance(event.target.value);}}/></label>
        <button type="submit">{editing?"保存并核对纠正":"保存并核对这条记忆"}</button><button type="button" onClick={()=>{serial.current++;setEditing(null);setMemoryText("");setProvenance("");}}>取消此条本地编辑</button>
      </fieldset></form>
      <AaosDialog role="alertdialog" title="确认遗忘获准记忆" description="从当前记忆存储移除所选条目；原聊天与备份保留。" open={forgetOpen} onOpenChange={open=>{if(!busy)setForgetOpen(open);}} onCloseAutoFocus={event=>{const origin=forgetOrigin.current;if(origin?.isConnected&&!origin.disabled){event.preventDefault();origin.focus();}}} trigger={<button disabled={disabled||!profile.memories.length} onClick={event=>{forgetOrigin.current=event.currentTarget;setForgetTarget(null);}}>审阅遗忘全部记忆</button>}><p>{forgetTarget?`遗忘当前存储中的 ${forgetTarget}`:`遗忘当前存储的全部 ${profile.memories.length} 条记忆`}。保留偏好与学习目标；不宣称从历史聊天、备份或设备介质安全擦除。</p><button disabled={disabled} onClick={()=>void write(forgetTarget?{operation:"forget",id:forgetTarget}:{operation:"forget_all"})}>确认遗忘</button><button disabled={busy} onClick={()=>setForgetOpen(false)}>取消遗忘</button></AaosDialog>
    </>:null}
    {pending?<><p role="status">有一项变更尚未确认；保留原提交与文字，仅查询当前存储，不自动重发。</p><button disabled={busy} onClick={()=>void reconcile()}>核对未确认变更</button>{observed?<><p>已读当前存储 v{observed.revision} · {observed.memories.length} 条；原提交预期 v{pending.expected.revision}。</p><button disabled={busy} onClick={adoptObserved}>采用当前版本并保留本地编辑</button></>:null}</>:null}
  </section>;
}
