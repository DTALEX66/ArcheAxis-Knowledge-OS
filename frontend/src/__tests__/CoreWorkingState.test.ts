import { expect, it, vi } from "vitest";
import { encodeEditorContent } from "../components/DocumentEditor";
import { CoreWorkingStateSession, type WorkingState, type WorkingRead, type WorkingEditor, type WorkingTransport } from "../presentation/coreWorkingState";
const editor=(text:string):WorkingEditor=>({type:"doc",content:[{type:"paragraph",attrs:{block_id:"stable",opaque:{future:[1,null,"保留"]}},content:[{type:"text",text}]}]});
const state=():WorkingState=>({drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null});
function fixture(initial=state()) {
  let server:WorkingRead={schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:initial,draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false};
  const publish=(next:WorkingState):WorkingRead=>{
    server={...server,state:structuredClone(next),state_revision:server.state_revision+1,draft_digests:Object.fromEntries(Object.keys(next.drafts).map(id=>[id,"b".repeat(64)]))};return structuredClone(server);
  };
  const transport:WorkingTransport={read:vi.fn(async()=>structuredClone(server)),write:vi.fn(async request=>publish(request.state)),
    clearJob:vi.fn(async request=>{const next=structuredClone(server.state);delete next.pending_jobs![request.request_id];if(!Object.keys(next.pending_jobs!).length)delete next.pending_jobs;return publish(next);}),
    clearSaved:vi.fn(async request=>{const next=structuredClone(server.state);delete next.drafts[request.document_id];return publish(next);}),
    recover:vi.fn(async request=>{const result=publish(request.action==="preserve"?server.recovery_candidates!:state());server={...result,recovery_candidates:null,recovery_requires_confirmation:false};return structuredClone(server);})};
  return {transport,session:new CoreWorkingStateSession(transport),publish,get:()=>server,set:(next:WorkingRead)=>{server=next;}};
}
it("editor drafts survive the JSON transport boundary without false identity rejection",async()=>{
  const f=fixture();await f.session.load();
  vi.mocked(f.transport.write).mockImplementation(async request=>f.publish(JSON.parse(JSON.stringify(request.state)) as WorkingState));
  const encoded=encodeEditorContent({type:"doc",attrs:{originalAttrs:null},content:[{type:"paragraph",attrs:{block_id:"stable",originalAttrs:null},content:[{type:"text",text:"原创中文正文"}]}]});
  if(encoded.type!=="doc"||!encoded.content)throw new Error("Invalid editor fixture");
  f.session.rememberDraft("doc-a",encoded as WorkingEditor,1);
  await f.session.flush();
  expect(f.session.getSnapshot().status).toBe("ready");
  const read=new CoreWorkingStateSession(f.transport);await read.load();
  expect(read.getSnapshot().state.drafts["doc-a"].editor_json).toStrictEqual(encoded);
  expect(await f.session.clearSaved("doc-a",{base_version:1,editor_json:encoded as WorkingEditor},2)).toBe(true);
});
it("SIMULATED: reloads independent Core-journal drafts and scene while preserving unknown fields",async()=>{
  const f=fixture();await f.session.load();f.session.rememberDraft("doc-a",editor("甲"),1);f.session.rememberDraft("doc-b",editor("乙"),2);f.session.rememberScene("03","doc-b");await f.session.flush();
  const reopened=new CoreWorkingStateSession(f.transport);await reopened.load();
  expect(reopened.getSnapshot().state).toEqual(f.session.getSnapshot().state);
  expect(reopened.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("甲"));
});
it("rejects malformed work-state readbacks before replacing retained drafts",async()=>{
  const f=fixture();await f.session.load();f.session.rememberDraft("doc-a",editor("仍保留"),1);
  vi.mocked(f.transport.read).mockResolvedValueOnce({documents:[]} as never);
  await expect(f.session.load()).rejects.toThrow("UI_WORKING_STATE_DTO_INVALID");
  expect(f.session.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("仍保留"));
  expect(f.session.getSnapshot().status).toBe("blocked");
});
it("concurrent initial reads share one request and preserve input typed while read is pending",async()=>{
  const f=fixture();let finish!:(value:WorkingRead)=>void;
  vi.mocked(f.transport.read).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  const first=f.session.load(),second=f.session.load();expect(f.transport.read).toHaveBeenCalledTimes(1);
  f.session.rememberDraft("doc-a",editor("读取期间新输入"),1);finish(f.get());await Promise.all([first,second]);
  expect(f.session.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("读取期间新输入"));
  expect(f.session.getSnapshot().status).toBe("unsaved");
});
it("changed restore epoch exposes fresh candidate basis without replacing current local input",async()=>{
  const f=fixture();await f.session.load();f.session.rememberDraft("doc-a",editor("现场草稿"),1);await f.session.flush();
  const candidate={...state(),drafts:{"doc-b":{base_version:1,editor_json:editor("备份候选")}}};
  f.set({...f.get(),restore_epoch:"c".repeat(32),state:state(),recovery_candidates:candidate,recovery_requires_confirmation:true});
  await f.session.load();expect(f.session.getSnapshot().status).toBe("recovery");expect(f.session.getSnapshot().state.drafts["doc-a"]).toBeDefined();
  await f.session.recover("preserve");expect(f.transport.recover).toHaveBeenCalledWith(expect.objectContaining({restore_epoch:"c".repeat(32),action:"preserve"}));
  expect(f.session.getSnapshot().state.drafts["doc-a"]).toBeDefined();expect(f.session.getSnapshot().status).toBe("blocked");
});
it("late journal ACK updates revision without replacing a newer local draft",async()=>{
  const f=fixture();await f.session.load();let finish!:(value:WorkingRead)=>void;
  vi.mocked(f.transport.write).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  f.session.rememberDraft("doc-a",editor("已发送"),1);const writing=f.session.flush();
  const sent=structuredClone(f.session.getSnapshot().state);f.session.rememberDraft("doc-a",editor("后续输入"),1);
  finish(f.publish(sent));await writing;
  expect(f.session.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("后续输入"));
  expect(f.session.getSnapshot().status).toBe("unsaved");await f.session.flush();expect(f.get().state.drafts["doc-a"].editor_json).toEqual(editor("后续输入"));
});
it("lost journal ACK blocks replay until readback confirms the same frozen state",async()=>{
  const f=fixture();await f.session.load();f.session.rememberDraft("doc-a",editor("不丢失"),1);
  vi.mocked(f.transport.write).mockImplementationOnce(async request=>{f.publish(request.state);throw new Error("lost ACK");});
  await expect(f.session.flush()).rejects.toThrow("lost ACK");await expect(f.session.flush()).rejects.toThrow("先读取");
  expect(f.transport.write).toHaveBeenCalledTimes(1);await f.session.load();expect(f.session.getSnapshot().status).toBe("ready");
  expect(f.session.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("不丢失"));
});
it("403 or conflicting remote revision never replaces local drafts",async()=>{
  const f=fixture();await f.session.load();f.session.rememberDraft("doc-a",editor("本地草稿"),1);
  vi.mocked(f.transport.write).mockRejectedValueOnce(new Error("403 forbidden"));await expect(f.session.flush()).rejects.toThrow("403");
  f.publish({...state(),drafts:{"doc-b":{base_version:1,editor_json:editor("另一现场")}}});
  await expect(f.session.load()).rejects.toThrow("其他修订");expect(f.session.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("本地草稿"));
});
it("clear_saved uses Core digest and retains a newer edit arriving during clear ACK",async()=>{
  const f=fixture();await f.session.load();const sent={base_version:1,editor_json:editor("保存内容")};f.session.rememberDraft("doc-a",sent.editor_json,1);await f.session.flush();
  let finish!:(value:WorkingRead)=>void;vi.mocked(f.transport.clearSaved).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  const clearing=f.session.clearSaved("doc-a",sent,2);await Promise.resolve();
  f.session.rememberDraft("doc-a",editor("晚编辑"),2);finish(f.publish(state()));await clearing;
  expect(f.transport.clearSaved).toHaveBeenCalledWith(expect.objectContaining({document_id:"doc-a",base_version:1,saved_version:2,content_sha256:"b".repeat(64)}));
  expect(f.session.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("晚编辑"));
});
it("concurrent conditional clear requests serialize instead of issuing two CAS writes",async()=>{
  const f=fixture();await f.session.load();const sent={base_version:1,editor_json:editor("同一保存内容")};
  f.session.rememberDraft("doc-a",sent.editor_json,1);await f.session.flush();
  let finish!:(value:WorkingRead)=>void;
  vi.mocked(f.transport.clearSaved).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  const first=f.session.clearSaved("doc-a",sent,2),second=f.session.clearSaved("doc-a",sent,2);
  await Promise.resolve();expect(f.transport.clearSaved).toHaveBeenCalledTimes(1);
  finish(f.publish(state()));expect(await first).toBe(true);expect(await second).toBe(false);
  expect(f.transport.clearSaved).toHaveBeenCalledTimes(1);expect(f.session.getSnapshot().status).toBe("ready");
});
it("lost clear ACK reconciles a matching deletion without reintroducing the saved draft",async()=>{
  const f=fixture();await f.session.load();const sent={base_version:1,editor_json:editor("保存内容")};f.session.rememberDraft("doc-a",sent.editor_json,1);await f.session.flush();
  vi.mocked(f.transport.clearSaved).mockImplementationOnce(async()=>{f.publish(state());throw new Error("clear ACK lost");});
  await expect(f.session.clearSaved("doc-a",sent,2)).rejects.toThrow();await f.session.load();
  expect(f.session.getSnapshot().state.drafts["doc-a"]).toBeUndefined();expect(f.session.getSnapshot().status).toBe("ready");
});
it.each(["preserve","discard"] as const)("restore candidates require explicit %s before use",async action=>{
  const candidate={...state(),drafts:{"doc-a":{base_version:1,editor_json:editor("候选")}}};const f=fixture();
  f.set({...f.get(),restore_epoch:"c".repeat(32),recovery_candidates:candidate,recovery_requires_confirmation:true});
  await f.session.load();expect(f.session.getSnapshot().state.drafts).toEqual({});expect(f.transport.recover).not.toHaveBeenCalled();
  await expect(f.session.flush()).rejects.toThrow();await f.session.recover(action);
  expect(f.session.getSnapshot().state).toEqual(action==="preserve"?candidate:state());
});
it("an original create caller cannot POST until frozen journal ACK is confirmed",async()=>{
  const f=fixture();await f.session.load();const post=vi.fn();
  const body={create_request_id:"note-stable",title:"原创笔记",editor_json:editor("")};
  vi.mocked(f.transport.write).mockImplementationOnce(async request=>{f.publish(request.state);throw new Error("journal ACK lost");});
  await expect((async()=>{await f.session.stageOriginal(body);post(body);})()).rejects.toThrow();expect(post).not.toHaveBeenCalled();
  await f.session.load();const reopened=new CoreWorkingStateSession(f.transport);await reopened.load();
  expect(reopened.getSnapshot().state.pending_original).toEqual(body);await reopened.stageOriginal(body);post(reopened.getSnapshot().state.pending_original);
  expect(post).toHaveBeenCalledWith(body);
});

