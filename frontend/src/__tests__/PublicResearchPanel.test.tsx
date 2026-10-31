import { expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { PublicResearchPanel, type PublicResearchHit, type PublicResearchSnapshot } from "../components/PublicResearchPanel";

const hit=(id:string,url="https://example.test/same"):PublicResearchHit=>({id,url,family:"research",provider:"合成科研来源",title:`材料 ${id}`,retrievedAt:"2026-10-20T00:00:00Z",content:"excerpt",excerpt:`独立返回的摘录 ${id}\r\n保留`,locator:null,license:null,freeAccess:"unknown"});
const read=(hits:PublicResearchHit[]):PublicResearchSnapshot=>({status:"read",query:"公开关键词",families:["encyclopedia","community","research"],channels:[{family:"encyclopedia",status:"complete"},{family:"community",status:"offline"},{family:"research",status:"limited"}],hits});
function query(){fireEvent.change(screen.getByRole("textbox",{name:"公开检索关键词"}),{target:{value:"公开关键词"}});}

it("never sends a query from an unavailable production panel and keeps only an explicit authored plan",()=>{
 const save=vi.fn((_text:string)=>true);render(<PublicResearchPanel onKeepNote={save}/>);
 expect(screen.getByRole("textbox",{name:"公开检索关键词"})).toHaveValue("");
 expect(screen.getByRole("button",{name:"检索公开资料"})).toBeDisabled();query();
 fireEvent.click(screen.getByRole("button",{name:"把检索计划加入未决草稿"}));
 expect(save).toHaveBeenCalledOnce();expect(save.mock.calls[0][0]).toContain("未执行外部检索");
 expect(screen.getByRole("button",{name:"把检索计划加入未决草稿"})).toBeDisabled();
});

it("passes only explicitly entered public terms and selected families to a supplied presentation callback",()=>{
 const search=vi.fn();render(<PublicResearchPanel snapshot={{status:"idle"}} onSearch={search} onKeepNote={()=>true}/>);
 expect(search).not.toHaveBeenCalled();query();fireEvent.click(screen.getByRole("checkbox",{name:"社区"}));
 fireEvent.click(screen.getByRole("button",{name:"检索公开资料"}));
 expect(search).toHaveBeenCalledWith("公开关键词",["encyclopedia","research"],"academia");
});

it("changes only the bounded forum plan until an explicit search and protects old comparison choices",()=>{
 const search=vi.fn();render(<PublicResearchPanel snapshot={read([hit("forum")])} onSearch={search} onKeepNote={()=>true}/>);query();
 expect(screen.getByRole("combobox",{name:"社区论坛站点"})).toHaveValue("academia");
 fireEvent.click(screen.getByRole("checkbox",{name:"对照结果 1"}));
 fireEvent.change(screen.getByRole("combobox",{name:"社区论坛站点"}),{target:{value:"stats"}});
 expect(search).not.toHaveBeenCalled();
 expect(screen.getByRole("checkbox",{name:"对照结果 1"})).toBeDisabled();
 expect(screen.getByRole("button",{name:"把对照记录加入未决草稿"})).toBeDisabled();
 expect(screen.getByRole("heading",{name:"材料 forum",level:4})).toBeInTheDocument();
 fireEvent.click(screen.getByRole("button",{name:"检索公开资料"}));
 expect(search).toHaveBeenCalledWith("公开关键词",["encyclopedia","community","research"],"stats");
});

it("shows the failed provider and Crossref fallback separately without claiming an authoritative page or complete search",()=>{
 const response=read([{...hit("doi","https://doi.org/10.1234/synthetic"),provider:"crossref",content:"metadata",excerpt:""}]);
 if(response.status!=="read")throw Error("fixture");
 response.channels=[{family:"encyclopedia",provider:"wikipedia",status:"complete"},{family:"community",provider:"stackexchange",status:"complete"},{family:"research",provider:"openalex",status:"limited"},{family:"research",provider:"crossref",status:"complete"}];
 render(<PublicResearchPanel snapshot={response} onKeepNote={()=>true}/>);query();
 const status=screen.getByRole("list",{name:"本次来源状态"});
 expect(within(status).getByText("科研 / OpenAlex：限流，结果可能不完整")).toBeInTheDocument();
 expect(within(status).getByText(/科研 \/ Crossref：本次检索完成/)).toHaveTextContent("回退来源，仅元数据");
 expect(screen.getByText(/部分来源尚未完成/)).toBeInTheDocument();
 expect(screen.getByRole("link",{name:"打开来源页面"})).toHaveAttribute("href","https://doi.org/10.1234/synthetic");
 expect(screen.queryByRole("link",{name:/官方/})).not.toBeInTheDocument();
 expect(screen.getByText("未取得正文或摘录")).toBeInTheDocument();
});

it("opens a returned stats discussion as a source page",()=>{
 const response=read([{...hit("stats","https://stats.stackexchange.com/questions/123/example"),family:"community",provider:"stackexchange"}]);
 render(<PublicResearchPanel snapshot={response} onKeepNote={()=>true}/>);query();
 expect(screen.getByRole("link",{name:"打开来源页面"})).toHaveAttribute("href","https://stats.stackexchange.com/questions/123/example");
});

it("preserves every same-address record and writes comparisons only as unverified authored notes",()=>{
 const save=vi.fn((_text:string)=>true);const hits=[hit("first"),hit("second"),hit("other","https://example.test/other")];
 render(<PublicResearchPanel snapshot={read(hits)} onKeepNote={save}/>);query();
 expect(screen.getByText("收到 3 条记录，按相同地址分组为 2 项；原记录均保留。")).toBeInTheDocument();
 expect(screen.getByText("独立返回的摘录 second 保留",{exact:false})).toBeInTheDocument();
 fireEvent.click(screen.getByRole("checkbox",{name:"对照结果 1"}));
 fireEvent.click(screen.getByRole("checkbox",{name:"对照结果 2"}));
 const compare=screen.getByRole("region",{name:"公开来源对照"});
 fireEvent.change(within(compare).getByRole("combobox",{name:"对照 1 判断"}),{target:{value:"conflict"}});
 fireEvent.change(within(compare).getByRole("combobox",{name:"对照 2 判断"}),{target:{value:"opposes"}});
 fireEvent.click(within(compare).getByRole("button",{name:"把对照记录加入未决草稿"}));
 const note=save.mock.calls[0][0];expect(note).toContain("未核验，未绑定固定原件");
 for(const record of hits){expect(note).toContain(record.url);expect(note).toContain(record.title);expect(note).toContain(record.excerpt);}
 expect(note).toContain("存在冲突");expect(note).toContain("反对");expect(note).toContain("许可：未知");
});

it("does not call a partial empty response a completed zero-result search",()=>{
 const view=render(<PublicResearchPanel snapshot={read([])} onKeepNote={()=>true}/>);query();
 expect(screen.getByText("本次未返回记录；未完成来源是否存在结果仍未知。")).toBeInTheDocument();
 const complete=read([]);if(complete.status!=="read")throw new Error("fixture");complete.channels=complete.families.map(family=>({family,status:"complete"}));
 view.rerender(<PublicResearchPanel snapshot={complete} onKeepNote={()=>true}/>);
 expect(screen.getByText("本次所选来源均完成，未返回匹配结果。")).toBeInTheDocument();
});

it("distinguishes reading the stored receipt from a new explicit network search and keeps partial results",()=>{
 const search=vi.fn(),readReceipt=vi.fn();
 render(<PublicResearchPanel snapshot={read([hit("retained")])} requestId="synthetic-request" onRead={readReceipt} onSearch={search} onKeepNote={()=>true}/>);query();
 expect(screen.getByText(/回读只读取这次请求的已存回执/)).toHaveTextContent("不会重新联网");
 expect(screen.getByText(/部分来源尚未完成/)).toHaveTextContent("已返回的结果仍保留");
 fireEvent.click(screen.getByRole("button",{name:"回读本次公开请求"}));
 expect(readReceipt).toHaveBeenCalledOnce();expect(search).not.toHaveBeenCalled();
 expect(screen.getByText("材料 retained")).toBeInTheDocument();
 fireEvent.click(screen.getByRole("button",{name:"检索公开资料"}));
 expect(search).toHaveBeenCalledWith("公开关键词",["encyclopedia","community","research"],"academia");
 expect(readReceipt).toHaveBeenCalledOnce();
});

it("keeps old query and scope results visible but disallows binding or comparison save",()=>{
 render(<PublicResearchPanel snapshot={read([hit("a")])} onKeepNote={()=>true}/>);query();
 fireEvent.click(screen.getByRole("checkbox",{name:"对照结果 1"}));
 fireEvent.change(screen.getByRole("textbox",{name:"公开检索关键词"}),{target:{value:"新关键词"}});
 expect(screen.getByRole("checkbox",{name:"对照结果 1"})).toBeDisabled();
 expect(screen.getByRole("button",{name:"把对照记录加入未决草稿"})).toBeDisabled();
 expect(screen.getByText(/以下是上次关键词/)).toHaveTextContent("公开关键词");
});

it("does not promote ambiguous duplicate channel states to a complete empty search",()=>{
 const response=read([]);if(response.status!=="read")throw new Error("fixture");
 response.channels=response.families.map(family=>({family,status:"complete"}));
 response.channels.push({family:"community",status:"failed"});
 render(<PublicResearchPanel snapshot={response} onKeepNote={()=>true}/>);query();
 expect(screen.getByText("本次未返回记录；未完成来源是否存在结果仍未知。")).toBeInTheDocument();
});

it("retains comparison selection when appending is rejected and respects readonly",()=>{
 const save=vi.fn((_text:string)=>false);const snapshot=read([hit("a")]);
 const view=render(<PublicResearchPanel snapshot={snapshot} onKeepNote={save}/>);query();
 fireEvent.click(screen.getByRole("checkbox",{name:"对照结果 1"}));
 fireEvent.click(screen.getByRole("button",{name:"把对照记录加入未决草稿"}));
 expect(screen.getByRole("checkbox",{name:"对照结果 1"})).toBeChecked();
 expect(screen.getByText(/未加入未决草稿/)).toBeInTheDocument();
 view.rerender(<PublicResearchPanel snapshot={snapshot} onKeepNote={save} readOnly/>);
 expect(screen.getByRole("button",{name:"把对照记录加入未决草稿"})).toBeDisabled();expect(save).toHaveBeenCalledOnce();
});

it("never mistakes failed, loading or cancelled states for completed search",()=>{
 const cancel=vi.fn();const view=render(<PublicResearchPanel snapshot={{status:"failed"}} onKeepNote={()=>true}/>);
 expect(screen.getByRole("alert")).toHaveTextContent("是否存在结果仍未知");
 view.rerender(<PublicResearchPanel snapshot={{status:"loading"}} onCancel={cancel} onKeepNote={()=>true}/>);
 fireEvent.click(screen.getByRole("button",{name:"请求停止公开检索"}));expect(cancel).toHaveBeenCalledOnce();
 view.rerender(<PublicResearchPanel snapshot={{status:"cancelled"}} onKeepNote={()=>true}/>);
 expect(screen.getByText(/远端是否停止仍未知/)).toBeInTheDocument();
});

it("bounds comparison to six addresses without dropping retrieved records",()=>{
 const response=read(Array.from({length:7},(_,i)=>hit(String(i),`https://example.test/${i}`)));
 render(<PublicResearchPanel snapshot={response} onKeepNote={()=>true}/>);query();
 for(let i=1;i<=7;i++)fireEvent.click(screen.getByRole("checkbox",{name:`对照结果 ${i}`}));
 expect(screen.getAllByRole("checkbox",{checked:true})).toHaveLength(9);
 expect(screen.getByText("最多同时对照 6 个地址；请先移除一项。")).toBeInTheDocument();
 expect(screen.getByRole("checkbox",{name:"对照结果 7"})).not.toBeChecked();
 expect(screen.getByText("收到 7 条记录，按相同地址分组为 7 项；原记录均保留。")).toBeInTheDocument();
});

it("does not carry old comparison choices into a newer response",()=>{
 const first=read([hit("old")]);const view=render(<PublicResearchPanel snapshot={first} onKeepNote={()=>true}/>);query();
 fireEvent.click(screen.getByRole("checkbox",{name:"对照结果 1"}));expect(screen.getByRole("region",{name:"公开来源对照"})).toBeInTheDocument();
 view.rerender(<PublicResearchPanel snapshot={read([hit("new")])} onKeepNote={()=>true}/>);
 expect(screen.getByRole("checkbox",{name:"对照结果 1"})).not.toBeChecked();expect(screen.queryByRole("region",{name:"公开来源对照"})).not.toBeInTheDocument();
});


it("submits every exact same-address hit with the authored stance to the binding consumer, not the unbound note callback",async()=>{
 const save=vi.fn(()=>true),compare=vi.fn(async()=>true),snapshot=read([hit("first"),hit("second")]);
 render(<PublicResearchPanel snapshot={snapshot} onKeepNote={save} onCompare={compare}/>);query();
 fireEvent.click(screen.getByRole("checkbox",{name:"对照结果 1"}));
 fireEvent.change(screen.getByRole("combobox",{name:"对照 1 判断"}),{target:{value:"conflict"}});
 fireEvent.click(screen.getByRole("button",{name:"把对照记录加入未决草稿"}));
 await waitFor(()=>expect(compare).toHaveBeenCalledWith([{family:"research",id:"first",stance:"conflict"},{family:"research",id:"second",stance:"conflict"}]));
 expect(save).not.toHaveBeenCalled();await waitFor(()=>expect(screen.getByRole("button",{name:"把对照记录加入未决草稿"})).toBeDisabled());
});


it("focuses an evidence card without selecting comparison or materializing and clears focus for a new receipt",()=>{
 const first=read([hit("a"),hit("b","https://example.test/other")]);const materialize=vi.fn(),keep=vi.fn(()=>true);
 const view=render(<PublicResearchPanel snapshot={first} onKeepNote={keep} onMaterialize={materialize}/>);query();
 fireEvent.click(screen.getByRole("button",{name:"聚焦结果 2"}));
 expect(screen.getByRole("button",{name:"聚焦结果 2"})).toHaveAttribute("aria-pressed","true");
 expect(screen.getByRole("checkbox",{name:"对照结果 2"})).not.toBeChecked();
 expect(materialize).not.toHaveBeenCalled();expect(keep).not.toHaveBeenCalled();
 view.rerender(<PublicResearchPanel snapshot={read([hit("new")])} onKeepNote={keep} onMaterialize={materialize}/>);
 expect(screen.getByRole("button",{name:"聚焦结果 1"})).toHaveAttribute("aria-pressed","false");
});
