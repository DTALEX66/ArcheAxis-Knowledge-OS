type Capability = Record<string, unknown>;

/** Uses the existing Core registry; registration never certifies an output or model. */
export function ModelTaskRoles({capabilities,scopeLabel}:{capabilities:ReadonlyMap<string,Capability>|null;scopeLabel?:string}) {
  const conversion=["text.extract","pdf.extract","image.ocr","office.structure","media.transcribe","media.video"];
  const registered=capabilities ? conversion.filter(name=>capabilities.has(name)) : [];
  const answer=capabilities?.get("machine.answer");
  return <section aria-label="模型与工具职责">
    <h3>模型与工具职责</h3>
    <article><h4>本地资料转换</h4>
      <p>解析、OCR、转写、切分与来源定位由对应工具和专用 worker 承担；对话模型不替代这些步骤。</p>
      <p>{scopeLabel ? `仅观察「${scopeLabel}」；其他转换路由不在本次读取范围。` : capabilities===null?"当前工具状态未知":`当前 Core 登记 ${registered.length} 项转换路由；登记不代表产物已验证`}</p>
      <p>处理结果保留原件和损失说明；基础保存不等待模型或联网核验。</p>
    </article>
    <article><h4>日常对话与学习</h4>
      <p>{answer?answer.enabled===false?"本地回答路由已禁用":"本地回答路由已登记；模型推理状态尚未由此验证":scopeLabel?"本次没有观察本地回答路由；不据此判断它未配置或不可用。":"本地回答路由未确认"}</p>
      <p>在受控 AI 任务中显式读取本地清单、选择模型和预算；清单、已加载与实际回答分别核对。4B 或 27B 的历史测试不固定最终基座。</p>
      <p>仅使用当前任务获准的知识材料；本地失败不静默转云。返回的模型身份、用量与未知费用随任务保存。</p>
    </article>
    <article><h4>联网研究与核验</h4>
      <p>通过文档检查明确选择供应商、材料、用途与费用边界；供应商真实接通状态未知，目录声明不是实测。</p>
      <p>搜索使用单独授权的查询，保存实际来源与可定位引文。模型判断和来源事实分开，未读资料不能成为证据。</p>
    </article>
    <p>模型标注、事实验证和正式入库选择相互独立；最终采用由用户决定，检查结果不替代用户选择。</p>
  </section>;
}