it("SIMULATED job journal survives lost save ACK/reopen and refuses changing the frozen identity",async()=>{
  const f=fixture();await f.session.load();
  const entry={source_id:"source",source_revision:"a".repeat(64),job_id:"job",request_id:"frozen",kind:"text",body:{deadline_ms:60000,split:false,words:false},surface:"manual" as const,mode:"single" as const,origin_restore_epoch:"initial",relative:null};
  vi.mocked(f.transport.write).mockImplementationOnce(async request=>{f.publish(request.state);throw new Error("lost journal ACK");});
  await expect(f.session.stageJob(entry)).rejects.toThrow("lost journal ACK");
  expect(f.session.getSnapshot().status).toBe("blocked");await f.session.load();
  const reopened=new CoreWorkingStateSession(f.transport);await reopened.load();
  expect(reopened.getSnapshot().state.pending_jobs?.frozen).toEqual(entry);
  await expect(reopened.stageJob({...entry,body:{...entry.body,deadline_ms:1}})).rejects.toThrow("不同的冻结");
  await reopened.clearJob(entry,"terminal");
  expect(f.transport.clearJob).toHaveBeenCalledWith(expect.objectContaining({request_id:"frozen",action:"terminal"}));
  expect(reopened.getSnapshot().state.pending_jobs).toBeUndefined();
});
it("SIMULATED job clear refusal preserves the exact entry and late clear ACK preserves newer drafts",async()=>{
  const f=fixture();await f.session.load();const entry={source_id:"source",source_revision:"a".repeat(64),job_id:"job",request_id:"frozen",kind:"text",body:{deadline_ms:60000,split:false,words:false},surface:"folder" as const,mode:"single" as const,origin_restore_epoch:"initial",relative:"owned.txt"};await f.session.stageJob(entry);
  vi.mocked(f.transport.clearJob!).mockRejectedValueOnce(new Error("still running"));
  await expect(f.session.clearJob(entry,"abandon_unadmitted")).rejects.toThrow("still running");
  expect(f.session.getSnapshot().state.pending_jobs?.frozen).toEqual(entry);await f.session.load();
  let finish!:(v:WorkingRead)=>void;vi.mocked(f.transport.clearJob!).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  const clearing=f.session.clearJob(entry,"terminal");await vi.waitFor(()=>expect(finish).toBeTypeOf("function"));
  f.session.rememberDraft("doc-a",editor("清理期间新输入"),1);
  const next=structuredClone(f.get().state);delete next.pending_jobs;finish(f.publish(next));await clearing;
  expect(f.session.getSnapshot().state.drafts["doc-a"].editor_json).toEqual(editor("清理期间新输入"));
});

