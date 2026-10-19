import {conversation, conversationConsumer, mergeConversationEvents} from "../api/conversation";
import type {ConversationSessionDto, ConversationSummaryDto, ConversationRequestDto, ConversationPreviewDto, ConversationReceiptDto, ConversationStatusDto, MaterialContextDto, MaterialSelectionDto} from "../api/generated/conversation";
import type {ModelLane} from "../api/generated/model-configuration-contract";
import {resolveProductModel, ModelBindingRequiredError} from "../runtime/modelBinding";
import {modelTimeoutMessage} from "../api/machineFailure";

type Result = ConversationReceiptDto | ConversationStatusDto;
function terminalMessage(result: Result | null | undefined, fallback: string): string {
  if(result && "state" in result && result.state==="failed") return modelTimeoutMessage(result.reason_code) ?? "模型执行失败，未生成可用回答；原请求已保留。";
  if(result && "state" in result && result.state==="cancelled") return "请求已取消，没有生成可用回答；原请求已保留。";
  return fallback;
}
export type CompanionContext = {material?: MaterialContextDto; selection?: MaterialSelectionDto};
export type CompanionSnapshot = {
  sessions: ConversationSummaryDto[]; current: ConversationSessionDto | null;
  question: string; lane: ModelLane; preview: ConversationPreviewDto | null;
  result: Result | null; message: string; busy: boolean; paused: boolean;
  active: ConversationRequestDto | null; outstandingId: string | null;
  confirmedReceipts: ConversationReceiptDto[];
};

