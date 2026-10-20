import {RawReceiptButton} from "./DiagnosticConsole";
import type {ConversationRequestDto} from "../api/generated/conversation";

type RequestSummary = Pick<ConversationRequestDto, "question" | "material" | "selection" | "model" | "model_configuration" | "max_tokens" | "timeout_s"> & {purpose: string};
export type MaterialPresentation = {identity: NonNullable<RequestSummary["material"]>; title: string};
function matchingTitle(material: RequestSummary["material"], presentation?: MaterialPresentation): string | undefined {
  if(!material || !presentation?.title.trim()) return;
  const identity=(value:NonNullable<RequestSummary["material"]>)=>JSON.stringify(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)));
  return identity(material)===identity(presentation.identity)?presentation.title:undefined;
}
/** User confirmation reads the exact frozen request, never the current configuration. */
export function FrozenRequestSummary({request, destinationCandidates, materialPresentation}: {request: RequestSummary; destinationCandidates?: string[]; materialPresentation?: MaterialPresentation}) {
  const profile = request.model_configuration?.profile;
  const purposes: Record<string, string> = {companion: "日常陪伴", material_learning: "材料学习"};
  const material = request.material;
  const materialTitle=matchingTitle(material,materialPresentation);
  return <section className="frozen-request-summary" aria-label="待确认请求">
    <p>待发送问题：{request.question}</p>
    <dl>
      <dt>用途</dt><dd>{purposes[request.purpose] ?? request.purpose}</dd>
      <dt>材料范围</dt><dd>{material?.kind === "document" ? `${materialTitle?`《${materialTitle}》，`:""}已保存文档第 ${material.version} 版${material.block_id?"，指定内容块":""}` : material ? `${materialTitle?`《${materialTitle}》，`:""}已固定提取结果` : "不附加材料"}{request.selection ? "，仅所选片段" : material ? "，当前版本全文" : ""}</dd>
      <dt>模型</dt><dd>{profile?.model ?? request.model ?? "由本地服务选择，尚未确定"}{request.model_configuration ? `（${request.model_configuration.lane === "deep" ? "深度" : "快速"}）` : ""}</dd>
      <dt>目的地</dt><dd>{profile?.endpoint ?? (destinationCandidates?.length ? `由本地服务从以下地址选择：${destinationCandidates.join("、")}` : "本地服务，具体地址尚未确定")}</dd>
      <dt>生成限制</dt><dd>最多 {request.max_tokens} token，等待上限 {request.timeout_s} 秒</dd>
    </dl>
    {material&&!materialTitle?<p>材料标题尚未核对；可查看精确身份后确认。</p>:null}
    {material?<RawReceiptButton label="冻结材料身份与选区" visibleLabel="核对材料身份与选区" category="data" payload={{material,selection:request.selection}}/>:null}
  </section>;
}
