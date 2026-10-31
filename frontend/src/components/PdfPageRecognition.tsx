import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "./DiagnosticConsole";
import { JobContent } from "./JobContent";
import type {AnchorDto,OriginalDto} from "../api/generated/core-contract";
import {sha256} from "../presentation/exchangeProof";
import {OcrImageReader} from "./OcrImageReader";

type Page = {
  page: number | null;
  source_id: string;
  origin_ref: string;
  original_name: string;
  sha256: string;
  recognised: boolean;
  text: string | null;
  job_id: string | null;
};
type Pages = {
  pdf_source_id: string;
  page_count: number;
  recognised_count: number;
  pages: Page[];
  note: string;
};

function pagesShape(value: unknown, sourceId: string): Pages {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid pages");
  const item = value as Record<string, unknown>;
  if (item.pdf_source_id !== sourceId || typeof item.note !== "string" || !Array.isArray(item.pages)) {
    throw new Error("invalid pages");
  }
  if (![item.page_count, item.recognised_count].every((count) => Number.isSafeInteger(count) && Number(count) >= 0)
    || item.page_count !== item.pages.length || Number(item.recognised_count) > Number(item.page_count)) {
    throw new Error("invalid pages");
  }
  for (const entry of item.pages) {
    const page = entry as Record<string, unknown>;
    if (typeof page.source_id !== "string" || !page.source_id || typeof page.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(page.sha256)
      || typeof page.recognised !== "boolean" || typeof page.origin_ref !== "string"
      || typeof page.original_name !== "string"
      || !(page.page === null || (Number.isSafeInteger(page.page) && Number(page.page) > 0))
      || !(page.text === null || typeof page.text === "string")
      || !(page.job_id === null || typeof page.job_id === "string")) {
      throw new Error("invalid pages");
    }
  }
  if (new Set(item.pages.map(page => (page as Page).source_id)).size !== item.pages.length
    || item.pages.filter(page => (page as Page).recognised).length !== item.recognised_count) throw new Error("invalid pages identity");
  return item as unknown as Pages;
}

