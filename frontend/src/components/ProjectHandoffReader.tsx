import { Component, useEffect, useRef, useState } from "react";
import type { JSONContent } from "@tiptap/core";
import { coreCommand } from "../api/core";
import { parseContextProposal, assertPreview, assertSnapshot, verifyProposalFingerprint, type ContextProposal, type Preview, type Snapshot } from "../api/projectHandoff";
import { AaosDialog } from "../design-system/AaosPrimitives";
import { focusVisibleTarget } from "../presentation/focus";
import { DocumentSnapshot } from "./DocumentSnapshot";
import { RawReceiptButton } from "./DiagnosticConsole";

// Stored future/opaque nodes remain intact; a projection failure must not unmount Exchange.
class SnapshotProjection extends Component<{value: JSONContent}, {failed:boolean}> {
  state = {failed:false};
  static getDerivedStateFromError() { return {failed:true}; }
  render() {
    return this.state.failed ? <p role="alert">固定正文结构暂不能预览；原文档未改变，本次未展示不支持的结构。</p>
      : <DocumentSnapshot value={this.props.value} label="固定版本全文" showRaw={false} />;
  }
}

/** Local human reads only: the proposal never grants navigation, execution or acceptance. */
export function ProjectHandoffReader() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [paused, setPaused] = useState(false);
  const restoring = useRef(false);
  const root = useRef<HTMLElement>(null), trigger = useRef<HTMLButtonElement>(null);
  const generation = useRef(0), locked = useRef(false), mounted = useRef(false), opened = useRef(false);
  const approved = useRef<ContextProposal | null>(null);
  // Radix marks the opener tree aria-hidden while its own modal portal is open.
  const visible = () => {
    if (!root.current?.isConnected || root.current.closest('[hidden],[inert]') || (!opened.current && root.current.closest('[aria-hidden="true"]'))) return false;
    for (let node: HTMLElement | null = root.current; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden" || style.visibility === "collapse") return false;
    }
    return true;
  };
  function clear(message = "") {
    generation.current++; locked.current = false; approved.current = null;
    setPreview(null); setSnapshot(null); setBusy(false); setError(message);
  }
  function changeOpen(next: boolean) {
    if (next && !visible()) return;
    opened.current = next; clear(); setText(""); setOpen(next);
  }
  useEffect(() => {
    mounted.current = true;
    const invalidate = () => { clear("工作区已变化；请重新取得并粘贴当前提案。"); setText(""); };
    window.addEventListener("workspace-invalidated", invalidate);
    const pause = () => { restoring.current = true; setPaused(true); invalidate(); };
    const resume = () => { restoring.current = false; setPaused(false); };
    window.addEventListener("workspace-restore-start", pause);
    window.addEventListener("workspace-restore-finish", resume);
    return () => { mounted.current = false; generation.current++; locked.current = false;
      window.removeEventListener("workspace-invalidated", invalidate);
      window.removeEventListener("workspace-restore-start", pause);
      window.removeEventListener("workspace-restore-finish", resume);
    };
  }, []);
  useEffect(() => {
    if (!preview) return;
    const timer = window.setTimeout(() => clear("提案已到期；正文已关闭，请重新取得提案。"), Math.max(0, Math.min(preview.expires_at_ms, snapshot?.expires_at_ms ?? preview.expires_at_ms) - Date.now()));
    return () => window.clearTimeout(timer);
  }, [preview, snapshot]);
  useEffect(() => {
    if (!open) return;
    // Dock retains parked views. A portal must not keep their body visible.
    const observer = new MutationObserver(() => {
      if (opened.current && !visible()) { opened.current = false; clear(); setText(""); setOpen(false); }
    });
    observer.observe(document.body, {subtree:true,childList:true,attributes:true,attributeFilter:["hidden","inert","aria-hidden","style","class"]});
    return () => observer.disconnect();
  }, [open]);
  const current = (request: number) => mounted.current && !restoring.current && opened.current && visible() && request === generation.current;
  async function read(body: boolean) {
    if (locked.current || restoring.current || !opened.current || !visible()) return;
    locked.current = true; setBusy(true); setError("");
    const request = ++generation.current;
    try {
      if (body) {
        if (!preview || !approved.current) throw new Error("请先明确预览当前提案。");
        const proposal = approved.current;
        assertPreview(preview, proposal);
        if (preview.reference_state === "NOT_FOUND") throw new Error("此本机工作区未找到引用，未读取其他对象。");
        const value = await coreCommand<unknown>("project_handoff_snapshot", {body:proposal});
        const bound = assertSnapshot(value, proposal, preview.proposal_sha256);
        if (current(request)) setSnapshot(bound);
      } else {
        setPreview(null); setSnapshot(null); approved.current = null;
        const proposal = parseContextProposal(text);
        const value = await coreCommand<unknown>("project_handoff_preview", {body:proposal});
        const bound = assertPreview(value, proposal);
        await verifyProposalFingerprint(proposal, bound.proposal_sha256);
        assertPreview(bound, proposal); // Digest work may finish after expiry or another selection.
        if (current(request)) { approved.current = proposal; setPreview(bound); }
      }
    } catch (cause) {
      if (current(request)) { setSnapshot(null); setError(cause instanceof Error ? cause.message : "只读核验失败；未打开正文。"); }
    } finally {
      if (current(request)) { locked.current = false; setBusy(false); }
    }
  }
  return <section ref={root} tabIndex={-1} aria-label="跨项目固定引用">
    <AaosDialog title="跨项目固定引用阅读" description="只在本机读取固定版本；不会执行提案或接纳知识。关闭后返回原交换页面。"
      open={open} onOpenChange={changeOpen} trigger={<button ref={trigger} type="button">预览跨项目引用</button>}
      onCloseAutoFocus={event => { event.preventDefault(); focusVisibleTarget(trigger.current, root.current); }}>
      <label>上下文提案 JSON<textarea aria-label="上下文提案 JSON" value={text} onChange={event => {clear();setText(event.target.value);}} /></label>
      <button type="button" disabled={paused || busy || !text.trim()} onClick={() => void read(false)}>预览引用信息</button>
      {paused ? <p role="status">恢复核对中，暂不读取引用。</p> : null}
      {busy ? <p role="status">正在核对本机固定引用…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {preview && preview.proposal.payload.kind === "context" ? <section aria-label="提案只读预览">
        <h3>本机文档第 {preview.proposal.payload.source.reference.version} 版</h3>
        <p>来源身份尚未认证（UNVERIFIED）；所声明选区尚未核验（UNVERIFIED）。</p>
        <p>仅显示固定版本全文；不保证所声明选区已定位或内容已获依据支持。</p>
        <p>{preview.reference_state === "CURRENT" ? "预览时，此引用与当前保存版本一致。" : preview.reference_state === "STALE" ? "预览时，当前保存版本已变化；可明确读取所引用的旧版，不替代为新版。" : "本机未找到此引用，正文不可用。"}</p>
        <RawReceiptButton label="跨项目引用预览" payload={preview} category="data" />
        <button type="button" disabled={paused || busy || preview.reference_state === "NOT_FOUND" || snapshot !== null} onClick={() => void read(true)}>打开固定版本全文</button>
      </section> : null}
      {snapshot ? <section aria-label="本机固定版本只读正文"><p>本机固定版本 · 第 {snapshot.reference.version} 版 · 只读</p>
        <p>{snapshot.reference_state === "STALE" ? "读取时当前保存版本已变化；这里保留并显示引用的旧版全文。" : "读取时此固定版本仍与当前保存版本一致。"}</p>
        <SnapshotProjection key={`${snapshot.proposal_sha256}:${snapshot.reference.document_id}:${snapshot.reference.version}`} value={snapshot.editor_json as JSONContent} />
        <RawReceiptButton label="跨项目固定正文身份" payload={Object.fromEntries(Object.entries(snapshot).filter(([key]) => key !== "editor_json"))} category="data" />
      </section> : null}
      <button type="button" onClick={() => changeOpen(false)}>关闭并返回</button>
    </AaosDialog>
  </section>;
}
