/** Mirrors the canonical Core create_optional_with_request identity contract. */
export async function documentRequestIdentity(requestId:string):Promise<string> {
  if(!/^[A-Za-z0-9_-]{1,128}$/.test(requestId))throw new Error("文档创建请求身份无效。");
  const hash=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(requestId));
  return "doc_req_"+Array.from(new Uint8Array(hash)).map(v=>v.toString(16).padStart(2,"0")).join("");
}
