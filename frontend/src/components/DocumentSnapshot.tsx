import type {JSONContent} from "@tiptap/core";
import {RawReceiptButton} from "./DiagnosticConsole";

function previewText(node: JSONContent): string {
  if (!node || typeof node !== "object" || Array.isArray(node) || (node.content != null && !Array.isArray(node.content))) return "此处有暂不能预览的内容，原内容已保留";
  if (typeof node.text === "string") return Array.isArray(node.marks) && node.marks.some(mark => mark?.type === "strike") ? `〔删除线：${node.text}〕` : node.text;
  if (node.type === "hardBreak") return "\n";
  if (node.type === "evidenceReference") return `引用：${node.attrs?.excerpt ?? "已关联来源"}`;
  if (["orderedList", "bulletList", "taskList"].includes(node.type ?? "")) {
    const start = Number.isSafeInteger(node.attrs?.start) ? node.attrs!.start as number : 1;
    return (node.content ?? []).map((item, index) => {
      const prefix = node.type === "orderedList" ? `${start + index}. ` : node.type === "taskList"
        ? item?.attrs?.checked === true ? "[x] " : item?.attrs?.checked === false ? "[ ] " : "[?] " : "- ";
      // Indent continuation lines so nested lists remain attached to their item.
      return prefix + previewText(item).replace(/\n/g, `\n${" ".repeat(prefix.length)}`);
    }).join("\n");
  }
  if (!node.content?.length && !["doc", "paragraph", "heading", "codeBlock", "blockquote", "listItem", "taskItem"].includes(node.type ?? "")) return "此处有暂不能预览的内容，原内容已保留";
  const inline = ["paragraph", "heading", "codeBlock"].includes(node.type ?? "");
  return (node.content ?? []).map(previewText).join(inline ? "" : "\n");
}
/** A read-only text projection of this exact snapshot; no editor or business writes. */
export function DocumentSnapshot({value, label, showRaw = true}: {value: JSONContent; label: string; showRaw?: boolean}) {
  return <><pre className="document-snapshot-text" aria-label={label}>{previewText(value)}</pre>{showRaw ? <RawReceiptButton label={`${label}结构记录`} payload={value} category="data"/> : null}</>;
}