export function PdfPageRecognition({ sourceId,onPageSelect,currentPage }: { sourceId: string;currentPage?:number;onPageSelect?:(page:number)=>void }) {
  const [pages, setPages] = useState<Pages | null>(null);
  const [open, setOpen] = useState<Page | null>(null);
  const [recognitionOpen, setRecognitionOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const epoch=useRef(0),refreshing=useRef<number|null>(null);
  const [image,setImage]=useState<{original:OriginalDto;anchors:AnchorDto[]}|null>(null);
  const [imageBusy,setImageBusy]=useState(false),[imageError,setImageError]=useState("");
  useEffect(()=>{epoch.current++;refreshing.current=null;setPages(null);setOpen(null);setImage(null);setImageError("");setImageBusy(false);setRecognitionOpen(false);setMessage("");setBusy(false);return()=>{epoch.current++;};},[sourceId]);

  async function run(action: () => Promise<void>) {
    if (refreshing.current!==null) return;
    const current=++epoch.current;refreshing.current=current;setImageBusy(false);
    setBusy(true);
    try {
      await action();
    } catch {
      // A refusal replaces the sentence only: whatever was really read stays on screen.
    } finally {
      if(refreshing.current===current){refreshing.current=null;setBusy(false);}
    }
  }

  async function refresh() {
    await run(async () => {
      const current=epoch.current;
      try {
        const read = pagesShape(await coreCommand<unknown>("source_pages", { source_id: sourceId }), sourceId);
        if(current!==epoch.current)return;
        setPages(read);
        setOpen(null);setImage(null);setImageError("");setRecognitionOpen(false);
        setMessage(read.page_count
          ? `已读取 ${read.page_count} 个页面，其中 ${read.recognised_count} 页有识别文本。`
          : "此来源没有被渲染过的页面：它的文字层本就可读，或从未走过 OCR 链。");
      } catch (error) {
        if(current!==epoch.current)return;
        // A failed read never replaces what was really read before it: the list on screen is
        // the last one Core actually answered for.
        setMessage(String(error).includes("找不到")
          ? "本地核心找不到此来源，未显示任何页面。"
          : "页面识别回写读取失败；未替换已有内容。");
      }
    });
  }

  useEffect(()=>{
    if(!open||currentPage===undefined||open.page===currentPage)return;
    const target=pages?.pages.find(p=>p.page===currentPage);
    if(target)openPage(target,false);
    else{epoch.current++;setOpen(null);setImage(null);setImageError("");setImageBusy(false);setRecognitionOpen(false);setMessage("当前 PDF 页没有已读取的页图记录；未沿用其他页的识别结果。");}
  },[currentPage]);

  function openPage(page: Page,notify=true) {
    epoch.current++;setImage(null);setImageError("");setImageBusy(false);
    setRecognitionOpen(false);
    if(notify&&page.page!==null)onPageSelect?.(page.page);
    setOpen(page);
    if (!page.recognised) {
      setMessage(`第 ${page.page ?? "？"} 页没有识别文本：OCR 路由未对该页产出内容，原件仍在保管中。`);
    } else {
      setMessage(`第 ${page.page ?? "？"} 页显示的是该页自己的识别结果。`);
    }
  }

  async function openImage(){
    if(!open||imageBusy||refreshing.current!==null)return;
    const current=++epoch.current,target=open;setImageBusy(true);setImage(null);setImageError("");
    try{
      const original=await coreCommand<OriginalDto>("source_original",{source_id:target.source_id});
      if(current!==epoch.current)return;
      if(original.source_id!==target.source_id||original.sha256!==target.sha256||!original.media_type.startsWith("image/")||typeof original.content_base64!=="string")throw new Error("页面原件身份不符");
      const bytes=Uint8Array.from(atob(original.content_base64),c=>c.charCodeAt(0));
      if(await sha256(bytes)!==target.sha256)throw new Error("页面原件字节不符");
      if(current!==epoch.current)return;
      const result=await coreCommand<{anchors:AnchorDto[]}>("anchors_list",{source_id:target.source_id});
      if(current!==epoch.current)return;
      if(!Array.isArray(result.anchors)||result.anchors.some(a=>!a||a.source_id!==target.source_id||a.source_revision!==target.sha256||typeof a.anchor_id!=="string"||typeof a.position!=="string"))throw new Error("页面引用身份不符");
      setImage({original,anchors:result.anchors});
    }catch{if(current===epoch.current)setImageError("此页原图与引用未核对；保留 PDF 和识别记录，未替换为其他页面。");}
    finally{if(current===epoch.current)setImageBusy(false);}
  }

  return (
    <section aria-label="PDF 页面识别回写">
      <h4>PDF 页面识别回写</h4>
      <button disabled={busy} onClick={() => void refresh()}>读取页面与识别文本</button>
      {message ? <p role="status">{message}</p> : null}
      {pages ? (
        <>
          <p>页面 {pages.page_count} · 已识别 {pages.recognised_count} · 未识别 {pages.page_count - pages.recognised_count}</p>
          <p>{pages.note}</p>
          {pages.pages.length ? (
            <ul>
              {pages.pages.map((page) => (
                <li key={`${page.origin_ref}:${page.source_id}`}>
                  <button disabled={busy} onClick={() => openPage(page)}>
                    第 {page.page ?? "？"} 页 · {page.original_name}
                  </button>
                  <span>{page.recognised ? " 已识别" : " 未识别（无文本）"}</span>
                  {!page.job_id ? <span> · 无作业</span> : null}
                  <RawReceiptButton
                    label="页面摘要与来源关系"
                    payload={{ sha256: page.sha256, origin_ref: page.origin_ref, source_id: page.source_id, job_id: page.job_id }}
                  />
                </li>
              ))}
            </ul>
          ) : null}
        </>
      ) : null}
      {open?.text ? (
        <>
          <label htmlFor="page-recognition">第 {open.page ?? "？"} 页的识别文本（引擎所读，非正确性判定）</label>
          <textarea id="page-recognition" readOnly rows={8} value={open.text} />
        </>
      ) : null}
      {open ? <div>
        <p>识别使用此页的本地图片原件；结果与 PDF 文字层分开保存。完成后点击“读取页面与识别文本”核对回写。</p>
        <button type="button" disabled={busy||imageBusy} onClick={()=>void openImage()}>查看此页原图与引用</button>
        {imageBusy?<p role="status">正在核对此页原图与引用…</p>:null}
        {imageError?<p role="alert">{imageError}</p>:null}
        {image?<OcrImageReader key={`${open.source_id}:${open.sha256}`} sourceId={open.source_id} revision={open.sha256} name={open.original_name} original={image.original} anchors={image.anchors}/>:null}
        <button onClick={() => setRecognitionOpen(true)}>处理此页识别文本</button>
        {recognitionOpen ? <JobContent key={`${open.source_id}:${open.sha256}`} sourceId={open.source_id} sourceRevision={open.sha256} name={open.original_name} pinnedJobId={open.job_id??undefined} onAnchor={anchor=>{if(image&&anchor.source_id===open.source_id&&anchor.source_revision===open.sha256)setImage({...image,anchors:[...image.anchors.filter(a=>a.anchor_id!==anchor.anchor_id),anchor]});}} /> : null}
      </div> : null}
    </section>
  );
}
