// GENERATED from packages/contracts/v2/ai-asset.schema.json. Do not hand edit.
// Schema SHA256: 38de01ec460d34ea42e69162224eeb0830a8b2919b66c08681d4bb2bbf67439e
export type JSONValue = null | boolean | number | string | Array<JSONValue> | { [key: string]: JSONValue };
export type ObjectReference = { "kind": "document"; "document_id": string; "version": number; "block_id"?: string | null } | { "kind": "source"; "source_id": string; "sha256": string } | { "kind": "knowledge"; "knowledge_id": string };
export type AssetSnapshot = { "document_id": string; "version": number; "content_sha256": string };
export type AssetKind = "memory" | "knowledge_package" | "rule" | "skill" | "experience";
export type AssetOutcome = "passed" | "failed" | "unmeasured";
export type AssetJudgment = { "criterion_id": string; "outcome": AssetOutcome; "basis": string };
export type AssetReview = { "asset": AssetSnapshot; "rubric": AssetSnapshot; "reviewer": string; "basis": string; "judgments": Array<AssetJudgment>; "outcome": AssetOutcome };
export type AiAsset = { "schema": "archeaxis.ai-asset/v1"; "kind": AssetKind; "content": JSONValue; "purpose": string; "scope": Array<ObjectReference>; "provenance": Array<ObjectReference>; "expires_at"?: number | null; "state": "candidate" | "adopted" | "withdrawn"; "members": Array<AssetSnapshot>; "conflicts": Array<AssetSnapshot>; "revises"?: AssetSnapshot | null; "review"?: AssetReview | null; "source_payload"?: JSONValue | null };
export type AssetConsumer = "local-machine" | "manual-context-packet";
export type AssetOperation = "read_packet" | "answer" | "retest";
export type AssetContextGrant = { "schema": "archeaxis.asset-context-grant/v1"; "asset": AssetSnapshot; "purpose": string; "consumer": AssetConsumer; "operations": Array<AssetOperation>; "authorization_basis": string; "expires_at"?: number | null; "state": "candidate" | "granted" | "revoked" };
export type AssetPacketRequest = { "request_id": string; "grant": AssetSnapshot; "asset": AssetSnapshot; "purpose": string; "consumer": AssetConsumer; "operation": AssetOperation };
export type AssetPacketItem = { "snapshot": AssetSnapshot; "kind": AssetKind; "content": JSONValue; "purpose": string; "scope": Array<ObjectReference>; "provenance": Array<ObjectReference>; "engine_execution": "NOT_EXECUTED"; "grants_professional_truth": false; "grants_human_mastery": false; "grants_machine_qualification": false };
export type AssetPacket = { "schema": "archeaxis.ai-context-packet/v1"; "asset": AssetSnapshot; "consumer": AssetConsumer; "purpose": string; "operation": "read_packet"; "items": Array<AssetPacketItem>; "grant": AssetSnapshot; "reference_only_sources": true; "private_session_access": false; "tool_execution": "NOT_EXECUTED"; "machine_qualification": false; "human_mastery": false; "professional_truth": false };
export type AssetPacketReceipt = { "schema": "archeaxis.ai-context-packet-receipt/v1"; "request_id": string; "request_sha256": string; "packet_sha256": string; "asset": AssetSnapshot; "grant": AssetSnapshot; "consumer": AssetConsumer; "purpose": string; "operation": "read_packet"; "delivery_status": "PREPARED_NOT_SENT_TO_PEER"; "model_execution": "NOT_EXECUTED"; "tool_execution": "NOT_EXECUTED"; "grants_machine_qualification": false; "grants_human_mastery": false };
export type AssetPacketResponse = { "packet": AssetPacket; "packet_sha256": string; "receipt": AssetPacketReceipt; "audit_task_id": string; "duplicate": boolean };
export type AiAssetListItem = { "document_id": string; "title": string; "version": number; "content_sha256": string };
export type AiAssetsPage = { "items": Array<AiAssetListItem>; "next_cursor": string | null };
export type MachineAssetContext = { "schema": "archeaxis.machine-asset-context/v1"; "asset": AssetSnapshot; "grant": AssetSnapshot; "consumer": "local-machine"; "operation": "answer" | "retest"; "packet_sha256": string; "member_snapshots": Array<AssetSnapshot>; "tool_execution": "NOT_EXECUTED"; "private_session_access": false };
export type AiAssetDtoByName = { JSONValue: JSONValue; ObjectReference: ObjectReference; AssetSnapshot: AssetSnapshot; AssetKind: AssetKind; AssetOutcome: AssetOutcome; AssetJudgment: AssetJudgment; AssetReview: AssetReview; AiAsset: AiAsset; AssetConsumer: AssetConsumer; AssetOperation: AssetOperation; AssetContextGrant: AssetContextGrant; AssetPacketRequest: AssetPacketRequest; AssetPacketItem: AssetPacketItem; AssetPacket: AssetPacket; AssetPacketReceipt: AssetPacketReceipt; AssetPacketResponse: AssetPacketResponse; AiAssetListItem: AiAssetListItem; AiAssetsPage: AiAssetsPage; MachineAssetContext: MachineAssetContext };
const definitions: Record<string,Schema> = {"JSONValue":{"anyOf":[{"type":"null"},{"type":"boolean"},{"type":"number"},{"type":"string"},{"type":"array","items":{"$ref":"#/$defs/JSONValue"}},{"type":"object","additionalProperties":{"$ref":"#/$defs/JSONValue"}}]},"ObjectReference":{"oneOf":[{"type":"object","additionalProperties":false,"properties":{"kind":{"const":"document"},"document_id":{"type":"string","minLength":1,"maxLength":256,"pattern":"^(?!\\.{1,2}$)[A-Za-z0-9_.-]+$"},"version":{"type":"integer","minimum":1,"maximum":9223372036854775807},"block_id":{"anyOf":[{"type":"string","minLength":1,"maxLength":256,"pattern":"^(?!\\.{1,2}$)[A-Za-z0-9_.-]+$"},{"type":"null"}]}},"required":["kind","document_id","version"]},{"type":"object","additionalProperties":false,"properties":{"kind":{"const":"source"},"source_id":{"type":"string","minLength":1,"maxLength":256,"pattern":"^(?!\\.{1,2}$)[A-Za-z0-9_.-]+$"},"sha256":{"type":"string","pattern":"^[0-9a-f]{64}$","minLength":64,"maxLength":64}},"required":["kind","source_id","sha256"]},{"type":"object","additionalProperties":false,"properties":{"kind":{"const":"knowledge"},"knowledge_id":{"type":"string","minLength":1,"maxLength":256,"pattern":"^(?!\\.{1,2}$)[A-Za-z0-9_.-]+$"}},"required":["kind","knowledge_id"]}]},"AssetSnapshot":{"type":"object","additionalProperties":false,"properties":{"document_id":{"type":"string","minLength":1,"maxLength":128},"version":{"type":"integer","minimum":1,"maximum":9223372036854775807},"content_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$","minLength":64,"maxLength":64}},"required":["document_id","version","content_sha256"]},"AssetKind":{"type":"string","enum":["memory","knowledge_package","rule","skill","experience"]},"AssetOutcome":{"type":"string","enum":["passed","failed","unmeasured"]},"AssetJudgment":{"type":"object","additionalProperties":false,"properties":{"criterion_id":{"type":"string"},"outcome":{"$ref":"#/$defs/AssetOutcome"},"basis":{"type":"string","minLength":1,"maxLength":16384}},"required":["criterion_id","outcome","basis"]},"AssetReview":{"type":"object","additionalProperties":false,"properties":{"asset":{"$ref":"#/$defs/AssetSnapshot"},"rubric":{"$ref":"#/$defs/AssetSnapshot"},"reviewer":{"type":"string","minLength":1,"maxLength":128},"basis":{"type":"string","minLength":1,"maxLength":16384},"judgments":{"type":"array","items":{"$ref":"#/$defs/AssetJudgment"},"maxItems":64},"outcome":{"$ref":"#/$defs/AssetOutcome"}},"required":["asset","rubric","reviewer","basis","judgments","outcome"]},"AiAsset":{"type":"object","additionalProperties":false,"properties":{"schema":{"const":"archeaxis.ai-asset/v1"},"kind":{"$ref":"#/$defs/AssetKind"},"content":{"$ref":"#/$defs/JSONValue","description":"Inert JSON; combined content/source_payload at most65536 UTF8 serialized bytes; depth16/nodes4096 bounded by Core."},"purpose":{"type":"string","maxLength":1024,"description":"Core enforces at most 1024 UTF8 bytes; adopted/granted requires nonblank."},"scope":{"type":"array","items":{"$ref":"#/$defs/ObjectReference"},"maxItems":32},"provenance":{"type":"array","items":{"$ref":"#/$defs/ObjectReference"},"maxItems":32},"expires_at":{"anyOf":[{"type":"integer","minimum":0,"maximum":253402300799},{"type":"null"}]},"state":{"type":"string","enum":["candidate","adopted","withdrawn"]},"members":{"type":"array","items":{"$ref":"#/$defs/AssetSnapshot"},"maxItems":64},"conflicts":{"type":"array","items":{"$ref":"#/$defs/AssetSnapshot"},"maxItems":32},"revises":{"anyOf":[{"$ref":"#/$defs/AssetSnapshot"},{"type":"null"}]},"review":{"anyOf":[{"$ref":"#/$defs/AssetReview"},{"type":"null"}]},"source_payload":{"anyOf":[{"$ref":"#/$defs/JSONValue"},{"type":"null"}]}},"required":["schema","kind","content","purpose","scope","provenance","state","members","conflicts"]},"AssetConsumer":{"type":"string","enum":["local-machine","manual-context-packet"]},"AssetOperation":{"type":"string","enum":["read_packet","answer","retest"]},"AssetContextGrant":{"type":"object","additionalProperties":false,"properties":{"schema":{"const":"archeaxis.asset-context-grant/v1"},"asset":{"$ref":"#/$defs/AssetSnapshot"},"purpose":{"type":"string","maxLength":1024,"description":"Core enforces at most 1024 UTF8 bytes; adopted/granted requires nonblank."},"consumer":{"$ref":"#/$defs/AssetConsumer"},"operations":{"type":"array","items":{"$ref":"#/$defs/AssetOperation"},"maxItems":3},"authorization_basis":{"type":"string","maxLength":16384},"expires_at":{"anyOf":[{"type":"integer","minimum":0,"maximum":253402300799},{"type":"null"}]},"state":{"type":"string","enum":["candidate","granted","revoked"]}},"required":["schema","asset","purpose","consumer","operations","authorization_basis","state"]},"AssetPacketRequest":{"type":"object","additionalProperties":false,"properties":{"request_id":{"type":"string","minLength":1,"maxLength":128,"pattern":"^[!-~]+$"},"grant":{"$ref":"#/$defs/AssetSnapshot"},"asset":{"$ref":"#/$defs/AssetSnapshot"},"purpose":{"type":"string","maxLength":1024},"consumer":{"$ref":"#/$defs/AssetConsumer"},"operation":{"$ref":"#/$defs/AssetOperation"}},"required":["request_id","grant","asset","purpose","consumer","operation"]},"AssetPacketItem":{"type":"object","additionalProperties":false,"properties":{"snapshot":{"$ref":"#/$defs/AssetSnapshot"},"kind":{"$ref":"#/$defs/AssetKind"},"content":{"$ref":"#/$defs/JSONValue"},"purpose":{"type":"string"},"scope":{"type":"array","items":{"$ref":"#/$defs/ObjectReference"},"maxItems":32},"provenance":{"type":"array","items":{"$ref":"#/$defs/ObjectReference"},"maxItems":32},"engine_execution":{"const":"NOT_EXECUTED"},"grants_professional_truth":{"const":false},"grants_human_mastery":{"const":false},"grants_machine_qualification":{"const":false}},"required":["snapshot","kind","content","purpose","scope","provenance","engine_execution","grants_professional_truth","grants_human_mastery","grants_machine_qualification"]},"AssetPacket":{"type":"object","additionalProperties":false,"properties":{"schema":{"const":"archeaxis.ai-context-packet/v1"},"asset":{"$ref":"#/$defs/AssetSnapshot"},"consumer":{"$ref":"#/$defs/AssetConsumer"},"purpose":{"type":"string"},"operation":{"const":"read_packet"},"items":{"type":"array","items":{"$ref":"#/$defs/AssetPacketItem"},"maxItems":128},"grant":{"$ref":"#/$defs/AssetSnapshot"},"reference_only_sources":{"const":true},"private_session_access":{"const":false},"tool_execution":{"const":"NOT_EXECUTED"},"machine_qualification":{"const":false},"human_mastery":{"const":false},"professional_truth":{"const":false}},"required":["schema","asset","consumer","purpose","operation","items","grant","reference_only_sources","private_session_access","tool_execution","machine_qualification","human_mastery","professional_truth"]},"AssetPacketReceipt":{"type":"object","additionalProperties":false,"properties":{"schema":{"const":"archeaxis.ai-context-packet-receipt/v1"},"request_id":{"type":"string"},"request_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$","minLength":64,"maxLength":64},"packet_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$","minLength":64,"maxLength":64},"asset":{"$ref":"#/$defs/AssetSnapshot"},"grant":{"$ref":"#/$defs/AssetSnapshot"},"consumer":{"$ref":"#/$defs/AssetConsumer"},"purpose":{"type":"string"},"operation":{"const":"read_packet"},"delivery_status":{"const":"PREPARED_NOT_SENT_TO_PEER"},"model_execution":{"const":"NOT_EXECUTED"},"tool_execution":{"const":"NOT_EXECUTED"},"grants_machine_qualification":{"const":false},"grants_human_mastery":{"const":false}},"required":["schema","request_id","request_sha256","packet_sha256","asset","grant","consumer","purpose","operation","delivery_status","model_execution","tool_execution","grants_machine_qualification","grants_human_mastery"]},"AssetPacketResponse":{"type":"object","additionalProperties":false,"properties":{"packet":{"$ref":"#/$defs/AssetPacket"},"packet_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$","minLength":64,"maxLength":64},"receipt":{"$ref":"#/$defs/AssetPacketReceipt"},"audit_task_id":{"type":"string"},"duplicate":{"type":"boolean"}},"required":["packet","packet_sha256","receipt","audit_task_id","duplicate"]},"AiAssetListItem":{"type":"object","additionalProperties":false,"properties":{"document_id":{"type":"string"},"title":{"type":"string"},"version":{"type":"integer"},"content_sha256":{"type":"string"}},"required":["document_id","title","version","content_sha256"]},"AiAssetsPage":{"type":"object","additionalProperties":false,"properties":{"items":{"type":"array","items":{"$ref":"#/$defs/AiAssetListItem"}},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}]}},"required":["items","next_cursor"]},"MachineAssetContext":{"type":"object","additionalProperties":false,"properties":{"schema":{"const":"archeaxis.machine-asset-context/v1"},"asset":{"$ref":"#/$defs/AssetSnapshot"},"grant":{"$ref":"#/$defs/AssetSnapshot"},"consumer":{"const":"local-machine"},"operation":{"enum":["answer","retest"],"type":"string"},"packet_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$","minLength":64,"maxLength":64},"member_snapshots":{"type":"array","items":{"$ref":"#/$defs/AssetSnapshot"},"maxItems":128},"tool_execution":{"const":"NOT_EXECUTED"},"private_session_access":{"const":false}},"required":["schema","asset","grant","consumer","operation","packet_sha256","member_snapshots","tool_execution","private_session_access"]}};

