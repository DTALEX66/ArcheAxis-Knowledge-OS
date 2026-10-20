import { assertHandoffDto, type Handoff, type Preview, type Snapshot, type Context } from "./generated/project-handoff";
export type { Preview, Snapshot } from "./generated/project-handoff";
export type ContextProposal = Handoff & { payload: Context };

function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([k,v]) => `${JSON.stringify(k)}:${stable(v)}`).join(",")}}`;
  return JSON.stringify(value);
}
function context(value: unknown, now: number): ContextProposal {
  const proposal = assertHandoffDto<Handoff>("Handoff", value);
  if (proposal.payload.kind !== "context" || proposal.created_at_ms > now || proposal.expires_at_ms <= now ||
      proposal.expires_at_ms - proposal.created_at_ms > 30_000) throw new Error("上下文引用已过期或用途不支持，请重新取得引用。");
  const selection = proposal.payload.source.selection;
  if ((selection.kind === "text_range" && selection.start_utf16 >= selection.end_utf16) ||
      (selection.kind === "page_range" && selection.first_page > selection.last_page) ||
      (selection.kind === "time_range" && selection.start_ms >= selection.end_ms)) throw new Error("引用范围无效，未读取正文。");
  return proposal as ContextProposal;
}
/** 与Core相同的v1域分隔与规范JSON；元数据指纹不是身份签名或执行权。 */
export async function verifyProposalFingerprint(proposal: ContextProposal, expected: string): Promise<void> {
  const bytes = new TextEncoder().encode("archeaxis.project-handoff/v1\0" + stable(proposal));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const actual = Array.from(new Uint8Array(digest)).map(x => x.toString(16).padStart(2, "0")).join("");
  if (actual !== expected) throw new Error("预览指纹与原上下文引用不符，未打开正文。");
}
export function parseContextProposal(text: string): ContextProposal {
  if (new TextEncoder().encode(text).length > 65_536) throw new Error("上下文引用超过64KiB，未发送。");
  let value: unknown;
  try { value = JSON.parse(text); } catch { throw new Error("请输入完整的上下文引用JSON。"); }
  // JSON.parse会静默覆盖重名键；在已校验语法的有限输入上另检解码后的键名。
  const tokens = text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]/g) ?? [];
  const stack: Array<Set<string> | null> = [];
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    if (token === "{" || token === "[") {
      stack.push(token === "{" ? new Set() : null);
      if (stack.length > 128) throw new Error("上下文引用层级过深，未发送。");
    } else if (token === "}" || token === "]") stack.pop();
    else if (token.startsWith('"') && tokens[i + 1] === ":") {
      const keys = stack[stack.length - 1], key: string = JSON.parse(token);
      if (keys?.has(key)) throw new Error("上下文引用包含重复字段，未发送。");
      keys?.add(key);
    }
  }
  return context(value, Date.now());
}
export function assertPreview(value: unknown, proposal: ContextProposal, now = Date.now()): Preview {
  context(proposal, now);
  const reply = assertHandoffDto<Preview>("Preview", value);
  if (stable(reply.proposal) !== stable(proposal) || reply.checked_at_ms < proposal.created_at_ms || reply.checked_at_ms > now ||
      reply.expires_at_ms > proposal.expires_at_ms || reply.expires_at_ms <= now || reply.expires_at_ms - reply.checked_at_ms > 30_000) {
    throw new Error("预览与当前引用或有效期不符，请重新预览。");
  }
  return reply;
}
export function assertSnapshot(value: unknown, proposal: ContextProposal, expectedProposalSha: string, now = Date.now()): Snapshot {
  context(proposal, now);
  const reply = assertHandoffDto<Snapshot>("Snapshot", value);
  if (reply.proposal_sha256 !== expectedProposalSha || stable(reply.producer) !== stable(proposal.producer) ||
      stable(reply.reference) !== stable(proposal.payload.source.reference) || reply.checked_at_ms < proposal.created_at_ms ||
      reply.checked_at_ms > now || reply.expires_at_ms > proposal.expires_at_ms || reply.expires_at_ms <= now ||
      reply.expires_at_ms - reply.checked_at_ms > 30_000) throw new Error("正文与固定引用或有效期不符，未替换为其他版本。");
  return reply;
}
