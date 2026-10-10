import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { BoundedJobPanel, type BoundedJobCommand } from "../components/BoundedJobPanel";
import type { MachineTaskRowDto, MachineTasksPageDto } from "../api/generated/core-contract";
import { failureMessage } from "../presentation/labels";
import { RawReceiptButton } from "../components/DiagnosticConsole";

const outcomeLabel = { succeeded: "任务回执成功", failed: "任务回执失败", unmeasured: "未测评" };
// Parent updates must not replace the port and reset an accepted running job.
const boundedJobCommand: BoundedJobCommand = (operation,payload) => coreCommand(operation,payload);

/** Durable Core history, separate from human mastery and general agent execution. */
type TaskIdentity=Omit<MachineTaskRowDto,"principal"|"recorded_at">&Partial<Pick<MachineTaskRowDto,"principal"|"recorded_at">>;
export function CanonicalMachineReceiptsSpace({initialTaskId}:{initialTaskId?:string}={}) {
  const [rows, setRows] = useState<MachineTaskRowDto[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TaskIdentity | null>(null);
  const [receipt, setReceipt] = useState<Record<string, unknown> | null>(null);
  const [reading, setReading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const listEpoch = useRef(0), detailEpoch = useRef(0);

  async function load(next?: string) {
    const epoch = ++listEpoch.current;
    setLoading(true); setError(null);
    try {
      const page = await coreCommand<MachineTasksPageDto>("machine_tasks_list", next ? { cursor: next } : {});
      if (new Set(page.items.map(row => row.task_id)).size !== page.items.length) throw new Error("duplicate receipt identity");
      if (epoch !== listEpoch.current) return;
      setRows(previous => next ? [...previous, ...page.items.filter(row => !previous.some(old => old.task_id === row.task_id))] : page.items);
      setCursor(page.next_cursor); setLoaded(true);
    } catch (reason) { if (epoch === listEpoch.current) setError(failureMessage(reason)); }
    finally { if (epoch === listEpoch.current) setLoading(false); }
  }
  useEffect(() => { void load(); return () => { listEpoch.current++; detailEpoch.current++; }; }, []);

  async function open(row: TaskIdentity) {
    const epoch = ++detailEpoch.current;
    setSelected(row); setReceipt(null); setDetailError(null); setReading(true);
    try {
      const proof = await coreCommand<Record<string, unknown>>("machine_task_get", { task_id: row.task_id });
      for (const key of ["task_id", "conditions", "knowledge_version", "method_version", "tool_version", "model_version", "scope", "outcome", "failure", "retest_of"] as const) {
        if (proof[key] !== row[key]) throw new Error("receipt readback identity mismatch");
      }
      if (epoch === detailEpoch.current) setReceipt(proof);
    } catch (reason) { if (epoch === detailEpoch.current) setDetailError(failureMessage(reason)); }
    finally { if (epoch === detailEpoch.current) setReading(false); }
  }

  useEffect(()=>{if(!initialTaskId)return;const epoch=++detailEpoch.current;setReceipt(null);setSelected(null);setReading(true);setDetailError(null);void coreCommand<Record<string,unknown>>("machine_task_get",{task_id:initialTaskId}).then(proof=>{if(epoch!==detailEpoch.current)return;if(proof.task_id!==initialTaskId||typeof proof.conditions!=="string"||typeof proof.scope!=="string"||typeof proof.model_version!=="string"||!["succeeded","failed","unmeasured"].includes(String(proof.outcome))||["knowledge_version","method_version","tool_version","failure","retest_of"].some(key=>proof[key]!==null&&typeof proof[key]!=="string"))throw new Error("pinned task identity mismatch");setSelected(proof as TaskIdentity);setReceipt(proof);}).catch(reason=>{if(epoch===detailEpoch.current)setDetailError(failureMessage(reason));}).finally(()=>{if(epoch===detailEpoch.current)setReading(false);});return()=>{detailEpoch.current++;};},[initialTaskId]);
  let conditions: Record<string, unknown> | null = null;
  if (receipt && typeof receipt.conditions === "string") {
    try { const parsed: unknown = JSON.parse(receipt.conditions); if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) conditions = parsed as Record<string, unknown>; }
    catch { /* Non-JSON conditions are retained in the immutable receipt below. */ }
  }
  const answer = conditions?.answer && typeof conditions.answer === "object" ? (conditions.answer as Record<string, unknown>).answer : null;
  return <section aria-label="受限任务与回执" className="ui-content-main-side ui-machine-receipts">
    <div>
      <h2>受限任务与回执</h2>
      <BoundedJobPanel command={boundedJobCommand} />
      <p>读取本地 Core 已保存的机器任务。任务结果、真人掌握、专业知识资格和参数训练分别记录。</p>
      <button disabled={loading} onClick={() => void load()}>刷新任务回执</button>
      {loading ? <p role="status">正在读取任务回执…</p> : null}
      {error ? <p role="alert">任务读取失败：{error}。已有回执仍保留，可重试。</p> : null}
      {loaded && !loading && !error && rows.length === 0 ? <p>尚无已保存的机器任务。执行回答后可在此读取实际回执。</p> : null}
      <ul className="action-list">{rows.map(row => <li key={row.task_id}>
        <button aria-pressed={selected?.task_id === row.task_id} onClick={() => void open(row)}>{row.task_id} · {outcomeLabel[row.outcome]}</button>
        <p>{row.scope} · 模型 {row.model_version} · {row.recorded_at}</p>
      </li>)}</ul>
      {cursor ? <button disabled={loading} onClick={() => void load(cursor)}>读取下一页任务回执</button> : null}
      <p>这里提供有限业务任务的历史和读回。通用 Agent Runtime 与任意工具执行尚未接通。</p>
    </div>
    <aside aria-label="任务回执详情">
      {!selected&&reading?<p role="status">正在核对指定机器任务…</p>:null}{!selected&&detailError?<p role="alert">指定回执未确认：{detailError}</p>:null}
      {selected ? <>
        <h3>{selected.task_id}</h3>
        <p>机器身份 · {outcomeLabel[selected.outcome]} · {selected.scope}</p>
        {reading ? <p role="status">正在核对持久化回执…</p> : null}
        {detailError ? <p role="alert">回执未确认：{detailError}</p> : null}
        {receipt ? <>
          <dl><dt>知识版本</dt><dd>{selected.knowledge_version ?? "未绑定"}</dd><dt>模型版本</dt><dd>{selected.model_version}</dd>
            <dt>方法版本</dt><dd>{selected.method_version ?? "未记录"}</dd><dt>工具版本</dt><dd>{selected.tool_version ?? "未记录"}</dd>
            <dt>复测绑定</dt><dd>{selected.retest_of ?? "非复测"}</dd></dl>
          {typeof conditions?.question === "string" ? <><h4>原问题</h4><p>{conditions.question}</p></> : null}
          {typeof answer === "string" ? <><h4>原机器回答</h4><pre aria-label="历史机器回答">{answer}</pre></> : null}
          {selected.failure ? <p>失败依据：{selected.failure}</p> : null}
          <p>历史内容只读；撤回知识不会改写既有回答或回执。复测成功回执也不代表真人掌握。</p>
          <RawReceiptButton label="完整持久化任务回执" payload={{ ...receipt, principal: selected.principal, recorded_at: selected.recorded_at }} />
        </> : null}
        <button onClick={() => { detailEpoch.current++; setSelected(null); setReceipt(null); setReading(false); setDetailError(null); }}>关闭回执详情</button>
      </> : <p>选择实际任务，核对来源版本、条件与结果。</p>}
    </aside>
  </section>;
}
