import { useEffect, useState } from "react";
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

// Bottom activity dock: always projects durable Job/Outbox state. It never
// labels arbitrary controls as completed work.
export function ActivityDock({ onInspect }: { onInspect?: (target: InspectionTarget) => void }) {
  const [items, setItems] = useState<ActivityItemDto[]>([]);
  const [summary, setSummary] = useState("正在读取活动…");
  const [delivery, setDelivery] = useState("投递状态：读取中");
  const [expanded, setExpanded] = useState(false);

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
        <button type="button" aria-label={expanded ? "折叠活动坞" : "展开活动坞"} aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>{expanded ? "⌄" : "⌃"}</button>
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
