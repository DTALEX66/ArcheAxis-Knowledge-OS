import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CanonicalExpressionBoard } from "../components/CanonicalExpressionBoard";
import { parseExpressionDocument, type ExpressionDocument, type ExpressionMedia } from "../presentation/expression";
const initial: ExpressionDocument = { schema: "archeaxis.expression/v1", nodes: [{ id: "one", type: "text", x: -80, y: -50, width: 240, height: 180, text: "起点\n中文" }, { id: "two", type: "text", x: 120, y: 100, width: 240, height: 180, text: "终点" }], edges: [{ id: "edge", fromNode: "one", toNode: "two", label: "引用关系" }], context: { knowledge_id: "actual-kid" }, capability_metadata: { future: { owner: "未知载荷", supported: false } } };
const media: ExpressionMedia = { source_id: "s_real-source", sha256: "a".repeat(64), media_type: "image/png" };
function Harness({ value = initial, onChange = vi.fn(), ...props }: Partial<React.ComponentProps<typeof CanonicalExpressionBoard>>) {
 const [state,setState]=useState(value);return <CanonicalExpressionBoard {...props} value={state} onChange={next=>{setState(next);onChange(next);}} />;
}
afterEach(()=>vi.restoreAllMocks());
describe("CanonicalExpressionBoard",()=>{
 it("emits changes through the owner and leaves incoming value untouched",()=>{
  const change=vi.fn();render(<CanonicalExpressionBoard value={initial} onChange={change}/>);
  fireEvent.change(screen.getByLabelText("节点文字 1"),{target:{value:"只改此节点"}});
  const next=change.mock.calls[0][0];expect(next.nodes[0].text).toBe("只改此节点");expect(initial.nodes[0].text).toBe("起点\n中文");expect(next.context).toEqual(initial.context);expect(next.capability_metadata).toEqual(initial.capability_metadata);expect(next.edges).toEqual(initial.edges);expect(screen.getByLabelText("节点文字 1")).toHaveValue(initial.nodes[0].text);
 });
 it("preserves full Chinese IME input and multiline Enter without committing or moving",()=>{
  const change=vi.fn();render(<Harness onChange={change}/>);const area=screen.getByLabelText("节点文字 1");
  fireEvent.compositionStart(area);fireEvent.change(area,{target:{value:"中文输入过程\n第二行"}});fireEvent.keyDown(area,{key:"Enter",isComposing:true});fireEvent.keyDown(area,{key:"ArrowLeft"});fireEvent.compositionEnd(area);fireEvent.change(area,{target:{value:"中文输入完成\n第二行\n"}});
  expect(area).toHaveValue("中文输入完成\n第二行\n");const last=change.mock.calls.at(-1)![0];expect(last.nodes[0].text).toBe("中文输入完成\n第二行\n");expect(last.nodes[0].x).toBe(-80);
 });
 it("adds a UUID text node without a prompt",()=>{
  const prompt=vi.spyOn(window,"prompt");const uuid=vi.spyOn(crypto,"randomUUID").mockReturnValue("12345678-1234-1234-1234-123456789012");const change=vi.fn();render(<Harness onChange={change}/>);fireEvent.click(screen.getByRole("button",{name:"添加文本节点"}));expect(uuid).toHaveBeenCalledOnce();expect(prompt).not.toHaveBeenCalled();expect(change.mock.calls[0][0].nodes.at(-1)).toMatchObject({id:"12345678-1234-1234-1234-123456789012",type:"text",text:""});
 });
 it("keyboard movement retains negative coordinates and does not eat text editing keys",()=>{
  const change=vi.fn();render(<Harness onChange={change}/>);const node=screen.getByRole("article",{name:"节点 1"});fireEvent.keyDown(node,{key:"ArrowLeft"});fireEvent.keyDown(node,{key:"ArrowUp",shiftKey:true});expect(change.mock.calls.at(-1)![0].nodes[0]).toMatchObject({x:-81,y:-60});
  fireEvent.keyDown(screen.getByLabelText("节点文字 1"),{key:"ArrowRight"});expect(change).toHaveBeenCalledTimes(2);
 });
 it("edits negative positions and dimensions without normalizing context",()=>{
  const change=vi.fn();render(<Harness onChange={change}/>);fireEvent.change(screen.getByLabelText("当前节点"),{target:{value:"one"}});
  fireEvent.change(screen.getByLabelText("X 坐标"),{target:{value:"-123.5"}});fireEvent.blur(screen.getByLabelText("X 坐标"));fireEvent.change(screen.getByLabelText("宽度"),{target:{value:"1"}});fireEvent.blur(screen.getByLabelText("宽度"));expect(change.mock.calls.at(-1)![0].nodes[0]).toMatchObject({x:-123.5,width:1});expect(change.mock.calls.at(-1)![0].context).toEqual(initial.context);
 });
 it("rejects oversized coordinates/dimensions without silently clamping",()=>{
  const change=vi.fn();render(<Harness onChange={change}/>);fireEvent.change(screen.getByLabelText("当前节点"),{target:{value:"one"}});fireEvent.change(screen.getByLabelText("X 坐标"),{target:{value:"100001"}});fireEvent.blur(screen.getByLabelText("X 坐标"));expect(screen.getByRole("alert")).toHaveTextContent("坐标");fireEvent.change(screen.getByLabelText("高度"),{target:{value:"0"}});fireEvent.blur(screen.getByLabelText("高度"));expect(screen.getByRole("alert")).toHaveTextContent("尺寸");expect(change).not.toHaveBeenCalled();
 });
 it("rejects UTF8 byte overflow without truncation",()=>{
  const change=vi.fn();render(<Harness onChange={change}/>);fireEvent.change(screen.getByLabelText("节点文字 1"),{target:{value:"中".repeat(5462)}});expect(change).not.toHaveBeenCalled();expect(screen.getByRole("alert")).toHaveTextContent("未截断");
 });
 it("adds, edits and removes a UUID edge through real endpoint selections",()=>{
  const change=vi.fn();render(<Harness onChange={change}/>);fireEvent.change(screen.getByLabelText("连线起点"),{target:{value:"two"}});fireEvent.change(screen.getByLabelText("连线终点"),{target:{value:"one"}});fireEvent.change(screen.getByLabelText("新连线文字"),{target:{value:"反向\n关系"}});fireEvent.click(screen.getByRole("button",{name:"添加连线"}));expect(change.mock.calls.at(-1)![0].edges[1]).toMatchObject({fromNode:"two",toNode:"one",label:"反向\n关系"});
  fireEvent.change(screen.getByLabelText("连线文字 2"),{target:{value:"新关系"}});expect(change.mock.calls.at(-1)![0].edges[1].label).toBe("新关系");fireEvent.click(screen.getByLabelText("删除连线 2"));expect(change.mock.calls.at(-1)![0].edges).toEqual(initial.edges);
 });
 it("rejects a missing endpoint instead of inventing a node",()=>{
  const change=vi.fn();render(<Harness onChange={change}/>);fireEvent.click(screen.getByRole("button",{name:"添加连线"}));expect(change).not.toHaveBeenCalled();expect(screen.getByRole("alert")).toHaveTextContent("真实起点");
 });
 it("removes all incident edges together with a node",()=>{
  const change=vi.fn();render(<Harness onChange={change}/>);fireEvent.click(screen.getByLabelText("删除节点 1"));expect(change.mock.calls[0][0].nodes.map((n:{id:string})=>n.id)).toEqual(["two"]);expect(change.mock.calls[0][0].edges).toEqual([]);
 });
 it("adds only validated actual media metadata and invokes host renderer",async()=>{
  const change=vi.fn();const renderer=vi.fn((m:ExpressionMedia)=><img src="blob:verified-core-fixture" alt={`来源 ${m.source_id}`}/>);render(<Harness onChange={change} onAddMedia={async()=>media} renderMedia={renderer}/>);fireEvent.click(screen.getByRole("button",{name:"添加媒体节点"}));await waitFor(()=>expect(screen.getByRole("img")).toHaveAttribute("src","blob:verified-core-fixture"));expect(change.mock.calls[0][0].nodes.at(-1)).toMatchObject({type:"media",media});expect(renderer).toHaveBeenCalledWith(media,expect.objectContaining({type:"media"}));
 });
 it("does not render active SVG/HTML or add unverified media",async()=>{
  const change=vi.fn();const renderer=vi.fn();render(<Harness onChange={change} onAddMedia={async()=>({...media,media_type:"image/svg+xml"} as unknown as ExpressionMedia)} renderMedia={renderer}/>);fireEvent.click(screen.getByRole("button",{name:"添加媒体节点"}));await waitFor(()=>expect(screen.getByRole("alert")).toHaveTextContent("无效"));expect(change).not.toHaveBeenCalled();expect(renderer).not.toHaveBeenCalled();
 });
 it("reports media read failure without inventing preview content",async()=>{
  const change=vi.fn();render(<Harness onChange={change} onAddMedia={async()=>{throw new Error("fixture failure");}}/>);fireEvent.click(screen.getByRole("button",{name:"添加媒体节点"}));await waitFor(()=>expect(screen.getByRole("alert")).toHaveTextContent("读取失败"));expect(change).not.toHaveBeenCalled();
 });
 it("does not let a late media request overwrite a changed controlled canvas",async()=>{
  let resolve!:(value:ExpressionMedia)=>void;const request=new Promise<ExpressionMedia>(r=>{resolve=r;});const change=vi.fn();const {rerender}=render(<CanonicalExpressionBoard value={initial} onChange={change} onAddMedia={()=>request}/>);fireEvent.click(screen.getByRole("button",{name:"添加媒体节点"}));rerender(<CanonicalExpressionBoard value={{...initial,nodes:[]}} onChange={change} onAddMedia={()=>request}/>);await act(async()=>{resolve(media);await request;});expect(change).not.toHaveBeenCalled();expect(screen.getByRole("alert")).toHaveTextContent("画布已变更");
 });
 it("read-only does not emit text, geometry, deletion or creation writes",()=>{
  const change=vi.fn();render(<Harness readOnly onChange={change}/>);expect(screen.getByRole("button",{name:"添加文本节点"})).toBeDisabled();expect(screen.getByLabelText("节点文字 1")).toHaveAttribute("readonly");fireEvent.keyDown(screen.getByRole("article",{name:"节点 1"}),{key:"ArrowLeft"});fireEvent.click(screen.getByLabelText("删除节点 1"));expect(change).not.toHaveBeenCalled();
 });
});

