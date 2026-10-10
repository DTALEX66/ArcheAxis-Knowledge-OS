import { webcrypto } from "node:crypto";
import { Blob as NodeBlob } from "node:buffer";
import { describe,it,expect,vi,beforeEach,afterEach } from "vitest";
import { verifiedOriginal,verifiedExport,sha256,downloadBytes } from "../presentation/exchangeProof";
import { assertCoreDto,type DocumentDto,type DocumentExportDto } from "../api/generated/core-contract";
beforeEach(()=>vi.stubGlobal("crypto",webcrypto));
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});
const bytes=new TextEncoder().encode("原字节\n");
async function original(){const sha=await sha256(bytes);const source={source_id:"source-1",source_revision:"rev-1",sha256:sha,original_name:"notes.txt",imported_at:"now"};return {source,asset:{source_id:source.source_id,name:source.original_name,media_type:"text/plain",sha256:sha,content_base64:Buffer.from(bytes).toString("base64")}};}
async function exported(){
 const saved:DocumentDto={document_id:"doc-1",version:2,title:"笔记",source_id:null,source_revision:null,content_sha256:"a".repeat(64),editor_json:{type:"doc",attrs:{unknown_legacy:{original:[1,"原文"]}},content:[]},text_projection:"正文",blocks:[]};
 const hash=await sha256(new TextEncoder().encode(saved.text_projection));
 const manifest={schema:"archeaxis-document-export-1",document:saved,anchors:[],loss:[{code:"projection",message:"参考媒体"}],projection_sha256:hash};
 const proof:DocumentExportDto={document_id:saved.document_id,version:saved.version,format:"markdown",source_revision:null,projection_sha256:hash,files:[{path:"document.md",media_type:"text/markdown",content:"正文\n\n## Source identity\n\n    {}"},{path:"manifest.json",media_type:"application/json",content:JSON.stringify(manifest,null,2)}]};return {saved,proof};
}
describe("exchange canonical proofs (SIMULATED DTO)",()=>{
 it("validates original bytes, never a converted substitute",async()=>{const {source,asset}=await original();expect(Array.from(await verifiedOriginal(source,asset))).toEqual(Array.from(bytes));});
 it.each(["identity","sha","bytes"])("refuses mismatched original %s",async kind=>{const {source,asset}=await original();if(kind==="identity")asset.source_id="other";if(kind==="sha")asset.sha256="b".repeat(64);if(kind==="bytes")asset.content_base64=Buffer.from("wrong").toString("base64");await expect(verifiedOriginal(source,asset)).rejects.toThrow();});
 it("allows canonical no-source export null and retains exact manifest bytes",async()=>{const {saved,proof}=await exported();expect(assertCoreDto("DocumentExportDto",proof)).toEqual(proof);expect(await verifiedExport(saved,proof,"markdown")).toBe(proof);});
 it.each(["version","unknown","hash","markdown","missing"])("refuses export %s mismatch",async kind=>{const {saved,proof}=await exported();if(kind==="version")proof.version++;if(kind==="unknown"){const m=JSON.parse(proof.files[1].content);delete m.document.editor_json.attrs;proof.files[1].content=JSON.stringify(m);}if(kind==="hash")proof.projection_sha256="b".repeat(64);if(kind==="markdown")proof.files[0].content="伪正文";if(kind==="missing")proof.files.pop();await expect(verifiedExport(saved,proof,"markdown")).rejects.toThrow();});
 it("browser download preserves original raw bytes and exact unnormalized manifest text",async()=>{let captured!:NodeBlob;const create=vi.fn((blob:NodeBlob)=>{captured=blob;return "blob:owned-fixture";});vi.stubGlobal("Blob",NodeBlob);vi.stubGlobal("URL",{createObjectURL:create,revokeObjectURL:vi.fn()});vi.spyOn(HTMLAnchorElement.prototype,"click").mockImplementation(()=>{});downloadBytes(bytes,"../原件.txt","text/plain");expect(Array.from(new Uint8Array(await captured.arrayBuffer()))).toEqual(Array.from(bytes));const raw='{\n "legacy": {"number":1.0, "unknown":[null,"未改写"]}\n}';downloadBytes(raw,"manifest.json","application/json");expect(await captured.text()).toBe(raw);expect(create).toHaveBeenCalledTimes(2);await new Promise(resolve=>setTimeout(resolve,5));});
 it("rejects malformed export union with canonical single-schema validator",async()=>{const {proof}=await exported();expect(()=>assertCoreDto("DocumentExportDto",{...proof,source_revision:42})).toThrow();});
});
