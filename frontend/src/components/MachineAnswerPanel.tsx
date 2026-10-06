import { useEffect, useRef, useState } from "react";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "./DiagnosticConsole";

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid response");
  return value as Record<string, unknown>;
}

type ReviewAction = "accepted" | "rejected" | "deprecated";

export function MachineAnswerPanel({ knowledgeId }: { knowledgeId: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Record<string, unknown> | null>(null);
  const [task, setTask] = useState<unknown>(null);
  const [corrected, setCorrected] = useState("");
  const [note, setNote] = useState("");
  const [correctionAuthor, setCorrectionAuthor] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [correction, setCorrection] = useState<Record<string, unknown> | null>(null);
  const [candidate, setCandidate] = useState<Record<string, unknown> | null>(null);
  const [retest, setRetest] = useState<Record<string, unknown> | null>(null);
  const [retestTask, setRetestTask] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const alive = useRef(true);

  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  async function readCandidate(id: string) {
    const value = record(await coreCommand("knowledge_get", { id }));
    if (value.knowledge_id !== id || typeof value.body !== "string" || typeof value.version !== "string" || !value.version
      || !["candidate", "accepted", "rejected", "deprecated"].includes(String(value.status))) {
      throw new Error("invalid correction candidate");
    }
    return value;
  }

  async function ask() {
    if (!question.trim() || busy) return;
    setBusy(true); setAnswer(null); setTask(null); setCorrection(null); setCandidate(null); setRetest(null); setRetestTask(null);
    setCorrected(""); setNote(""); setReviewNote(""); setMessage("正在执行本地机器回答，等待真实回执…");
    try {
      const response = record(await coreCommand("machine_answer", { body: { knowledge_id: knowledgeId, question: question.trim(), max_tokens: 2048, timeout_s: 120 } }));
      const rawAnswer = record(response.answer);
      if (response.knowledge_id !== knowledgeId || typeof response.answer_id !== "string" || typeof response.question !== "string"
        || typeof rawAnswer.answer !== "string" || !rawAnswer.answer.trim() || response.authority !== "candidate") throw new Error("invalid answer receipt");
      const proof = record(await coreCommand("machine_task_get", { task_id: response.answer_id }));
      if (proof.task_id !== response.answer_id || typeof proof.conditions !== "string") throw new Error("invalid task readback");
      const stored = record(JSON.parse(proof.conditions));
      if (stored.answer_id !== response.answer_id || record(stored.answer).answer !== rawAnswer.answer) throw new Error("answer readback mismatch");
      if (alive.current) { setAnswer(response); setTask(proof); setMessage("本地回答已持久化读回。它仍是候选，不是已接受知识或能力评分。"); }
    } catch {
      if (alive.current) setMessage("回答未完成或持久化读回未确认。不会显示推测的成功结果。");
    } finally { if (alive.current) setBusy(false); }
  }

  async function correct() {
    if (!answer || busy || !corrected.trim() || !note.trim() || !correctionAuthor.trim()) return;
    setBusy(true);
    try {
      const receipt = record(await coreCommand("machine_correction", { body: {
        answer_id: answer.answer_id, knowledge_id: knowledgeId, question: answer.question,
        machine_answer: record(answer.answer).answer, corrected_answer: corrected.trim(),
        error_note: note.trim(), reviewer: correctionAuthor.trim(),
      } }));
      if (receipt.answer_id !== answer.answer_id || receipt.status !== "candidate" || receipt.authority !== "candidate"
        || receipt.corrects_knowledge_id !== knowledgeId || receipt.question !== answer.question
        || receipt.machine_answer !== record(answer.answer).answer || receipt.corrected_answer !== corrected.trim()
        || receipt.error_note !== note.trim() || receipt.reviewer !== correctionAuthor.trim()
        || typeof receipt.correction_candidate_id !== "string" || typeof receipt.failed_task_id !== "string") throw new Error("invalid correction receipt");
      if (!alive.current) return;
      setCorrection(receipt);
      const value = await readCandidate(receipt.correction_candidate_id);
      if (value.body !== receipt.corrected_answer || value.status !== "candidate") throw new Error("candidate readback does not match correction receipt");
      if (alive.current) { setCandidate(value); setReviewer(correctionAuthor.trim()); setMessage("纠正已保存为候选；审核尚未发生，候选正文、来源范围和机器回答可供对照。"); }
    } catch {
      if (alive.current) setMessage("纠正已提交或候选读回未确认。请保留填写内容并读取 Core 回执核对状态。");
    } finally { if (alive.current) setBusy(false); }
  }

  async function reviewCorrection(action: ReviewAction) {
    if (!candidate || busy || !reviewer.trim() || !reviewNote.trim()) return;
    setBusy(true);
    try {
      const id = String(candidate.knowledge_id);
      const receipt = record(await coreCommand("knowledge_review", { id, body: {
        action, reviewer: reviewer.trim(), note: reviewNote.trim(), expected_version: candidate.version,
      } }));
      if (receipt.knowledge_id !== id) throw new Error("review identity mismatch");
      const latest = await readCandidate(id);
      if (alive.current) {
        setCandidate(latest);
        setMessage(action === "accepted" ? "Core 已接受此纠正知识。独立复测尚未执行，不能据此宣称机器改进。"
          : action === "rejected" ? "Core 已拒绝此纠正候选；机器回答和审核记录仍保留。"
          : "Core 已将此纠正标记为弃用；候选、来源和复测证据仍保留。" );
      }
    } catch {
      if (alive.current) setMessage("纠正审核未完成，可能版本已变化。保留审核备注并重新读取候选后再决定。");
    } finally { if (alive.current) setBusy(false); }
  }

  async function reloadCandidate() {
    const id = candidate?.knowledge_id ?? correction?.correction_candidate_id;
    if (typeof id !== "string" || busy) return;
    setBusy(true);
    try {
      const value = await readCandidate(id);
      if (correction && value.body !== correction.corrected_answer) throw new Error("candidate receipt mismatch");
      if (alive.current) { setCandidate(value); setMessage("已重新读取 Core 当前候选与版本。"); }
    }
    catch { if (alive.current) setMessage("候选重新读取失败；当前对照仍保留，审核操作已暂停。"); }
    finally { if (alive.current) setBusy(false); }
  }

  async function runIndependentRetest() {
    if (!answer || !correction || !candidate || candidate.status !== "accepted" || retest || busy) return;
    const failedTaskId = correction.failed_task_id;
    const candidateId = String(candidate.knowledge_id);
    const originalQuestion = String(answer.question);
    const request = { retest_of: failedTaskId, knowledge_id: candidateId, question: originalQuestion, max_tokens: 2048, timeout_s: 120 };
    setBusy(true); setMessage("正在以已审核纠正知识重答原问题；Core 回执与任务读回确认前不显示为完成…");
    try {
      const response = record(await coreCommand("machine_retest", { body: request }));
      const machine = record(response.answer);
      if (response.schema !== "archeaxis.machine-retest/v1" || response.retest_of !== failedTaskId
        || response.knowledge_id !== candidateId || response.question !== originalQuestion
        || response.authority !== "candidate" || typeof response.retest_task_id !== "string"
        || typeof machine.answer !== "string" || !machine.answer.trim()) throw new Error("invalid retest receipt");
      const proof = record(await coreCommand("machine_task_get", { task_id: response.retest_task_id }));
      if (proof.task_id !== response.retest_task_id || typeof proof.conditions !== "string") throw new Error("invalid retest readback");
      const stored = record(JSON.parse(proof.conditions));
      if (stored.retest_of !== failedTaskId || stored.knowledge_id !== candidateId
        || record(stored.answer).answer !== machine.answer || proof.outcome !== "unmeasured") throw new Error("retest identity or outcome mismatch");
      if (alive.current) {
        setRetest(response); setRetestTask(proof);
        setMessage("Core 独立复测回执与持久化任务读回一致；复测结果仍是未测评候选，请真人对照两次回答。没有自动判定改进。");
      }
    } catch {
      if (alive.current) setMessage("复测未完成或持久化读回未确认。保留纠正与原失败回执；可重试同一绑定请求，不能据此宣称完成。");
    } finally { if (alive.current) setBusy(false); }
  }

  return <section aria-label="知识到机器回答">
    <h4>基于当前知识的本地回答</h4>
    <label>实际问题 <textarea value={question} disabled={busy} onChange={event => setQuestion(event.target.value)} /></label>
    <button disabled={busy || !question.trim()} onClick={() => void ask()}>执行本地机器回答</button>
    {message ? <p role="status">{message}</p> : null}
    {answer ? <>
      <h4>机器回答候选</h4><pre aria-label="真实机器回答">{String(record(answer.answer).answer)}</pre>
      <p>机器回答未被接受为知识。保存错误纠正不会自行改变已接受知识，也不会证明机器改进。</p>
      <RawReceiptButton label="持久化任务与模型回执" payload={task} />
      <p>若你实际发现错误，可记录具体更正；没有错误无需提交。</p>
      <label>正确答案 <textarea value={corrected} disabled={busy} onChange={event => setCorrected(event.target.value)} /></label>
      <label>具体错误依据 <textarea value={note} disabled={busy} onChange={event => setNote(event.target.value)} /></label>
      <label>纠正提交者 <input value={correctionAuthor} disabled={busy} onChange={event => setCorrectionAuthor(event.target.value)} /></label>
      <button disabled={busy || !corrected.trim() || !note.trim() || !correctionAuthor.trim()} onClick={() => void correct()}>记录使用者纠正候选</button>
      {correction ? <>
        <h4>纠正对照与范围</h4>
        <dl><div><dt>纠正候选 ID</dt><dd>{String(correction.correction_candidate_id)}</dd></div>
          <div><dt>绑定知识</dt><dd>{String(correction.corrects_knowledge_id)}</dd></div>
          <div><dt>纠正候选修订</dt><dd>{candidate ? String(candidate.version) : "Core 候选读回未确认"}</dd></div>
          <div><dt>本题</dt><dd>{String(correction.question)}</dd></div>
          <div><dt>原机器回答</dt><dd>{String(correction.machine_answer)}</dd></div>
          <div><dt>使用者纠正</dt><dd>{String(correction.corrected_answer)}</dd></div>
          <div><dt>Core 候选正文读回</dt><dd>{candidate ? String(candidate.body) : "未确认；审核操作不可用"}</dd></div>
          <div><dt>错误依据</dt><dd>{String(correction.error_note)}</dd></div>
          <div><dt>状态</dt><dd>{candidate ? String(candidate.status) : "候选读回未确认"}</dd></div>
        </dl>
        <RawReceiptButton label="机器纠正候选回执" payload={correction} />
        {!candidate ? <button disabled={busy} onClick={() => void reloadCandidate()}>重新读取纠正候选</button> : null}
      </> : null}
      {candidate ? <section aria-label="纠正候选审核">
        <h4>真人审核与决定</h4>
        <label>审核者 <input value={reviewer} disabled={busy} onChange={event => setReviewer(event.target.value)} /></label>
        <label>审核依据 <textarea value={reviewNote} disabled={busy} onChange={event => setReviewNote(event.target.value)} /></label>
        <button disabled={busy || candidate.status !== "candidate" || !reviewer.trim() || !reviewNote.trim()} onClick={() => void reviewCorrection("accepted")}>接受纠正知识</button>
        <button disabled={busy || candidate.status !== "candidate" || !reviewer.trim() || !reviewNote.trim()} onClick={() => void reviewCorrection("rejected")}>拒绝纠正候选</button>
        <button disabled={busy} onClick={() => void reloadCandidate()}>重新读取审核版本</button>
        <button disabled={busy || candidate.status !== "accepted" || !reviewer.trim() || !reviewNote.trim()} onClick={() => void reviewCorrection("deprecated")}>撤回已接受纠正（标记为弃用）</button>
        {candidate.status === "accepted" ? <>
          <p>已审核知识可用于重答原问题。Core 会校验先前失败任务和知识修订 lineage；接受知识本身不等同复测通过。</p>
          <button disabled={busy || Boolean(retest)} onClick={() => void runIndependentRetest()}>{retest ? "独立复测已记录" : "以已接受纠正知识运行独立复测"}</button>
          {retest ? <section aria-label="独立复测结果对照">
            <h4>独立复测结果对照</h4>
            <dl><div><dt>复测任务</dt><dd>{String(retest.retest_task_id)}</dd></div><div><dt>绑定失败任务</dt><dd>{String(retest.retest_of)}</dd></div><div><dt>作答知识 ID</dt><dd>{String(retest.knowledge_id)}</dd></div><div><dt>候选审核读回版本</dt><dd>{String(candidate.version)}</dd></div><div><dt>评价状态</dt><dd>未测评；等待真人比较</dd></div></dl>
            <h5>原机器回答（失败样本）</h5><pre>{String(record(answer.answer).answer)}</pre>
            <h5>纠正后复测回答（候选）</h5><pre aria-label="独立复测机器回答">{String(record(retest.answer).answer)}</pre>
            <p>Core 仅记录独立复测及其失败任务绑定，不自动推断纠正有效；真人比较结果尚未记录。</p>
            <RawReceiptButton label="复测任务持久化回执" payload={retestTask} />
            <RawReceiptButton label="机器复测回执" payload={retest} />
          </section> : null}
        </> : null}
      </section> : null}
    </> : null}
  </section>;
}