type Schema = { [key: string]: any } | boolean;
const own = (value: object, key: string) => Object.prototype.hasOwnProperty.call(value, key);
function sameJson(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v,i) => sameJson(v,b[i]));
  if (a && b && typeof a === "object" && typeof b === "object" && !Array.isArray(a) && !Array.isArray(b)) {
    const keys=Object.keys(a); return keys.length===Object.keys(b).length && keys.every(k=>own(b,k)&&sameJson((a as Record<string,unknown>)[k],(b as Record<string,unknown>)[k]));
  }
  return false;
}
// Reject values JSON cannot faithfully carry, even inside inert arbitrary content.
function isJson(value: unknown, stack = new Set<object>()): boolean {
  if (value === null || typeof value === "string" || typeof value === "boolean") return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (!value || typeof value !== "object" || stack.has(value) || Object.getOwnPropertySymbols(value).length) return false;
  if (!Array.isArray(value) && Object.getPrototypeOf(value)!==Object.prototype && Object.getPrototypeOf(value)!==null) return false;
  stack.add(value);
  let valid: boolean;
  if (Array.isArray(value)) valid=Object.keys(value).length===value.length && Object.getOwnPropertyNames(value).length===value.length+1 && Array.from({length:value.length},(_,i)=>{const d=Object.getOwnPropertyDescriptor(value,String(i));return !!d&&own(d,"value")&&isJson(d.value,stack);}).every(Boolean);
  else valid=Object.keys(value).length===Object.getOwnPropertyNames(value).length && Object.keys(value).every(k=>{const d=Object.getOwnPropertyDescriptor(value,k);return !!d&&own(d,"value")&&isJson(d.value,stack);});
  stack.delete(value); return valid;
}
function validate(node: Schema, value: unknown): boolean {
  if (node===true) return true;
  if (node===false) return false;
  if (node.$ref) {
    const name=node.$ref.replace(/^#\/\$defs\//,"");
    if (!own(definitions,name) || !validate(definitions[name],value)) return false;
  }
  if (own(node,"const") && !sameJson(node.const,value)) return false;
  if (node.enum && !node.enum.some((v:unknown)=>sameJson(v,value))) return false;
  if (node.anyOf && !node.anyOf.some((child:Schema)=>validate(child,value))) return false;
  if (node.oneOf && node.oneOf.filter((child:Schema)=>validate(child,value)).length!==1) return false;
  if (node.allOf && !node.allOf.every((child:Schema)=>validate(child,value))) return false;
  if (node.not && validate(node.not,value)) return false;
  if (Array.isArray(node.type)) {
    if (!node.type.some((type:string)=>validate({...node,type},value))) return false;
  } else if (node.type) {
    switch(node.type) {
      case "null": if(value!==null)return false;break;
      case "boolean": if(typeof value!=="boolean")return false;break;
      case "number": if(typeof value!=="number"||!Number.isFinite(value))return false;break;
      case "integer": if(typeof value!=="number"||!Number.isSafeInteger(value))return false;break;
      case "string": if(typeof value!=="string")return false;break;
      case "array": if(!Array.isArray(value))return false;break;
      case "object": if(!value||typeof value!=="object"||Array.isArray(value))return false;break;
      default: return false;
    }
  }
  if (typeof value==="number") {
    if(node.minimum!==undefined&&value<node.minimum)return false;
    if(node.maximum!==undefined&&value>node.maximum)return false;
    if(node.exclusiveMinimum!==undefined&&value<=node.exclusiveMinimum)return false;
    if(node.exclusiveMaximum!==undefined&&value>=node.exclusiveMaximum)return false;
    if(node.multipleOf!==undefined&&!Number.isInteger(value/node.multipleOf))return false;
  }
  if (typeof value==="string") {
    const length=Array.from(value).length;
    if(node.minLength!==undefined&&length<node.minLength)return false;
    if(node.maxLength!==undefined&&length>node.maxLength)return false;
    if(node.pattern!==undefined&&!new RegExp(node.pattern,"u").test(value))return false;
  }
  if (Array.isArray(value)) {
    if(node.minItems!==undefined&&value.length<node.minItems)return false;
    if(node.maxItems!==undefined&&value.length>node.maxItems)return false;
    if(node.items!==undefined&&!value.every(v=>validate(node.items,v)))return false;
    if(node.uniqueItems&&value.some((v,i)=>value.slice(0,i).some(p=>sameJson(v,p))))return false;
  }
  if(value&&typeof value==="object"&&!Array.isArray(value)) {
    const keys=Object.keys(value),properties=node.properties??{};
    if(node.minProperties!==undefined&&keys.length<node.minProperties)return false;
    if(node.maxProperties!==undefined&&keys.length>node.maxProperties)return false;
    if(node.required&&!node.required.every((k:string)=>own(value,k)))return false;
    for (const key of keys) {
      const item=(value as Record<string,unknown>)[key];
      if(own(properties,key)) {if(!validate(properties[key],item))return false;}
      else if(node.additionalProperties===false)return false;
      else if(typeof node.additionalProperties==="object"&&!validate(node.additionalProperties,item))return false;
    }
  }
  return true;
}
export function assertAiAssetDto<T>(name: keyof AiAssetDtoByName, value: unknown): T {
  let valid=false;
  try { valid=own(definitions,name)&&isJson(value)&&validate(definitions[name],value); } catch { valid=false; }
  if(!valid) throw new Error(`Invalid AI asset contract: ${name}`);
  return value as T;
}
