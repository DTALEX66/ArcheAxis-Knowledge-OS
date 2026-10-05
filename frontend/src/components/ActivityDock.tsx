import { useCallback, useEffect, useState } from "react";
import {
  dispatchDelivery,
  getActivity,
  getActivityObject,
  getDelivery,
  retryFailedDelivery,
  type ActivityItemDto,
} from "../api/workspace";
import type { InspectionTarget } from "./Inspector";
import { stateLabel, userErrorMessage } from "../presentation/labels";
import { coreCommand } from "../api/core";
import type { SourceDto, SourceJobDto, SourceJobsDto } from "../api/generated/core-contract";

type DockProps = { onInspect?: (target: InspectionTarget) => void; commandPaletteOpen?: boolean };

function useDockExpansion(commandPaletteOpen: boolean) {
  const [expanded, setExpanded] = useState(false);
  const toggle = useCallback(() => setExpanded(value => !value), []);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (commandPaletteOpen || event.defaultPrevented || event.repeat || event.isComposing || event.getModifierState("AltGraph")) return;
      if (!event.ctrlKey || !event.altKey || event.shiftKey || event.metaKey || event.key.toLowerCase() !== "j") return;
      event.preventDefault();
      toggle();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [commandPaletteOpen, toggle]);
  return { expanded, toggle };
}

function CanonicalActivityDock({ onInspect, commandPaletteOpen = false }: DockProps) {
  const [jobs, setJobs] = useState<Array<SourceJobDto & { name: string }>>([]);
  const [message, setMessage] = useState("正在读取正典任务…");
  const { expanded, toggle } = useDockExpansion(commandPaletteOpen);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let alive = true;
    const changed = () => setRefresh(value => value + 1);
    window.addEventListener("archeaxis-job-changed", changed);
    coreCommand<{ sources: SourceDto[] }>("sources_list").then(async ({ sources }) => {
      let capped = false;
      const results: Array<Array<SourceJobDto & { name: string }>> = [];
      for (const source of sources.slice(0, 20)) {
        if (!alive) return;
        const result = await coreCommand<SourceJobsDto>("source_jobs", { source_id: source.source_id });
        if (result.source_id !== source.source_id || result.jobs.some(job => job.input_ref !== source.source_id)) throw new Error("source jobs identity mismatch");
        capped ||= result.jobs_capped;
        results.push(result.jobs.map(job => ({ ...job, name: source.original_name })));
      }
      if (!alive) return;
      const rows = results.flat().sort((a, b) => (b.completed_at ?? b.created_at).localeCompare(a.completed_at ?? a.created_at));
      setJobs(rows.slice(0, 5));
      setMessage(`前 ${Math.min(sources.length, 20)} 个原件的正典任务：${rows.length}${capped ? "（部分原件最多显示 50 条）" : ""}`);
    }).catch(() => { if (alive) { setJobs([]); setMessage("正典任务读取未完成，请刷新重试。"); } });
    return () => { alive = false; window.removeEventListener("archeaxis-job-changed", changed); };
  }, [refresh]);
  return <footer id="activity-dock" className="activity-dock" aria-label="活动坞">
    <div className="activity-dock-summary"><span className="activity-dock-indicator" aria-hidden="true" /><span className="activity-dock-item">{message}</span><button type="button" onClick={() => setRefresh(value => value + 1)}>刷新任务</button><button type="button" aria-label={expanded ? "折叠活动坞" : "展开活动坞"} aria-expanded={expanded} title="展开/收起活动回执（Ctrl+Alt+J）" aria-keyshortcuts="Control+Alt+J" onClick={toggle}>{expanded ? "⌄" : "⌃"}</button></div>
    {expanded ? <div className="activity-dock-body">{jobs.map(job => <span className="activity-dock-item" key={job.job_id}>{job.name} · {stateLabel(job.state)} <button type="button" onClick={() => onInspect?.({ title: job.name, source: "Rust Core 任务记录", lifecycle: stateLabel(job.state), updatedAt: job.completed_at ?? job.created_at, detail: `任务 ${job.job_id}；尝试 ${job.attempt ?? "尚未执行"}${job.error ? "；存在处理错误，请在资料页面查看错误与重试" : ""}` })}>查看活动详情</button></span>)}<span className="activity-dock-item">处理成功不等同识别核验或专业依据已确认。</span></div> : null}
  </footer>;
}

