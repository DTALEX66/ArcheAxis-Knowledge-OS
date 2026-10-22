import {useEffect,useRef,useState} from "react";
import type {AnchorDto,OriginalDto} from "../api/generated/core-contract";
import {isOcrAnchor,ocrBounds,readOcrReference,type OcrReference,type OcrBox} from "../presentation/ocrReference";
import {focusVisibleTarget} from "../presentation/focus";
import "./ocr-image-reader.css";

export type OcrImageSeek={sourceId:string;revision:string;anchorId:string;position:string;sequence:number};
export function OcrImageReader({sourceId,revision,name,original,anchors,seek}:{sourceId:string;revision:string;name:string;original:OriginalDto;anchors:AnchorDto[];seek?:OcrImageSeek}){
  const epoch=useRef(0),figure=useRef<HTMLElement>(null),marker=useRef<SVGRectElement>(null);
  const pending=useRef(false),focusOwner=useRef<Element|null>(null);
  const [size,setSize]=useState<{width:number;height:number}|null>(null),[selected,setSelected]=useState<OcrReference|null>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  const identity=JSON.stringify([sourceId,revision,original.sha256]);
  const rows=anchors.filter(a=>a.source_id===sourceId&&a.source_revision===revision&&isOcrAnchor(a));
  useEffect(()=>{epoch.current++;pending.current=false;focusOwner.current=null;setSelected(null);setSize(null);setError("");setBusy(false);return()=>{epoch.current++;};},[identity]);
  async function locate(anchor:AnchorDto){
    const current=++epoch.current,owner=document.activeElement;pending.current=true;focusOwner.current=null;setBusy(true);setSelected(null);setError("");
    try{
      const value=await readOcrReference(sourceId,revision,anchor,()=>current===epoch.current);
      if(current!==epoch.current)return;
      if(document.activeElement===owner)focusOwner.current=owner;
      setSelected(value);
    }catch(e){if(current===epoch.current)setError(e instanceof Error?e.message:"识别引用读取未完成");}
    finally{if(current===epoch.current){pending.current=false;setBusy(false);}}
  }
  useEffect(()=>{
    if(!seek||seek.sourceId!==sourceId||seek.revision!==revision)return;
    const anchor=rows.find(a=>a.anchor_id===seek.anchorId&&a.position===seek.position);
    if(anchor)void locate(anchor);else{epoch.current++;pending.current=false;focusOwner.current=null;setSelected(null);setBusy(false);setError("未找到此版本的识别引用，未替换为其他位置。");}
  },[identity,seek]);
  let bounds:OcrBox|null=null,boundsError="";
  try{if(selected&&size)bounds=ocrBounds(selected.boxes,size.width,size.height);}catch(e){boundsError=e instanceof Error?e.message:"识别坐标无效";}
  useEffect(()=>{
    if(!selected||!size||boundsError||!focusOwner.current)return;
    const owner=focusOwner.current;focusOwner.current=null;
    if(document.activeElement!==owner)return;
    focusVisibleTarget(figure.current,null);
    // Wait for the overlay to exist, then reveal the cited area instead of the
    // centre of a potentially much taller original image.
    if(document.activeElement===figure.current)(marker.current??figure.current)?.scrollIntoView?.({block:"center",inline:"nearest"});
  },[selected,size,boundsError]);
  if(original.source_id!==sourceId||original.sha256!==revision)return <p role="alert">原图身份未核对，未显示其他来源。</p>;
  return <section className="ocr-image-reader" aria-label="原图与识别位置">
    <figure ref={figure} tabIndex={0} aria-label="识别位置原图">
      <div className="ocr-image-frame">
        <img className="original-derived-image" src={`data:${original.media_type};base64,${original.content_base64}`} alt={`原件 ${name}`} onLoad={e=>setSize({width:e.currentTarget.naturalWidth,height:e.currentTarget.naturalHeight})} onError={()=>{setSize(null);setError("此浏览器无法显示原图；原件与引用仍保留。");}}/>
        {bounds&&size?<svg aria-label="已核对识别区域" viewBox={`0 0 ${size.width} ${size.height}`} preserveAspectRatio="none"><rect ref={marker} x={bounds.x} y={bounds.y} width={bounds.w} height={bounds.h}/></svg>:null}
      </div>
    </figure>
    {rows.length?<div role="group" aria-label="已保存识别引用">{rows.map((a,i)=><button type="button" key={a.anchor_id} disabled={a.location_status==="revision_mismatch"} aria-disabled={busy||undefined} onClick={()=>{if(!pending.current)void locate(a);}}>查看第 {i+1} 条识别引用</button>)}</div>:null}
    {busy?<p role="status">正在核对引用与原识别结果…</p>:null}
    {error||boundsError?<p role="alert">识别位置未显示：{error||boundsError}。保留原件，未自动迁移引用。</p>:null}
    {selected&&!error&&!boundsError?<><pre tabIndex={0} aria-label="定位识别原文">{selected.quote}</pre><p role="status">{bounds?"已核对原识别文字与原图区域；高亮来自引擎记录，不代表文字正确。":!size?"原图尚未显示，暂不绘制区域。":"此引用未提供原图区域，仅显示已核对的识别文字。"}</p></>:null}
  </section>;
}
