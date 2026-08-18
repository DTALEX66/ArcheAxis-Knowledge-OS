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
    const res = await fetcher(`${baseUrl}${path}`);
    if (!res.ok) {
      throw new Error(`${path} -> ${res.status}`);
    }
    return (await res.json()) as T;
  }

  async function postJSON<T>(path: string, body: unknown): Promise<T> {
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