/** App-owned presentation state. Core alone owns durable history and request outcomes. */
export class CompanionSession {
  private value: CompanionSnapshot = {sessions: [], current: null, question: "", lane: "fast", preview: null, result: null, message: "", busy: false, paused: false, active: null, outstandingId: null, confirmedReceipts: []};
  private listeners = new Set<() => void>();
  private generation = 0;
  private initialized = false;
  private catalogEpoch = 0;
  private catalogFlight: Promise<void> | null = null;
  private frozen: ConversationRequestDto | null = null;
  private pending = new Map<string, string>();
  private terminalReceipts = new Map<string, ConversationReceiptDto>();
  private previewOwner: {view: object; key: string} | null = null;
  getSnapshot = () => this.value;
  subscribe = (listener: () => void) => {this.listeners.add(listener); return () => {this.listeners.delete(listener);};};
  private publish(patch: Partial<CompanionSnapshot>) {
    this.value = {...this.value, ...patch};
    // 已核对的回执独立展示；不伪造或改写 Core 的历史事件。
    this.value.confirmedReceipts = [...this.terminalReceipts.values()].filter(r => r.session_id === this.value.current?.session_id);
    this.value.outstandingId = this.value.current ? this.pending.get(this.value.current.session_id) ?? this.value.current.requests.find(r => r.state === "EXECUTING" && !this.terminalReceipts.has(`${this.value.current!.session_id}:${r.request_id}`))?.request_id ?? null : null;
    for (const listener of this.listeners) listener();
  }
  private begin() {if (this.value.busy || this.value.paused) return null; this.publish({busy: true}); return ++this.generation;}
  private valid(generation: number) {return generation === this.generation && !this.value.paused;}
  private finish(generation: number) {if (this.valid(generation)) this.publish({busy: false});}
  private clearPreview() {this.frozen = null; this.previewOwner = null; this.publish({preview: null});}
  pause() {
    ++this.catalogEpoch; this.initialized = false;
    this.detach();
  }
  detach() {
    ++this.generation;
    // Preserve admitted request IDs even when transport identity becomes uncertain.
    this.publish({paused: true, busy: false, active: null, message: "工作区身份待核对；会话与原请求保留，暂不发送。"});
  }
  resume() {if (this.value.paused) this.publish({paused: false, message: "工作区已核对；未确认的提问可继续查询。"});}
  async refreshCatalog() {
    if (this.value.paused || this.catalogFlight) return;
    this.initialized = false;
    await this.initialize();
  }
  async initialize() {
    if (this.initialized || this.value.paused) return;
    if (this.catalogFlight) return this.catalogFlight;
    this.initialized = true;
    const flight = this.readCatalog(); this.catalogFlight = flight;
    try {await flight;} finally {if (this.catalogFlight === flight) this.catalogFlight = null;}
  }
  private async readCatalog() {
    const epoch = this.catalogEpoch;
    try {
      const result = await conversation.history({session_id: null, after_sequence: 0, limit: 64});
      if (epoch === this.catalogEpoch && !this.value.paused && "sessions" in result) {
        const sessions = [...this.value.sessions, ...result.sessions];
        this.publish({sessions: sessions.filter((s, i) => sessions.findIndex(other => other.session_id === s.session_id) === i)});
      }
    } catch {if (epoch === this.catalogEpoch && !this.value.paused) {this.initialized = false; this.publish({message: "会话目录暂未确认，请重读或创建。"});}}
  }
  contextChanged(view: object, key: string) {
    if (this.previewOwner?.view !== view || this.previewOwner.key === key || this.pending.get(this.frozen?.session_id ?? "") === this.frozen?.request_id && this.frozen !== null) return;
    ++this.generation;
    this.clearPreview();
    this.publish({busy: false});
  }
  setQuestion(question: string) {if (this.value.busy || this.value.paused) return; this.clearPreview(); this.publish({question});}
  setLane(lane: ModelLane) {if (this.value.busy || this.value.paused || this.uncertain()) return; this.clearPreview(); this.publish({lane});}
  terminal() {
    const {result, current, outstandingId} = this.value;
    const confirmed = current && outstandingId ? this.terminalReceipts.get(`${current.session_id}:${outstandingId}`) : null;
    return confirmed?.state ?? (result && "state" in result && ["completed", "failed", "cancelled"].includes(result.state) && result.session_id === current?.session_id && (!outstandingId || result.request_id === outstandingId) ? result.state : null);
  }
  private record(result: Result) {
    if ("state" in result && ["completed", "failed", "cancelled"].includes(result.state)) this.terminalReceipts.set(`${result.session_id}:${result.request_id}`, result);
  }
  private recordHistory(history: ConversationSessionDto) {
    for (const request of history.requests) if (request.receipt && request.receipt.session_id === history.session_id && request.receipt.request_id === request.request_id) this.record(request.receipt);
  }
  private async syncHistory(sessionId: string, generation: number) {
    const history = await conversation.history({session_id: sessionId, after_sequence: 0, limit: 64});
    if (!this.valid(generation) || this.value.current?.session_id !== sessionId) return;
    if (!("events" in history)) throw Error("history identity");
    const events = mergeConversationEvents(this.value.current.events, history.events, sessionId);
    this.recordHistory(history);
    this.publish({current: {...history, events}});
  }
  private async syncConfirmedHistory(sessionId: string, generation: number, message: string) {
    try {
      await this.syncHistory(sessionId, generation);
      if (this.valid(generation)) this.publish({message});
    } catch {
      // 推理终态和历史传输是两个事实；历史失败不能把终态降回 UNKNOWN。
      if (this.valid(generation)) this.publish({message: `${terminalMessage(this.value.result,"原请求回执已核对；")}历史暂未同步，请重读历史。`});
    }
  }
  uncertain() {return Boolean(this.value.outstandingId && !this.terminal() && !(this.value.busy && this.value.active?.request_id === this.value.outstandingId));}
  async load(id: string) {
    if (!id) return;
    const generation = this.begin(); if (generation === null) return;
    const previousId = this.value.current?.session_id;
    this.clearPreview();
    try {
      const result = await conversation.history({session_id: id, after_sequence: 0, limit: 64});
      if (!this.valid(generation)) return;
      if (!("events" in result) || result.session_id !== id) throw Error("history identity");
      const pendingId = this.pending.get(id);
      const receipt = result.requests.find(r => r.request_id === pendingId)?.receipt;
      this.recordHistory(result);
      this.publish({current: result, result: receipt ?? (id === previousId ? this.value.result : null), message: terminalMessage(receipt ?? result.requests.at(-1)?.receipt, "历史已读回；未确认的提问请继续查询。")});
    } catch {if (this.valid(generation)) this.publish({message: "会话历史未确认。"});}
    finally {this.finish(generation);}
  }
  async more() {
    const current = this.value.current; if (!current) return;
    const generation = this.begin(); if (generation === null) return;
    try {
      const history = await conversation.history({session_id: current.session_id, after_sequence: current.events.at(-1)?.sequence ?? 0, limit: 64});
      if (this.valid(generation) && "events" in history) {this.recordHistory(history); this.publish({current: {...history, events: mergeConversationEvents(current.events, history.events, current.session_id)}});}
    } catch {if (this.valid(generation)) this.publish({message: "后续事件未确认，已读历史保留。"});}
    finally {this.finish(generation);}
  }
  async create() {
    const generation = this.begin(); if (generation === null) return;
    try {
      const current = await conversation.create({session_id: crypto.randomUUID(), title: "本地陪伴会话", consumer: conversationConsumer});
      if (!this.valid(generation)) return;
      this.clearPreview();
      this.publish({current, result: null, sessions: [{session_id: current.session_id, title: current.title, last_sequence: current.last_sequence, consumer: conversationConsumer}, ...this.value.sessions]});
    } catch {if (this.valid(generation)) this.publish({message: "会话创建未确认。"});}
    finally {this.finish(generation);}
  }
  async prepare(context: CompanionContext, view: object) {
    const {current, question, lane} = this.value;
    if (!current || !question.trim() || this.uncertain()) return;
    const generation = this.begin(); if (generation === null) return;
    this.clearPreview(); this.previewOwner = {view, key: JSON.stringify(context)};
    try {
      const body: ConversationRequestDto = {session_id: current.session_id, request_id: crypto.randomUUID(), purpose: context.material ? "material_learning" : "companion", material: context.material ?? null, selection: context.selection ?? null, question, model: null, max_tokens: 2048, timeout_s: 120, preview: true, confirmed_plan_sha256: null};
      const resolved = await resolveProductModel(context.material ? "material" : "companion", lane);
      if (!this.valid(generation)) return;
      if (resolved) {body.model_configuration = resolved; body.model = resolved.profile.model; body.max_tokens = Math.min(body.max_tokens, resolved.profile.max_tokens); body.timeout_s = resolved.profile.timeout_s;}
      const preview = await conversation.preview(body);
      if (!this.valid(generation)) return;
      this.frozen = {...body, preview: false, confirmed_plan_sha256: preview.plan_sha256};
      // A completed previous request no longer owns the next explicit preview.
      this.pending.delete(current.session_id);
      this.publish({preview, result: null, message: "核对当前会话、问题、历史上下文和本地目的地后确认。"});
    } catch (error) {if (this.valid(generation)) this.publish({message: error instanceof ModelBindingRequiredError ? error.message : "请求预览失败：可能有未确认的旧请求或材料版本不符。"});}
    finally {this.finish(generation);}
  }
  async execute() {
    const body = this.frozen;
    if (!body || this.pending.get(body.session_id) === body.request_id || this.uncertain()) return;
    const generation = this.begin(); if (generation === null) return;
    this.pending.set(body.session_id, body.request_id);
    this.publish({active: body});
    try {
      const result = await conversation.execute(body);
      if (!this.valid(generation)) return;
      this.record(result);
      this.publish({result});
      if ("state" in result) await this.syncConfirmedHistory(body.session_id, generation, terminalMessage(result,"回执与历史已读回；回答仍需你判断。"));
      else this.publish({message: "执行结果尚未确认，请查询原请求。"});
    } catch {if (this.valid(generation)) this.publish({message: "执行结果尚未确认，请查询原请求。"});}
    finally {if (this.valid(generation)) this.publish({active: null}); this.finish(generation);}
  }
  async readRequest(requestId: string) {
    const current = this.value.current; if (!current) return;
    const generation = this.begin(); if (generation === null) return;
    try {
      const result = await conversation.status({session_id: current.session_id, request_id: requestId});
      if (!this.valid(generation)) return;
      this.record(result); this.publish({result, message: "仅查询原请求，不再次推理。"});
      if ("state" in result) await this.syncConfirmedHistory(current.session_id, generation, terminalMessage(result,"原请求回执与历史已读回；回答仍需你判断。"));
    } catch {if (this.valid(generation)) this.publish({message: "请求状态未确认。"});}
    finally {this.finish(generation);}
  }
  async cancel() {
    const body = this.value.active; if (!body || this.value.paused) return;
    const generation = this.generation;
    try {
      const result = await conversation.cancel(body);
      if (this.valid(generation)) this.publish({message: result.cancel_requested ? "已申请取消，仍在等待实际结果。" : "该请求已不接受取消，请读回终态。"});
    } catch {if (this.valid(generation)) this.publish({message: "取消确认失败，请查询同一请求。"});}
  }
}