it.each(["terminal","abandon_unadmitted"] as const)("SIMULATED committed job clear with lost ACK reconciles without reintroducing intent: %s",async action=>{
  const f=fixture();await f.session.load();
  const entry={source_id:"source",source_revision:"a".repeat(64),job_id:"job",request_id:"frozen",kind:"text",body:{deadline_ms:60000,split:false,words:false},surface:"manual" as const,mode:"single" as const,origin_restore_epoch:"initial",relative:null};
  await f.session.stageJob(entry);
  vi.mocked(f.transport.clearJob!).mockImplementationOnce(async()=>{const next=structuredClone(f.get().state);delete next.pending_jobs;f.publish(next);throw new Error("committed clear ACK lost");});
  await expect(f.session.clearJob(entry,action)).rejects.toThrow("committed clear ACK lost");
  expect(f.session.getSnapshot().state.pending_jobs?.frozen).toEqual(entry);
  await expect(f.session.flush()).rejects.toThrow("先读取");
  await f.session.load();
  expect(f.session.getSnapshot().state.pending_jobs).toBeUndefined();
  expect(f.session.getSnapshot().status).toBe("ready");
  const writes=vi.mocked(f.transport.write).mock.calls.length;
  await f.session.flush();
  expect(f.transport.write).toHaveBeenCalledTimes(writes);
  expect(f.transport.clearJob).toHaveBeenCalledTimes(1);
});

