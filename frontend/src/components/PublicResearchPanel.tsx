import { useEffect, useState } from "react";
import { RawReceiptButton } from "./DiagnosticConsole";
import type { PublicResearchReceiptDto, PublicResearchSourceDto } from "../api/generated/core-contract";
import { comparisonStances, type ComparisonChoice } from "../presentation/publicEvidenceComparison";

// Presentation inputs remain separate from the canonical IPC DTOs.
export type PublicResearchFamily = "encyclopedia" | "community" | "research";
export const publicResearchFamilies: Record<PublicResearchFamily,string> = {encyclopedia:"百科",community:"社区",research:"科研"};
export type PublicResearchHit = {
  id:string; family:PublicResearchFamily; provider:string; title:string; url:string;
  retrievedAt:string; content:"metadata"|"excerpt"|"full_text";
  excerpt:string; locator:string|null; license:string|null; freeAccess:"free"|"unknown";
};
export type PublicResearchSnapshot =
  | {status:"unavailable"|"idle"|"loading"|"failed"|"cancelled"}
  | {status:"read";query:string;families:PublicResearchFamily[];channels:Array<{family:PublicResearchFamily;status:"complete"|"limited"|"failed"|"offline"|"unknown"}>;hits:PublicResearchHit[]};
const unavailable:PublicResearchSnapshot={status:"unavailable"};
const contentLabels={metadata:"仅元数据",excerpt:"已取得摘录",full_text:"已取得全文"};
const channelLabels={complete:"本次检索完成",limited:"限流，结果可能不完整",failed:"检索失败，结果未知",offline:"离线，结果未知",unknown:"状态未知"};
const stanceLabels=comparisonStances;
type Stance=keyof typeof stanceLabels;

