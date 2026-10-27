import { failureMessage } from "../presentation/labels";
import { RawReceiptButton } from "./DiagnosticConsole";
import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { assertCoreDto, type DocumentDto, type DocumentPackageDto, type DocumentPackageImportDto } from "../api/generated/core-contract";
import { downloadBytes, sameValue } from "../presentation/exchangeProof";

/** File selection grants only a new ordinary document; never knowledge approval. */
export function PortableDocumentExchange({ saved, onImported }: { saved: DocumentDto|null; onImported?: (id:string)=>void }) {
  const [selected,setSelected]=useState<DocumentPackageDto|null>(null);
  const [pending,setPending]=useState<{request_id:string;package:DocumentPackageDto}|null>(null);
  const [message,setMessage]=useState(""); const [busy,setBusy]=useState(false); const flight=useRef(false);
  const alive=useRef(true); const currentSaved=useRef(saved);currentSaved.current=saved;
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  const [failure,setFailure]=useState<unknown>(null);
  const fail=(error:unknown)=>{setFailure(error instanceof Error?{name:error.name,message:error.message}:error);setMessage(error instanceof Error?failureMessage(error):"结果未知；保留同一请求重试。");};
  async function choose(file:File|undefined) {
    if(!file||flight.current||pending)return;
    flight.current=true;setBusy(true);setFailure(null);
    setSelected(null);setMessage("");
    try {if(file.size>40*1024*1024)throw new Error("包超过 40 MiB 文本上限。");
      const value=assertCoreDto<DocumentPackageDto>("DocumentPackageDto",JSON.parse(await file.text()));
      const bytes=value.objects.reduce((total,object)=>total+object.bytes.length,0);
      if(bytes>8*1024*1024)throw new Error("媒体和原件总字节超过 8 MiB 上限。");
      if(alive.current){setSelected(value);setMessage("已读取所选包；尚未保存。保存前会检查内容完整性；检查失败不会创建部分文档。");}
    }catch(error){if(alive.current)fail(error);}finally{flight.current=false;if(alive.current)setBusy(false);}
  }
  async function exportPackage() {
    if(!saved||flight.current)return;flight.current=true;setBusy(true);setFailure(null);
    try {const value=await coreCommand<DocumentPackageDto>("document_package_export",{document_id:saved.document_id});
      if(!sameValue(value.document,saved))throw new Error("文档版本变化，请重新读取后导出。");
      if(!alive.current||!sameValue(currentSaved.current,saved))return;
      downloadBytes(JSON.stringify(value),`${saved.document_id}-v${saved.version}.aak-document.json`,"application/json");
      setMessage("已请求下载文档包；请在下载位置确认文件。包含绑定原件及表达媒体字节，历史引用位置会保留在详细信息中。");
    }catch(error){if(alive.current)fail(error);}finally{flight.current=false;if(alive.current)setBusy(false);}
  }
  async function importPackage() {
    if(flight.current||(!pending&&!selected))return;flight.current=true;setBusy(true);setFailure(null);
    try {
      // Same selected bytes remain the same request after a component restart.
      const digest=pending?"":Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(JSON.stringify(selected))))).map(v=>v.toString(16).padStart(2,"0")).join("");
      const request=pending??{request_id:`package_${digest}`,package:selected!};if(!alive.current)return;setPending(request);
      const receipt=await coreCommand<DocumentPackageImportDto>("document_package_import",request);
      const read=await coreCommand<DocumentDto>("document_version",{document_id:receipt.document.document_id,version:receipt.document.version});
      if(!sameValue(read,receipt.document))throw new Error("保存结果尚未确认；请重试同一次导入，不会另建文档。");
      if(!alive.current)return;
      setPending(null);setSelected(null);setMessage("已保存为新文档；尚未加入知识库，旧引用位置需要重新核对。");onImported?.(read.document_id);
    }catch(error){if(alive.current)fail(error);}finally{flight.current=false;if(alive.current)setBusy(false);}
  }
  return <section aria-label="文档与附件导入导出"><h3>文档与附件导入导出</h3>
    <p>文档包包含已保存的内容、绑定的原件和媒体文件。原文件总量上限为 8 MiB，JSON 包上限为 40 MiB；它只能恢复这份文档，不能恢复整个工作区。</p>
    <button disabled={!saved||busy||!!pending} onClick={()=>void exportPackage()}>下载文档与媒体便携包</button>
    <label>选择本地文档包<input type="file" accept=".json,application/json" disabled={busy||!!pending} onChange={event=>void choose(event.target.files?.[0])}/></label>
    {selected?<p>待保存：{selected.document.title}；{selected.objects.length} 个绑定原件／媒体。模型核验不是保存前置。</p>:null}
    <button disabled={busy||(!selected&&!pending)} onClick={()=>void importPackage()}>{pending?"检查结果并重试同一次导入":"确认保存为新普通文档"}</button>
    {message?<p role="status">{message}</p>:null}{failure!==null?<RawReceiptButton label="文档便携包错误详细信息" payload={failure}/>:null}
  </section>;
}
