import { runtimeJSON, runtimePostJSON } from "./workspace";

// Learner-state API client (Tutor-MCP-inspired): neutral learner state.
// Provider-agnostic — the learner model belongs to ArcheAxis, not any LLM.
export interface MasteryDisplay {
  node_id: string;
  human: { level: string; label: string };
  machine: { level: string; label: string };
  evidence: string;
  action: string;
  delta: number;
}

export interface MasteryResponse {
  card_id: string;
  state: MasteryDisplay;
  signal: Record<string, unknown>;
}

export interface ReviewQueueResponse {
  due_count: number;
  due: unknown[];
}

export interface TeachBackInput {
  record_id: string;
  concept: string;
  restatement: string;
  reference: string;
  key_terms: string[];
}

export interface TeachBackEvaluation {
  accuracy: number;
  coverage: number;
  paraphrase: number;
  organization: number;
  overall: number;
  passes: boolean;
  missing_terms: string[];
  extra_claims: string[];
}

export interface TeachBackResponse {
  record_id: string;
  concept: string;
  evaluation: TeachBackEvaluation;
}

export interface PrincipleHit {
  principle_id: string;
  statement: string;
  category: string;
  confidence: number;
  usage_count: number;
  status: string;
  score: number;
}

export interface PrinciplesResponse {
  count: number;
  principles: PrincipleHit[];
}

export function learningApi(
  baseUrl = "/api/v1/learning",
  fetcher: typeof fetch = fetch,
) {
  async function getJSON<T>(path: string): Promise<T> {
    if (window.__TAURI__?.core?.invoke) return runtimeJSON<T>(`${baseUrl}${path}`);
    const res = await fetcher(`${baseUrl}${path}`);
    if (!res.ok) {
      throw new Error(`${path} -> ${res.status}`);
    }
    return (await res.json()) as T;
  }

  async function postJSON<T>(path: string, body: unknown): Promise<T> {
    if (window.__TAURI__?.core?.invoke) {
      return runtimePostJSON<T>(`${baseUrl}${path}`, body as Record<string, unknown>, "learning");
    }
    const res = await fetcher(`${baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error(`${path} -> ${res.status}`);
    }
    return (await res.json()) as T;
  }

  return {
    reviewQueue: (limit = 20) =>
      getJSON<ReviewQueueResponse>(`/review-queue?limit=${limit}`),
    mastery: (cardId: string) =>
      getJSON<MasteryResponse>(`/mastery/${encodeURIComponent(cardId)}`),
    teachBack: (input: TeachBackInput) =>
      postJSON<TeachBackResponse>("/teach-back", input),
    principles: (query = "", topK = 5) =>
      getJSON<PrinciplesResponse>(
        `/principles?query=${encodeURIComponent(query)}&top_k=${topK}`,
      ),
  };
}

export type LearningApi = ReturnType<typeof learningApi>;

// ── loop gap closure endpoints (quiz / path / tick / review outcome) ──

export interface QuizItem {
  item_id: string;
  concept: string;
  kind: "recall" | "mcq";
  prompt: string;
  answer: string;
  distractors: string[];
}

export interface QuizResponse {
  concept: string;
  items: QuizItem[];
}

export interface PathStep {
  concept: string;
  kind: string;
  reason: string;
}

export interface PathResponse {
  goal: string;
  steps: PathStep[];
}

export interface TickResponse {
  node_id: string;
  action: string;
  state: Record<string, unknown>;
  payload: Record<string, unknown>;
}

export interface ReviewOutcomeInput {
  card_id: string;
  command_id: string;
  quality: number;
  mistake_detail?: string;
}

export interface ReviewOutcomeResponse {
  review_id: string;
  mistake_id: string | null;
  mastered: boolean;
  review_count: number;
  machine_knowledge_created: boolean;
}

export interface LearningApiExt extends ReturnType<typeof learningApi> {
  quiz: (input: { concept: string; reference: string; keyTerms?: string[]; otherConcepts?: string[] }) => Promise<QuizResponse>;
  learningPath: (input: { goal: string; graph: { nodes: string[]; edges: string[][] }; masteryMap?: Record<string, number> }) => Promise<PathResponse>;
  tick: (input: Record<string, unknown>) => Promise<TickResponse>;
  reviewOutcome: (input: ReviewOutcomeInput) => Promise<ReviewOutcomeResponse>;
}

export function learningApiExt(
  baseUrl = "/api/v1/learning",
  fetcher: typeof fetch = fetch,
): LearningApiExt {
  const base = learningApi(baseUrl, fetcher);
  async function getJSON<T>(path: string): Promise<T> {
    if (window.__TAURI__?.core?.invoke) return runtimeJSON<T>(`${baseUrl}${path}`);
    const res = await fetcher(`${baseUrl}${path}`);
    if (!res.ok) throw new Error(`${path} -> ${res.status}`);
    return (await res.json()) as T;
  }
  async function postJSON<T>(path: string, body: unknown): Promise<T> {
    if (window.__TAURI__?.core?.invoke) {
      return runtimePostJSON<T>(`${baseUrl}${path}`, body as Record<string, unknown>, "learning");
    }
    const res = await fetcher(`${baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`${path} -> ${res.status}`);
    return (await res.json()) as T;
  }
  return {
    ...base,
    quiz: ({ concept, reference, keyTerms, otherConcepts }) => {
      const params = new URLSearchParams({ concept, reference });
      if (keyTerms?.length) params.set("key_terms", keyTerms.join(","));
      if (otherConcepts?.length) params.set("other_concepts", otherConcepts.join(","));
      return getJSON<QuizResponse>(`/quiz?${params.toString()}`);
    },
    learningPath: (input) => postJSON<PathResponse>("/learning-path", input),
    tick: (input) => postJSON<TickResponse>("/tick", input),
    reviewOutcome: (input) => postJSON<ReviewOutcomeResponse>("/review-outcome", input),
  };
}