export function PublicResearchPanel({snapshot=unavailable,onSearch,onCancel,onKeepNote,onCompare,readOnly=false,receipt,requestId,journal=[],message,acting=false,onRead,onList,onMaterialize,onOpenRaw}: {
  snapshot?:PublicResearchSnapshot;
  onSearch?:(query:string,families:PublicResearchFamily[])=>void;
  onCancel?:()=>void;
  onKeepNote:(text:string)=>boolean;
  onCompare?:(choices:readonly ComparisonChoice[])=>Promise<boolean>;
  readOnly?:boolean;
  receipt?:PublicResearchReceiptDto|null; requestId?:string; journal?:PublicResearchReceiptDto[]; message?:string; acting?:boolean;
  onRead?:(receipt?:PublicResearchReceiptDto)=>void; onList?:()=>void;
  onMaterialize?:(hit:PublicResearchHit)=>void; onOpenRaw?:(reference:PublicResearchSourceDto)=>void;
}) {
  const [query,setQuery]=useState("");
  const [families,setFamilies]=useState<PublicResearchFamily[]>(["encyclopedia","community","research"]);
  const [content,setContent]=useState("all");
  const [selection,setSelection]=useState<{snapshot:PublicResearchSnapshot;values:Record<string,Stance>}>({snapshot,values:{}});
  const [focus,setFocus]=useState<{snapshot:PublicResearchSnapshot;url:string}|null>(null);
  const [notice,setNotice]=useState("");
  const [kept,setKept]=useState("");
  useEffect(()=>{if(receipt){setQuery(receipt.query);setFamilies([...receipt.families]);}},[receipt?.request_id]);
  const result=snapshot.status==="read"?snapshot:null;
  const current=!!result&&result.query===query&&families.length===result.families.length&&families.every(f=>result.families.includes(f));
  const allComplete=!!result&&result.families.length>0&&result.families.every(f=>{const rows=result.channels.filter(row=>row.family===f);return rows.length===1&&rows[0].status==="complete";});
  const chosen=selection.snapshot===snapshot?selection.values:{};
  // Same-address grouping is a display aid only: all returned records and their
  // version/time/content differences remain visible and in the authored note.
  const groups=new Map<string,PublicResearchHit[]>();
  for(const hit of result?.hits??[])groups.set(hit.url,[...(groups.get(hit.url)??[]),hit]);
  const visible=[...groups].filter(([,hits])=>content==="all"||hits.some(hit=>hit.content===content));
  const selected=[...groups].filter(([url])=>Object.hasOwn(chosen,url));
  const plan=`公开检索计划（未执行外部检索）\n关键词：${query}\n来源范围：${families.map(f=>publicResearchFamilies[f]).join("、")}\n仅使用明确输入的公开关键词；没有发送研究正文。`;
  const comparison=`作者对照记录（未核验，未绑定固定原件）\n关键词：${result?.query??""}\n${selected.map(([url,hits],i)=>`对照 ${i+1}：${stanceLabels[chosen[url]]}\n${hits.map(hit=>`来源：${publicResearchFamilies[hit.family]} / ${hit.provider}\n标题：${hit.title}\n地址：${hit.url}\n取得时间：${hit.retrievedAt}\n内容范围：${contentLabels[hit.content]}\n定位：${hit.locator??"未提供"}\n许可：${hit.license??"未知"}\n免费条件：${hit.freeAccess==="free"?"本次返回声明免费；不推定后续条件":"未知"}\n摘录：${hit.excerpt}`).join("\n")}\n`).join("\n")}`;
  function keep(text:string) {
    if(readOnly||kept===text)return;
    if(onKeepNote(text)){setKept(text);setNotice("已加入未决草稿；还需保存研究草稿。没有建立固定来源引用或知识采用记录。");}
    else setNotice("未加入未决草稿；输入与对照选择保留，请先处理研究页的保存限制。");
  }
  async function keepComparison(){
    if(readOnly||acting||!current||kept===comparison)return;
    if(!onCompare){keep(comparison);return;}
    const choices=selected.flatMap(([url,hits])=>hits.map(hit=>({family:hit.family,id:hit.id,stance:chosen[url]})));
    if(await onCompare(choices)){setKept(comparison);setNotice("人工判断与固定来源定位已加入未决草稿；还需保存，未执行知识采用。");}
    else setNotice("未加入比较草稿；输入与对照选择保留。请核对来源、定位或保存限制后显式重试。");
  }
  function choose(url:string,checked:boolean) {
    if(!current)return;
    const values={...chosen};
    if(checked){if(selected.length>=6){setNotice("最多同时对照 6 个地址；请先移除一项。");return;}values[url]="unclassified";}
    else delete values[url];
    setSelection({snapshot,values});setNotice("");
  }
  const busy=snapshot.status==="loading";
  return <section className="public-research-panel" aria-label="公开资料检索">
    <header className="public-research-heading"><div><p className="research-eyebrow">外部资料 · 显式检索</p><h3>公开资料检索</h3></div><span className="research-state">{busy?"检索中":snapshot.status==="read"?"已返回 · 待核验":snapshot.status==="idle"?"尚未检索":snapshot.status==="unavailable"?"尚未接线":"结果需核对"}</span></header>
    <p>手动填写可公开的关键词。不会自动使用研究问题、正文、附件或模型生成的链接；结果与作者判断分别保留。</p>
    {onSearch?<p>本轮范围：英文 Wikipedia 词条导言、Academia Stack Exchange 问题正文、OpenAlex 元数据与可用摘要。不是全网或中文完整覆盖；wikitext 保留原表示，全文仅指社区问题正文。</p>:null}
    <label>公开检索关键词<input aria-label="公开检索关键词" value={query} maxLength={1000} disabled={busy||acting} onChange={event=>{setQuery(event.target.value);setNotice("");}}/></label>
    <fieldset disabled={busy||acting}><legend>检索来源范围</legend>{(Object.entries(publicResearchFamilies) as [PublicResearchFamily,string][]).map(([id,label])=><label key={id}><input type="checkbox" checked={families.includes(id)} onChange={event=>setFamilies(previous=>event.target.checked?[...previous,id]:previous.filter(f=>f!==id))}/>{label}</label>)}</fieldset>
    <div className="research-reference-actions"><button type="button" disabled={!onSearch||busy||acting||!query.trim()||!families.length} title={!onSearch?"百科、社区、科研检索尚未接线":undefined} onClick={()=>onSearch?.(query,[...families])}>检索公开资料</button>{busy&&onCancel?<button type="button" onClick={onCancel}>请求停止公开检索</button>:null}<button type="button" disabled={readOnly||!query.trim()||!families.length||kept===plan} onClick={()=>keep(plan)}>把检索计划加入未决草稿</button></div>
    {!query.trim()||!families.length?<p className="research-action-reason">{!query.trim()?"先填写“公开检索关键词”":"至少选择一个“检索来源范围”"}，检索按钮才可用；这一步不会自动使用研究问题或正文。</p>:readOnly?<p className="research-action-reason">当前研究页为只读，保存或取得写入权后才能把检索计划加入草稿。</p>:null}
    <p role={snapshot.status==="failed"?"alert":"status"}>{snapshot.status==="unavailable"?"百科、社区、科研检索尚未接线；没有发出请求，结果未知。":snapshot.status==="idle"?"尚未检索公开资料。":busy?"正在检索公开资料；尚无完成结论。":snapshot.status==="failed"?"公开检索未确认；是否存在结果仍未知，请显式回读原请求。":snapshot.status==="cancelled"?"本页已停止等待；远端是否停止仍未知。":!current?`以下是上次关键词“${result?.query}”与原范围的结果；输入已变化，请重新检索。`:"已收到本次检索返回；各来源是否完成分别列明，内容尚未核验。"}</p>
    {requestId?<p>本次请求标识：<code>{requestId}</code>；保留用于回读，不自动重试。</p>:null}
    {onRead&&requestId?<button type="button" disabled={busy||acting} onClick={()=>onRead()}>回读本次公开请求</button>:null}
    {onList?<button type="button" disabled={busy||acting} onClick={onList}>恢复最近公开请求记录</button>:null}
    {journal.length?<ul aria-label="最近公开请求">{journal.map(item=><li key={item.request_id}>{item.query} · {item.state}<button type="button" disabled={busy||acting} onClick={()=>onRead?.(item)}>回读请求 {item.query}</button></li>)}</ul>:null}
    {receipt?<><p>请求状态：{receipt.state} · 知识采用：未执行。</p><RawReceiptButton label="公开检索正式回执与原始来源" payload={receipt} category="data"/>{receipt.channels?.map(channel=>channel.raw_source&&onOpenRaw?<button type="button" key={channel.family} onClick={()=>onOpenRaw(channel.raw_source!)}>读取{publicResearchFamilies[channel.family]}原始 API 原件</button>:null)}</>:null}
    {message?<p role="status">{message}</p>:null}
    {result?<>
      <ul aria-label="本次来源状态">{result.families.map(f=>{const channels=result.channels.filter(row=>row.family===f);return <li key={f}>{publicResearchFamilies[f]}：{channels.length===1?channelLabels[channels[0].status]:"状态未知"}</li>;})}</ul>
      <label>结果内容范围<select aria-label="结果内容范围" value={content} onChange={event=>setContent(event.target.value)}><option value="all">全部返回内容</option>{Object.entries(contentLabels).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
      <p>{groups.size?`收到 ${result.hits.length} 条记录，按相同地址分组为 ${groups.size} 项；原记录均保留。`:(allComplete?"本次所选来源均完成，未返回匹配结果。":"本次未返回记录；未完成来源是否存在结果仍未知。")}{groups.size>0&&visible.length===0?" 当前内容筛选没有匹配项。":""}</p>
      <ul className="public-research-results">{visible.map(([url,hits],i)=><li key={url} data-selected={focus?.snapshot===snapshot&&focus.url===url}><article><div className="research-evidence-heading"><button type="button" aria-pressed={focus?.snapshot===snapshot&&focus.url===url} onClick={()=>setFocus({snapshot,url})}>聚焦结果 {i+1}</button><span>{hits.length} 条原始返回记录</span></div><h4>{hits[0].title}</h4><p>{hits.map(hit=>`${publicResearchFamilies[hit.family]} / ${hit.provider}`).join("；")}</p><p>{url}</p>{officialUrl(url)?<a href={url} target="_blank" rel="noopener noreferrer">打开官方记录页</a>:null}<label><input type="checkbox" checked={Object.hasOwn(chosen,url)} disabled={!current||acting} onChange={event=>choose(url,event.target.checked)}/>对照结果 {i+1}</label><details open={focus?.snapshot===snapshot&&focus.url===url}><summary>查看结果 {i+1} 详情 · 相同地址 {hits.length} 条记录</summary>{hits.map(hit=><div key={hit.id}><p>{hit.title} · {hit.provider} · {contentLabels[hit.content]}</p><p>取得时间：{hit.retrievedAt}</p><p>许可：{hit.license??"未知"} · 免费条件：{hit.freeAccess==="free"?"本次返回声明免费；后续条件仍需核对":"未知"}</p><p>原文定位：{hit.locator??"未提供；不能声称已定位"}</p><blockquote>{hit.excerpt||"未取得正文或摘录"}</blockquote>{onMaterialize?<button type="button" disabled={readOnly||busy||acting||!current} onClick={()=>onMaterialize(hit)}>将{hit.title}固定快照与原始 API 加入材料</button>:null}</div>)}<RawReceiptButton label={`公开检索结果 ${i+1} 的完整记录`} payload={hits} category="data"/></details></article></li>)}</ul>
      {selected.length?<section aria-label="公开来源对照"><h4>作者对照 · {selected.length}/6</h4><p>支持、反对、冲突是作者标注；相同地址或多条记录不证明来源独立，也不代表专业核验。{onCompare?" 保存对照前会固定所选完整派生快照并核对定位（每份最多16KiB）；定位不指向原API字节或原站。":""}</p><div className="public-research-comparison">{selected.map(([url,hits],i)=><article key={url}><h5>{hits[0].title}</h5><p>{hits.map(hit=>`${hit.provider} · ${hit.excerpt||contentLabels[hit.content]}`).join("\n")}</p><label>对照 {i+1} 判断<select aria-label={`对照 ${i+1} 判断`} value={chosen[url]} disabled={!current||acting} onChange={event=>setSelection({snapshot,values:{...chosen,[url]:event.target.value as Stance}})}>{Object.entries(stanceLabels).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label></article>)}</div><button type="button" disabled={readOnly||acting||!current||kept===comparison} onClick={()=>void keepComparison()}>把对照记录加入未决草稿</button></section>:null}
    </>:null}
    {notice?<p role="status">{notice}</p>:null}
  </section>;
}
function officialUrl(value:string){try{const url=new URL(value);return url.protocol==="https:"&&!url.username&&!url.password&&!url.port&&["en.wikipedia.org","academia.stackexchange.com","openalex.org"].includes(url.hostname);}catch{return false;}}
