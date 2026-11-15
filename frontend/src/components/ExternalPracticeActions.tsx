import { useState } from "react";
import type { RecordView } from "../api/generated/teaching-contract";
import { practiceActions,type PracticeAction } from "../presentation/externalPractice";

/** Prepares ordinary human-authored records, never executes a tutorial or claims progress. */
export function ExternalPracticeActions({items,disabled,onPrepare}:{items:RecordView[];disabled:boolean;onPrepare:(action:PracticeAction,basis:RecordView|null)=>void}) {
  const [action,setAction]=useState<PracticeAction>("requirement"),[basis,setBasis]=useState("");
  const entry=practiceActions[action],parents:readonly string[]=entry.parents;
  const eligible=items.filter(item=>!item.withdrawn&&parents.includes(item.record.kind));
  const chosen=eligible.find(item=>item.record.record_id===basis)??null;
  return <section aria-label="外部实践计划与文字记录" className="stitch-teaching-card">
    <h3>外部实践计划与文字记录</h3><p>无需连接外部工具或上传成果。开始、本人自报完成和人工反馈都只是记录，不是独立评价、成绩或掌握证明。</p>
    <label>实践操作<select disabled={disabled} value={action} onChange={event=>{setAction(event.target.value as PracticeAction);setBasis("");}}>{Object.entries(practiceActions).map(([key,value])=><option key={key} value={key}>{value.label}</option>)}</select></label>
    {parents.length?<label>实践依据记录<select disabled={disabled} value={chosen?.record.record_id??""} onChange={event=>setBasis(event.target.value)}><option value="">选择已保存的固定记录</option>{eligible.map(item=><option key={item.record.record_id} value={item.record.record_id}>{item.record.purpose} · {item.record.record_id}</option>)}</select></label>:null}
    {chosen?<p>将绑定记录 {chosen.record.record_id} 与知识版本 {chosen.record.knowledge_version}；后续修订不会自动改绑。</p>:null}
    <button type="button" disabled={disabled||!!parents.length&&!chosen} onClick={()=>onPrepare(action,chosen)}>准备实践文字草稿</button>
    <p>准备后在下方补充实际内容，再明确保存；教程链接仅供本人记录，本页不打开或执行外部材料。</p>
  </section>;
}
