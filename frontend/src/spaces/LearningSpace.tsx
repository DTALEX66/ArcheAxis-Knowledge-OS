// Learning space — Human Learning Vault (absorbs DeepTutor workspace tabs,
// Studyield Teach-Back, FSRS review queue and OpenTutor mastery views).
// Learner state is provider-agnostic (Tutor-MCP pattern): the UI talks only
// to /api/v1/learning/* and never to an LLM directly.
import { useEffect, useState } from "react";
import {
  learningApiExt,
  type LearningApiExt,
  type MasteryDisplay,
  type PathStep,
  type QuizItem,
  type TeachBackInput,
} from "../api/learning";

type Tab = "review" | "mastery" | "teachback" | "quiz" | "path";

const TABS: readonly { id: Tab; label: string }[] = [
  { id: "review", label: "复习队列" },
  { id: "mastery", label: "掌握度" },
  { id: "teachback", label: "Teach-Back" },
  { id: "quiz", label: "练习测验" },
  { id: "path", label: "学习路径" },
];

const ACTION_LABELS: Record<string, string> = {
  teach_human: "AI 强于人 → 教你",
  distill_human: "人强于 AI → 蒸馏你",
  collaborate: "双方已掌握 → 协作实践",
  learn_first: "双方未掌握 → 先学习",
  review_evidence: "证据过时 → 先核验",
};

function ReviewQueueView({ api }: { api: LearningApiExt }) {
  const [dueCount, setDueCount] = useState<number | null>(null);
  const [cardId, setCardId] = useState("");
  const [quality, setQuality] = useState("3");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .reviewQueue(20)
      .then((r) => {
        if (alive) setDueCount(r.due_count);
      })
      .catch((e: unknown) => {
        if (alive) setError(e instanceof Error ? e.message : "加载失败");
      });
    return () => {
      alive = false;
    };
  }, [api]);

  return (
    <section aria-label="复习队列" className="learning-panel">
      <h3>FSRS 复习队列</h3>
      <p className="space-description">
        到期卡片按遗忘曲线排序（FSRS），掌握度来自复习快照而非模型置信度。
      </p>
      {error ? <p className="space-hint">加载失败：{error}</p> : null}
      <p className="space-hint">
        {dueCount === null ? "加载中…" : `当前到期 ${dueCount} 张卡片`}
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await api.reviewOutcome({
              card_id: cardId.trim(),
              command_id: `ui-${Date.now()}`,
              quality: Number(quality),
            });
            setSubmitted(`已提交 ${cardId.trim()} (Q${quality})`);
            setCardId("");
          } catch (err) {
            setError(err instanceof Error ? err.message : "提交失败");
          }
        }}
      >
        <label htmlFor="rv-card">卡片 ID</label>
        <input id="rv-card" value={cardId} onChange={(e) => setCardId(e.target.value)} placeholder="card_id" />
        <label htmlFor="rv-quality">质量 (0-5)</label>
        <input id="rv-quality" type="number" min={0} max={5} value={quality} onChange={(e) => setQuality(e.target.value)} />
        <button type="submit" disabled={!cardId.trim()}>提交复习结果</button>
      </form>
      {submitted ? <p className="space-hint">{submitted}</p> : null}
    </section>
  );
}