// Bottom activity dock: always projects durable Job/Outbox state. It never
// labels arbitrary controls as completed work.
export function ActivityDock({ onInspect, commandPaletteOpen = false }: DockProps) {
  return window.__TAURI__?.core?.invoke ? <CanonicalActivityDock onInspect={onInspect} commandPaletteOpen={commandPaletteOpen} /> : <LegacyActivityDock onInspect={onInspect} commandPaletteOpen={commandPaletteOpen} />;
}

function LegacyActivityDock({ onInspect, commandPaletteOpen = false }: DockProps) {
  const [items, setItems] = useState<ActivityItemDto[]>([]);
  const [summary, setSummary] = useState("正在读取活动…");
  const [delivery, setDelivery] = useState("投递状态：读取中");
  const { expanded, toggle } = useDockExpansion(commandPaletteOpen);

  async function refresh() {
    const [activity, currentDelivery] = await Promise.all([getActivity(5), getDelivery()]);
    setItems(activity.items);
    setSummary(activity.items.length === 0 ? "暂无持久化活动" : `最近活动：${activity.items.length}`);
    const failed = currentDelivery.summary.outbox.failed ?? 0;
    setDelivery(currentDelivery.summary.jobs === 0
      ? "投递状态：暂无记录"
      : failed > 0 ? `投递状态：失败 ${failed}` : "投递状态：可用");
  }

  useEffect(() => {
    let alive = true;
    refresh()
      .then(() => { if (!alive) return; })
      .catch((error: Error) => {
        if (!alive) return;
        setSummary(`活动不可用：${userErrorMessage(error.message)}`);
        setDelivery("投递状态：不可用");
      });
    return () => { alive = false; };
  }, []);

  async function operate(action: () => Promise<{ status: string }>) {
    let result: { status: string };
    try {
      result = await action();
    } catch (error) {
      setDelivery(`投递状态：${userErrorMessage(error instanceof Error ? error.message : error)}`);
      return;
    }
    const verdict = stateLabel(result.status);
    setDelivery(`投递状态：${verdict}`);
    try {
      await refresh();
      setDelivery(`投递状态：${verdict}`);
    } catch {
      setDelivery(`投递状态：${verdict}；读回暂不可用`);
    }
  }

  async function inspect(item: ActivityItemDto) {
    try {
      const detail = await getActivityObject(item.public_ref);
      onInspect?.({
        title: detail.label,
        source: detail.source ?? "工作台",
        lifecycle: stateLabel(detail.state),
        updatedAt: detail.updated_at,
        detail: "活动详情已从本地回读",
      });
    } catch (error) {
      setSummary(`活动详情不可用：${userErrorMessage(error instanceof Error ? error.message : error)}`);
    }
  }

  return (
    <footer id="activity-dock" className="activity-dock" aria-label="活动坞">
      <div className="activity-dock-summary">
        <span className="activity-dock-indicator" aria-hidden="true" />
        <span className="activity-dock-item">{summary}</span>
        <span className="activity-dock-item">{delivery}</span>
        <button type="button" aria-label={expanded ? "折叠活动坞" : "展开活动坞"} aria-expanded={expanded} title="展开/收起活动回执（Ctrl+Alt+J）" aria-keyshortcuts="Control+Alt+J" onClick={toggle}>{expanded ? "⌄" : "⌃"}</button>
      </div>
      {expanded ? <div className="activity-dock-body">
        {items.slice(0, 3).map((item) => <span className="activity-dock-item" key={item.public_ref}>{item.label} · {stateLabel(item.state)} <button type="button" onClick={() => void inspect(item)}>查看活动详情</button></span>)}
        <span className="activity-dock-item">来源：任务 / 投递 / 回执</span>
        <button type="button" onClick={() => void operate(dispatchDelivery)}>投递下一条</button>
        <button type="button" onClick={() => void operate(retryFailedDelivery)}>重试失败投递</button>
      </div> : null}
    </footer>
  );
}
