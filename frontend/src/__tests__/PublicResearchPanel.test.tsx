import { expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
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
 expect(search).toHaveBeenCalledWith("公开关键词",["encyclopedia","research"]);
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