describe("expression strict read contract",()=>{
 it("returns original complete payload without stripping inert capability metadata",()=>{expect(parseExpressionDocument(initial)).toBe(initial);expect(parseExpressionDocument({...initial,context:null,capability_metadata:null})).not.toBeNull();});
 it("rejects unknown fields at every executable/document envelope boundary",()=>{
  for (const patch of [{...initial,future:true},{...initial,nodes:[{...initial.nodes[0],future:true}]},{...initial,edges:[{...initial.edges[0],future:true}]},{...initial,context:{future:"unknown"}},{...initial,nodes:[{...initial.nodes[0],type:"media",media:{...media,future:true}}]}])expect(parseExpressionDocument(patch)).toBeNull();
 });
 it("rejects duplicate identifiers, dangling edges, nonfinite geometry, forbidden media and overbudget inert metadata",()=>{
  for(const bad of [{...initial,nodes:[initial.nodes[0],initial.nodes[0]]},{...initial,edges:[{...initial.edges[0],toNode:"missing"}]},{...initial,nodes:[{...initial.nodes[0],x:Infinity}]},{...initial,nodes:[{...initial.nodes[0],media}]},{...initial,nodes:[{...initial.nodes[0],type:"media",media:{...media,media_type:"text/html"}}]},{...initial,capability_metadata:{key:"中".repeat(2000)}}])expect(parseExpressionDocument(bad)).toBeNull();
 });
});

