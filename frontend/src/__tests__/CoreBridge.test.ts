import { afterEach, describe, expect, it, vi } from "vitest";
import { coreCommand, verifyCanonicalCore } from "../api/core";
import { ApiError } from "../api/client";

afterEach(() => { delete window.__TAURI__; });
it.each([undefined,[],[{backup_id:"c".repeat(32),filename:`${"c".repeat(32)}.sqlite`,code:"AAK-BACKUP-INVALID",message:"SIMULATED preserved"}]])("SIMULATED optional unavailable backups decode without changing valid backups",async(unavailable)=>{
  const body={backups:[],...(unavailable===undefined?{}:{unavailable_backups:unavailable})};
  window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:200,body})}};
  await expect(coreCommand("workspace_backups")).resolves.toEqual(body);
});
it.each([null,[{backup_id:"bad",filename:"bad.sqlite",code:"AAK-BACKUP-INVALID",message:"preserved"}],[{backup_id:"c".repeat(32),filename:"bad.sqlite",code:"INVENTED",message:"preserved"}]])("SIMULATED unavailable backup metadata cannot bypass the generated decoder",async(unavailable_backups)=>{
  window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:200,body:{backups:[],unavailable_backups}})}};
  await expect(coreCommand("workspace_backups")).rejects.toMatchObject({status:502,code:"incompatible"});
});
describe("finite Core bridge", () => {
  it("retains unknown model/cost and rejects invented connected status",async()=>{
    const body={schema:"archeaxis.machine-configuration/v1",worker_registered:true,selection_source:"EXPLICIT_LAUNCH",availability:"CONFIGURED_UNVERIFIED",model_identity:null,destination:"LOCAL_LOOPBACK_ONLY",material_scope:"AUTHORIZED_KNOWLEDGE_AND_EXPLICIT_QUESTION",inference_status:"NOT_EXECUTED",loaded_status:"UNKNOWN",usage:null,cost:null,network_performed:false,evidence_scope:"LAUNCH_POLICY_ONLY"};
    const invoke=vi.fn().mockResolvedValue({status:200,body});window.__TAURI__={core:{invoke}};
    expect(await coreCommand("machine_configuration")).toEqual(body);
    expect(invoke).toHaveBeenCalledWith("core_command",{request:{operation:"machine_configuration",payload:{}}});
    invoke.mockResolvedValue({status:200,body:{...body,availability:"CONNECTED",cost:0}});
    await expect(coreCommand("machine_configuration")).rejects.toThrow();
  });
  it.each(["3.51.3","3.50.7","3.44.6","3.52.0"])("accepts a fixed SQLite version %s",async(sqlite_version)=>{
    window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:200,body:{runtime:"archeaxis-api",contract:"0.1.0-outline",schema_version:7,sqlite_version}})}};
    await expect(verifyCanonicalCore()).resolves.toBeUndefined();
  });
  it.each(["3.46.0","3.51.2",undefined])("rejects an old or missing SQLite version %s",async(sqlite_version)=>{
    window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:200,body:{runtime:"archeaxis-api",contract:"0.1.0-outline",schema_version:7,sqlite_version}})}};
    await expect(verifyCanonicalCore()).rejects.toMatchObject({message:"本地核心需更新。"});
  });
  it("forwards only a business operation and payload, never an HTTP URL or token", async () => {
    const invoke = vi.fn().mockResolvedValue({ status: 200, body: { runtime: "archeaxis-api", contract: "0.1.0-outline", schema_version: 7, sqlite_version: "3.51.3" } });
    window.__TAURI__ = { core: { invoke } };
    await verifyCanonicalCore();
    expect(invoke).toHaveBeenCalledWith("core_command", { request: { operation: "system_version", payload: {} } });
  });
  it("distinguishes a missing object, a refused argument, a core fault and an identity refusal", async () => {
    const cases: Array<[number, RegExp]> = [
      [404, /暂时找不到这项内容，请刷新列表后重试/],
      [400, /这项操作未获允许，请检查填写的内容后重试/],
      [503, /这项操作暂时未能完成，请查看问题记录后重试/],
      [403, /你暂时不能进行这项操作，请检查是否已获得授权/],
    ];
    for (const [status, pattern] of cases) {
      window.__TAURI__ = { core: { invoke: vi.fn().mockResolvedValue({ status, body: {} }) } };
      await expect(coreCommand("sources_list")).rejects.toMatchObject({status, message:expect.stringMatching(pattern), code:status === 403 ? "unauthorized" : "unavailable"});
    }
  });
  it("reports version conflict and rejects malformed status instead of returning success", async () => {
    const invoke = vi.fn().mockResolvedValue({ status: 409, body: {} });
    window.__TAURI__ = { core: { invoke } };
    await expect(coreCommand("document_draft", {})).rejects.toMatchObject({ status: 409 });
    invoke.mockResolvedValue({ status: "200", body: {} });
    await expect(coreCommand("sources_list")).rejects.toMatchObject({ status: 502 });
  });
  it("validates successful DTO bodies and withholds raw native exception text", async () => {
    const invoke = vi.fn().mockResolvedValue({status:200,body:{sources:[{source_id:"partial"}]}});
    window.__TAURI__={core:{invoke}};
    await expect(coreCommand("sources_list")).rejects.toMatchObject({status:502,code:"incompatible"});
    invoke.mockRejectedValue("CORE_RESPONSE_INVALID private transport details");
    await expect(coreCommand("sources_list")).rejects.toMatchObject({status:502,message:"本地核心暂时无法响应，请保留草稿后重试。"});
  });
  it("accepts only a structurally complete machine retest receipt", async () => {
    const receipt={schema:"archeaxis.machine-retest/v1",retest_task_id:"retest_1",answer_id:"retest_1",retest_of:"evaluation_1",knowledge_id:"knowledge_1",question:"fixture question",answer:{answer:"fixture answer"},authority:"candidate",prior:{},request:{},note:"human comparison required"};
    const invoke=vi.fn().mockResolvedValue({status:200,body:receipt});
    window.__TAURI__={core:{invoke}};
    await expect(coreCommand("machine_retest",{body:{retest_of:"evaluation_1",knowledge_id:"knowledge_1",question:"fixture question"}})).resolves.toEqual(receipt);
    invoke.mockResolvedValue({status:200,body:{...receipt,authority:"accepted"}});
    await expect(coreCommand("machine_retest",{body:{}})).rejects.toMatchObject({status:502,code:"incompatible"});
  });
});

