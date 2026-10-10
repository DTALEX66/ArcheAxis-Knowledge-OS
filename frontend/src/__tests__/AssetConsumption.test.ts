import { beforeEach,afterEach,it,expect,vi } from "vitest";
import { webcrypto } from "node:crypto";
import { readAssetConsumption } from "../presentation/assetConsumption";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const pin={document_id:"asset_grant",version:1,content_sha256:"a".repeat(64)};
const assetPin={document_id:"asset",version:2,content_sha256:"b".repeat(64)};
const asset={schema:"archeaxis.ai-asset/v1",kind:"knowledge_package",content:{inert:"no execution"},purpose:"",scope:[],provenance:[],state:"adopted",members:[],conflicts:[]};
const grant={schema:"archeaxis.asset-context-grant/v1",asset:assetPin,purpose:"固定用途",consumer:"local-machine",operations:["answer","retest"],authorization_basis:"本人决定",state:"granted"};
const doc=(p:typeof pin,namespace:string,v:unknown)=>({...p,title:"fixture",source_id:null,source_revision:null,blocks:[],text_projection:"",editor_json:{type:"doc",attrs:{[namespace]:v},content:[]}});
let rows:Record<string,any>;
beforeEach(()=>{vi.stubGlobal("crypto",webcrypto);rows={asset_grant:doc(pin,"archeaxis_asset_context_grant",structuredClone(grant)),asset:doc(assetPin,"archeaxis_ai_asset",structuredClone(asset))};bridge.call.mockReset();bridge.call.mockImplementation(async(_op,p)=>structuredClone(rows[p.document_id]));});
afterEach(()=>vi.unstubAllGlobals());
it("actual current snapshots preserve pins; reference selection alone conveys no inferred knowledge grant",async()=>{const value=await readAssetConsumption(pin,"answer");expect(value.request).toMatchObject({asset:assetPin,grant:pin,purpose:"固定用途",consumer:"local-machine",operation:"answer"});expect(value.current).toBe(true);expect(bridge.call.mock.calls.map(x=>x[1].document_id)).toEqual(["asset_grant","asset"]);});
it.each(["grant_changed","asset_changed","revoked","withdrawn","expired","manual_consumer"])("fails %s without upgrading pins",async kind=>{if(kind==="grant_changed")rows.asset_grant.version=2;else if(kind==="asset_changed")rows.asset.version=3;else if(kind==="revoked")rows.asset_grant.editor_json.attrs.archeaxis_asset_context_grant.state="revoked";else if(kind==="withdrawn")rows.asset.editor_json.attrs.archeaxis_ai_asset.state="withdrawn";else if(kind==="expired")rows.asset_grant.editor_json.attrs.archeaxis_asset_context_grant.expires_at=1;else rows.asset_grant.editor_json.attrs.archeaxis_asset_context_grant.consumer="manual-context-packet";await expect(readAssetConsumption(pin,"answer")).rejects.toThrow();});
it("package member must be current adopted actual asset version",async()=>{const member={document_id:"member",version:1,content_sha256:"c".repeat(64)};rows.asset.editor_json.attrs.archeaxis_ai_asset.members=[member];rows.member=doc(member,"archeaxis_ai_asset",{...asset,kind:"memory",state:"withdrawn"});await expect(readAssetConsumption(pin,"answer")).rejects.toThrow(/成员/);});
it("nested grandchild withdrawal refuses the complete package graph",async()=>{
 const member={document_id:"member",version:1,content_sha256:"c".repeat(64)},child={...member,document_id:"child"};
 rows.asset.editor_json.attrs.archeaxis_ai_asset.members=[member];rows.member=doc(member,"archeaxis_ai_asset",{...asset,members:[child]});rows.child=doc(child,"archeaxis_ai_asset",{...asset,state:"withdrawn"});await expect(readAssetConsumption(pin,"answer")).rejects.toThrow(/成员/);
});
it.each(["root","member"])("unresolved %s conflict refuses consumption",async level=>{
 const member={document_id:"member",version:1,content_sha256:"c".repeat(64)};
 if(level==="root")rows.asset.editor_json.attrs.archeaxis_ai_asset.conflicts=[member];else {rows.asset.editor_json.attrs.archeaxis_ai_asset.members=[member];rows.member=doc(member,"archeaxis_ai_asset",{...asset,conflicts:[assetPin]});}
 await expect(readAssetConsumption(pin,"answer")).rejects.toThrow(/冲突/);
});
it.each(["duplicate","cycle","depth"])("bounded graph rejects %s without implying current qualification",async kind=>{
 const member={document_id:"member",version:1,content_sha256:"c".repeat(64)};rows.asset.editor_json.attrs.archeaxis_ai_asset.members=kind==="duplicate"?[member,member]:[member];rows.member=doc(member,"archeaxis_ai_asset",{...asset,members:kind==="cycle"?[assetPin]:[]});
 if(kind==="depth"){let current=rows.member;for(let n=2;n<=5;n++){const next={...member,document_id:`member${n}`};current.editor_json.attrs.archeaxis_ai_asset.members=[next];rows[next.document_id]=doc(next,"archeaxis_ai_asset",structuredClone(asset));current=rows[next.document_id];}}
 await expect(readAssetConsumption(pin,"answer")).rejects.toThrow(/循环、重复或超出/);
});
