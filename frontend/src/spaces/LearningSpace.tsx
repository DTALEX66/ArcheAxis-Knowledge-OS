// Learning space — Human Learning Vault (absorbs DeepTutor workspace tabs,
// Studyield Teach-Back, FSRS review queue and OpenTutor mastery views).
// Learner state is provider-agnostic (Tutor-MCP pattern): the UI talks only
// to /api/v1/learning/* and never to an LLM directly.
import { useEffect, useState } from "react";
import {
  learningApiExt,
  type DueCard,
  type LearningApiExt,
  type MasteryDisplay,
  type PathStep,
  type QuizItem,
  type TeachBackInput,
} from "../api/learning";
import { userErrorMessage } from "../presentation/labels";

type Tab = "review" | "mastery" | "teachback" | "quiz" | "path";

const TABS: readonly { id: Tab; label: string }[] = [
  { id: "review", label: "复习队列" },
  { id: "mastery", label: "掌握度" },
  { id: "teachback", label: "复述检验" },
  { id: "quiz", label: "练习测验" },
  { id: "path", label: "学习路径" },
];

const ACTION_LABELS: Record<string, string> = {
  teach_human: "机器证据更强 → 引导学习",
  distill_human: "人类证据更强 → 形成候选",
  collaborate: "双方已掌握 → 协作实践",
  learn_first: "双方未掌握 → 先学习",
  review_evidence: "证据过时 → 先核验",
};

function dueCardLabel(card: DueCard, index: number): string {
  if (!card.due_local) return `到期卡片 ${index + 1}`;
  const due = new Date(card.due_local);
  return Number.isNaN(due.getTime())
    ? `到期卡片 ${index + 1}`
    : `到期卡片 ${index + 1} · ${due.toLocaleString("zh-CN")}`;
}

function ReviewQueueView({ api }: { api: LearningApiExt }) {
  const [dueCount, setDueCount] = useState<number | null>(null);
  const [dueCards, setDueCards] = useState<DueCard[]>([]);
  const [cardId, setCardId] = useState("");
  const [quality, setQuality] = useState("3");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .reviewQueue(20)
      .then((r) => {
        if (alive) {
          setDueCount(r.due_count);
          setDueCards(r.due);
          setCardId((current) => current || r.due[0]?.card_id || "");
        }
      })
      .catch((e: unknown) => {
        if (alive) setError(userErrorMessage(e instanceof Error ? e.message : e));
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
            setSubmitted(`已提交复习结果（质量 ${quality}）`);
          } catch (err) {
            setError(userErrorMessage(err instanceof Error ? err.message : err));
          }
        }}
      >
        <label htmlFor="rv-card">待复习卡片</label>
        <select id="rv-card" value={cardId} disabled={dueCards.length === 0} onChange={(e) => setCardId(e.target.value)}>
          {dueCards.length === 0 ? <option value="">暂无到期卡片</option> : null}
          {dueCards.map((card, index) => <option key={card.card_id} value={card.card_id}>{dueCardLabel(card, index)}</option>)}
        </select>
        <label htmlFor="rv-quality">复习质量（0–5）</label>
        <input id="rv-quality" type="number" min={0} max={5} value={quality} onChange={(e) => setQuality(e.target.value)} />
        <button type="submit" disabled={!cardId.trim()}>提交复习结果</button>
      </form>
      {submitted ? <p className="space-hint">{submitted}</p> : null}
    </section>
  );
}

