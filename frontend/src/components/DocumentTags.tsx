import type {DocumentDto,DocumentSummaryDto} from "../api/generated/core-contract";
import {useState} from "react";

export function normalizedTag(value:string):string { return value.trim().replace(/^#/,"").toLowerCase(); }
export function matchesTag(document:DocumentSummaryDto,value:string):boolean {
 const key=normalizedTag(value);
 return !key || Boolean(document.tags?.some(tag=>tag.key===key || tag.key.startsWith(key+"/")));
}
export function TagNavigation({documents,value,onChange}:{documents:DocumentSummaryDto[];value:string;onChange:(value:string)=>void}) {
 const [sort,setSort]=useState<"name"|"count">("name");
 const [view,setView]=useState<"flat"|"tree">("flat");
 const [collapsed,setCollapsed]=useState<Set<string>>(()=>new Set());
 const facets=new Map<string,{name:string;documents:Set<string>}>();
 for(const document of documents)for(const tag of document.tags??[]) {
  const names=tag.name.split("/");const keys=tag.key.split("/");
  for(let index=1;index<=keys.length;index++) {
   const key=keys.slice(0,index).join("/");
   const facet=facets.get(key)??{name:names.slice(0,index).join("/"),documents:new Set<string>()};
   facet.documents.add(document.document_id);facets.set(key,facet);
  }
 }
 const ordered=[...facets].sort(([a,left],[b,right])=>(sort==="count"?right.documents.size-left.documents.size:0)||a.localeCompare(b));
 const tagButton=(key:string,facet:{name:string;documents:Set<string>},name=facet.name)=><button key={key} type="button" aria-label={`筛选标签 ${facet.name}，${facet.documents.size}篇已加载文档`} aria-pressed={normalizedTag(value)===key} onClick={()=>onChange(key)}>#{name} <span>{facet.documents.size}</span></button>;
 const children=new Map<string,string[]>();
 for(const [key] of ordered) {
  const slash=key.lastIndexOf("/");const parent=slash<0?"":key.slice(0,slash);
  const siblings=children.get(parent);if(siblings)siblings.push(key);else children.set(parent,[key]);
 }
 function branches(parent:string):React.ReactNode {
  return <ul>{(children.get(parent)??[]).map(key=>{
   const facet=facets.get(key)!;const hasChildren=children.has(key);const expanded=!collapsed.has(key);
   return <li key={key}><div className="document-tag-branch">
    {hasChildren?<button type="button" aria-label={`${expanded?"收起":"展开"} ${facet.name} 的下级标签`} aria-expanded={expanded} onClick={()=>setCollapsed(current=>{const next=new Set(current);if(next.has(key))next.delete(key);else next.add(key);return next;})}><span aria-hidden="true">{expanded?"▾":"▸"}</span></button>:null}
    {tagButton(key,facet,facet.name.split("/").at(-1))}
   </div>{hasChildren&&expanded?branches(key):null}</li>;
  })}</ul>;
 }
 return <section className="document-tag-navigation" aria-label="已保存标签导航">
  <label>标签，包含下级 <input type="search" aria-label="按标签筛选，包含下级标签" value={value} onChange={event=>onChange(event.target.value)}/></label>
  {value?<button type="button" onClick={()=>onChange("")}>清除标签筛选</button>:null}
  <p>标签来自已保存版本；计数和筛选覆盖已加载文档，可继续分页。</p>
  <div className="document-tag-controls"><label>标签排序方式<select value={sort} onChange={event=>setSort(event.target.value as "name"|"count")}><option value="name">按名称</option><option value="count">按文档数量</option></select></label><label>标签显示方式<select value={view} onChange={event=>setView(event.target.value as "flat"|"tree")}><option value="flat">平面显示</option><option value="tree">层级显示</option></select></label></div>
  <p>父级计数包含下级标签；同一篇文档只计一次。排序、折叠和显示方式不修改已保存标签。</p>
  {view==="tree"?<div className="document-tag-tree" aria-label="标签层级列表">{branches("")}</div>:<div className="document-tag-chips">{ordered.map(([key,facet])=>tagButton(key,facet))}</div>}
  {documents.some(document=>document.metadata_status!=="COMPLETE"||!Array.isArray(document.tags))?<p role="status">部分已加载文档的标签信息未知或不完整；当前结果不能证明全库没有此标签。</p>:null}
 </section>;
}
const issueLabels:Record<string,string>={FRONTMATTER_LIMIT:"属性区超过读取上限",INVALID_OR_UNSUPPORTED_YAML:"属性格式无效或暂不支持",UNTERMINATED_FRONTMATTER:"属性区没有结束标记",TAGS_PROPERTY_REQUIRES_LIST:"tags 属性需要列表",NON_TEXT_TAG:"标签列表含非文本值",INVALID_TAG:"有标签不符合可用格式",TAG_LIMIT:"标签超过读取上限",PROPERTIES_MAPPING_REQUIRED_OR_LIMIT:"属性需要不超过64项的映射",UNSUPPORTED_EDITOR_NODE:"部分内容节点暂不支持标签提取",EDITOR_DEPTH:"内容层级超过读取上限"};
export function SavedDocumentMetadata({document,onTag}:{document:DocumentDto;onTag:(tag:string)=>void}) {
 return <section className="saved-document-metadata" aria-label="已保存标签与属性">
  <h4>标签与属性 · v{document.version}</h4>
  {document.tags?<div className="document-tag-chips">{document.tags.map(tag=><button key={tag.key} type="button" onClick={()=>onTag(tag.key)} aria-label={`查看标签 ${tag.name} 的文档`}>#{tag.name}</button>)}{!document.tags.length&&document.metadata_status==="COMPLETE"?<p>此保存版本没有标签。</p>:null}</div>:<p>当前核心未提供此版本的标签信息。</p>}
  {document.metadata_status==="PARTIAL"?<p role="status">部分标签或属性无法解析；原文保持不变。{document.metadata_issues?.map(code=>issueLabels[code]??"存在尚未识别的元数据限制").join("；")}</p>:null}
  {document.properties?<details><summary>保存版属性（{Object.keys(document.properties).length}项）</summary><dl>{Object.entries(document.properties).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{typeof value==="string"?value:JSON.stringify(value)}</dd></div>)}</dl><p>属性取自保存正文；修改正文并保存后更新。日期按原文本保留，嵌套值按结构显示；不代表原软件全部属性能力。</p></details>:null}
 </section>;
}
