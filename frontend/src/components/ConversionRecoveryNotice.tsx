import { conversionRecovery } from "../presentation/conversionRecovery";
import { RawReceiptButton } from "./DiagnosticConsole";

/** Guidance only: execution and retry remain governed by the existing job controls. */
export function ConversionRecoveryNotice({ status }: { status: unknown }) {
  const recovery = conversionRecovery(status);
  if (!recovery) return null;
  return <section aria-label="语音转写组件恢复指引">
    <h4>{recovery.title}</h4>
    <p>原件已保留。请先补齐语音转写组件，再处理这份音频或视频。</p>
    <ol>
      <li>打开下方诊断，保留这份失败记录，交给安装或维护人员核对。</li>
      <li>请安装或维护人员提供包含已授权转写模型的完整应用包；已有本地模型时，也可修复应用已登记的模型位置。当前界面没有语音模型目录选择器，应用不会自动下载模型。</li>
      <li>补齐组件并重启应用后，回到这份原件，先读取转换状态，再使用页面允许的转换或重试按钮。无需重新导入原件。</li>
    </ol>
    <RawReceiptButton label="语音转写模型缺失诊断" visibleLabel="查看语音组件诊断" category="data" payload={status}/>
  </section>;
}
