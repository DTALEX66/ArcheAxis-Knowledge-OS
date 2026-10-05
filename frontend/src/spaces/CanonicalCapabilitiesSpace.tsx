import { useEffect, useState } from "react";
import { coreCommand } from "../api/core";
import { CAPABILITY_CATALOG, type CapabilityCatalogEntry } from "../api/generated/capability-catalog";
import { Section } from "../components/RealData";
import type { SpaceId } from "./spaces";

// UI navigation only; implementation declarations remain in the existing map.
const destinations: Partial<Record<string, SpaceId>> = {
 "CAP-0010":"library","CAP-0020":"library","CAP-0030":"library",
 "CAP-0040":"learning","CAP-0050":"vault","CAP-0110":"vault","CAP-0140":"library",
};
function record(value:unknown):Record<string,unknown>{if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("invalid response");return value as Record<string,unknown>;}
export function CanonicalCapabilitiesSpace({onNavigate}:{onNavigate:(id:SpaceId)=>void}) {
 const [selected,setSelected]=useState<CapabilityCatalogEntry|null>(null);
 const [query,setQuery]=useState("");const [live,setLive]=useState<Map<string,Record<string,unknown>>|null>(null);const [message,setMessage]=useState("");
 async function refresh(){
  try{
   const response=record(await coreCommand("capabilities_list"));if(!Array.isArray(response.capabilities))throw new Error("invalid capability list");
   const rows=response.capabilities.map(record);if(rows.some(row=>typeof row.capability!=="string"))throw new Error("invalid capability identity");
   setLive(new Map(rows.map(row=>[String(row.capability),row])));setMessage("已读取当前 Core worker 握手；不代表引擎产物通过。");
  }catch{setLive(null);setMessage("当前健康与权限读取失败，显示未知；目录详情仍可浏览。");}
 }
 useEffect(()=>{void refresh();},[]);
 const visible=CAPABILITY_CATALOG.entries.filter(entry=>`${entry.atlas.capability_id} ${entry.atlas.canonical_name} ${entry.atlas.dependencies.join(" ")}`.toLowerCase().includes(query.toLowerCase()));
 const destination=selected?destinations[selected.atlas.capability_id]:undefined;
 return <Section title="探索与蓝图"><p>完整能力目录来自现有 Atlas；目录声明、运行实现、权限与即时健康分别展示。未来能力可浏览详情。</p><label>查找能力 <input value={query} onChange={event=>setQuery(event.target.value)}/></label><button onClick={()=>void refresh()}>刷新当前健康与权限</button>
 <p>{CAPABILITY_CATALOG.entries.length} 项正式目录；当前筛选 {visible.length} 项。</p><ul>{visible.map(entry=><li key={entry.atlas.capability_id}><button onClick={()=>setSelected(entry)}>{entry.atlas.capability_id} · {entry.atlas.canonical_name}</button> · {entry.implementation.state === "not_implemented" ? "尚未实现" : entry.implementation.state === "worker_backed" ? "worker 实现声明" : "Core 原生实现声明"}</li>)}</ul>
 {selected?<article aria-label="能力详情"><h4>{selected.atlas.canonical_name}</h4><p>目录 ID {selected.atlas.capability_id}</p><p>目录声明：{selected.atlas.authority_status} · 技术 {selected.atlas.technical_state} · 路线 {selected.atlas.roadmap_state} · 时段 {selected.atlas.activation_horizon}</p><p>场景对象：{selected.atlas.objects.join("、")}</p><p>相关视图：{selected.atlas.views.join("、")}</p><p>依赖声明：{selected.atlas.dependencies.length?selected.atlas.dependencies.join("、"):"目录未列依赖"}</p><p>执行前提：{selected.atlas.entry_gate.join("；")||"目录未列前提"}</p><p>所需验收证据：{selected.atlas.exit_evidence.join("；")||"目录未列证据要求"}</p><p>回退：{selected.atlas.fallbacks.join("；")||"目录未列回退"}</p><p>供体映射未建立；不按相似名称推断已吸收关系。</p>
 <h4>当前运行联接、权限与健康</h4><p>实现声明来源：config/capability-map.v1.json · {selected.implementation.state}。声明本身不证明本轮执行。</p>{selected.implementation.runtime_capabilities.length?<ul>{selected.implementation.runtime_capabilities.map(capability=>{const observation=live?.get(capability);return <li key={capability}>{capability}<p>连接/权限：{typeof observation?.enabled === "boolean"?(observation.enabled?"允许":"已禁用"):"未知"} · 即时健康：{typeof observation?.health === "string"?observation.health:"未观察"}</p>{observation?<details><summary>Core 握手原始读回</summary><pre>{JSON.stringify(observation,null,2)}</pre></details>:null}</li>;})}</ul>:<p>{selected.implementation.state==="not_implemented"?"没有当前运行实现，执行动作不可用。":"此项声明为 Core 原生；worker 握手不提供该项的运行证据。"}</p>}
 <p>实际引擎身份、版本与产物质量需在具体 job 的质量回执核验。</p><button disabled={!destination||selected.implementation.state==="not_implemented"} onClick={()=>{if(destination)onNavigate(destination);}}>{destination?"打开当前产品入口":"当前执行入口尚未提供"}</button></article>:<p>选择任一能力查看正式详情。</p>}
 {message?<p role="status">{message}</p>:null}<details><summary>目录投影来源与哈希</summary><pre>{JSON.stringify(CAPABILITY_CATALOG.sources,null,2)}</pre><p>此文件由原始 Atlas 与联接表生成，不是另一份状态真值。</p></details></Section>;
}
