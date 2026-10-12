import {useState} from "react";
import {webcrypto} from "node:crypto";
import {beforeEach,it,expect,vi} from "vitest";
import {render,screen,fireEvent,waitFor} from "@testing-library/react";
import {SpaceView} from "../spaces/SpaceView";
import {CanonicalTeachingSpace} from "../spaces/CanonicalTeachingSpace";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const key="course:course-exact:artifact:lesson-exact",knowledgeId="knowledge-exact";
function course(){return {status:"candidate",human_review_required:true,stale:false,manifest:{schema:"archeaxis.course-manifest/v1",manifest_id:"course-exact",title:"同源课程",status:"candidate",knowledge_components:[{component_id:"component-exact",title:"要点",statement:"来源引文"}],learning_objectives:[{statement:"解释原件",knowledge_component_ids:["component-exact"]}],artifacts:[{artifact_id:"lesson-exact",artifact_type:"lesson",renderer:"native-lesson",knowledge_ids:["component-exact"],status:"candidate",derived_only:true,human_review_required:true}]},bindings:[{knowledge_id:knowledgeId,knowledge_version:knowledgeId,component_id:"component-exact",source_id:"source-exact",source_revision:"source-revision-exact",stale:false}]};}
function assessment(){return {item_key:key,assessment_id:"assessment-exact",knowledge_id:knowledgeId,knowledge_version:knowledgeId,question:"解释同一来源的证据",content:"同一来源核对正文",source_id:"source-exact",anchor_id:"anchor-exact"};}
const events:unknown[]=[];
function setup(failure?:"course"|"assessment"|"state"){bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
 switch(op){
 case "course_list":return {items:[],next_cursor:null};case "teaching_list":return {items:[],next_cursor:null};
 case "search":return {items:[{knowledge_id:knowledgeId,head:"已接受的同源知识"}]};
 case "knowledge_get":return {knowledge_id:knowledgeId,status:"accepted",source_id:"source-exact",anchor_id:"anchor-exact"};
 case "course_from_knowledge":return {course:course(),human_review_required:true,suggested_learning_item:{item_key:key,course_id:"course-exact",artifact_id:"lesson-exact",knowledge_id:knowledgeId,knowledge_version:knowledgeId,source_id:"source-exact",source_revision:"source-revision-exact"}};
 case "course_get":return failure==="course"?{...course(),bindings:[{...course().bindings[0],knowledge_id:"other",knowledge_version:"other"}]}:course();
 case "course_render":return {course:course(),derived_only:true,canonical_bindings_verified:true,human_review_required:true,render:{derived_only:true,human_review_required:true,lesson:{content:"# 同源课时",frontmatter:{manifest_id:"course-exact",artifact_id:"lesson-exact"}}}};
 case "learning_reference":return {item_key:key};case "assessment_create":return assessment();case "assessment_get":return failure==="assessment"?{...assessment(),item_key:"different-item"}:assessment();
 case "learning_items":return {items:events.length?[{item_key:key,next_review:"2026-10-12T08:00:00Z"}]:[]};
 case "learning_state":return {item_key:p.item_key,learner:{assessment:failure==="state"?{...assessment(),knowledge_version:"other"}:assessment(),references:[{knowledge_id:knowledgeId,active:true}]},machine:{status:"not_recorded"}};
 case "learning_history":return {item_key:p.item_key,events:[...events]};
 case "learning_review":events.push(p.body);return {item_key:key,event_id:events.length,next_review:"2026-10-12T08:00:00Z"};
 default:throw new Error(`unconfigured ${op}`);
 }
});}
function Journey({initial="07"}:{initial?:string}){const[page,setPage]=useState(initial),[item,setItem]=useState<string>();return <SpaceView spaceId="learning" uiPageId={page} initialLearningItemKey={item} onInspect={()=>{}} onNavigate={()=>{throw new Error("legacy fallback forbidden");}} onOpenPage={setPage} onReviewItem={key=>{setItem(key);setPage("06");}}/>;}
beforeEach(()=>{bridge.call.mockReset();events.length=0;vi.stubGlobal("crypto",webcrypto);});
it("SIMULATED mounted accepted knowledge→actual course/assessment→page11 practice→page12 review keeps one immutable object",async()=>{
 setup();render(<Journey/>);
 fireEvent.click(screen.getByRole("button",{name:"搜索知识"}));fireEvent.click(await screen.findByRole("button",{name:"已接受的同源知识"}));
 fireEvent.click(await screen.findByRole("button",{name:"从当前知识生成课程与课时"}));fireEvent.click(await screen.findByRole("button",{name:"由课程课时建立学习问题"}));
 fireEvent.click(await screen.findByRole("button",{name:"练习此学习项目"}));
 const answer=await screen.findByRole("textbox",{name:"本次答案"});fireEvent.change(answer,{target:{value:"独立作答同一来源"}});
 fireEvent.click(screen.getByRole("button",{name:"反馈与修订"}));
 await waitFor(()=>expect(screen.getByRole("textbox",{name:"本次答案"})).toHaveValue("独立作答同一来源"));
 fireEvent.click(screen.getByRole("button",{name:"查看答案与核对内容"}));fireEvent.click(screen.getByLabelText("回答正确"));fireEvent.change(screen.getByLabelText("学习者自评"),{target:{value:"3"}});fireEvent.click(screen.getByRole("button",{name:"记录复习结果"}));
 await screen.findByText(/Core 已确认复习记录/);
 expect(events).toHaveLength(1);expect(events[0]).toMatchObject({item_key:key,assessment_id:"assessment-exact",knowledge_version:knowledgeId,answer:"独立作答同一来源",correct:true,rating:3});
 expect(bridge.call.mock.calls.some(([op])=>["knowledge_review","machine_answer","teaching_create"].includes(op))).toBe(false);
 expect(bridge.call.mock.calls.filter(([op])=>op==="assessment_create")).toHaveLength(1);
 expect(bridge.call).toHaveBeenCalledWith("course_get",{course_id:"course-exact"});
});
it.each(["course","assessment"] as const)("SIMULATED page11 refuses %s identity substitution without creating another object",async failure=>{
 setup(failure);render(<CanonicalTeachingSpace pageId="11" initialItemKey={key}/>);await screen.findByRole("alert");expect(screen.queryByRole("textbox",{name:"本次答案"})).toBeNull();expect(bridge.call.mock.calls.some(([op])=>["assessment_create","learning_review","course_from_knowledge"].includes(op))).toBe(false);
});
it("SIMULATED page12 rejects learning_state bound to a different immutable knowledge version",async()=>{
 setup("state");render(<CanonicalTeachingSpace pageId="12" initialItemKey={key}/>);await screen.findByText("学习记录读取失败，暂时不能提交结果。");expect(screen.queryByRole("button",{name:"记录复习结果"})).toBeNull();expect(events).toHaveLength(0);
});
it("SIMULATED explicitly selected persisted review item can continue into page11 without recreating its assessment",async()=>{
 setup();events.push({prior:true});render(<Journey initial="06"/>);
 fireEvent.click(await screen.findByRole("button",{name:key}));
 await waitFor(()=>expect(screen.getByRole("button",{name:"练习此学习项目"})).toBeEnabled());
 fireEvent.click(screen.getByRole("button",{name:"练习此学习项目"}));
 await screen.findByRole("textbox",{name:"本次答案"});
 expect(bridge.call.mock.calls.some(([op])=>["assessment_create","learning_reference","course_from_knowledge"].includes(op))).toBe(false);
});
