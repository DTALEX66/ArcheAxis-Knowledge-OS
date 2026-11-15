import { useEffect, useState } from "react";
import { coreCommand } from "../api/core";
import type { ObjectReference } from "../api/generated/research-contract";

type Currentness = {
  knowledge_id: string;
  status: "candidate" | "accepted" | "rejected" | "deprecated";
  currentness: "current" | "superseded" | "not_current";
  active: boolean;
  superseded_by: string | null;
  successor_count: number;
  valid_to: string | null;
};
type Observation = { identity: string; state: "reading" | "unknown" } |
  { identity: string; state: "read"; value: Currentness };
const token = (value: unknown): value is string => typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$/.test(value);

/** This annotation is not an authorization or a new evaluation of the content. */
function readCurrentness(value: unknown, knowledgeId: string): Currentness {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid currentness");
  const row = value as Record<string, unknown>;
  if (row.knowledge_id !== knowledgeId || row.exists !== true || typeof row.active !== "boolean"
    || !["candidate", "accepted", "rejected", "deprecated"].includes(String(row.status))
    || !["current", "superseded", "not_current"].includes(String(row.currentness))
    || !Number.isSafeInteger(row.successor_count) || Number(row.successor_count) < 0
    || !(row.superseded_by === null || (token(row.superseded_by) && row.superseded_by !== knowledgeId))
    || !(row.valid_to === null || (typeof row.valid_to === "string" && row.valid_to.length <= 256))) {
    throw new Error("currentness identity or fields differ");
  }
  const successor = row.successor_count as number;
  if ((successor === 0) !== (row.superseded_by === null)
    || (row.currentness === "superseded") !== (successor > 0)
    || (row.currentness === "current") !== row.active
    || (row.active && row.status !== "candidate" && row.status !== "accepted")
    || (row.currentness === "not_current" && row.status !== "rejected" && row.status !== "deprecated")) {
    throw new Error("inconsistent currentness");
  }
  return row as Currentness;
}

/** Always reads the original immutable knowledge ID; a successor is an explicit navigation only. */
export function KnowledgeCurrentnessNotice({ knowledgeId, onOpenReference }: {
  knowledgeId: string;
  onOpenReference?: (reference: ObjectReference) => void;
}) {
  const [revision, setRevision] = useState(0);
  const identity = `${knowledgeId}:${revision}`;
  const [observation, setObservation] = useState<Observation>({ identity, state: "reading" });
  useEffect(() => {
    let alive = true;
    setObservation({ identity, state: "reading" });
    if (!token(knowledgeId)) {
      setObservation({ identity, state: "unknown" });
      return () => { alive = false; };
    }
    void coreCommand("knowledge_qualification", { id: knowledgeId }).then(value => {
      const current = readCurrentness(value, knowledgeId);
      if (alive) setObservation({ identity, state: "read", value: current });
    }).catch(() => {
      if (alive) setObservation({ identity, state: "unknown" });
    });
    return () => { alive = false; };
  }, [identity, knowledgeId]);
  // On a prop change, the old observation must not be shown even before the effect runs.
  const current = observation.identity === identity ? observation : { identity, state: "reading" as const };
  const view = current.state === "read" ? current.value : null;
  return <aside aria-label="知识引用当前性" data-knowledge-id={knowledgeId}>
    <p aria-live="polite">{current.state === "reading" ? "正在核对固定知识引用…"
      : current.state === "unknown" ? "当前性尚未核对：读取失败或返回身份不符；未当作当前版本。"
      : view?.currentness === "superseded" ? "历史知识版本：已有后继修订，原引用保持不变。"
      : view?.currentness === "not_current" ? "知识引用已失效：该版本已拒绝或弃用，仍保留历史。"
      : view?.status === "candidate" ? "当前知识候选：尚未接纳，不代表内容已核验。"
      : "当前知识版本：当前性已核对，不代表内容已核验。"}</p>
    {view?.superseded_by ? <p>后继修订：<code>{view.superseded_by}</code>（共 {view.successor_count} 项；未自动选择）。
      {onOpenReference ? <button type="button" onClick={() => onOpenReference({ kind: "knowledge", knowledge_id: view.superseded_by! })}>查看首个后继修订</button> : null}
    </p> : null}
    <p>原引用和旧评价保持原绑定；当前性不授予 AI 使用权限或人类掌握。</p>
    <button type="button" disabled={current.state === "reading"} onClick={() => setRevision(value => value + 1)}>重新核对当前性</button>
  </aside>;
}
