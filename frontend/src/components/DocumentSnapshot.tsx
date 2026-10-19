import type {JSONContent} from "@tiptap/core";
import {RawReceiptButton} from "./DiagnosticConsole";

function previewText(node: JSONContent): string {
  if (typeof node.text === "string") return node.text;
  if (node.type === "hardBreak") return "\n";
  if (node.type === "evidenceReference") return `引用：${node.attrs?.excerpt ?? "已关联来源"}`;
  if (!node.content?.length && !["doc", "paragraph", "heading", "codeBlock", "blockquote", "bulletList", "orderedList", "listItem"].includes(node.type ?? "")) return "此处有暂不能预览的内容，原内容已保留";
  const inline = ["paragraph", "heading", "codeBlock"].includes(node.type ?? "");
  return (node.content ?? []).map(previewText).join(inline ? "" : "\n");
}
/** A read-only text projection of this exact snapshot; no editor or business writes. */
export function DocumentSnapshot({value, label, showRaw = true}: {value: JSONContent; label: string; showRaw?: boolean}) {
  return <><pre className="document-snapshot-text" aria-label={label}>{previewText(value)}</pre>{showRaw ? <RawReceiptButton label={`${label}结构记录`} payload={value} category="data"/> : null}</>;
}
