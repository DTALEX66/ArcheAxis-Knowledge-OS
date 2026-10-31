import type { TeachingRecord } from "../api/generated/teaching-contract";

const stageCopy: Record<string, { title:string; goal:string; artifact:string; outline:string }> = {
  "08": { title:"明确这次要解决的问题", goal:"写清学习对象、现在的困难和希望得到的结果。", artifact:"需求简报", outline:"学习对象与使用场景：\n\n目前的困难：\n\n希望达到的结果：\n\n如何检查是否解决：\n" },
  "09": { title:"把需求变成可阅读的表达", goal:"对照选中的需求，安排内容顺序、例子与表达方式。", artifact:"表达预览", outline:"面向谁：\n\n核心解释：\n\n例子或演示：\n\n表达顺序与形式：\n" },
  "10": { title:"核对本次交付内容", goal:"对照表达方案检查正文，保留本次实际交付的版本。", artifact:"交付快照", outline:"本次交付内容：\n\n适用范围：\n\n与表达方案的差异：\n\n仍待解决的问题：\n" },
  "11": { title:"先独立说明，再核对理解", goal:"真实问题在学习区作答；这里保留自己的讲解、疑问和使用辅助的情况。", artifact:"我的讲解", outline:"不看参考时，我会这样解释：\n\n我使用的例子：\n\n仍不确定的地方：\n" },
  "12": { title:"对照原内容记录反馈与改动", goal:"指出具体问题、修正内容和原因，保留原版本供比较。", artifact:"反馈与修订对照", outline:"原内容中的具体问题：\n\n建议或实际修正：\n\n修改原因与待核实处：\n" },
};

/** A read-only projection of the real draft and its parent; no inferred score or generated result. */
export function TeachingStageWorkspace({pageId,parent,purpose,content,disabled,onOutline}:{pageId:string;parent:TeachingRecord|null;purpose:string;content:string;disabled:boolean;onOutline:(text:string)=>void}) {
  const stage=stageCopy[pageId];
  if(!stage)return null;
  const showComparison=pageId!=="08";
  return <section className="teaching-stage-workspace" aria-label={stage.artifact}>
    <header><div><span className="teaching-stage-kicker">当前阶段 · {stage.artifact}</span><h3>{stage.title}</h3><p>{stage.goal}</p></div>{!content.trim()?<button type="button" disabled={disabled} onClick={()=>onOutline(stage.outline)}>插入{stage.artifact}提纲</button>:null}</header>
    {pageId==="08"?<ol className="teaching-brief-prompts"><li>谁会使用这份内容？</li><li>具体卡在哪一步？</li><li>完成后能做什么？</li></ol>:null}
    {showComparison?<div className="teaching-stage-comparison">
      <article aria-label="本阶段参考内容"><h4>{pageId==="09"?"原需求":pageId==="10"?"表达方案或修订":pageId==="12"?"原交付或反馈":"原交付内容"}</h4>{parent?<><strong>{parent.purpose}</strong><p>{parent.content}</p></>:<p>尚未选中父记录。可在下方“记录属性与关联”选择实际版本；也可先保存自己的准备正文。</p>}</article>
      <article aria-label="当前产物预览"><h4>{stage.artifact}</h4>{purpose?<strong>{purpose}</strong>:null}<p>{content||"在下方写入正文，这里将展示当前内容。预览尚未保存，不代表已经交付或通过测评。"}</p></article>
    </div>:null}
    {pageId==="11"?<p className="teaching-stage-boundary">手工讲解不计分。真实问题、独立作答与复习记录使用本页的学习区，不能用登记记录替代。</p>:null}
  </section>;
}