function MasteryView({ api }: { api: LearningApiExt }) {
  const [cardId, setCardId] = useState("");
  const [state, setState] = useState<MasteryDisplay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!cardId.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.mastery(cardId.trim());
      setState(r.state);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "查询失败");
      setState(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="掌握度" className="learning-panel">
      <h3>双轴掌握度（Human / Machine / Evidence）</h3>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <label htmlFor="mastery-card">卡片 ID</label>
        <input
          id="mastery-card"
          value={cardId}
          onChange={(e) => setCardId(e.target.value)}
          placeholder="card_id"
        />
        <button type="submit" disabled={busy || !cardId.trim()}>
          {busy ? "查询中…" : "查询"}
        </button>
      </form>
      {error ? <p className="space-hint">查询失败：{error}</p> : null}
      {state ? (
        <dl className="mastery-bars">
          <div>
            <dt>Human</dt>
            <dd aria-label={`human ${state.human.level}`}>
              <span className="bar" style={{ width: `${levelWidth(state.human.level, "human")}%` }} />
              {state.human.level} · {state.human.label}
            </dd>
          </div>
          <div>
            <dt>Machine</dt>
            <dd aria-label={`machine ${state.machine.level}`}>
              <span className="bar" style={{ width: `${levelWidth(state.machine.level, "machine")}%` }} />
              {state.machine.level} · {state.machine.label}
            </dd>
          </div>
          <div>
            <dt>Evidence</dt>
            <dd aria-label={`evidence ${state.evidence}`}>{state.evidence}</dd>
          </div>
          <p className="space-hint">
            建议动作：{ACTION_LABELS[state.action] ?? state.action}（Δ={state.delta}）
          </p>
        </dl>
      ) : null}
    </section>
  );
}

function levelWidth(level: string, axis: "human" | "machine"): number {
  const levels = axis === "human"
    ? ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]
    : ["K0", "K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8"];
  const index = levels.indexOf(level);
  return Math.round(((index + 1) / levels.length) * 100);
}

function TeachBackView({ api }: { api: LearningApiExt }) {
  const [form, setForm] = useState({
    record_id: "",
    concept: "",
    restatement: "",
    reference: "",
    key_terms: "",
  });
  const [result, setResult] = useState<Awaited<ReturnType<LearningApiExt["teachBack"]>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const input: TeachBackInput = {
      record_id: form.record_id || `tb-${Date.now()}`,
      concept: form.concept.trim(),
      restatement: form.restatement.trim(),
      reference: form.reference.trim(),
      key_terms: form.key_terms.split(",").map((t) => t.trim()).filter(Boolean),
    };
    if (!input.concept || !input.restatement || !input.reference) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.teachBack(input));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "提交失败");
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Teach-Back" className="learning-panel">
      <h3>Teach-Back（你讲给 AI，AI 判断你理解了多少）</h3>
      <form onSubmit={submit}>
        <label htmlFor="tb-concept">概念</label>
        <input id="tb-concept" value={form.concept} onChange={(e) => setForm({ ...form, concept: e.target.value })} />
        <label htmlFor="tb-restatement">你的复述</label>
        <textarea id="tb-restatement" rows={3} value={form.restatement} onChange={(e) => setForm({ ...form, restatement: e.target.value })} />
        <label htmlFor="tb-reference">参考答案</label>
        <textarea id="tb-reference" rows={3} value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
        <label htmlFor="tb-terms">关键术语（逗号分隔）</label>
        <input id="tb-terms" value={form.key_terms} onChange={(e) => setForm({ ...form, key_terms: e.target.value })} />
        <button type="submit" disabled={busy}>评分</button>
      </form>
      {error ? <p className="space-hint">提交失败：{error}</p> : null}
      {result ? (
        <dl className="teachback-result" aria-label="teach-back result">
          <div><dt>总体</dt><dd>{Math.round(result.evaluation.overall * 100)}% {result.evaluation.passes ? "✅ 达到 M3-解释" : "未达标"}</dd></div>
          <div><dt>准确</dt><dd>{Math.round(result.evaluation.accuracy * 100)}%</dd></div>
          <div><dt>覆盖</dt><dd>{Math.round(result.evaluation.coverage * 100)}%</dd></div>
          <div><dt>换词</dt><dd>{Math.round(result.evaluation.paraphrase * 100)}%</dd></div>
          {result.evaluation.missing_terms.length > 0 ? (
            <p className="space-hint">遗漏术语：{result.evaluation.missing_terms.join("、")}</p>
          ) : null}
          {result.evaluation.extra_claims.length > 0 ? (
            <p className="space-hint">疑似臆造：{result.evaluation.extra_claims.join("、")}</p>
          ) : null}
        </dl>
      ) : null}
    </section>
  );
}


