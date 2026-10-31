import { useEffect, useRef, useState } from "react";
import { readHostConfigurationPlans } from "../api/uiHost";
import type { ConfigurationPlanCatalog } from "../api/generated/core-contract";
import { capabilityOperationName } from "../presentation/capabilityCenter";

export function ConfigurationPlanPanel() {
  const [catalog, setCatalog] = useState<ConfigurationPlanCatalog | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("尚未读取计划。");
  const mounted = useRef(false);
  const pending = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function read() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setCatalog(null);
    try {
      const next = await readHostConfigurationPlans();
      if (mounted.current) {
        setCatalog(next);
        setMessage("已读取当前配置；服务可用性与安装状态尚未验证。");
      }
    } catch {
      if (mounted.current) setMessage("计划读取失败，当前状态未知；请手动重试。");
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return <section aria-label="配置与部署计划" className="card" style={{ padding: 16, overflowWrap: "anywhere" }}>
    <h2>配置与部署计划</h2>
    <p>在这里查看已保存的配置和可选服务。目前支持读取本机服务配置；远端连接、下载、安装与更新尚不可用。</p>
    <button disabled={busy} onClick={() => void read()}>读取配置与部署计划</button>
    <p role="status">{message}</p>
    {catalog && <>
      <p>配置版本 {catalog.configuration_revision} · 服务连接与安装状态尚未验证</p>
      <details><summary>配置指纹与功能标识</summary>
        <p>配置 SHA-256：{catalog.configuration_sha256}（配置内容指纹，不代表模型文件已校验）</p>
        {catalog.modules.map(row => <p key={row.capability}>功能标识：{row.capability}</p>)}
      </details>
      <h3>已登记功能</h3>
      {catalog.modules.length === 0 ? <p>当前未登记功能。</p> : <ul>{catalog.modules.map(row => <li key={row.capability}>
        {row.capability === "text.extract" ? "文字解析" : capabilityOperationName(row.capability)} · {row.enabled === null ? "启用状态未知" : row.enabled ? "已启用" : "已停用"} · 实际运行尚未验证
      </li>)}</ul>}
      <h3>服务与下载候选</h3>
      {catalog.plans.length === 0 && <p>当前没有已配置的服务候选，请先保存产品服务配置。</p>}
      {catalog.plans.map(plan => <article key={plan.plan_id}>
        <h4>{plan.model} · {plan.mode === "existing_service" ? "已有本机服务" : "本机下载"}</h4>
        <p>来源：{plan.source ?? "未知，尚无获准来源"} · 版本：{plan.version ?? "未知"} · 大小：{plan.size_bytes === null ? "未知" : `${plan.size_bytes} 字节`}</p>
        <p>{plan.mode === "existing_service" ? "尚未检查服务连接；本次只读取配置，不会连接服务或更改当前模型。连接前仍需检查权限。" : "暂不可下载或安装：还没有可用的安装工具与已获允许的下载来源。本次未创建文件。"}</p>
        <details><summary>查看技术标识与文件校验</summary><p>计划标识：{plan.plan_id} · 配置标识：{plan.profile_id}</p><p>文件 SHA-256：{plan.artifact_sha256 ?? "未知"}</p></details>
      </article>)}
    </>}
  </section>;
}