it("pointer drag retains negative stored coordinates independently of render origin",()=>{
 const change=vi.fn();render(<Harness onChange={change}/>);const handle=screen.getByLabelText("拖动节点 1");
 const capture=vi.fn();Object.defineProperty(handle,"setPointerCapture",{value:capture});
 fireEvent(handle,new MouseEvent("pointerdown",{bubbles:true,button:0,clientX:100,clientY:100}));
 fireEvent(handle,new MouseEvent("pointermove",{bubbles:true,clientX:80,clientY:70}));
 fireEvent(handle,new MouseEvent("pointerup",{bubbles:true}));expect(change.mock.calls.at(-1)![0].nodes[0]).toMatchObject({x:-100,y:-80});expect(capture).toHaveBeenCalled();
});

it("allows intermediate minus and decimal geometry input before committing",()=>{
 const change=vi.fn();render(<Harness onChange={change}/>);fireEvent.change(screen.getByLabelText("当前节点"),{target:{value:"one"}});const field=screen.getByLabelText("X 坐标");fireEvent.change(field,{target:{value:"-"}});expect(field).toHaveValue("-");expect(change).not.toHaveBeenCalled();fireEvent.change(field,{target:{value:"-12.5"}});fireEvent.blur(field);expect(change.mock.calls[0][0].nodes[0].x).toBe(-12.5);
});

