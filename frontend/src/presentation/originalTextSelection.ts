export function textareaOriginalRange(text:string,start:number,end:number){
 const boundaries=[0];
 for(let index=0;index<text.length;index++){
  if(text[index]==="\r"&&text[index+1]==="\n")index++;
  boundaries.push(index+1);
 }
 if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||end<=start||end>=boundaries.length)throw new Error("invalid displayed selection");
 return {start:boundaries[start],end:boundaries[end]};
}

export function originalTextSelection(bytes:Uint8Array,start:number,end:number){
 const text=new TextDecoder("utf-8",{fatal:true,ignoreBOM:true}).decode(bytes);
 const encoded=new TextEncoder().encode(text);
 if(encoded.length!==bytes.length||encoded.some((byte,index)=>byte!==bytes[index]))throw new Error("original encoding mismatch");
 if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||end<=start||end>text.length)throw new Error("invalid selection");
 const splits=(at:number)=>at>0&&at<text.length&&/[\uD800-\uDBFF]/.test(text[at-1])&&/[\uDC00-\uDFFF]/.test(text[at]);
 if(splits(start)||splits(end))throw new Error("split Unicode character");
 const begin=new TextEncoder().encode(text.slice(0,start)).length,finish=new TextEncoder().encode(text.slice(0,end)).length;
 return {text,quote:text.slice(start,end),start:begin,end:finish,bytes:bytes.slice(begin,finish)};
}
