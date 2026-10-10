import { afterEach, expect, it, vi } from "vitest";
import { coreCommand } from "../api/core";
import { ApiError } from "../api/client";
afterEach(()=>{delete window.__TAURI__;});
it.each([[403,"RECORDED",`withheld_${"a".repeat(64)}`],[500,"FAILED",null]] as const)("preserves finite execution state at status %s without exposing raw body",async(status,audit_status,audit_task_id)=>{
 window.__TAURI__={core:{invoke:vi.fn(async()=>({status,body:{schema:"archeaxis.machine-execution-refusal/v1",execution_state:"EXECUTED_BUT_WITHHELD",answer_published:false,audit_status,audit_task_id,question:"must not propagate",answer:"must not propagate"}}))}};
 let caught:unknown;try{await coreCommand("machine_answer",{});}catch(error){caught=error;}
 expect(caught).toBeInstanceOf(ApiError);const error=caught as ApiError;expect(error.execution).toEqual({execution_state:"EXECUTED_BUT_WITHHELD",answer_published:false,audit_status,audit_task_id});expect(JSON.stringify(error.execution)).not.toMatch(/must not propagate/);
});
it("inconsistent execution envelope cannot claim a recorded audit",async()=>{
 window.__TAURI__={core:{invoke:vi.fn(async()=>({status:403,body:{schema:"archeaxis.machine-execution-refusal/v1",execution_state:"EXECUTED_BUT_WITHHELD",answer_published:false,audit_status:"RECORDED",audit_task_id:null}}))}};
 let caught:unknown;try{await coreCommand("machine_retest",{});}catch(error){caught=error;}
 expect(caught).toBeInstanceOf(ApiError);expect((caught as ApiError).execution).toBeUndefined();
});
