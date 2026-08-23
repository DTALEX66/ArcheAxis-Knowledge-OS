import { useEffect, useState } from "react";
import { getActivity, type ActivityItemDto } from "../api/workspace";

// Bottom activity dock: always projects durable Job/Outbox state. It never
// labels arbitrary controls as completed work.
export function ActivityDock() {
  const [items, setItems] = useState<ActivityItemDto[]>([]);
  const [summary, setSummary] = useState("正在读取活动…");

  useEffect(() => {
    let alive = true;
    getActivity(5)
      .then((activity) => {
        if (!alive) return;
        setItems(activity.items);
        setSummary(activity.items.length === 0 ? "暂无持久化活动" : `最近活动：${activity.items.length}`);
      })
      .catch((error: Error) => { if (alive) setSummary(`活动不可用：${error.message}`); });
    return () => { alive = false; };
  }, []);

  return (
    <footer className="activity-dock" aria-label="活动坞">
      <span className="activity-dock-item">{summary}</span>
      {items.slice(0, 3).map((item) => <span className="activity-dock-item" key={item.public_ref}>{item.label} · {item.state}</span>)}
      <span className="activity-dock-item">来源：Job / Outbox / Receipt</span>
    </footer>
  );
}