function QuizPanel({ api }: { api: LearningApiExt }) {
  const [items, setItems] = useState<QuizItem[] | null>(null);
  const [concept, setConcept] = useState("BKT");
  const [reference, setReference] = useState("");
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!concept.trim() || !reference.trim()) return;
    setBusy(true);
    try {
      const r = await api.quiz({ concept: concept.trim(), reference: reference.trim() });
      setItems(r.items);
      setSelected({});
      setFeedback({});
    } finally {
      setBusy(false);
    }
  }

  function answer(item: QuizItem, value: string) {
    setSelected({ ...selected, [item.item_id]: value });
    setFeedback({
      ...feedback,
      [item.item_id]: value === item.answer ? "✓ 正确" : `✗ 期望：${item.answer}`,
    });
  }

  return (
    <section aria-label="练习测验" className="learning-panel">
      <h3>练习测验（recall / MCQ）</h3>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <label htmlFor="qz-concept">概念</label>
        <input id="qz-concept" value={concept} onChange={(e) => setConcept(e.target.value)} />
        <label htmlFor="qz-reference">知识参考</label>
        <textarea id="qz-reference" rows={2} value={reference} onChange={(e) => setReference(e.target.value)} />
        <button type="submit" disabled={busy}>生成测验</button>
      </form>
      {items?.map((item) => (
        <div key={item.item_id} className="quiz-item">
          <p>{item.prompt}</p>
          {item.kind === "mcq" ? (
            <div>
              {[...item.distractors, item.answer].map((opt) => (
                <button key={opt} type="button" onClick={() => answer(item, opt)}>
                  {opt}
                </button>
              ))}
            </div>
          ) : (
            <button type="button" onClick={() => answer(item, item.answer)}>显示答案</button>
          )}
          {feedback[item.item_id] ? <p className="space-hint">{feedback[item.item_id]}</p> : null}
        </div>
      ))}
    </section>
  );
}

function PathView({ api }: { api: LearningApiExt }) {
  const [goal, setGoal] = useState("d");
  const [graph, setGraph] = useState(`{"nodes":["a","b","c","d"],"edges":[["a","b"],["b","c"],["c","d"]]}`);
  const [steps, setSteps] = useState<PathStep[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function build() {
    setBusy(true);
    setError(null);
    try {
      const parsed = JSON.parse(graph) as { nodes: string[]; edges: string[][] };
      const r = await api.learningPath({ goal: goal.trim(), graph: parsed });
      setSteps(r.steps);
    } catch (e) {
      setError(e instanceof Error ? e.message : "路径生成失败");
      setSteps(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="学习路径" className="learning-panel">
      <h3>个性化学习路径（先修图 → 拓扑顺序）</h3>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void build();
        }}
      >
        <label htmlFor="path-goal">目标概念</label>
        <input id="path-goal" value={goal} onChange={(e) => setGoal(e.target.value)} />
        <label htmlFor="path-graph">先修图 JSON</label>
        <textarea id="path-graph" rows={2} value={graph} onChange={(e) => setGraph(e.target.value)} />
        <button type="submit" disabled={busy}>生成路径</button>
      </form>
      {error ? <p className="space-hint">生成失败：{error}</p> : null}
      {steps ? (
        <ol className="learning-path">
          {steps.map((s) => (
            <li key={s.concept}>
              <strong>{s.concept}</strong> · {s.kind} — {s.reason}
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

export function LearningSpace() {
  const [tab, setTab] = useState<Tab>("review");
  const [api] = useState(() => learningApiExt());

  return (
    <section className="space-view" aria-labelledby="space-learning">
      <h2 id="space-learning" className="space-title">Learning</h2>
      <p className="space-description">
        人类学习库（Human Learning Vault）：FSRS 复习、双轴掌握度与 Teach-Back 理解验证。
      </p>
      <nav aria-label="学习功能" className="learning-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            aria-current={tab === t.id ? "page" : undefined}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
      {tab === "review" ? <ReviewQueueView api={api} /> : null}
      {tab === "mastery" ? <MasteryView api={api} /> : null}
      {tab === "teachback" ? <TeachBackView api={api} /> : null}
      {tab === "quiz" ? <QuizPanel api={api} /> : null}
      {tab === "path" ? <PathView api={api} /> : null}
    </section>
  );
}
