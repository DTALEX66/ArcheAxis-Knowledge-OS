import {RawReceiptButton} from "./DiagnosticConsole";
import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { diagnoseModelConnection, readModelInventory } from "../runtime/modelConnection";
import { addLmStudioPreset, addLmStudioQuickConnection, LM_STUDIO_DEFAULT_MAX_TOKENS } from "../runtime/lmStudioPreset";
import type { ModelConfiguration, ModelPurpose, ModelLane, ModelProfile } from "../api/generated/model-configuration-contract";
import "./ModelConfiguration.css";
const purposes: ModelPurpose[] = ["answer","retest","material","companion","document_check","embedding"];
const lanes: ModelLane[] = ["fast","deep"];
const blank: ModelProfile = {endpoint:"http://127.0.0.1:1234/v1",protocol:"openai",model:"",credential_ref:null,max_tokens:LM_STUDIO_DEFAULT_MAX_TOKENS,timeout_s:120};
type ConnectionStatus = {status:"idle"|"testing"|"success"|"error";message?:string;latency_ms?:number};
export function ModelConfigurationPanel({materialBudgetLane}:{materialBudgetLane?:ModelLane}={}){
 const [secret,setSecret]=useState("");
 const [snapshot,setSnapshot]=useState<ModelConfiguration|null>(null);
 const [draftProfiles,setDraftProfiles]=useState<ModelConfiguration["profiles"]>({});
 const [profileEdited,setProfileEdited]=useState(false);
 const [profileId,setProfileId]=useState("local"); const [profile,setProfile]=useState<ModelProfile>(blank);
 const [bindings,setBindings]=useState<ModelConfiguration["bindings"]>([]);const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);
 const [connectionStatus,setConnectionStatus]=useState<ConnectionStatus>({status:"idle"});
 const connectionRequest=useRef(0),connectionAbort=useRef<AbortController|null>(null);
 const presetRequest=useRef(0),presetAbort=useRef<AbortController|null>(null);
 const configurationRequest=useRef(0);
 useEffect(()=>{if(materialBudgetLane)void load();return()=>{configurationRequest.current++;};},[materialBudgetLane]);
 useEffect(()=>()=>{presetRequest.current++;presetAbort.current?.abort();},[]);
 useEffect(()=>{connectionRequest.current++;connectionAbort.current?.abort();setConnectionStatus({status:"idle"});return()=>{connectionRequest.current++;connectionAbort.current?.abort();};},[profileId,profile]);
 function editProfile(value:ModelProfile){if(value.protocol!==profile.protocol)setSecret("");setProfile(value);setProfileEdited(true);}
 function profilesWithEdit(){return {...draftProfiles,...(profileEdited||Object.hasOwn(draftProfiles,profileId)?{[profileId]:profile}:{})};}
 function selectProfile(id:string){setSecret("");const drafts=profilesWithEdit();setDraftProfiles(drafts);setProfileId(id);setProfile(Object.hasOwn(drafts,id)?drafts[id]:blank);setProfileEdited(false);}
 async function storeCredential(){
  const value=secret;setSecret("");if(!value)return;setBusy(true);
  try{const invoke=window.__TAURI__?.core?.invoke;if(!invoke)throw new Error("native_required");
   const reference=await invoke("model_credential_create",{secret:value});
   if(typeof reference!=="string"||!/^aak_cred_[a-f0-9]{32}$/.test(reference))throw new Error("invalid_reference");
   editProfile({...profile,credential_ref:reference});setMessage("凭证已存入本机安全存储；请保存配置以绑定引用。");
  }catch{setMessage("安全存储写入失败；输入已清空，请在本机桌面应用重试。");}finally{setSecret("");setBusy(false);}
 }
 async function load(){const request=++configurationRequest.current;setBusy(true);try{const value=await coreCommand<ModelConfiguration>("model_configuration_get");if(request!==configurationRequest.current)return;setSnapshot(value);setDraftProfiles(value.profiles);setBindings(value.bindings);const id=(materialBudgetLane?value.bindings.find(binding=>binding.purpose==="material"&&binding.lane===materialBudgetLane)?.profile_id:undefined)??(materialBudgetLane?"":Object.keys(value.profiles)[0]??"local");setProfileId(id);setProfile(Object.hasOwn(value.profiles,id)?value.profiles[id]:blank);setProfileEdited(false);setMessage(`已读取版本 ${value.revision}；保存后新请求使用用途绑定。`);}catch{if(request===configurationRequest.current)setMessage("配置读取失败；现有草稿保留。");}finally{if(request===configurationRequest.current)setBusy(false);}}
 async function save(){if(!snapshot)return;setBusy(true);try{const configuration={...snapshot,profiles:Object.fromEntries(Object.entries({...draftProfiles,[profileId]:profile}).map(([id,value])=>[id,{...value,endpoint:materialBudgetLane?value.endpoint:value.endpoint.replace(/\/+$/,"")} ])),bindings};const value=await coreCommand<ModelConfiguration>("model_configuration_put",{body:{expected_revision:snapshot.revision,configuration}});setSnapshot(value);setDraftProfiles(value.profiles);setBindings(value.bindings);setProfile(value.profiles[profileId]??profile);setProfileEdited(false);setMessage(materialBudgetLane?`已保存版本 ${value.revision}；请回到材料问答点击“预览材料提问”，核对后确认新请求。旧请求保持原预算，没有自动重试。`:`已保存版本 ${value.revision}；已开始但结果未确认的旧请求，请重新检查。`);}catch{setMessage("保存被拒绝：请核对服务地址、凭证引用、模型、绑定和版本；重新读取配置后再保存。");}finally{setBusy(false);}}
 async function preset(){if(!snapshot||busy)return;setBusy(true);const request=++presetRequest.current;presetAbort.current?.abort();const controller=new AbortController();presetAbort.current=controller;const timer=setTimeout(()=>controller.abort(),5000);try{const names=await readModelInventory(blank,controller.signal);if(request!==presetRequest.current)return;const next=addLmStudioPreset({...snapshot,profiles:profilesWithEdit(),bindings},names);setDraftProfiles(next.profiles);setBindings(next.bindings);const id=next.bindings.find(binding=>binding.purpose==="material"&&binding.lane==="fast")?.profile_id??profileId;setProfileId(id);setProfile(next.profiles[id]??blank);setProfileEdited(false);setMessage("已补齐缺失的 LM Studio FAST/DEEP 配置草稿，保存后生效；已有绑定保留。模型加载需在本地服务完成。");}catch(error){if(request===presetRequest.current)setMessage(controller.signal.aborted?"本地模型目录读取超时；配置草稿保留。":error instanceof Error?error.message:"本地模型预设未生成；配置草稿保留。");}finally{clearTimeout(timer);if(request===presetRequest.current)setBusy(false);}}
 const [quickBusy,setQuickBusy]=useState(false);const [quickMessage,setQuickMessage]=useState("");
 async function quickConnect(){
  setQuickBusy(true);setQuickMessage("正在读取本机 LM Studio 模型目录…");
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),5000);
  try{
   const names=await readModelInventory({endpoint:"http://127.0.0.1:1234/v1",protocol:"openai"},controller.signal);
   const current=await coreCommand<ModelConfiguration>("model_configuration_get");
   const next=addLmStudioQuickConnection(current,names);
   const changed=next.bindings.length!==current.bindings.length;
   const value=changed?await coreCommand<ModelConfiguration>("model_configuration_put",{body:{expected_revision:current.revision,configuration:next}}):current;
   const id=value.bindings.find(binding=>binding.purpose==="material"&&binding.lane===(materialBudgetLane??"fast"))?.profile_id??Object.keys(value.profiles)[0]??"local";
   setSnapshot(value);setDraftProfiles(value.profiles);setBindings(value.bindings);setProfileId(id);setProfile(value.profiles[id]??blank);setProfileEdited(false);
   setQuickMessage(changed?"已补齐并保存本机 LM Studio 的缺失用途绑定；新配置输出预算为 4096，已有配置与绑定保留。":"现有用途绑定已完整，已有配置与输出预算保留；未重复保存。");
  }catch(error){setQuickMessage(controller.signal.aborted?"读取本机模型目录超时；请确认 LM Studio 服务已启动。":error instanceof Error?`连接失败：${error.message}`:"连接失败；请确认 LM Studio 已启动并加载模型。");}
  finally{clearTimeout(timer);setQuickBusy(false);}
 }
 async function testConnection(){
  if(profile.protocol==="openai-buffered"){setConnectionStatus({status:"error",message:"云端配置仅在已确认的材料请求中使用；此处不发送云端诊断。"});return;}
  const request=++connectionRequest.current;connectionAbort.current?.abort();const controller=new AbortController();connectionAbort.current=controller;
  const timer=setTimeout(()=>controller.abort(),5000),start=performance.now();setConnectionStatus({status:"testing"});
  try{const message=await diagnoseModelConnection(profile,controller.signal);if(connectionRequest.current===request)setConnectionStatus({status:"success",message,latency_ms:Math.round(performance.now()-start)});}
  catch(error){if(connectionRequest.current===request)setConnectionStatus({status:"error",message:controller.signal.aborted?"连接诊断超时；可重试，配置草稿保留。":error instanceof Error?error.message:"连接失败；请核对地址与浏览器跨域许可。"});}
  finally{clearTimeout(timer);}
 }
 if(materialBudgetLane){
  const boundId=snapshot?.bindings.find(binding=>binding.purpose==="material"&&binding.lane===materialBudgetLane)?.profile_id;
  const bound=boundId&&snapshot&&Object.hasOwn(snapshot.profiles,boundId)&&profileId===boundId;
  return <section className="model-quick-start" aria-label="当前材料模型输出预算">
   <h4>材料{materialBudgetLane==="deep"?"深度":"快速"}通道的输出预算</h4>
   <p>这里读取当前已保存的用途绑定。旧请求、模型和预算保持冻结；保存设置不会再次提问。</p>
   {bound&&snapshot?<><p>当前配置：{profileId}；模型：{profile.model}；已保存预算：{snapshot.profiles[profileId].max_tokens} token。</p>
    <p>较小的预算可能被模型思考过程用完，可手动尝试 4096。此配置若用于其他用途，保存后也影响它们的新请求。</p>
    {profile.protocol==="openai-buffered"?<p>这是云端配置；更高预算可能增加费用。保存设置不会发送材料。</p>:null}
    <fieldset disabled={busy||quickBusy}><legend>配置版本 {snapshot.revision}</legend>
     <label>最大输出 token <input type="number" min="128" max="4096" step="1" value={profile.max_tokens} onChange={e=>editProfile({...profile,max_tokens:Number(e.target.value)})}/></label>
     <button type="button" disabled={!profileEdited||!Number.isInteger(profile.max_tokens)||profile.max_tokens<128||profile.max_tokens>4096} onClick={()=>void save()}>保存材料输出预算</button>
    </fieldset></>:snapshot?<><p>当前材料通道尚未绑定有效模型，请先明确连接并保存用途绑定。</p><button type="button" disabled={busy||quickBusy} onClick={()=>void quickConnect()}>{quickBusy?"正在连接…":"一键连接本机 LM Studio"}</button></>:null}
   <button type="button" disabled={busy||quickBusy} onClick={()=>void load()}>重新读取材料模型配置</button>
   <p role="status">{message}</p>{quickMessage?<p role="status">{quickMessage}</p>:null}
  </section>;
 }
 return <div className="card" style={{padding:16}}><h2>产品模型与用途绑定</h2><p>普通使用只需连接本机 LM Studio；协议、端点、凭据与用途绑定都收在高级配置里。</p><section className="model-quick-start" aria-label="快速连接本机模型"><h3>只想先用起来？</h3><p>确认 LM Studio 已启动并加载模型，点一次即可完成连接与四个用途绑定。</p><button type="button" disabled={quickBusy} onClick={()=>void quickConnect()}>{quickBusy?"正在连接…":"一键连接本机 LM Studio"}</button><p role="status">{quickMessage}</p></section><button disabled={busy} onClick={()=>void load()}>读取模型配置</button>{snapshot&&<details className="model-advanced"><summary>高级配置（协议、端点、凭据、用途绑定）</summary><fieldset disabled={busy}><legend>配置版本 {snapshot.revision}</legend><button type="button" onClick={()=>void preset()}>补齐 LM Studio FAST/DEEP 配置</button><label>选择配置 <select value={profileId} onChange={e=>selectProfile(e.target.value)}>{Array.from(new Set([...Object.keys(draftProfiles),profileId])).filter(Boolean).map(id=><option key={id} value={id}>{id}</option>)}</select></label><label>配置名称 <input value={profileId} onChange={e=>selectProfile(e.target.value)} /></label><label>{profile.protocol==="openai-buffered"?"云端 HTTPS 服务地址 ":"本地服务地址 "}<input value={profile.endpoint} onChange={e=>editProfile({...profile,endpoint:e.target.value})}/></label><button type="button" disabled={profile.protocol==="openai-buffered"||connectionStatus.status==="testing"||!profile.endpoint} onClick={()=>void testConnection()}>{connectionStatus.status==="testing"?"测试中...":"测试连接"}</button>{connectionStatus.status==="success"&&<p style={{color:"var(--ax-success)"}}>✓ {connectionStatus.message}</p>}{connectionStatus.status==="error"&&<p style={{color:"var(--ax-danger)"}}>✗ {connectionStatus.message}</p>}{["success","error"].includes(connectionStatus.status)?<RawReceiptButton label="模型连接诊断" category="runtime" payload={{profile_id:profileId,endpoint:profile.endpoint,protocol:profile.protocol,model:profile.model,...connectionStatus}}/>:null}<label>协议 <select value={profile.protocol} onChange={e=>editProfile({...profile,protocol:e.target.value as ModelProfile["protocol"],timeout_s:e.target.value==="openai-buffered"?Math.min(profile.timeout_s,60):profile.timeout_s})}><option value="openai">LM Studio / OpenAI compatible</option><option value="ollama">Ollama（手动兼容）</option><option value="openai-buffered">云端 OpenAI buffered（仅材料）</option></select></label>{profile.protocol==="openai-buffered"?<><p>仅支持公网 HTTPS 域名。每次材料请求单独确认上传及未知费用。</p><label>凭证引用 <input placeholder="aak_cred_ + 32 位小写十六进制" value={profile.credential_ref??""} onChange={e=>editProfile({...profile,credential_ref:e.target.value||null})}/></label><p>填写已有安全存储中的引用；请勿在引用框填写密钥。</p><label>新增云端密钥 <input type="password" autoComplete="off" maxLength={2560} value={secret} onChange={e=>setSecret(e.target.value)}/></label><button type="button" disabled={!secret||busy} onClick={()=>void storeCredential()}>存入本机安全存储</button><button type="button" disabled={!secret} onClick={()=>setSecret("")}>清空密钥输入</button><p>密钥仅写入本机凭证库；此操作不发送云请求。模型名称须使用服务实际返回的固定模型 ID，别名返回不同名称时会拒绝结果。</p></>:null}<label>模型名称 <input value={profile.model} onChange={e=>editProfile({...profile,model:e.target.value})}/></label><label>最大输出 token <input type="number" min="128" max="4096" value={profile.max_tokens} onChange={e=>editProfile({...profile,max_tokens:Number(e.target.value)})}/></label><label>超时秒数 <input type="number" min="1" max={profile.protocol==="openai-buffered"?60:120} value={profile.timeout_s} onChange={e=>editProfile({...profile,timeout_s:Number(e.target.value)})}/></label>{purposes.flatMap(purpose=>lanes.map(lane=><label key={`${purpose}-${lane}`}>{purpose} / {lane.toUpperCase()} <select value={bindings.find(b=>b.purpose===purpose&&b.lane===lane)?.profile_id??""} onChange={e=>setBindings([...bindings.filter(b=>b.purpose!==purpose||b.lane!==lane),...(e.target.value?[{purpose,lane,profile_id:e.target.value}]:[])])}><option value="">未绑定（请求将阻止）</option>{Array.from(new Set([...Object.keys(draftProfiles),profileId])).filter(id=>Boolean(id)&&(purpose==="material"||(id===profileId?profile:draftProfiles[id])?.protocol!=="openai-buffered")).map(id=><option key={id} value={id}>{id}</option>)}</select></label>))}<button onClick={()=>void save()}>保存配置与用途绑定</button></fieldset></details>}<p role="status">{message}</p></div>;
}
