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

function Ledger({ title, rows }: { title: string; rows: Record<string, unknown> }) {
  const entries = Object.entries(rows).filter(([key]) => key in LABELS);
  return (
    <article className="archive-ledger">
      <header><span>真实读回</span><h3>{title}</h3></header>
      {entries.length === 0 ? <p className="muted">暂无可验证数据</p> : (
        <dl>{entries.slice(0, 6).map(([key, value]) => (
          <div key={key}><dt>{label(key)}</dt><dd>{valueOf(value, key)}</dd></div>
        ))}</dl>
      )}
    </article>
  );
}

export function WorkspaceSpace({ onNavigate }: { onNavigate: (id: SpaceId) => void }) {
  const [status, setStatus] = useState<HomeDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getHome()
      .then((result) => { if (alive) setStatus(result as HomeDto); })
      .catch((reason: Error) => { if (alive) setError(userErrorMessage(reason.message)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  return (
    <section className="space-view workspace-overview" aria-labelledby="workspace-title">
      <div className="archive-page-head" role="group" aria-label="工作台标题">
        <div>
          <span className="archive-eyebrow">可信知识工作台</span>
          <h1 id="workspace-title">工作台总览</h1>
          <p>从同一个可审查工作面继续研究，查看原件、主张、证据、学习与回执。</p>
        </div>
        <span className="truth-chip">真实本地读回</span>
      </div>

      <section className="workbench-hero">
        <div className="hero-ledger">
          <span className="archive-eyebrow">研究台账 · 当前上下文</span>
          <h2>原件、主张与证据，留在同一个可审查的工作面。</h2>
          <p>每个对象都能回到来源、版本和操作回执；未知状态不会被替换成零或伪进度。</p>
          <div className="evidence-flow" aria-label="证据关系">
            <span>原件</span><i>→</i><span>转换块</span><i>→</i><span>主张</span><i>→</i><span>证据束</span>
          </div>
        </div>
        <aside className="next-actions" aria-label="下一步">
          <span className="archive-eyebrow">下一步</span>
          <button className="next-action" type="button" aria-label="查看原件与锚点" onClick={() => onNavigate("library")}><span>01</span><div><strong>查看原件与锚点</strong><small>阅读、搜索和安全回写。</small></div></button>
          <button className="next-action" type="button" aria-label="检查证据生命周期" onClick={() => onNavigate("evidence")}><span>02</span><div><strong>检查证据生命周期</strong><small>支持、反驳、背景与适用范围。</small></div></button>
          <a className="next-action" href="#activity-dock" aria-label="处理任务与回执"><span>03</span><div><strong>处理任务与回执</strong><small>失败保留原件，可恢复重试。</small></div></a>
        </aside>
      </section>

      {loading ? <Loading label="工作台" /> : error ? <DataError label="工作台" message={error} /> : (
        <section className="archive-columns" aria-label="工作区真实状态">
          <Ledger title="发布状态" rows={status?.release ?? {}} />
          <Ledger title="真实计数" rows={status?.counts ?? {}} />
          <Ledger title="组件状态" rows={status?.components ?? {}} />
          <article className="archive-ledger">
            <header><span>治理边界</span><h3>可用能力</h3></header>
            {Object.keys(status?.capabilities ?? {}).length === 0 ? <p className="muted">暂无能力状态</p> : (
              <ul>{Object.entries(status?.capabilities ?? {}).filter(([capability]) => capability in LABELS).map(([capability, state]) => (
                <li key={capability}><span>{label(capability)}</span><strong>{valueOf(state, capability)}</strong></li>
              ))}</ul>
            )}
          </article>
          <article className="archive-ledger">
            <header><span>操作回执</span><h3>近期活动</h3></header>
            {(status?.recent_activity ?? []).length === 0 ? <p className="muted">暂无持久化活动</p> : (
              <ul>{status?.recent_activity?.map((item) => (
                <li key={item.public_ref}><span>{item.label}</span><strong>{valueOf(item.state)}</strong></li>
              ))}</ul>
            )}
          </article>
        </section>
      )}
    </section>
  );
}