it("SIMULATED lost clear ACK readback preserves later drafts and independent job intents",async()=>{
  const f=fixture();await f.session.load();
  const entry={source_id:"source",source_revision:"a".repeat(64),job_id:"job",request_id:"frozen",kind:"text",body:{deadline_ms:60000,split:false,words:false},surface:"manual" as const,mode:"single" as const,origin_restore_epoch:"initial",relative:null};await f.session.stageJob(entry);
  let reject!:(reason:Error)=>void;vi.mocked(f.transport.clearJob!).mockImplementationOnce(()=>new Promise((_,fail)=>{reject=fail;}));
  const clearing=f.session.clearJob(entry,"terminal");const failed=expect(clearing).rejects.toThrow("lost ACK");
  await vi.waitFor(()=>expect(reject).toBeTypeOf("function"));
  const other={...entry,job_id:"other-job",request_id:"other-request"};
  f.session.rememberDraft("doc-b",editor("清理以后继续输入"),2);
  f.session.change(local=>{local.pending_jobs![other.request_id]=other;});
  const next=structuredClone(f.get().state);delete next.pending_jobs;f.publish(next);reject(new Error("lost ACK"));await failed;
  await f.session.load();
  expect(f.session.getSnapshot().state.pending_jobs).toEqual({[other.request_id]:other});
  expect(f.session.getSnapshot().state.drafts["doc-b"].editor_json).toEqual(editor("清理以后继续输入"));
  expect(f.session.getSnapshot().status).toBe("unsaved");
  await f.session.flush();expect(f.get().state.pending_jobs).toEqual({[other.request_id]:other});
});