function MasteryView({ api }: { api: LearningApiExt }) {
  const [cardId, setCardId] = useState("");
  const [dueCards, setDueCards] = useState<DueCard[]>([]);
  const [state, setState] = useState<MasteryDisplay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    api.reviewQueue(200)
      .then((result) => {
        if (!alive) return;
        setDueCards(result.due);
        setCardId(result.due[0]?.card_id ?? "");
      })
      .catch((reason: unknown) => {
        if (alive) setError(userErrorMessage(reason instanceof Error ? reason.message : reason));
      });
    return () => { alive = false; };
  }, [api]);

  async function load() {
    if (!cardId.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.mastery(cardId.trim());
      setState(r.state);
    } catch (e: unknown) {
      setError(userErrorMessage(e instanceof Error ? e.message : e));
      setState(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="掌握度" className="learning-panel">
      <h3>人类、机器与证据三轴掌握度</h3>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void load();
        }}
      >
        <label htmlFor="mastery-card">学习卡片</label>
        <select
          id="mastery-card"
          value={cardId}
          disabled={dueCards.length === 0}
          onChange={(e) => setCardId(e.target.value)}
        >
          {dueCards.length === 0 ? <option value="">暂无到期卡片</option> : null}
          {dueCards.map((card, index) => <option key={card.card_id} value={card.card_id}>{dueCardLabel(card, index)}</option>)}
        </select>
        <button type="submit" disabled={busy || !cardId.trim()}>
          {busy ? "查询中…" : "查询"}
        </button>
      </form>
      {error ? <p className="space-hint">查询失败：{error}</p> : null}
      {state ? (
        <dl className="mastery-bars">
          <div>
            <dt>人类掌握</dt>
            <dd aria-label={`人类掌握 ${state.human.level}`}>
              <span className="bar" style={{ width: `${levelWidth(state.human.level, "human")}%` }} />
              {state.human.level} · {state.human.label}
            </dd>
          </div>
          <div>
            <dt>机器掌握</dt>
            <dd aria-label={`机器掌握 ${state.machine.level}`}>
              <span className="bar" style={{ width: `${levelWidth(state.machine.level, "machine")}%` }} />
              {state.machine.level} · {state.machine.label}
            </dd>
          </div>
          <div>
            <dt>证据状态</dt>
            <dd aria-label={`证据状态 ${state.evidence}`}>{state.evidence}</dd>
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
      setError(userErrorMessage(e instanceof Error ? e.message : e));
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="复述检验" className="learning-panel">
      <h3>复述检验（你讲给机器，系统检查理解程度）</h3>
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
        <dl className="teachback-result" aria-label="复述检验结果">
          <div><dt>总体</dt><dd>{Math.round(result.evaluation.overall * 100)}% {result.evaluation.passes ? "已达标" : "未达标"}</dd></div>
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
  const [concept, setConcept] = useState("");
  const [reference, setReference] = useState("");
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!concept.trim() || !reference.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.quiz({ concept: concept.trim(), reference: reference.trim() });
      setItems(r.items);
      setSelected({});
      setFeedback({});
    } catch (reason) {
      setError(userErrorMessage(reason instanceof Error ? reason.message : reason));
      setItems(null);
    } finally {
      setBusy(false);
    }
  }

  function answer(item: QuizItem, value: string) {
    setSelected({ ...selected, [item.item_id]: value });
    setFeedback({
      ...feedback,
      [item.item_id]: value === item.answer ? "正确" : `错误，期望：${item.answer}`,
    });
  }

  return (
    <section aria-label="练习测验" className="learning-panel">
      <h3>练习测验（回忆 / 选择题）</h3>
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
        <button type="submit" disabled={busy || !concept.trim() || !reference.trim()}>生成测验</button>
      </form>
      {error ? <p className="space-hint">生成失败：{error}</p> : null}
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
  const [goal, setGoal] = useState("");
  const [prerequisites, setPrerequisites] = useState("");
  const [steps, setSteps] = useState<PathStep[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function build() {
    const requestedGoal = goal.trim();
    if (!requestedGoal) return;
    setBusy(true);
    setError(null);
    try {
      const nodes = prerequisites.split(",").map((item) => item.trim()).filter(Boolean);
      if (!nodes.includes(requestedGoal)) nodes.push(requestedGoal);
      const edges = nodes.slice(0, -1).map((node, index) => [node, nodes[index + 1]]);
      const r = await api.learningPath({ goal: requestedGoal, graph: { nodes, edges } });
      setSteps(r.steps);
    } catch (e) {
      setError(userErrorMessage(e instanceof Error ? e.message : e));
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
        <label htmlFor="path-prerequisites">先修概念（用逗号分隔）</label>
        <input id="path-prerequisites" value={prerequisites} onChange={(e) => setPrerequisites(e.target.value)} />
        <button type="submit" disabled={busy || !goal.trim()}>生成路径</button>
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
    <section className="space-page" aria-labelledby="space-learning">
      <h1 id="space-learning" className="space-page-title">学习</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        人类学习库：FSRS 复习、三轴掌握度与复述理解检验。
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
