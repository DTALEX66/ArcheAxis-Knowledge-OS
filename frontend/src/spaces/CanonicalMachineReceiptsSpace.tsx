import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { BoundedJobPanel, type BoundedJobCommand } from "../components/BoundedJobPanel";
import type { MachineTaskRowDto, MachineTasksPageDto } from "../api/generated/core-contract";
import { failureMessage } from "../presentation/labels";
import { localDateTime } from "../presentation/display";
import { RawReceiptButton } from "../components/DiagnosticConsole";
import "./machine-receipts.css";

const outcomeLabel = { succeeded: "已完成", failed: "失败", unmeasured: "未测评" };
function taskKind(scope: string): string {
  return ({ "runtime.answer": "AI 回答", "runtime.retest": "纠正后复测", "runtime.evaluation.failed": "回答评测", "runtime.execution.withheld": "未发布的 AI 运行" } as Record<string, string>)[scope] ?? "AI 任务";
}
// Parent updates must not replace the port and reset an accepted running job.
const boundedJobCommand: BoundedJobCommand = (operation,payload) => coreCommand(operation,payload);

/** Durable Core history, separate from human mastery and general agent execution. */
type TaskIdentity=Omit<MachineTaskRowDto,"principal"|"recorded_at">&Partial<Pick<MachineTaskRowDto,"principal"|"recorded_at">>;
export function CanonicalMachineReceiptsSpace({initialTaskId,active=true}:{initialTaskId?:string;active?:boolean}={}) {
  const [rows, setRows] = useState<MachineTaskRowDto[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TaskIdentity | null>(null);
  const [receipt, setReceipt] = useState<Record<string, unknown> | null>(null);
  const [reading, setReading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [pane, setPane] = useState<"history"|"processing">("history");
  useEffect(()=>{if(active&&initialTaskId)setPane("history");},[active,initialTaskId]);
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
  return <section aria-label="资料处理与 AI 任务记录" className="ui-machine-receipts">
    <header className="machine-receipts-heading"><div><h2>任务与记录</h2><p>选择已保存任务，查看原问题、回答与版本。</p></div><div role="group" aria-label="任务内容类型"><button type="button" aria-pressed={pane==="history"} onClick={()=>setPane("history")}>AI 任务记录</button><button type="button" aria-pressed={pane==="processing"} onClick={()=>setPane("processing")}>资料处理任务</button></div></header>
    <div hidden={pane!=="processing"} className="machine-processing-pane"><BoundedJobPanel command={boundedJobCommand} /></div>
    <div hidden={pane!=="history"} className="machine-history-workspace"><div className="machine-task-list">
      <p>查看本机已保存的 AI 任务。处理完成不代表回答正确，也不代表你已掌握知识。</p>
      <button disabled={loading} onClick={() => void load()}>刷新任务记录</button>
      {loading ? <p role="status">正在读取任务记录…</p> : null}
      {error ? <p role="alert">任务读取失败：{error}。已有记录仍保留，可以重试。</p> : null}
      {loaded && !loading && !error && rows.length === 0 ? <p>尚无已保存的机器任务。执行回答后可在此查看详细记录。</p> : null}
      <ul className="action-list">{rows.map((row, index) => <li key={row.task_id}>
        <button aria-pressed={selected?.task_id === row.task_id} onClick={() => void open(row)}>{taskKind(row.scope)} {index + 1} · {outcomeLabel[row.outcome]}</button>
        <p>模型 {row.model_version} · <time dateTime={row.recorded_at} title={row.recorded_at}>{localDateTime(row.recorded_at)}</time></p>
      </li>)}</ul>
      {cursor ? <button disabled={loading} onClick={() => void load(cursor)}>查看更多任务记录</button> : null}
      <p>这里显示已保存的任务历史；自由运行代理和任意工具执行尚不可用。</p>
    </div>
    <aside aria-label="任务记录详情" className="machine-task-detail">
      {!selected&&reading?<p role="status">正在读取指定 AI 任务…</p>:null}{!selected&&detailError?<p role="alert">指定任务记录尚未确认：{detailError}</p>:null}
      {selected ? <>
        <h3>{taskKind(selected.scope)} · {outcomeLabel[selected.outcome]}</h3>
        {reading ? <p role="status">正在检查已保存的记录…</p> : null}
        {detailError ? <p role="alert">任务记录尚未确认：{detailError}</p> : null}
        {receipt ? <>
          <details><summary>来源与版本详情</summary><dl><dt>任务编号</dt><dd>{selected.task_id}</dd><dt>知识版本</dt><dd>{selected.knowledge_version ?? "未绑定"}</dd><dt>模型版本</dt><dd>{selected.model_version}</dd>
            <dt>方法版本</dt><dd>{selected.method_version ?? "未记录"}</dd><dt>工具版本</dt><dd>{selected.tool_version ?? "未记录"}</dd>
            <dt>复测关联</dt><dd>{selected.retest_of ?? "非复测"}</dd></dl></details>
          {typeof conditions?.question === "string" ? <><h4>原问题</h4><p>{conditions.question}</p></> : null}
          {typeof answer === "string" ? <><h4>原机器回答</h4><pre aria-label="历史机器回答">{answer}</pre></> : null}
          {selected.failure ? <details><summary>查看失败说明</summary><p>{selected.failure}</p></details> : null}
          <p>历史内容只读；撤回知识不会改写已有回答和记录。复测完成也不代表你已掌握知识。</p>
          <RawReceiptButton label="完整任务详细信息" payload={{ ...receipt, principal: selected.principal, recorded_at: selected.recorded_at }} />
        </> : null}
        <button onClick={() => { detailEpoch.current++; setSelected(null); setReceipt(null); setReading(false); setDetailError(null); }}>关闭任务详情</button>
      </> : <div className="machine-task-empty"><h3>打开一项任务</h3><p>选择左侧记录，在这里完整阅读原问题和回答，核对来源、版本与评测情况。</p></div>}
    </aside>
    </div>
  </section>;
}
