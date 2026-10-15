import { coreCommand } from "./core";
import { assertCoreDto, type CharacterProfile, type CharacterMemoryWrite, type CharacterMemoryReceipt, type CharacterMemoryExport } from "./generated/core-contract";
import { sameValue } from "../presentation/exchangeProof";

export type MemoryCommand = CharacterMemoryWrite["command"];
const bytes = (value:string) => new TextEncoder().encode(value).length;
export function memoryProfile(value:unknown):CharacterProfile {
  const profile=assertCoreDto<CharacterProfile>("CharacterProfile",value);
  const text=(value:string,max:number)=>!value.includes("\0")&&bytes(value)<=max;
  if(!text(profile.preferences,8192)||!text(profile.learning_goals,8192)||bytes(JSON.stringify(profile))>131072
    ||new Set(profile.memories.map(row=>row.id)).size!==profile.memories.length
    ||profile.memories.some(row=>!row.text.trim()||!row.provenance.trim()||!text(row.text,4096)||!text(row.provenance,1024)))throw new Error("MEMORY_PROFILE_INVALID");
  return profile;
}
export async function readMemoryProfile(){return memoryProfile(await coreCommand("character_memory_get"));}
export function memoryAttempt(base:CharacterProfile,command:MemoryCommand) {
  const profile=structuredClone(memoryProfile(base));
  if(profile.revision>=Number.MAX_SAFE_INTEGER)throw new Error("MEMORY_REVISION_LIMIT");
  const forgotten:string[]=[];
  switch(command.operation){
    case "profile":profile.preferences=command.preferences;profile.learning_goals=command.learning_goals;break;
    case "remember":if(profile.memories.some(row=>row.id===command.memory.id))throw new Error("MEMORY_ALREADY_EXISTS");profile.memories.push(structuredClone(command.memory));break;
    case "correct":{const index=profile.memories.findIndex(row=>row.id===command.memory.id);if(index<0)throw new Error("MEMORY_NOT_FOUND");profile.memories[index]=structuredClone(command.memory);break;}
    case "forget":if(!profile.memories.some(row=>row.id===command.id))throw new Error("MEMORY_NOT_FOUND");forgotten.push(command.id);profile.memories=profile.memories.filter(row=>row.id!==command.id);break;
    case "forget_all":forgotten.push(...profile.memories.map(row=>row.id));profile.memories=[];break;
    case "disable":profile.enabled=false;break;
    case "enable":profile.enabled=true;break;
  }
  profile.revision++;
  memoryProfile(profile);
  const body=assertCoreDto<CharacterMemoryWrite>("CharacterMemoryWrite",{workspace_id:base.workspace_id,restore_epoch:base.restore_epoch,expected_revision:base.revision,command:structuredClone(command)});
  return {body,base:structuredClone(base),expected:profile,forgotten};
}
export type MemoryAttempt = ReturnType<typeof memoryAttempt>;
export async function applyMemory(attempt:MemoryAttempt) {
  const receipt=assertCoreDto<CharacterMemoryReceipt>("CharacterMemoryReceipt",await coreCommand("character_memory_apply",{body:structuredClone(attempt.body)}));
  memoryProfile(receipt.profile);
  if(!sameValue(receipt.profile,attempt.expected)||!sameValue(receipt.forgotten_ids,attempt.forgotten)||receipt.live_store_deleted!==(attempt.forgotten.length>0))throw new Error("MEMORY_RECEIPT_MISMATCH");
  return receipt;
}
export async function exportMemory(){
  const value=assertCoreDto<CharacterMemoryExport>("CharacterMemoryExport",await coreCommand("character_memory_export"));
  memoryProfile(value.profile);
  return value;
}
