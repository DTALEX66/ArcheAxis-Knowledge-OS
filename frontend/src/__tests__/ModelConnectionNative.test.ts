import {afterEach, expect, it, vi} from "vitest";
import {readModelInventory} from "../runtime/modelConnection";

afterEach(()=>vi.unstubAllGlobals());

it("reads the native directory without requiring browser CORS or dispatching inference", async()=>{
  const invoke=vi.fn().mockResolvedValue({schema:"archeaxis.local-model-inventory/v1",models:["aaos-deep-27b-mtp"],inference_status:"NOT_EXECUTED",loaded_status:"UNKNOWN"});
  const fetcher=vi.fn().mockRejectedValue(new TypeError("CORS blocked"));
  vi.stubGlobal("__TAURI__",{core:{invoke}});vi.stubGlobal("fetch",fetcher);
  await expect(readModelInventory({endpoint:"http://127.0.0.1:1234/v1",protocol:"openai"},new AbortController().signal)).resolves.toEqual(["aaos-deep-27b-mtp"]);
  expect(invoke).toHaveBeenCalledTimes(1);
  expect(invoke).toHaveBeenCalledWith("model_inventory_read",{request:{endpoint:"http://127.0.0.1:1234/v1",protocol:"openai"}});
  expect(fetcher).not.toHaveBeenCalled();
});

it("keeps native failures finite and never falls back to browser networking", async()=>{
  const invoke=vi.fn().mockRejectedValue({code:"HTTP_FAILURE",status:503,body:"private response"});
  const fetcher=vi.fn();vi.stubGlobal("__TAURI__",{core:{invoke}});vi.stubGlobal("fetch",fetcher);
  await expect(readModelInventory({endpoint:"http://127.0.0.1:1234/v1",protocol:"openai"},new AbortController().signal)).rejects.toThrow("HTTP 503");
  expect(fetcher).not.toHaveBeenCalled();
});

it("rejects destinations before native invocation", async()=>{
  const invoke=vi.fn();vi.stubGlobal("__TAURI__",{core:{invoke}});
  for(const endpoint of ["https://example.com/v1","http://user:secret@127.0.0.1:1234/v1","http://127.0.0.1:1234/v1?token=hidden"]){
    await expect(readModelInventory({endpoint,protocol:"openai"},new AbortController().signal)).rejects.toThrow(/数值 loopback/);
  }
  expect(invoke).not.toHaveBeenCalled();
});

it("does not invoke after cancellation or accept a late native result",async()=>{
  const cancelled=new AbortController();cancelled.abort();const invoke=vi.fn();vi.stubGlobal("__TAURI__",{core:{invoke}});
  await expect(readModelInventory({endpoint:"http://127.0.0.1:1234/v1",protocol:"openai"},cancelled.signal)).rejects.toMatchObject({name:"AbortError"});
  expect(invoke).not.toHaveBeenCalled();
  const active=new AbortController();let resolve!:(value:unknown)=>void;
  invoke.mockReturnValue(new Promise(done=>{resolve=done;}));
  const read=readModelInventory({endpoint:"http://127.0.0.1:1234/v1",protocol:"openai"},active.signal);
  active.abort();resolve({schema:"archeaxis.local-model-inventory/v1",models:["old"],inference_status:"NOT_EXECUTED",loaded_status:"UNKNOWN"});
  await expect(read).rejects.toMatchObject({name:"AbortError"});
});

it.each([
  {schema:"wrong",models:["chosen"]},
  {schema:"archeaxis.local-model-inventory/v1",models:["chosen"],inference_status:"EXECUTED",loaded_status:"UNKNOWN"},
  {schema:"archeaxis.local-model-inventory/v1",models:[""],inference_status:"NOT_EXECUTED",loaded_status:"UNKNOWN"},
  {schema:"archeaxis.local-model-inventory/v1",models:Array(257).fill("chosen"),inference_status:"NOT_EXECUTED",loaded_status:"UNKNOWN"},
])("refuses incompatible native directory evidence", async result=>{
  vi.stubGlobal("__TAURI__",{core:{invoke:vi.fn().mockResolvedValue(result)}});
  await expect(readModelInventory({endpoint:"http://127.0.0.1:1234/v1",protocol:"openai"},new AbortController().signal)).rejects.toThrow(/格式不正确/);
});
