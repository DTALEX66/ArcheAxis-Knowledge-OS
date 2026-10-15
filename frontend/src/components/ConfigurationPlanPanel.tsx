import { useEffect, useRef, useState } from "react";
import { readHostConfigurationPlans } from "../api/uiHost";
import type { ConfigurationPlanCatalog } from "../api/generated/core-contract";

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
    <p>首期提供计划读取。已有服务仅支持本机回环地址；远端服务尚不支持。安装引擎尚未提供，下载、安装与更新需要正式计划和授权回执。</p>
    <button disabled={busy} onClick={() => void read()}>读取配置与部署计划</button>
    <p role="status">{message}</p>
    {catalog && <>
      <p>配置版本 {catalog.configuration_revision} · 配置 SHA-256：{catalog.configuration_sha256}（此值不是模型文件 hash）</p>
      <h3>已登记模块</h3>
      {catalog.modules.length === 0 ? <p>当前未登记模块。</p> : <ul>{catalog.modules.map(row => <li key={row.capability}>
        {row.capability} · {row.enabled === null ? "启用状态未知" : row.enabled ? "启用" : "停用"} · 引擎运行未验证
      </li>)}</ul>}
      <h3>服务与下载候选</h3>
      {catalog.plans.length === 0 && <p>当前没有已配置的服务候选，请先保存产品服务配置。</p>}
      {catalog.plans.map(plan => <article key={plan.plan_id}>
        <h4>{plan.profile_id} · {plan.model} · {plan.mode === "existing_service" ? "已有本机服务" : "本机下载"}</h4>
        <p>来源：{plan.source ?? "未知，尚无获准来源"} · 版本：{plan.version ?? "未知"} · 大小：{plan.size_bytes === null ? "未知" : `${plan.size_bytes} 字节`} · 文件 SHA-256：{plan.artifact_sha256 ?? "未知"}</p>
        <p>{plan.mode === "existing_service" ? "不可执行：只读取配置，尚未探测服务；连接执行须另行检查权限。风险范围：本机服务连接。回退：当前绑定未改变。" : "不可执行：缺少安装引擎与获准下载来源。风险范围：本机磁盘和进程。回退：未创建文件，无需清理。"}</p>
      </article>)}
    </>}
  </section>;
}
