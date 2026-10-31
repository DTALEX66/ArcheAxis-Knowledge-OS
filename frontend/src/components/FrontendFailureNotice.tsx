import {useEffect, useState} from "react";
import {installFrontendFailureListener, type FrontendFailureKind} from "../presentation/frontendFailures";
import {publishDiagnostic} from "../presentation/diagnostics";

/** A transient notice, not another log. Existing editors stay mounted. */
export function FrontendFailureNotice() {
  const [failure, setFailure] = useState<FrontendFailureKind | null>(null);
  useEffect(() => installFrontendFailureListener(setFailure), []);
  if (!failure) return null;
  return <section role="status" aria-label="操作遇到问题" style={{position:"fixed", right:16, bottom:88, zIndex:900, width:"min(420px, calc(100vw - 32px))", maxHeight:"calc(100vh - 120px)", overflow:"auto", boxSizing:"border-box", padding:16, border:"1px solid var(--ax-border-strong)", borderRadius:"var(--ax-radius-lg)", background:"var(--ax-panel)", color:"var(--ax-fg)", boxShadow:"var(--cabin-shadow)", overflowWrap:"anywhere"}}>
    <p>界面中的一项操作遇到了问题。保存或处理结果尚未确认，请先查看原页面的状态；不要重复提交。关闭此提示不会重新加载页面，请先保留仍可编辑的内容。</p>
    <button type="button" onClick={event => publishDiagnostic("界面操作遇到问题", {kind: failure, result: "尚未确认", retention: "仅本次会话"}, "runtime", event.currentTarget)}>查看问题记录</button>
    <button type="button" onClick={() => setFailure(null)}>关闭提示</button>
  </section>;
}
