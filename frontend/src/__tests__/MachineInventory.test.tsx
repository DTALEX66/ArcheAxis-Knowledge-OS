import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MachineAnswerPanel } from "../components/MachineAnswerPanel";
import { assertCoreDto } from "../api/generated/core-contract";
import { createHash, webcrypto } from "node:crypto";
const bridge = vi.hoisted(() => ({call: vi.fn()}));
vi.mock("../api/core", () => ({coreCommand: bridge.call}));
const reply = {schema:"archeaxis.machine-inventory/v1",status:"READ_VERIFIED",listed_model_count:1,selected_model_listed:true,loaded_status:"UNKNOWN",inference_status:"NOT_EXECUTED",usage:null,cost:null,evidence_scope:"MODEL_INVENTORY_ONLY"};
beforeEach(() => { bridge.call.mockReset(); });

it("keeps a previous explicit choice visible when inventory refresh fails", async()=>{
  bridge.call.mockResolvedValueOnce({...reply,model_choices:["m1"]}).mockRejectedValueOnce(new Error("synthetic inventory failure"));
  render(<MachineAnswerPanel knowledgeId="k1"/>);
  const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"探测本地模型清单"}));
  await user.selectOptions(screen.getByLabelText("兼容模式本地回答模型"),"m1");
  await user.click(screen.getByRole("button",{name:"探测本地模型清单"}));
  await waitFor(()=>expect(screen.getByLabelText("兼容模式本地回答模型")).toHaveValue("m1"));
  expect(screen.getByRole("option",{name:"m1（此前选择，本次清单未确认）"})).toBeInTheDocument();
});

it("probes only after an explicit click and blocks a duplicate pending request", async () => {
  let resolve!: (value: unknown) => void;
  bridge.call.mockImplementation(() => new Promise(done => {resolve = done;}));
  render(<MachineAnswerPanel knowledgeId="k1" />);
  expect(bridge.call).not.toHaveBeenCalled();
  const user = userEvent.setup(); const button = screen.getByRole("button", {name:"探测本地模型清单"});
  await user.click(button); await user.click(button);
  expect(bridge.call).toHaveBeenCalledTimes(1);
  expect(bridge.call).toHaveBeenCalledWith("machine_inventory");
  resolve(reply);
  await waitFor(() => expect(screen.getByLabelText("本地模型清单探测结果")).toHaveTextContent("加载状态未知，推理尚未验证"));
});

it("ignores a late result after changing knowledge", async () => {
  let resolve!: (value: unknown) => void;
  bridge.call.mockImplementation(() => new Promise(done => {resolve = done;}));
  const ui = render(<MachineAnswerPanel knowledgeId="k1" />);
  await userEvent.setup().click(screen.getByRole("button", {name:"探测本地模型清单"}));
  ui.rerender(<MachineAnswerPanel knowledgeId="k2" />);
  resolve(reply);
  await waitFor(() => expect(screen.getByLabelText("本地模型清单探测结果")).toHaveTextContent("清单未探测"));
  expect(screen.getByLabelText("本地模型清单探测结果")).not.toHaveTextContent("共 1 项");
});

it("rejects fake availability, leaked fields and fabricated failed counts", () => {
  expect(assertCoreDto("MachineInventoryDto", reply)).toEqual(reply);
  for(const model_choices of [[""],["m\n"],["m".repeat(257)],Array(257).fill("m")])expect(()=>assertCoreDto("MachineInventoryDto",{...reply,model_choices})).toThrow();
  for (const patch of [{loaded_status:"LOADED"},{inference_status:"PASS"},{endpoint:"SYNTHETIC_PRIVATE"},{status:"READ_FAILED"},{listed_model_count:257},{listed_model_count:-1},{listed_model_count:Infinity},{cost:0}]) {
    expect(() => assertCoreDto("MachineInventoryDto", {...reply,...patch})).toThrow();
  }
  expect(assertCoreDto("MachineInventoryDto", {...reply,status:"READ_FAILED",listed_model_count:null,selected_model_listed:null})).toBeTruthy();
});

it("binds explicit model selection to a frozen lost-ACK retry", async () => {
  vi.stubGlobal("crypto", webcrypto);
  const requests: Record<string,unknown>[]=[];
  let doc: Record<string,unknown>;
  bridge.call.mockImplementation(async(operation:string,payload?:{body:Record<string,unknown>})=>{
    if(operation==="model_configuration_get")return {schema:"archeaxis.model-configuration/v1",revision:0,profiles:{},bindings:[],workspace_id:"a".repeat(32),restore_epoch:"initial"};
    if(operation==="machine_inventory")return {...reply,model_choices:["m1","m2"]};
    if(operation==="machine_answer"){
      const request=payload!.body; requests.push(structuredClone(request));
      if(requests.length===1)throw new Error("synthetic lost ACK");
      doc={schema:"archeaxis.machine-answer/v1",answer_id:"answer_req_"+createHash("sha256").update(String(request.client_request_id)).digest("hex"),client_request_id:request.client_request_id,knowledge_id:"k1",question:request.question,authority:"candidate",answer:{answer:"synthetic answer",model:"m1",requested_model:"m1"},request:{schema:"archeaxis.machine-answer-request/v1",knowledge_id:"k1",question:request.question,max_tokens:request.max_tokens,timeout_s:120,context_grant:null,context_sha256:"a".repeat(64),model:"m1"}};
      return doc;
    }
    if(operation==="machine_task_get")return {task_id:doc.answer_id,scope:"runtime.answer",outcome:"unmeasured",model_version:"m1",knowledge_version:"k1@v1",conditions:JSON.stringify(doc)};
    throw new Error("unexpected operation");
  });
  render(<MachineAnswerPanel knowledgeId="k1"/>);
  const user=userEvent.setup();
  await user.click(screen.getByRole("button",{name:"探测本地模型清单"}));
  await user.selectOptions(screen.getByLabelText("兼容模式本地回答模型"),"m1");
  await user.selectOptions(screen.getByLabelText("本次输出预算"),"4096");
  await user.type(screen.getByLabelText("实际问题"),"synthetic question");
  await user.click(screen.getByRole("button",{name:"执行本地机器回答"}));
  await waitFor(()=>expect(screen.getByLabelText("兼容模式本地回答模型")).toBeDisabled());
  expect(screen.getByLabelText("本次输出预算")).toBeDisabled();
  await user.click(screen.getByRole("button",{name:"重试同一回答请求"}));
  expect(screen.queryByLabelText("真实机器回答")).not.toBeInTheDocument();
  expect(screen.getByRole("button",{name:"重试同一回答请求"})).toBeDisabled();
  expect(requests).toHaveLength(1);
  expect(requests[0].model).toBe("m1"); expect(typeof requests[0].client_request_id).toBe("string");
  expect(requests[0].max_tokens).toBe(4096);
  vi.unstubAllGlobals();
});
