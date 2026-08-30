import { useEffect, useState } from "react";
import { DataError, Loading } from "../components/RealData";
import { getHome, type ActivityItemDto } from "../api/workspace";
import { userErrorMessage } from "../presentation/labels";
import type { SpaceId } from "./spaces";

interface HomeDto {
  release?: Record<string, unknown>;
  counts?: Record<string, unknown>;
  capabilities?: Record<string, unknown>;
  components?: Record<string, unknown>;
  recent_activity?: ActivityItemDto[];
}

const LABELS: Record<string, string> = {
  version: "版本",
  status: "状态",
  public: "公开状态",
  jobs: "任务",
  evidence_anchors: "证据锚点",
  research: "研究候选",
  outbox: "待投递记录",
  learning: "学习产物",
  machine_knowledge: "机器知识",
  api: "本地接口",
  database: "本地数据库",
  worker: "异步处理器",
  outbox_dispatcher: "投递处理器",
  server_sent_events: "实时事件流",
  source_archive: "原件档案",
  governed_learning: "受治理学习",
  local_url_file_github_intake: "本地、网页与代码仓库导入",
  workspace_job_outbox_receipts: "任务、投递与回执",
  strict_governance_readback: "严格治理读回",
  audio_track_and_video_keyframes: "音轨与视频关键帧",
  image_ocr: "图像文字识别",
  asr_transcription: "语音转写",
  asynchronous_worker: "异步处理器",
  interactive_job_center: "交互式任务中心",
  postgresql_runtime: "PostgreSQL 运行支持",
  qdrant_runtime: "Qdrant 运行支持",
  public_installer: "公共安装包",
};

const STATES: Record<string, string> = {
  available: "可用",
  unavailable: "不可用",
  completed: "已完成",
  succeeded: "已完成",
  pending: "待处理",
  failed: "失败",
  unreleased: "源码未发布",
  released: "已发布",
  candidate: "候选",
  approved: "已批准",
  dependency_required: "需要依赖",
  not_implemented: "尚未实现",
  lease_fenced: "租约保护",
  not_connected: "未连接",
  ready_for_review: "待复核",
  deprecated: "已弃用",
  recorded: "已记录",
  true: "是",
  false: "否",
};

function label(key: string) {
  return LABELS[key] ?? "未识别字段";
}

function valueOf(value: unknown, key?: string): string {
  if (typeof value === "string") {
    if (key === "version") return value;
    return STATES[value] ?? "状态未知";
  }
  if (typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "是" : "否";
  if (value && typeof value === "object") {
    const values = Object.values(value as Record<string, unknown>);
    if (values.length && values.every((item) => typeof item === "number")) {
      return String(values.reduce<number>((sum, item) => sum + Number(item), 0));
    }
    return `${values.length} 项`;
  }
  return "未知";
}

function stateClass(value: string): string {
  if (["可用", "已完成", "已发布", "已批准", "是", "已记录"].includes(value)) return "state-ok";
  if (["不可用", "失败", "未连接", "已弃用"].includes(value)) return "state-warn";
  if (["待处理", "候选", "待复核", "需要依赖"].includes(value)) return "state-pending";
  return "";
}

function StatCard({ label: lbl, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{lbl}</span>
      <span className={`stat-value ${stateClass(value)}`}>{value}</span>
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  );
}

export function WorkspaceSpace({ onNavigate }: { onNavigate: (id: SpaceId) => void }) {
  const [home, setHome] = useState<HomeDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getHome()
      .then((result) => { if (alive) setHome(result as HomeDto); })
      .catch((reason: Error) => { if (alive) setError(userErrorMessage(reason.message)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  if (loading) return <Loading label="工作台" />;
  if (error) return <DataError label="工作台" message={error} />;

  const release = home?.release ?? {};
  const counts = home?.counts ?? {};
  const components = home?.components ?? {};
  const activity = home?.recent_activity ?? [];

  return (
    <section className="workspace-page" aria-labelledby="ws-title">
      <header className="ws-header">
        <div>
          <h1 id="ws-title">工作台</h1>
          <p className="ws-subtitle">可信知识工作台 · 版本 {valueOf(release.version, "version")}</p>
        </div>
      </header>

      <div className="ws-quick-actions">
        <button className="ws-action-card" onClick={() => onNavigate("intake")}>
          <span className="ws-action-icon">📥</span>
          <strong>导入资料</strong>
          <small>网页、文件、批量目录</small>
        </button>
        <button className="ws-action-card" onClick={() => onNavigate("library")}>
          <span className="ws-action-icon">📚</span>
          <strong>资料库</strong>
          <small>查看原件与锚点</small>
        </button>
        <button className="ws-action-card" onClick={() => onNavigate("vault")}>
          <span className="ws-action-icon">🔐</span>
          <strong>知识库</strong>
          <small>搜索、编辑、备份</small>
        </button>
        <button className="ws-action-card" onClick={() => onNavigate("settings")}>
          <span className="ws-action-icon">⚙️</span>
          <strong>设置</strong>
          <small>四库路径与工作区</small>
        </button>
      </div>

      <div className="ws-grid">
        <div className="ws-section">
          <h2>系统状态</h2>
          <div className="ws-stats">
            {Object.entries(components).filter(([k]) => k in LABELS).map(([k, v]) => (
              <StatCard key={k} label={label(k)} value={valueOf(v, k)} />
            ))}
          </div>
        </div>

        <div className="ws-section">
          <h2>数据概览</h2>
          <div className="ws-stats">
            {Object.entries(counts).filter(([k]) => k in LABELS).map(([k, v]) => (
              <StatCard key={k} label={label(k)} value={valueOf(v, k)} />
            ))}
          </div>
        </div>

        <div className="ws-section">
          <h2>近期活动</h2>
          {activity.length === 0 ? (
            <p className="ws-empty">暂无活动记录</p>
          ) : (
            <ul className="ws-activity-list">
              {activity.map((item) => (
                <li key={item.public_ref}>
                  <span className="ws-activity-label">{item.label}</span>
                  <span className={`ws-activity-state ${stateClass(valueOf(item.state))}`}>{valueOf(item.state)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
