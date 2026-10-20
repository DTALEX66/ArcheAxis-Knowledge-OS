import { CAPABILITY_PACKAGE_DETAILS } from "../api/generated/capability-package-details";
import { RawReceiptButton } from "./DiagnosticConsole";

/** 仅所选稳定CAP的构建时验证声明；不参与运行握手，也不授予安装、执行或许可资格。 */
export function CapabilityPackageDetails({ capabilityId }: { capabilityId: string }) {
  const rows = CAPABILITY_PACKAGE_DETAILS.entries.filter(row =>
    (row.manifest.capability_ids as readonly string[]).includes(capabilityId));
  return <section aria-label="能力包声明">
    <h4>能力包声明</h4>
    {!rows.length ? <p>此能力尚无已验证的包说明；许可、业务验证与运行状态均待核对。</p> : rows.map(row => <article key={row.identity.sha256} aria-label={`包说明 ${row.identity.package_id}`}>
      <p>包说明 {row.identity.package_id} · 声明版本 {row.identity.version}</p>
      <p>声明校验通过：原文件与公共来源引用匹配，兼容应用版本 {row.host_version}；发布者真实性尚未验证。</p>
      <p>这里内置的是扩展说明，不证明关联引擎内置、已安装或可用。</p>
      <p>依赖来源：{row.manifest.resource_keys.join("、") || "无外部来源声明"}</p>
      <p>许可声明：{row.manifest.license.expression ?? "未知"} · 审查尚未完成；声明校验不提供商业许可结论。</p>
      <p>业务验证尚未完成 · 当前运行状态未知；当前健康与权限仍以下方读取结果为准。</p>
      <p>权限仅限所选资料；{row.manifest.permissions.network==="none"?"不请求联网":"联网范围待审查"}，{row.manifest.permissions.cost==="none"?"不请求付费":"费用待核对"}；均未授权执行。具体申请项见运行诊断。</p>
      <p>缺少前提时不可用；损失：{row.manifest.fallback.losses.join("、") || "未声明损失"}；不自动降级或重试。</p>
      <RawReceiptButton label={`包说明身份与来源 · ${row.identity.package_id}`} payload={{ ...row, sources: CAPABILITY_PACKAGE_DETAILS.sources }} />
    </article>)}
  </section>;
}
