import {useState} from "react";
import {render,screen,fireEvent,within} from "@testing-library/react";
import {expect,it,vi} from "vitest";
import {CanonicalExpressionBoard} from "../components/CanonicalExpressionBoard";
import type {ExpressionDocument} from "../presentation/expression";

const dense:ExpressionDocument={schema:"archeaxis.expression/v1",nodes:Array.from({length:10},(_,index)=>({id:`n${index}`,type:index===9?"media":"text",x:index===0?-150:index*300,y:index===0?-80:index*90,width:260,height:180,text:index===0?"长文字\n".repeat(100):`正文${index}`,...(index===9?{media:{source_id:"source-actual",sha256:"a".repeat(64),media_type:"image/png"}}:{})})),edges:Array.from({length:15},(_,index)=>({id:`e${index}`,fromNode:`n${index%10}`,toNode:`n${(index+1)%10}`,label:`关系${index}`}))};
function Harness({change}:{change:(next:ExpressionDocument)=>void}){const [value,setValue]=useState(dense);return <CanonicalExpressionBoard value={value} onChange={next=>{setValue(next);change(next);}} renderMedia={media=><span>已保存媒体 {media.source_id}</span>}/>;}
it("keeps the viewport, actual media and all 15 keyboard-editable edges while changing a selected negative-position node",()=>{
 const change=vi.fn();render(<Harness change={change}/>);
 const viewport=screen.getByRole("region",{name:"画布滚动区域"});
 expect(within(viewport).getAllByRole("article")).toHaveLength(10);
 expect(within(viewport).getByText("已保存媒体 source-actual")).toBeInTheDocument();
 const inspector=screen.getByRole("complementary",{name:"当前节点属性与连线"});
 expect(within(inspector).getAllByRole("listitem")).toHaveLength(15);
 fireEvent.change(within(inspector).getByLabelText("当前节点"),{target:{value:"n0"}});
 fireEvent.change(within(inspector).getByLabelText("X 坐标"),{target:{value:"-225"}});
 fireEvent.blur(within(inspector).getByLabelText("X 坐标"));
 fireEvent.keyDown(within(viewport).getByRole("article",{name:"节点 1"}),{key:"ArrowLeft",shiftKey:true});
 expect(change.mock.calls.at(-1)![0].nodes[0].x).toBe(-235);
 expect(change.mock.calls.at(-1)![0].edges).toEqual(dense.edges);
 expect(change.mock.calls.at(-1)![0].nodes[9].media).toEqual(dense.nodes[9].media);
 expect(screen.getByRole("region",{name:"画布滚动区域"})).toBe(viewport);
 expect(within(viewport).getByLabelText("节点文字 1")).toHaveValue(dense.nodes[0].text);
});
it("scrolls only the canvas viewport to reveal an offscreen selection",()=>{
 render(<Harness change={vi.fn()}/>);
 const viewport=screen.getByRole("region",{name:"画布滚动区域"});
 Object.defineProperties(viewport,{clientWidth:{value:500},clientHeight:{value:350}});
 fireEvent.change(screen.getByLabelText("当前节点"),{target:{value:"n9"}});
 expect(viewport.scrollLeft).toBeGreaterThan(0);expect(viewport.scrollTop).toBeGreaterThan(0);
 expect(viewport.parentElement?.scrollTop).toBe(0);
});
