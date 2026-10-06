import { useEffect, useRef, useState } from "react";

export function MediaReader({bytes,mediaType,seek}:{bytes:Uint8Array;mediaType:string;seek?:{milliseconds:number;sequence:number}}) {
  const [url,setUrl]=useState("");
  const [message,setMessage]=useState("");
  const media=useRef<HTMLMediaElement|null>(null);
  useEffect(()=>{
    const owned=URL.createObjectURL(new Blob([bytes.slice().buffer],{type:mediaType}));
    setUrl(owned);setMessage("");
    return()=>URL.revokeObjectURL(owned);
  },[bytes,mediaType]);
  function locate() {
    if(!seek||!media.current)return;
    const seconds=seek.milliseconds/1000;
    const duration=media.current.duration;
    if(!Number.isFinite(seconds)||seconds<0||!Number.isFinite(duration)||seconds>duration){setMessage("引用时间超出可播放原件范围，未改变播放位置。");return;}
    media.current.currentTime=seconds;media.current.focus();setMessage(`已定位到 ${seconds.toFixed(2)} 秒；点击播放核对原件。`);
  }
  useEffect(()=>{if(media.current&&media.current.readyState>=1)locate();},[seek,url]);
  const common={src:url,controls:true,preload:"metadata",onLoadedMetadata:locate,onError:()=>setMessage("此原件无法由当前播放器解码；原件和识别结果仍保留。")};
  return <section aria-label="媒体原件播放器">
    {mediaType.startsWith("video/")?<video {...common} ref={element=>{media.current=element;}} aria-label="视频原件"/>:<audio {...common} ref={element=>{media.current=element;}} aria-label="音频原件"/>}
    <p>播放内容来自已核对 SHA 的本地原件；转写结果与原文核验分别记录。</p>
    {message?<p role="status">{message}</p>:null}
  </section>;
}
