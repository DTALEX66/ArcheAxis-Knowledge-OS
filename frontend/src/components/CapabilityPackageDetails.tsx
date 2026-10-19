import { CAPABILITY_PACKAGE_DETAILS } from "../api/generated/capability-package-details";
import { RawReceiptButton } from "./DiagnosticConsole";

/** 仅所选稳定CAP的构建时验证声明；不参与运行握手，也不授予安装、执行或许可资格。 */
export function CapabilityPackageDetails({ capabilityId }: { capabilityId: string }) {
  const rows = CAPABILITY_PACKAGE_DETAILS.entries.filter(row =>
    (row.manifest.capability_ids as readonly string[]).includes(capabilityId));
  return <section aria-label="能力包声明">
    <h4>能力包声明</h4>
    {!rows.length ? <p>此能力尚无已验证的包说明，manifest 身份 UNKNOWN；许可、资格与运行状态分别未知。</p> : rows.map(row => <article key={row.identity.sha256} aria-label={`包说明 ${row.identity.package_id}`}>
      <p>包说明 {row.identity.package_id} · 声明版本 {row.identity.version}</p>
      <p>声明校验通过：原字节身份、公共来源引用与构建宿主 {row.host_version} 兼容；发布者真实性 {row.source_authenticity}。</p>
      <p>这里内置的是 manifest 说明，不证明关联引擎内置、已安装或可用。</p>
      <p>贡献形式：{row.manifest.contribution_points.join("、")} · 来源稳定键：{row.manifest.resource_keys.join("、") || "无外部来源声明"}</p>
      <p>许可声明：{row.manifest.license.expression ?? "UNKNOWN"} · 审查 {row.manifest.license.review}；声明校验不提供商业许可结论。</p>
      <p>独立资格 {row.qualification} · 当前运行状态 {row.runtime}；当前健康与权限仍以下方范围化读回为准。</p>
      <p>申请权限：{row.manifest.permissions.requested.join("、") || "无"} · 网络 {row.manifest.permissions.network} · 费用 {row.manifest.permissions.cost}；均未授权执行。</p>
      <p>降级声明：{row.manifest.fallback.mode} · 损失 {row.manifest.fallback.losses.join("、") || "未声明损失"}；不自动降级或重试。</p>
      <RawReceiptButton label={`包说明身份与来源 · ${row.identity.package_id}`} payload={{ identity: row.identity, source_path: row.source_path, sources: CAPABILITY_PACKAGE_DETAILS.sources }} />
    </article>)}
  </section>;
}
