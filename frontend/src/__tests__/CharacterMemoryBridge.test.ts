import { afterEach, expect, it, vi } from "vitest";
import { coreCommand } from "../api/core";
const profile={schema:"archeaxis.character-memory/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",revision:1,enabled:false,preferences:"synthetic style",learning_goals:"synthetic goal",memories:[{id:"approved_fixture",text:"synthetic approved memory",provenance:"human fixture"}]};
const receipt={schema:"archeaxis.memory-write/v1",profile,live_store_deleted:false,forgotten_ids:[],historical_chat_modified:false,backups_modified:false,secure_erasure:false};
const exported={schema:"archeaxis.memory-export/v1",profile,contains_personal_memory:true,network_performed:false};
const context={schema:"archeaxis.character-context/v1",workspace_id:profile.workspace_id,restore_epoch:profile.restore_epoch,revision:1,enabled:false,preferences:"",learning_goals:"",approved_memories:[],authority:"human_preferences_only",grants:[],knowledge_admitted:false};
afterEach(()=>{delete window.__TAURI__;});
it("SIMULATED native invoke projects each finite memory response through its canonical schema",async()=>{
 for(const [operation,body] of [["character_memory_get",profile],["character_memory_apply",receipt],["character_memory_export",exported],["character_memory_context",context]] as const){const invoke=vi.fn().mockResolvedValue({status:200,body});window.__TAURI__={core:{invoke}};expect(await coreCommand(operation)).toEqual(body);expect(invoke).toHaveBeenCalledWith("core_command",{request:{operation,payload:{}}});}
});
it.each(["identity","erasure","backup","permissions","network"])("SIMULATED native memory %s drift is rejected before publication",async(field)=>{
 let operation:"character_memory_get"|"character_memory_apply"|"character_memory_context"|"character_memory_export"="character_memory_apply";
 let body:Record<string,unknown>={...receipt};
 if(field==="identity"){operation="character_memory_get";body={...profile,workspace_id:"invalid"};}
 if(field==="erasure")body.secure_erasure=true;
 if(field==="backup")body.backups_modified=true;
 if(field==="permissions"){operation="character_memory_context";body={...context,grants:["execute"]};}
 if(field==="network"){operation="character_memory_export";body={...exported,network_performed:true};}
 window.__TAURI__={core:{invoke:vi.fn().mockResolvedValue({status:200,body})}};await expect(coreCommand(operation)).rejects.toThrow();
});
