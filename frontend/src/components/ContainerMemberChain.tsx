import { useState } from "react";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "./DiagnosticConsole";

type Member = { source_id: string; member: string; origin_ref: string; original_name: string | null; sha256: string; readable: boolean; job_id: string | null };
type Members = { container_source_id: string; member_count: number; readable_count: number; custody_only_count: number; members: Member[]; note: string };
type Transform = { source_id: string; job_id: string; transform_id: number; raw_sha256: string; content: string };

function membersShape(value: unknown): Members {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid members");
  const item = value as Record<string, unknown>;
  if (typeof item.container_source_id !== "string" || !Array.isArray(item.members) || typeof item.note !== "string") throw new Error("invalid members");
  if (![item.member_count, item.readable_count, item.custody_only_count].every((n) => Number.isInteger(n))) throw new Error("invalid members");
  return item as unknown as Members;
}

function transformShape(value: unknown): Transform {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid transform");
  const item = value as Record<string, unknown>;
  if (typeof item.content !== "string" || !Number.isInteger(item.transform_id) || typeof item.raw_sha256 !== "string") throw new Error("invalid transform");
  return item as unknown as Transform;
}

export function ContainerMemberChain({ sourceId }: { sourceId: string }) {
  const [members, setMembers] = useState<Members | null>(null);
  const [selected, setSelected] = useState<Member | null>(null);
  const [reading, setReading] = useState<Transform | null>(null);
  const [quote, setQuote] = useState<{ start: number; end: number; text: string } | null>(null);
  const [statement, setStatement] = useState("");
  const [message, setMessage] = useState("");
  const [promotion, setPromotion] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    try { await action(); }
    catch { /* every refusal below replaces the message and keeps what was already read */ }
    finally { setBusy(false); }
  }

  async function refresh() {
    await run(async () => {
      try {
        setMembers(membersShape(await coreCommand<unknown>("source_members", { source_id: sourceId })));
        setMessage("已读取容器成员清单。");
      }
      catch (error) {
        // A container nobody recorded differs from an empty container: the first is a missing
        // object, the second is a fact about the file.
        setMessage(String(error).includes("找不到") ? "此来源没有成员记录：Core 不认为它是已登记的容器。" : "成员清单读取失败，未替换已有清单。");
      }
    });
  }

  async function openReading(member: Member) {
    setSelected(member);
    setReading(null);
    setQuote(null);
    setPromotion(null);
    if (!member.job_id) { setMessage("此成员没有可读作业，只有原件保管记录。"); return; }
    await run(async () => {
      try {
        setReading(transformShape(await coreCommand<unknown>("source_job_transform", { source_id: member.source_id, job_id: member.job_id })));
        setMessage("已读取该成员自己的识别结果。");
      }
      catch { setMessage("识别结果读取失败；不显示为已读取。"); }
    });
  }

  function captureSelection(event: { currentTarget: HTMLTextAreaElement }) {
    const { selectionStart, selectionEnd } = event.currentTarget;
    const text = event.currentTarget.value.slice(selectionStart, selectionEnd);
    setQuote(text.length ? { start: selectionStart, end: selectionEnd, text } : null);
  }

  async function promote() {
    if (!reading || !selected || !quote || !statement.trim()) return;
    await run(async () => {
      try {
        const receipt = await coreCommand<unknown>("knowledge_from_transform", {
          body: {
            knowledge_type: "FACTUAL_CLAIM",
            body: statement,
            source_id: selected.source_id,
            job_id: selected.job_id,
            transform_id: reading.transform_id,
            selection_start_utf16: quote.start,
            selection_end_utf16: quote.end,
            quote: quote.text,
          },
        });
        const item = (receipt && typeof receipt === "object" ? receipt : {}) as Record<string, unknown>;
        if (item.status !== "candidate" || item.requires_human_review !== true) throw new Error("refused");
        setPromotion(item);
        setMessage("已按选中原文登记为候选知识；候选仍需真人复核，产品不会替人接受它。");
      }
      catch { setMessage("升为候选被拒绝（原文与持久化识别结果不符、或身份不被允许）；未登记任何知识。"); }
    });
  }

  return (
    <section aria-label="容器成员与知识升链">
      <h4>容器成员与知识升链</h4>
      <button disabled={busy} onClick={() => void refresh()}>读取成员清单</button>
      {message ? <p role="status">{message}</p> : null}
      {members ? (
        <>
          <p>成员 {members.member_count} · 可读 {members.readable_count} · 仅保管 {members.custody_only_count}</p>
          <p>{members.note}</p>
          <ul>
            {members.members.map((member) => (
              <li key={`${member.source_id}:${member.origin_ref}`}>
                <button disabled={busy} onClick={() => openReading(member)}>{member.original_name ?? member.member}</button>
                <span>{member.readable ? " 已读取" : " 仅保管（无路由可读）"}</span>
                {!member.job_id ? <span> · 无作业</span> : null}
                <RawReceiptButton label="成员摘要与来源关系" payload={{ sha256: member.sha256, origin_ref: member.origin_ref, source_id: member.source_id, job_id: member.job_id }} />
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {reading ? (
        <>
          <label htmlFor="member-reading">该成员的识别结果（在此选中原文）</label>
          <textarea id="member-reading" readOnly rows={8} value={reading.content} onSelect={captureSelection} />
          <p>transform_id {reading.transform_id} · 原件 SHA-256 {reading.raw_sha256}</p>
          <p>{quote ? `选中 ${quote.text.length} 个 UTF-16 代码单位，偏移 ${quote.start}–${quote.end}` : "尚未选中原文。"}</p>
          <label htmlFor="member-statement">要登记为候选的陈述</label>
          <textarea id="member-statement" rows={2} value={statement} onChange={(event) => setStatement(event.target.value)} />
          <button disabled={busy || !quote || !statement.trim()} onClick={() => void promote()}>把选中原文升为知识候选</button>
          {promotion ? (
            <p>
              候选 {typeof promotion.knowledge_id === "string" ? promotion.knowledge_id : "回执未提供 knowledge_id"} ·
              锚点 {typeof promotion.anchor_id === "string" ? promotion.anchor_id : "未提供"} ·
              状态 {String(promotion.status)} · 需真人复核 {String(promotion.requires_human_review)}
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
