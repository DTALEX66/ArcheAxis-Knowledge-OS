import { useEffect, useState } from "react";
import { getActivityJobs } from "../api/runtime";

// Bottom activity dock: always projects durable Job/Outbox state. It never
// labels arbitrary controls as completed work.
export function ActivityDock() {
  const [summary, setSummary] = useState("正在读取活动…");

  useEffect(() => {
    let alive = true;
    getActivityJobs()
      .then((jobs) => {
        if (!alive) return;
        const total = Array.isArray(jobs.jobs) ? jobs.jobs.length : "—";
        setSummary(`真实任务：${total}`);
      })
      .catch((error: Error) => { if (alive) setSummary(`活动不可用：${error.message}`); });
    return () => { alive = false; };
  }, []);

  return (
    <footer className="activity-dock" aria-label="活动坞">
      <span className="activity-dock-item">{summary}</span>
      <span className="activity-dock-item">来源：Job / Outbox / Receipt</span>
    </footer>
  );
}