it("SIMULATED lost clear ACK does not erase changed local identity across restore epoch mismatch",async()=>{
  const f=fixture();await f.session.load();
  const entry={source_id:"source",source_revision:"a".repeat(64),job_id:"job",request_id:"frozen",kind:"text",body:{deadline_ms:60000,split:false,words:false},surface:"manual" as const,mode:"single" as const,origin_restore_epoch:"initial",relative:null};await f.session.stageJob(entry);
  vi.mocked(f.transport.clearJob!).mockImplementationOnce(async()=>{const next=structuredClone(f.get().state);delete next.pending_jobs;f.publish(next);throw new Error("lost ACK");});
  await expect(f.session.clearJob(entry,"terminal")).rejects.toThrow("lost ACK");
  const changed={...entry,body:{...entry.body,deadline_ms:1}};
  f.session.change(local=>{local.pending_jobs!.frozen=changed;});
  f.set({...f.get(),restore_epoch:"b".repeat(32)});await f.session.load();
  expect(f.session.getSnapshot().status).toBe("blocked");
  expect(f.session.getSnapshot().state.pending_jobs?.frozen).toEqual(changed);
  f.set({...f.get(),restore_epoch:"initial"});await f.session.load();
  expect(f.session.getSnapshot().state.pending_jobs?.frozen).toEqual(changed);
});

it("SIMULATED matching committed-clear readback preserves a newer local identity under the same request key",async()=>{
  const entry={source_id:"source",source_revision:"a".repeat(64),job_id:"job",request_id:"frozen",kind:"text",body:{deadline_ms:60000,split:false,words:false},surface:"manual" as const,mode:"single" as const,origin_restore_epoch:"initial",relative:null};
  const f=fixture({...state(),pending_jobs:{frozen:entry}});await f.session.load();
  vi.mocked(f.transport.clearJob!).mockImplementationOnce(async()=>{const next=structuredClone(f.get().state);delete next.pending_jobs;f.publish(next);throw new Error("lost ACK");});
  await expect(f.session.clearJob(entry,"terminal")).rejects.toThrow("lost ACK");
  const changed={...entry,body:{...entry.body,deadline_ms:1000}};
  f.session.change(local=>{local.pending_jobs!.frozen=changed;});await f.session.load();
  expect(f.session.getSnapshot().state.pending_jobs?.frozen).toEqual(changed);
  expect(f.session.getSnapshot().status).toBe("unsaved");
  expect(f.transport.clearJob).toHaveBeenCalledTimes(1);
});

it.each(["manual","folder","bounded"] as const)("SIMULATED duplicate job request is refused before local mutation: %s",async surface=>{
  const entry={source_id:"source",source_revision:"a".repeat(64),job_id:"job",request_id:"frozen",kind:"text",body:{deadline_ms:60000,split:false,words:false},surface,mode:"single" as const,origin_restore_epoch:"initial",relative:null};
  const f=fixture({...state(),pending_jobs:{frozen:entry}});await f.session.load();
  const before=structuredClone(f.session.getSnapshot());
  await expect(f.session.stageJob({...entry,request_id:"new-request"})).rejects.toThrow("先恢复原请求");
  expect(f.session.getSnapshot()).toEqual(before);expect(f.transport.write).not.toHaveBeenCalled();
  await f.session.stageJob(entry);expect(f.session.getSnapshot().state.pending_jobs).toEqual({frozen:entry});
});
