import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import type { LayoutSnapshot, LayoutLayout } from "../api/generated/layout-contract";
import { findUiPage } from "../presentation/uiPages";
import { failureMessage } from "../presentation/labels";
const presets = { default: { label: "日常", panels: ["01", "02"] }, reading: { label: "阅读", panels: ["03", "20"] }, research: { label: "研究", panels: ["05", "04"] }, learning: { label: "学习", panels: ["06", "11"] } } as const;
export function LayoutPreferencesPanel() {
  const [snapshot, setSnapshot] = useState<LayoutSnapshot | null>(null), [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false); const epoch = useRef(0), mounted = useRef(false);
  // This identity describes this local native host. No browser credentials or business data are stored here.
  const [device] = useState(() => {
    const key = "archeaxis.layout.device.v1", existing = localStorage.getItem(key);
    if (existing && /^[A-Za-z0-9_-]{1,64}$/.test(existing)) return existing;
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    const value = "desktop_" + Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
    localStorage.setItem(key, value); return value;
  });
  async function load() {
    const attempt = ++epoch.current; setBusy(true); setMessage("");
    try { const value = await coreCommand<LayoutSnapshot>("layout_read", { device_id: device }); if (value.device_id !== device) throw new Error("布局设备身份不一致"); if (mounted.current && epoch.current === attempt) setSnapshot(value); }
    catch (error) { if (mounted.current && epoch.current === attempt) setMessage(failureMessage(error)); }
    finally { if (mounted.current && epoch.current === attempt) setBusy(false); }
  }
  useEffect(() => { mounted.current = true; void load(); const reload = (event: Event) => { if ((event as CustomEvent<{confirmed?: boolean}>).detail?.confirmed === true) { setSnapshot(null); void load(); } }; window.addEventListener("workspace-invalidated", reload); return () => { mounted.current = false; ++epoch.current; window.removeEventListener("workspace-invalidated", reload); }; }, []);
  async function save(preset: keyof typeof presets) {
    if (!snapshot || busy || snapshot.recovery_reason) return;
    const selected = presets[preset], panels = [...selected.panels];
    const layout: LayoutLayout = { schema_version: 1, preset_id: preset, registered_panels: panels, dock_tree: { kind: "tabs", panels, active: panels[0] }, floating_bounds: {} };
    await change("layout_write", { ...identity(snapshot), layout }, "布局已保存");
  }
  function identity(value: LayoutSnapshot) { return { workspace_id: value.workspace_id, device_id: value.device_id, restore_epoch: value.restore_epoch, expected_revision: value.revision }; }
  async function change(operation: "layout_write" | "layout_recover", body: Record<string, unknown>, success: string) {
    const attempt = ++epoch.current; setBusy(true); setMessage("");
    try { const value = await coreCommand<LayoutSnapshot>(operation, { body }); if (value.workspace_id !== body.workspace_id || value.device_id !== body.device_id || value.restore_epoch !== body.restore_epoch || value.revision !== Number(body.expected_revision) + 1) throw new Error("布局保存回执身份不一致"); if (mounted.current && epoch.current === attempt) { setSnapshot(value); setMessage(success); } }
    catch (error) { if (mounted.current && epoch.current === attempt) setMessage(failureMessage(error)); }
    finally { if (mounted.current && epoch.current === attempt) setBusy(false); }
  }
  return <section className="setup-card" aria-label="设备布局偏好">
    <h2>设备布局</h2><p>保存常用面板组合，重新打开后可继续使用。</p>
    {snapshot && <><p>修订 {snapshot.revision} · {presets[snapshot.layout.preset_id as keyof typeof presets]?.label ?? "自定义"}</p>
      {snapshot.recovery_reason && <p role="status">已保留原布局。请确认恢复，或重新读取当前版本。</p>}
      <div>{Object.entries(presets).map(([key, preset]) => <button type="button" key={key} disabled={busy || !!snapshot.recovery_reason} onClick={() => void save(key as keyof typeof presets)}>{preset.label}布局</button>)}</div>
      <nav aria-label="已保存的布局面板">{snapshot.layout.registered_panels.map(id => <a key={id} href={`#page=${id}`}>{findUiPage(id)?.label ?? id} </a>)}</nav>
      <button type="button" disabled={busy} onClick={() => void change("layout_recover", { ...identity(snapshot), viewport_width: Math.max(320, Math.min(16000, window.innerWidth)), viewport_height: Math.max(240, Math.min(16000, window.innerHeight)) }, "布局已恢复")}>确认恢复布局</button>
    </>}
    <button type="button" disabled={busy} onClick={() => void load()}>重新读取布局</button>
    {message && <p role="status">{message}</p>}
  </section>;
}
