import {createHash,webcrypto} from "node:crypto";
import {beforeEach,expect,it,vi} from "vitest";
import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {CanonicalLibrarySpace} from "../spaces/CanonicalLibrarySpace";

const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
vi.mock("../components/JobContent",()=>({JobContent:()=>null}));
vi.mock("../components/FolderIngest",()=>({FolderIngest:()=>null}));
vi.mock("../components/ContainerMemberChain",()=>({ContainerMemberChain:()=>null}));
vi.mock("../components/PdfPageRecognition",()=>({PdfPageRecognition:()=> <section aria-label="已接通PDF页面识别"/>}));
vi.mock("../components/BackupPanel",()=>({BackupPanel:()=>null}));
vi.mock("../templates/TemplateWorkspace",()=>({TemplateLauncher:()=>null}));
vi.mock("../components/PdfReader",()=>({PdfReader:({bytes}:{bytes:Uint8Array})=><p>PDF字节 {bytes.length}</p>}));

// The bytes are authored fixtures; this tests verified-byte routing, not image decoding.
const fixtures=[
  {id:"scan-png",name:"scan.png",mime:"image/png",bytes:Buffer.from("authored PNG fixture")},
  {id:"scan-jpeg",name:"scan.jpeg",mime:"image/jpeg",bytes:Buffer.from("authored JPEG fixture")},
  {id:"scan-pdf",name:"scan.pdf",mime:"application/pdf",bytes:Buffer.from("%PDF authored fixture")},
].map(f=>({...f,sha:createHash("sha256").update(f.bytes).digest("hex")}));
const sources=fixtures.map(f=>({source_id:f.id,source_revision:f.sha,sha256:f.sha,original_name:f.name,imported_at:"2026-10-22"}));
const target=(index:number)=>({source_id:fixtures[index].id,source_revision:fixtures[index].sha,sha256:fixtures[index].sha});
beforeEach(()=>{
  vi.stubGlobal("crypto",webcrypto);bridge.call.mockReset();
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>{
    if(op==="sources_list")return {sources};
    if(op==="documents_list")return {documents:[],next_cursor:null,snapshot_count:0};
    if(op==="anchors_list")return {anchors:[]};
    if(op==="source_original"){
      const f=fixtures.find(f=>f.id===p.source_id)!;
      return {source_id:f.id,name:f.name,sha256:f.sha,media_type:f.mime,content_base64:f.bytes.toString("base64")};
    }
    throw new Error(`Unexpected ${op}`);
  });
});

it.each(["reader",undefined] as const)("SYNTHETIC %s: shows the verified scan before creating a Document or executing OCR",async purpose=>{
  render(<CanonicalLibrarySpace purpose={purpose} initialSourceTarget={purpose?target(0):undefined}/>);
  if(!purpose)fireEvent.click(await screen.findByRole("button",{name:"scan.png"}));
  expect(await screen.findByRole("img",{name:"原件 scan.png"})).toHaveAttribute("src",`data:image/png;base64,${fixtures[0].bytes.toString("base64")}`);
  expect(bridge.call.mock.calls.every(([op])=>["sources_list","documents_list","source_original","anchors_list"].includes(op))).toBe(true);
});

it("SYNTHETIC: replaces the preview with the selected source's verified bytes",async()=>{
  const view=render(<CanonicalLibrarySpace purpose="reader" initialSourceTarget={target(0)}/>);
  await screen.findByRole("img",{name:"原件 scan.png"});
  view.rerender(<CanonicalLibrarySpace purpose="reader" initialSourceTarget={target(1)}/>);
  expect(await screen.findByRole("img",{name:"原件 scan.jpeg"})).toHaveAttribute("src",`data:image/jpeg;base64,${fixtures[1].bytes.toString("base64")}`);
  expect(screen.queryByRole("img",{name:"原件 scan.png"})).toBeNull();
});

it("SYNTHETIC: routes an unlinked scanned PDF to the existing reader with its verified bytes",async()=>{
  render(<CanonicalLibrarySpace purpose="reader" initialSourceTarget={target(2)}/>);
  expect(await screen.findByText(`PDF字节 ${fixtures[2].bytes.length}`)).toBeVisible();
  expect(screen.getByRole("region",{name:"已接通PDF页面识别"})).toBeVisible();
});

it("SYNTHETIC: refuses a source whose returned bytes differ from its fingerprint",async()=>{
  const previous=bridge.call.getMockImplementation()!;
  bridge.call.mockImplementation(async(op:string,p:Record<string,unknown>={})=>op==="source_original"?{...await previous(op,p),content_base64:fixtures[1].bytes.toString("base64")}:previous(op,p));
  render(<CanonicalLibrarySpace purpose="reader" initialSourceTarget={target(0)}/>);
  await waitFor(()=>expect(screen.getByRole("alert")).toHaveTextContent("原件字节核验未完成"));
  expect(screen.queryByRole("img")).toBeNull();
});
