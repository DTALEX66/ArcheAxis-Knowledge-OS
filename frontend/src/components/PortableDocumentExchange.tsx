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
  const fail=(error:unknown)=>setMessage(error instanceof Error?error.message:"结果未知；保留同一请求重试。");
  async function choose(file:File|undefined) {
    if(!file||flight.current||pending)return;
    flight.current=true;setBusy(true);
    setSelected(null);setMessage("");
    try {if(file.size>16*1024*1024)throw new Error("包超过 16 MiB 文本上限。");
      const value=assertCoreDto<DocumentPackageDto>("DocumentPackageDto",JSON.parse(await file.text()));
      const bytes=value.objects.reduce((total,object)=>total+object.bytes.length,0);
      if(bytes>2*1024*1024)throw new Error("媒体和原件总字节超过 2 MiB 上限。");
      if(alive.current){setSelected(value);setMessage("已读取所选包；尚未保存。Core 将核验全部字节及结构，失败不注册部分文档。");}
    }catch(error){if(alive.current)fail(error);}finally{flight.current=false;if(alive.current)setBusy(false);}
  }
  async function exportPackage() {
    if(!saved||flight.current)return;flight.current=true;setBusy(true);
    try {const value=await coreCommand<DocumentPackageDto>("document_package_export",{document_id:saved.document_id});
      if(!sameValue(value.document,saved))throw new Error("文档版本变化，请重新读取后导出。");
      if(!alive.current||!sameValue(currentSaved.current,saved))return;
      downloadBytes(JSON.stringify(value),`${saved.document_id}-v${saved.version}.aak-document.json`,"application/json");
      setMessage("已请求下载文档包；磁盘落地未读回。包含绑定原件及表达媒体字节，历史锚点保留为元数据。");
    }catch(error){if(alive.current)fail(error);}finally{flight.current=false;if(alive.current)setBusy(false);}
  }
  async function importPackage() {
    if(flight.current||(!pending&&!selected))return;flight.current=true;setBusy(true);
    try {
      // Same selected bytes remain the same request after a component restart.
      const digest=pending?"":Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(JSON.stringify(selected))))).map(v=>v.toString(16).padStart(2,"0")).join("");
      const request=pending??{request_id:`package_${digest}`,package:selected!};if(!alive.current)return;setPending(request);
      const receipt=await coreCommand<DocumentPackageImportDto>("document_package_import",request);
      const read=await coreCommand<DocumentDto>("document_version",{document_id:receipt.document.document_id,version:receipt.document.version});
      if(!sameValue(read,receipt.document))throw new Error("保存读回未一致确认；保留同请求重试，不创建新文档。");
      if(!alive.current)return;
      setPending(null);setSelected(null);setMessage(`已保存新普通文档 ${read.document_id}；知识入库未执行，历史锚点未重新注册。`);onImported?.(read.document_id);
    }catch(error){if(alive.current)fail(error);}finally{flight.current=false;if(alive.current)setBusy(false);}
  }
  return <section aria-label="有界文档便携包"><h3>有界文档便携包</h3>
    <p>保全已保存结构和未知节点、绑定原件及表达媒体 CAS 字节。总原字节上限 2 MiB；不是全工作区恢复或授权迁移。</p>
    <button disabled={!saved||busy||!!pending} onClick={()=>void exportPackage()}>下载文档与媒体便携包</button>
    <label>选择本地文档包<input type="file" accept=".json,application/json" disabled={busy||!!pending} onChange={event=>void choose(event.target.files?.[0])}/></label>
    {selected?<p>待保存：{selected.document.title}；{selected.objects.length} 个绑定原件／媒体。模型核验不是保存前置。</p>:null}
    <button disabled={busy||(!selected&&!pending)} onClick={()=>void importPackage()}>{pending?"同请求核对并重试回导":"确认保存为新普通文档"}</button>
    {message?<p role="status">{message}</p>:null}
  </section>;
}
