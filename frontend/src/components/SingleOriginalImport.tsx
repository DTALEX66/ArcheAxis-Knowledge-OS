import { useEffect, useId, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { sha256 } from "../presentation/exchangeProof";
import { confirmedImport, type ImportReceipt } from "../presentation/importReceipt";

const MAX_BYTES = 64 * 1024 * 1024;
type Attempt = { name: string; bytes: number; expectedHash: string; body: { name: string; content_base64: string } };
type Confirmed = { attempt: Attempt; receipt: ImportReceipt };

/** Preserve the selected bytes until canonical custody has been acknowledged. No conversion is started here. */
export function SingleOriginalImport({ onImported, onOpenSource }: { onImported?: (receipt: ImportReceipt) => void; onOpenSource?: (id: string) => void }) {
  const owner = useId();
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Attempt | null>(null);
  const [confirmed, setConfirmed] = useState<Confirmed | null>(null);
  const [message, setMessage] = useState("");
  const alive = useRef(true), flight = useRef(false), request = useRef<Attempt | null>(null);
  function publish() { window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner, dirty: flight.current || !!request.current } })); }
  useEffect(() => { alive.current = true; return () => { alive.current = false; window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: { owner, dirty: false } })); }; }, [owner]);

  async function submit(attempt: Attempt) {
    const receipt = confirmedImport(await coreCommand("source_import", { body: attempt.body }), attempt.expectedHash);
    if (!alive.current) return;
    request.current = null; setPending(null); setConfirmed({ attempt, receipt });
    setMessage(receipt.duplicate ? "这份原件已在本地，已确认对应记录；内容识别仍需单独检查。" : "原件已保存在本地；尚未执行内容识别。现在可以打开原件，再选择转换或阅读。");
    try { onImported?.(receipt); }
    catch { setMessage("原件已确认保存；目录刷新未完成。可打开刚导入的原件，或稍后刷新原件目录。"); }
  }
  async function choose(file: File | undefined) {
    if (!file || flight.current || request.current) return;
    if (file.size > MAX_BYTES) { setMessage("文件超过 64 MiB 上限，未发起导入。请先选一份较小的资料。"); return; }
    flight.current = true; publish(); setBusy(true); setMessage(""); setConfirmed(null);
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (bytes.byteLength !== file.size) throw new Error("所选文件未完整读取");
      const expectedHash = await sha256(bytes);
      let binary = "";
      for (let offset = 0; offset < bytes.length; offset += 8192) binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
      if (!alive.current) return;
      const attempt = { name: file.name, bytes: bytes.length, expectedHash, body: { name: file.name, content_base64: btoa(binary) } };
      request.current = attempt; setPending(attempt); publish();
      await submit(attempt);
    } catch {
      if (alive.current) setMessage(request.current ? "导入结果尚未确认。已保留本次文件内容，请检查本地工作区连接，再重试这一次导入；不要改选文件。" : "文件暂时无法完整读取，未发起导入。请确认文件可打开，再重新选择。");
    } finally { flight.current = false; if (alive.current) { setBusy(false); publish(); } }
  }
  async function retry() {
    if (flight.current || !request.current) return;
    flight.current = true; publish(); setBusy(true); setMessage("");
    try { await submit(request.current); }
    catch { if (alive.current) setMessage("导入结果仍未确认。请保留原文件，检查本地工作区连接后重试这一次导入。"); }
    finally { flight.current = false; if (alive.current) { setBusy(false); publish(); } }
  }
  return <section className="exchange-single-import" aria-label="导入一份原件" aria-busy={busy}>
    <h4>先导入一份文件</h4>
    <p>可先选一份 TXT、Markdown 或已有文档，单文件上限 64 MiB。原文件与之后提取的内容分别保留。</p>
    <label className="exchange-choose-file" data-disabled={busy || !!pending}><span>选择文件并导入</span><input type="file" data-guide="first-original" aria-label="导入原件" disabled={busy || !!pending} onChange={event => { void choose(event.target.files?.[0]); event.target.value = ""; }} /></label>
    {busy ? <p role="status">正在核对并保存这份原件，请稍候…</p> : null}
    {message ? <p role={pending ? "alert" : "status"}>{message}</p> : null}
    {pending && !busy ? <div><p>待核对：{pending.name}（{pending.bytes} 字节）。重试使用刚才同一份内容。</p><button onClick={() => void retry()}>重试这一次原件导入</button></div> : null}
    {confirmed ? <div className="exchange-import-result"><p>已确认原件：{confirmed.attempt.name}（{confirmed.attempt.bytes} 字节）</p><p>保存后可在下方“原件目录”找到；识别失败时核对该原件的任务，不需要另导入一份。</p>{onOpenSource ? <button onClick={() => onOpenSource(confirmed.receipt.source_id)}>打开刚导入的原件</button> : null}</div> : null}
  </section>;
}