it.each(["machine_answer", "machine_retest"] as const)("SIMULATED %s retains safe machine failure without raw diagnostics",async(operation)=>{
  window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:503,body:{schema:"archeaxis.machine-call-failure/v1",operation:operation==="machine_answer"?"answer":"retest",reason_code:"NO_FINAL_ANSWER",execution_state:"UNVERIFIED",answer_published:false,message:"SYNTHETIC_PRIVATE",stderr:"SYNTHETIC_PRIVATE"}})}};
  const error=await coreCommand(operation,{}).catch(error=>error);
  if (!(error instanceof ApiError)) throw new Error("Expected finite Core failure");
  expect(error.machineFailure).toEqual({reason_code:"NO_FINAL_ANSWER",execution_state:"UNVERIFIED",answer_published:false});
  expect(error.message).toContain("模型未返回最终答案");
  expect(JSON.stringify(error)).not.toContain("SYNTHETIC_PRIVATE");
});
it.each(["SYNTHETIC_PRIVATE","__proto__"])("SIMULATED unknown machine reason %s stays generic",async(reason_code)=>{
  window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:503,body:{schema:"archeaxis.machine-call-failure/v1",operation:"retest",reason_code,execution_state:"UNVERIFIED",answer_published:false}})}};
  const error=await coreCommand("machine_retest",{}).catch(error=>error);
  if (!(error instanceof ApiError)) throw new Error("Expected finite Core failure");
  expect(error.machineFailure).toBeUndefined();
  expect(error.message).not.toContain(reason_code);
});

it.each(["machine_answer","machine_retest"] as const)("SIMULATED %s keeps a typed timeout and finite phase without claiming success",async operation=>{
 const diagnostics={request_stage:"model_request",discovery_elapsed_s:0.25,elapsed_s:5,error_type:"TimeoutError"};
 window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:503,body:{schema:"archeaxis.machine-call-failure/v1",operation:operation==="machine_answer"?"answer":"retest",reason_code:"MODEL_CALL_TIMEOUT",execution_state:"UNVERIFIED",answer_published:false,diagnostics:{...diagnostics,raw:"PRIVATE"}}})}};
 const error=await coreCommand(operation,{}).catch(error=>error);expect(error).toBeInstanceOf(ApiError);
 if(!(error instanceof ApiError))throw Error("Expected finite timeout");
 expect(error.machineFailure).toEqual({reason_code:"MODEL_CALL_TIMEOUT",execution_state:"UNVERIFIED",answer_published:false,diagnostics});expect(error.message).toContain("模型服务调用超时");expect(JSON.stringify(error)).not.toContain("PRIVATE");
});

