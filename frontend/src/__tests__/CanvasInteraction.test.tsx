import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { CanvasBoard } from "../components/CanvasBoard";
import { performanceMonitor } from "../runtime/performance";

const original = { nodes: [{ id:"n1",type:"text",x:10,y:20,width:100,height:60,text:"起点" }], edges:[] };
beforeEach(()=>performanceMonitor.clear());
afterEach(()=>{vi.restoreAllMocks();});

it("SIMULATED keyboard moves a node without dragging and leaves child editor arrows alone",()=>{
 const changed=vi.fn();render(<CanvasBoard doc={original} onChange={changed}/>);
 const node=screen.getByRole("group",{name:"节点 起点"});node.focus();fireEvent.keyDown(node,{key:"ArrowRight"});
 expect(changed.mock.calls[0][0].nodes[0]).toMatchObject({id:"n1",x:20,y:20});
 fireEvent.keyDown(node,{key:"ArrowDown",shiftKey:true});expect(changed.mock.calls[1][0].nodes[0]).toMatchObject({x:10,y:70});
 fireEvent.click(screen.getByRole("button",{name:"编辑 起点"}));fireEvent.keyDown(screen.getByRole("textbox"),{key:"ArrowLeft"});expect(changed).toHaveBeenCalledTimes(2);
});

it("SIMULATED Escape cancels editing without saving and restores the edit trigger focus",async()=>{
 const changed=vi.fn(),user=userEvent.setup();render(<CanvasBoard doc={original} onChange={changed}/>);
 const trigger=screen.getByRole("button",{name:"编辑 起点"});await user.click(trigger);const area=screen.getByRole("textbox",{name:"编辑节点 起点"});
 await user.clear(area);await user.type(area,"unsaved");await user.keyboard("{Escape}");
 expect(changed).not.toHaveBeenCalled();expect(screen.getByText("起点")).toBeInTheDocument();expect(trigger).toHaveFocus();
});

it("SIMULATED Enter commits once, preserves identity and returns focus after the text changes",async()=>{
 const changed=vi.fn();function Editor(){const [doc,setDoc]=useState<Record<string,unknown>>(original);return <CanvasBoard doc={doc} onChange={next=>{changed(next);setDoc(next);}}/>;}
 const user=userEvent.setup();render(<Editor/>);await user.click(screen.getByRole("button",{name:"编辑 起点"}));await user.clear(screen.getByRole("textbox"));await user.type(screen.getByRole("textbox"),"改后{Enter}");
 expect(changed).toHaveBeenCalledTimes(1);expect(changed.mock.calls[0][0].nodes[0]).toMatchObject({id:"n1",text:"改后"});expect(screen.getByRole("button",{name:"编辑 改后"})).toHaveFocus();
});

it("records actual mounted CanvasBoard render-to-commit elapsed metrics",()=>{
 const view=render(<CanvasBoard doc={original} onChange={()=>{}}/>);view.rerender(<CanvasBoard doc={{...original,edges:[]}} onChange={()=>{}}/>);
 const metrics=performanceMonitor.getComponentMetrics("CanvasBoard");expect(metrics.length).toBeGreaterThanOrEqual(2);
 expect(metrics.every(m=>Number.isFinite(m.duration_ms)&&m.duration_ms>=0)).toBe(true);
});

it("SIMULATED quality selection controls real decoration and document visibility is reflected without dropping nodes",async()=>{
 const user=userEvent.setup();const view=render(<CanvasBoard doc={original} onChange={()=>{}}/>);
 await user.selectOptions(screen.getByLabelText("画布显示质量"),"low");expect(screen.getByRole("group",{name:"节点 起点"})).toHaveStyle({boxShadow:"none",transition:"none"});
 vi.spyOn(document,"hidden","get").mockReturnValue(true);fireEvent(document,new Event("visibilitychange"));
 expect(view.container.querySelector(".canvas-board")).toHaveAttribute("data-visibility","hidden");expect(screen.getByText("起点")).toBeInTheDocument();
 view.unmount();fireEvent(document,new Event("visibilitychange"));
});
