import {coreCommand} from "../api/core";
import type {AnchorDto,AnchorResolutionDto} from "../api/generated/core-contract";
import {pinnedSuccess,verifiedJobOutput} from "./jobContentExecution";
import {utf8Sha256} from "../components/TranscriptionCues";

export type OcrBox={x:number;y:number;w:number;h:number};
export type OcrReference={quote:string;boxes:OcrBox[]};
function object(value:unknown):Record<string,unknown>{
  if(!value||typeof value!=="object"||Array.isArray(value))throw new Error("引用记录结构无效");
  return value as Record<string,unknown>;
}
export function isOcrAnchor(anchor:AnchorDto):boolean{
  try{return object(JSON.parse(anchor.position)).type==="ocr_line";}catch{return false;}
}

/** Read the pinned successful attempt. Never substitute the latest OCR result. */
export async function readOcrReference(sourceId:string,revision:string,anchor:AnchorDto,isCurrent:()=>boolean=()=>true):Promise<OcrReference>{
  if(!isCurrent())throw new Error("引用选择已变化");
  if(anchor.source_id!==sourceId||anchor.source_revision!==revision)throw new Error("引用属于另一来源版本");
  const resolved=await coreCommand<AnchorResolutionDto>("anchor_resolve",{source_id:sourceId,anchor_id:anchor.anchor_id});
  if(!isCurrent())throw new Error("引用选择已变化");
  if(resolved.source_id!==sourceId||resolved.anchor_id!==anchor.anchor_id||resolved.source_revision!==revision
    ||resolved.current_source_revision!==revision||resolved.scope!=="locator_provenance_only"||resolved.status!=="CURRENT"||resolved.position!==anchor.position)throw new Error("引用定位未通过当前核验");
  const p=object(JSON.parse(resolved.position));
  if(p.type!=="ocr_line"||typeof p.job_id!=="string"||!Number.isSafeInteger(p.attempt)||Number(p.attempt)<1
    ||!Number.isSafeInteger(p.char_start)||!Number.isSafeInteger(p.char_end)||Number(p.char_start)<0||Number(p.char_end)<=Number(p.char_start)
    ||!Array.isArray(p.path)||!p.path.length||typeof p.kind!=="string"||typeof p.checksum!=="string"||p.checksum!==anchor.checksum)throw new Error("识别引用缺少固定位置");
  const job=p.job_id;
  const [state,textRaw,structureRaw,lossRaw]=await Promise.all([
    coreCommand<Record<string,unknown>>("jobs_get",{job_id:job}),
    coreCommand("job_output",{job_id:job,kind:"text"}),
    coreCommand("job_output",{job_id:job,kind:"document_structure"}),
    coreCommand("job_output",{job_id:job,kind:"loss_report"}),
  ]);
  pinnedSuccess(state,job,sourceId);
  const [text,structure,loss]=await Promise.all([verifiedJobOutput(textRaw,"text"),verifiedJobOutput(structureRaw,"document_structure"),verifiedJobOutput(lossRaw,"loss_report")]);
  if(!isCurrent())throw new Error("引用选择已变化");
  if(state.attempt!==p.attempt||structure.metadata.sha256!==p.result_sha256||loss.metadata.sha256!==p.loss_sha256)throw new Error("识别任务或回执版本变化");
  const nodes:unknown=JSON.parse(structure.content),params=object(object(JSON.parse(loss.content)).params);
  if(params.input_sha256!==revision||!Array.isArray(nodes))throw new Error("识别回执未绑定此原件");
  if(!nodes.some(value=>{
    const n=object(value);
    return n.kind===p.kind&&JSON.stringify(n.path)===JSON.stringify(p.path)&&n.char_start===p.char_start&&n.char_end===p.char_end;
  }))throw new Error("固定结构位置未找到");
  const chars=Array.from(text.content),start=Number(p.char_start),end=Number(p.char_end);
  if(end>chars.length)throw new Error("引用文字范围无效");
  const quote=chars.slice(start,end).join("");
  if(!quote.trim()||await utf8Sha256(quote)!==p.checksum)throw new Error("识别引文指纹不一致");
  const boxes:OcrBox[]=[];
  if(params.regions!==undefined&&!Array.isArray(params.regions))throw new Error("原图区域记录无效");
  for(const value of (params.regions??[]) as unknown[]){
    const r=object(value);
    if(!Number.isSafeInteger(r.char_start)||!Number.isSafeInteger(r.char_end))throw new Error("区域文字范围无效");
    const a=Number(r.char_start),b=Number(r.char_end);
    if(b<=start||a>=end)continue;
    if(a<start||b>end||b<=a||typeof r.text!=="string"||chars.slice(a,b).join("")!==r.text)throw new Error("区域与固定引文不一致");
    const box=object(r.bbox);
    if(![box.x,box.y,box.w,box.h].every(n=>typeof n==="number"&&Number.isFinite(n))
      ||Number(box.x)<0||Number(box.y)<0||Number(box.w)<=0||Number(box.h)<=0)throw new Error("原图坐标无效");
    boxes.push({x:Number(box.x),y:Number(box.y),w:Number(box.w),h:Number(box.h)});
  }
  if(!isCurrent())throw new Error("引用选择已变化");
  const after=await coreCommand<AnchorResolutionDto>("anchor_resolve",{source_id:sourceId,anchor_id:anchor.anchor_id});
  if(!isCurrent()||after.source_id!==sourceId||after.anchor_id!==anchor.anchor_id||after.source_revision!==revision
    ||after.current_source_revision!==revision||after.scope!=="locator_provenance_only"||after.status!=="CURRENT"||after.position!==anchor.position)throw new Error("读取期间引用定位发生变化");
  return {quote,boxes};
}

export function ocrBounds(boxes:OcrBox[],width:number,height:number):OcrBox|null{
  if(!boxes.length)return null;
  if(width<=0||height<=0||boxes.some(b=>b.x+b.w>width||b.y+b.h>height))throw new Error("识别坐标超出当前原图");
  const area=boxes.reduce((a,b)=>({left:Math.min(a.left,b.x),top:Math.min(a.top,b.y),right:Math.max(a.right,b.x+b.w),bottom:Math.max(a.bottom,b.y+b.h)}),{left:width,top:height,right:0,bottom:0});
  return {x:area.left,y:area.top,w:area.right-area.left,h:area.bottom-area.top};
}
