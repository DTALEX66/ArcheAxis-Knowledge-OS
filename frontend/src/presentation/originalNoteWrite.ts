import type { JSONContent } from "@tiptap/core";
import { coreCommand } from "../api/core";
import type { DocumentDto } from "../api/generated/core-contract";
import { documentRequestIdentity } from "./documentRequestIdentity";
import { ApiError } from "../api/client";

export class OriginalNoteRefused extends Error {}

export type OriginalNoteAttempt = { id:string; body:{create_request_id:string;title:string;editor_json:JSONContent} };
function canonical(value:unknown):string {
  if(Array.isArray(value))return `[${value.map(canonical).join(",")}]`;
  if(value&&typeof value==="object")return `{${Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>`${JSON.stringify(key)}:${canonical(item)}`).join(",")}}`;
  return JSON.stringify(value);
}
export async function prepareOriginalNote():Promise<OriginalNoteAttempt> {
  const requestId=`note_${crypto.randomUUID()}`;
  return {id:await documentRequestIdentity(requestId),body:{create_request_id:requestId,title:"原创笔记",
    editor_json:{type:"doc",content:[{type:"paragraph",attrs:{block_id:crypto.randomUUID()}}]}}};
}
export function validateOriginalNote(attempt:OriginalNoteAttempt,document:DocumentDto):void {
  const node=attempt.body.editor_json.content![0];
  const block=document.blocks?.[0];
  if(document.document_id!==attempt.id||document.version!==1||document.title!==attempt.body.title
    ||document.source_id!==null||document.source_revision!==null||document.text_projection!==""
    ||!/^[a-f0-9]{64}$/.test(document.content_sha256)||canonical(document.editor_json)!==canonical(attempt.body.editor_json)
    ||document.blocks?.length!==1||block.block_id!==node.attrs!.block_id||block.ordinal!==0
    ||block.kind!=="paragraph"||block.text_projection!==""||canonical(block.node_json)!==canonical(node)) {
    throw new Error("笔记创建身份或完整正文读回不一致；冻结请求仍保留。");
  }
}
export async function confirmOriginalNote(attempt:OriginalNoteAttempt,readOnly=false):Promise<DocumentDto> {
  let ack:DocumentDto|undefined;
  if(!readOnly) {
    try { ack=await coreCommand<DocumentDto>("document_create",{body:structuredClone(attempt.body)}); }
    catch(error) {
      if(error instanceof ApiError&&[400,401,403,422].includes(error.status))throw new OriginalNoteRefused("本地核心明确拒绝了笔记创建；没有确认的创建结果。");
      throw error;
    }
    validateOriginalNote(attempt,ack);
  }
  const saved=await coreCommand<DocumentDto>("document_version",{document_id:attempt.id,version:1});
  validateOriginalNote(attempt,saved);
  if(ack&&ack.content_sha256!==saved.content_sha256)throw new Error("笔记创建回执与读回指纹不一致；冻结请求仍保留。");
  return saved;
}
