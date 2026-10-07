import { useState } from "react";
import { coreCommand } from "../api/core";
import { RawReceiptButton } from "./DiagnosticConsole";

type Page = {
  page: number | null;
  source_id: string;
  origin_ref: string;
  original_name: string;
  sha256: string;
  recognised: boolean;
  text: string | null;
  job_id: string | null;
};
type Pages = {
  pdf_source_id: string;
  page_count: number;
  recognised_count: number;
  pages: Page[];
  note: string;
};

function pagesShape(value: unknown): Pages {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid pages");
  const item = value as Record<string, unknown>;
  if (typeof item.pdf_source_id !== "string" || typeof item.note !== "string" || !Array.isArray(item.pages)) {
    throw new Error("invalid pages");
  }
  if (![item.page_count, item.recognised_count].every((count) => Number.isInteger(count))) {
    throw new Error("invalid pages");
  }
  for (const entry of item.pages) {
    const page = entry as Record<string, unknown>;
    if (typeof page.source_id !== "string" || typeof page.sha256 !== "string"
      || typeof page.recognised !== "boolean" || typeof page.origin_ref !== "string"
      || typeof page.original_name !== "string"
      || !(page.page === null || Number.isInteger(page.page))
      || !(page.text === null || typeof page.text === "string")
      || !(page.job_id === null || typeof page.job_id === "string")) {
      throw new Error("invalid pages");
    }
  }
  return item as unknown as Pages;
}

export function PdfPageRecognition({ sourceId }: { sourceId: string }) {
  const [pages, setPages] = useState<Pages | null>(null);
  const [open, setOpen] = useState<Page | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    try {
      await action();
    } catch {
      // A refusal replaces the sentence only: whatever was really read stays on screen.
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    await run(async () => {
      try {
        const read = pagesShape(await coreCommand<unknown>("source_pages", { source_id: sourceId }));
        setPages(read);
        setOpen(null);
        setMessage(read.page_count
          ? `已读取 ${read.page_count} 个页面，其中 ${read.recognised_count} 页有识别文本。`
          : "此来源没有被渲染过的页面：它的文字层本就可读，或从未走过 OCR 链。");
      } catch (error) {
        // A failed read never replaces what was really read before it: the list on screen is
        // the last one Core actually answered for.
        setMessage(String(error).includes("找不到")
          ? "本地核心找不到此来源，未显示任何页面。"
          : "页面识别回写读取失败；未替换已有内容。");
      }
    });
  }

  function openPage(page: Page) {
    setOpen(page);
    if (!page.recognised) {
      setMessage(`第 ${page.page ?? "？"} 页没有识别文本：OCR 路由未对该页产出内容，原件仍在保管中。`);
    } else {
      setMessage(`第 ${page.page ?? "？"} 页显示的是该页自己的识别结果。`);
    }
  }

  return (
    <section aria-label="PDF 页面识别回写">
      <h4>PDF 页面识别回写</h4>
      <button disabled={busy} onClick={() => void refresh()}>读取页面与识别文本</button>
      {message ? <p role="status">{message}</p> : null}
      {pages ? (
        <>
          <p>页面 {pages.page_count} · 已识别 {pages.recognised_count} · 未识别 {pages.page_count - pages.recognised_count}</p>
          <p>{pages.note}</p>
          {pages.pages.length ? (
            <ul>
              {pages.pages.map((page) => (
                <li key={`${page.origin_ref}:${page.source_id}`}>
                  <button disabled={busy} onClick={() => openPage(page)}>
                    第 {page.page ?? "？"} 页 · {page.original_name}
                  </button>
                  <span>{page.recognised ? " 已识别" : " 未识别（无文本）"}</span>
                  {!page.job_id ? <span> · 无作业</span> : null}
                  <RawReceiptButton
                    label="页面摘要与来源关系"
                    payload={{ sha256: page.sha256, origin_ref: page.origin_ref, source_id: page.source_id, job_id: page.job_id }}
                  />
                </li>
              ))}
            </ul>
          ) : null}
        </>
      ) : null}
      {open?.text ? (
        <>
          <label htmlFor="page-recognition">第 {open.page ?? "？"} 页的识别文本（引擎所读，非正确性判定）</label>
          <textarea id="page-recognition" readOnly rows={8} value={open.text} />
        </>
      ) : null}
    </section>
  );
}
