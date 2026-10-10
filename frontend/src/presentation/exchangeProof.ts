import type { DocumentDto, DocumentExportDto, OriginalDto, SourceDto } from "../api/generated/core-contract";
export function object(value:unknown):Record<string,unknown> {
  if(!value || typeof value!=="object" || Array.isArray(value))throw new Error("Core 返回对象格式不完整。");
  return value as Record<string,unknown>;
}
export function sameValue(a:unknown,b:unknown):boolean {
  if(a===b)return true;
  if(Array.isArray(a)||Array.isArray(b))return Array.isArray(a)&&Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>sameValue(v,b[i]));
  if(a&&b&&typeof a==="object"&&typeof b==="object") {
    const x=object(a),y=object(b), keys=Object.keys(x);
    return keys.length===Object.keys(y).length&&keys.every(k=>Object.hasOwn(y,k)&&sameValue(x[k],y[k]));
  }
  return false;
}
export async function sha256(bytes:Uint8Array):Promise<string> {
  const owned=new Uint8Array(bytes.length);owned.set(bytes);
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",owned.buffer))).map(v=>v.toString(16).padStart(2,"0")).join("");
}
export async function verifiedOriginal(source:SourceDto,original:OriginalDto):Promise<Uint8Array> {
  if(original.source_id!==source.source_id||original.sha256!==source.sha256||!/^[a-f0-9]{64}$/.test(source.sha256))throw new Error("原件身份或 SHA256 与所选对象不符。");
  if(typeof original.content_base64!=="string"||typeof original.name!=="string"||typeof original.media_type!=="string")throw new Error("原件字段不完整。");
  const bytes=Uint8Array.from(atob(original.content_base64),v=>v.charCodeAt(0));
  if(await sha256(bytes)!==source.sha256)throw new Error("原件字节核验失败；不开放下载或替换为其他文件。");
  return bytes;
}
export function pinnedDocument(value:DocumentDto,id:string):DocumentDto {
  if(value.document_id!==id||!Number.isSafeInteger(value.version)||value.version<1||!/^[a-f0-9]{64}$/.test(value.content_sha256)||typeof value.text_projection!=="string")throw new Error("文档身份或已保存版本无法核对。");
  return value;
}
export async function verifiedExport(saved:DocumentDto,proof:DocumentExportDto,format:"markdown"|"obsidian"):Promise<DocumentExportDto> {
  if(proof.document_id!==saved.document_id||proof.version!==saved.version||proof.format!==format||proof.source_revision!==saved.source_revision)throw new Error("导出范围不是所选已保存版本；请重新读取当前文档。");
  if(!Array.isArray(proof.files)||proof.files.length!==2||proof.files.filter(f=>f.path==="document.md").length!==1||proof.files.filter(f=>f.path==="manifest.json").length!==1)throw new Error("导出两文件不完整。");
  const manifestFile=proof.files.find(f=>f.path==="manifest.json")!,markdown=proof.files.find(f=>f.path==="document.md")!;
  if(manifestFile.media_type!=="application/json"||markdown.media_type!=="text/markdown"||typeof markdown.content!=="string"||typeof manifestFile.content!=="string")throw new Error("导出文件内容或格式不符。");
  const manifest=object(JSON.parse(manifestFile.content));
  if(manifest.schema!=="archeaxis-document-export-1"||!sameValue(manifest.document,saved)||!Array.isArray(manifest.anchors)||!Array.isArray(manifest.loss))throw new Error("导出快照与已保存正文／未知属性不一致。");
  if((manifest.loss as unknown[]).some(v=>{const item=object(v);return typeof item.code!=="string"||typeof item.message!=="string";}))throw new Error("Core 损失说明不完整。");
  const hash=await sha256(new TextEncoder().encode(saved.text_projection));
  if(hash!==proof.projection_sha256||manifest.projection_sha256!==hash)throw new Error("派生正文 SHA256 核验失败。");
  const expectedPrefix=format==="obsidian"?`---\narcheaxis_document: ${JSON.stringify(saved.document_id)}\narcheaxis_version: ${saved.version}\narcheaxis_source_revision: ${JSON.stringify(saved.source_revision)}\n---\n\n`:"";
  if(!markdown.content.startsWith(expectedPrefix+saved.text_projection+"\n\n## Source identity\n"))throw new Error("Markdown 正文与所选投影不一致。");
  return proof; // Preserve actual Core file strings. Never reserialize the manifest.
}
export function downloadBytes(bytes:Uint8Array|string,name:string,mediaType:string):void {
  const payload=typeof bytes==="string"?bytes:new Uint8Array(bytes).buffer;
  const url=URL.createObjectURL(new Blob([payload],{type:mediaType}));
  const link=document.createElement("a");link.href=url;link.download=name.replace(/[\\/\x00-\x1f]/g,"_")||"original";
  try{document.body.appendChild(link);link.click();}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),0);}
}