describe("expression pending edit contract",()=>{
 it("marks intermediate geometry dirty, keeps it after invalid blur, and clears only after commit/cancel",()=>{
  const pending=vi.fn();const change=vi.fn();render(<Harness onChange={change} onPendingEditChange={pending}/>);fireEvent.change(screen.getByLabelText("当前节点"),{target:{value:"one"}});const field=screen.getByLabelText("X 坐标");fireEvent.change(field,{target:{value:"-"}});expect(pending.mock.calls.at(-1)![0]).toBe(true);fireEvent.blur(field);expect(pending.mock.calls.at(-1)![0]).toBe(true);expect(field).toHaveValue("-");expect(change).not.toHaveBeenCalled();fireEvent.click(screen.getByLabelText("取消X 坐标修改"));expect(field).toHaveValue("-80");expect(pending.mock.calls.at(-1)![0]).toBe(false);
  fireEvent.change(field,{target:{value:"12."}});expect(pending.mock.calls.at(-1)![0]).toBe(true);fireEvent.blur(field);expect(change.mock.calls.at(-1)![0].nodes[0].x).toBe(12);expect(pending.mock.calls.at(-1)![0]).toBe(false);
 });
 it("preserves pending geometry across selected nodes and clears by Escape",()=>{
  const pending=vi.fn();render(<Harness onPendingEditChange={pending}/>);fireEvent.change(screen.getByLabelText("当前节点"),{target:{value:"one"}});fireEvent.change(screen.getByLabelText("X 坐标"),{target:{value:"-"}});fireEvent.change(screen.getByLabelText("当前节点"),{target:{value:"two"}});expect(pending.mock.calls.at(-1)![0]).toBe(true);fireEvent.change(screen.getByLabelText("当前节点"),{target:{value:"one"}});expect(screen.getByLabelText("X 坐标")).toHaveValue("-");fireEvent.keyDown(screen.getByLabelText("X 坐标"),{key:"Escape"});expect(pending.mock.calls.at(-1)![0]).toBe(false);
 });
 it("tracks endpoints and label drafts until explicit add or cancel",()=>{
  const pending=vi.fn();render(<Harness onPendingEditChange={pending}/>);fireEvent.change(screen.getByLabelText("连线起点"),{target:{value:"one"}});expect(pending.mock.calls.at(-1)![0]).toBe(true);fireEvent.click(screen.getByRole("button",{name:"取消未提交连线"}));expect(pending.mock.calls.at(-1)![0]).toBe(false);fireEvent.change(screen.getByLabelText("连线起点"),{target:{value:"one"}});fireEvent.change(screen.getByLabelText("连线终点"),{target:{value:"two"}});fireEvent.change(screen.getByLabelText("新连线文字"),{target:{value:"草稿"}});fireEvent.click(screen.getByRole("button",{name:"添加连线"}));expect(pending.mock.calls.at(-1)![0]).toBe(false);expect(screen.getByLabelText("连线起点")).toHaveValue("");expect(screen.getByLabelText("新连线文字")).toHaveValue("");
 });
 it("aggregates geometry and connection drafts without one cancellation clearing the other",()=>{
  const pending=vi.fn();render(<Harness onPendingEditChange={pending}/>);fireEvent.change(screen.getByLabelText("当前节点"),{target:{value:"one"}});fireEvent.change(screen.getByLabelText("X 坐标"),{target:{value:"-"}});fireEvent.change(screen.getByLabelText("新连线文字"),{target:{value:"尚未添加"}});fireEvent.click(screen.getByRole("button",{name:"取消未提交连线"}));expect(pending.mock.calls.at(-1)![0]).toBe(true);fireEvent.click(screen.getByLabelText("取消X 坐标修改"));expect(pending.mock.calls.at(-1)![0]).toBe(false);
 });
 it("marks media requests pending and cancels late material without creating nodes",async()=>{
  let resolve!:(value:ExpressionMedia)=>void;const request=new Promise<ExpressionMedia>(r=>{resolve=r;});const pending=vi.fn();const change=vi.fn();render(<Harness onChange={change} onPendingEditChange={pending} onAddMedia={()=>request}/>);fireEvent.click(screen.getByRole("button",{name:"添加媒体节点"}));expect(pending.mock.calls.at(-1)![0]).toBe(true);fireEvent.click(screen.getByRole("button",{name:"取消媒体添加"}));expect(pending.mock.calls.at(-1)![0]).toBe(false);await act(async()=>{resolve(media);await request;});expect(change).not.toHaveBeenCalled();
 });
 it("clears transient drafts for explicit new document or readonly transition",()=>{
  const pending=vi.fn();const props={value:initial,onChange:vi.fn(),onPendingEditChange:pending};const{rerender}=render(<CanonicalExpressionBoard {...props} documentKey="A"/>);fireEvent.change(screen.getByLabelText("新连线文字"),{target:{value:"A草稿"}});expect(pending.mock.calls.at(-1)![0]).toBe(true);rerender(<CanonicalExpressionBoard {...props} documentKey="B"/>);expect(pending.mock.calls.at(-1)![0]).toBe(false);expect(screen.getByLabelText("新连线文字")).toHaveValue("");fireEvent.change(screen.getByLabelText("新连线文字"),{target:{value:"B草稿"}});rerender(<CanonicalExpressionBoard {...props} documentKey="B" readOnly/>);expect(pending.mock.calls.at(-1)![0]).toBe(false);expect(screen.getByLabelText("新连线文字")).toHaveValue("");
 });
 it("clearing pending does not clear host content changes",()=>{
  function Owner(){const[state,setState]=useState(initial);const[changed,setChanged]=useState(false);const[pending,setPending]=useState(false);return <><output aria-label="工作区dirty">{String(changed||pending)}</output><CanonicalExpressionBoard value={state} onChange={next=>{setState(next);setChanged(true);}} onPendingEditChange={setPending}/></>;}
  render(<Owner/>);fireEvent.change(screen.getByLabelText("节点文字 1"),{target:{value:"已有内容修改"}});fireEvent.change(screen.getByLabelText("新连线文字"),{target:{value:"临时草稿"}});fireEvent.click(screen.getByRole("button",{name:"取消未提交连线"}));expect(screen.getByLabelText("工作区dirty")).toHaveTextContent("true");
 });
});