it.each(["machine_answer","machine_retest"] as const)("SIMULATED %s preserves measured failure fields and strips raw provider data",async(operation)=>{
  const diagnostics={requested_model:"synthetic-model",observed_model:null,finish_reason:"length",answer_source:"reasoning_content",elapsed_s:2.5,max_tokens:2048,usage:{input_tokens:12,output_tokens:2048}};
  window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:503,body:{schema:"archeaxis.machine-call-failure/v1",operation:operation==="machine_answer"?"answer":"retest",reason_code:"NO_FINAL_ANSWER",execution_state:"UNVERIFIED",answer_published:false,diagnostics:{...diagnostics,stderr:"SYNTHETIC_PRIVATE",usage:{...diagnostics.usage,raw:"SYNTHETIC_PRIVATE"}}}})}};
  const error=await coreCommand(operation,{}).catch(error=>error);
  expect(error).toBeInstanceOf(ApiError);
  if (!(error instanceof ApiError)) throw new Error("Expected finite Core failure");
  expect(error.machineFailure?.diagnostics).toEqual(diagnostics);
  expect(JSON.stringify(error)).not.toContain("SYNTHETIC_PRIVATE");
});


it("SIMULATED learning titles remain optional for an older Core and accept 80 Unicode scalars",async()=>{
  const legacy={items:[{item_key:"original-long-item-key",next_review:null}],count:1};
  const invoke=vi.fn().mockResolvedValue({status:200,body:legacy});window.__TAURI__={core:{invoke}};
  await expect(coreCommand("learning_items")).resolves.toEqual(legacy);
  const current={items:[{...legacy.items[0],display_title:"🛰".repeat(80)}],count:1};
  invoke.mockResolvedValue({status:200,body:current});
  await expect(coreCommand("learning_items")).resolves.toEqual(current);
});
it.each([null,"","🛰".repeat(81),42])("SIMULATED rejects a supplied malformed learning title %s",async(display_title)=>{
  const body={items:[{item_key:"original-long-item-key",next_review:null,display_title}],count:1};
  window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:200,body})}};
  await expect(coreCommand("learning_items")).rejects.toMatchObject({status:502,code:"incompatible"});
});

it("accepts a real-shaped embedded relation receipt through the finite runtime validator", async () => {
 const body={schema:"archeaxis.ingest-relations/v1",workspace_id:"workspace",restore_epoch:"initial",batch_id:"batch",ordinal:0,input_kind:"immutable_original_markdown",source_id:"source",source_revision:"a".repeat(64),relative_path:"note.md",
  document:{document_id:"doc",source_id:"source",source_revision:"a".repeat(64),title:"Note",version:2,editor_json:{type:"doc",content:[]},text_projection:"",content_sha256:"b".repeat(64),blocks:[]},
  added_relations:0,updated_relations:1,loss:["original_source_links_not_current_document_body"],links:[{ordinal:0,target:"peer",label:null,syntax:"wiki",embed:true,fragment:null,fragment_is_block:false,status:"resolved_reference",reason:"embed_presentation_requested",relation_id:"ingest_fixed",target_ordinal:1}]};
 const invoke=vi.fn().mockResolvedValue({status:200,body}); window.__TAURI__={core:{invoke}};
 await expect(coreCommand("ingest_member_relations_apply",{batch_id:"batch",ordinal:0})).resolves.toEqual(body);
 invoke.mockResolvedValue({status:200,body:{...body,updated_relations:-1}});
 await expect(coreCommand("ingest_member_relations_apply",{})).rejects.toMatchObject({status:502,code:"incompatible"});
 invoke.mockResolvedValue({status:200,body:{...body,links:[{...body.links[0],reason:"invented_render_success"}]}});
 await expect(coreCommand("ingest_member_relations_apply",{})).rejects.toMatchObject({status:502,code:"incompatible"});
});
