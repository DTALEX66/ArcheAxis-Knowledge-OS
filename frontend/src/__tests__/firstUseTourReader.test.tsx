import { useState } from "react";
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CanonicalExchangeSpace } from "../spaces/CanonicalExchangeSpace";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { beginFirstUseTour } from "../presentation/firstUseTour";

const mocks = vi.hoisted(() => ({ stages: [] as { element: HTMLElement; popover: { onNextClick: () => void } }[], core: vi.fn(), unavailable: vi.fn() }));
vi.mock("driver.js", () => ({ driver: vi.fn((config: { onDestroyed: () => void }) => ({
  highlight: vi.fn((stage: typeof mocks.stages[number]) => { mocks.stages.push(stage); }),
  destroy: vi.fn(() => config.onDestroyed()),
})) }));
vi.mock("../api/core", () => ({ coreCommand: mocks.core }));
const doc = { document_id: "doc_guide_retained", title: "已打开的普通笔记", version: 1, source_id: null, source_revision: null,
  content_sha256: "a".repeat(64), text_projection: "保留已选择的正文",
  editor_json: { type: "doc", content: [{ type: "paragraph", attrs: { block_id: "p1" }, content: [{ type: "text", text: "保留已选择的正文" }] }] }, blocks: [] };
let stop: (() => void) | undefined;
function Fixture({ selected }: { selected: boolean }) {
  const [page, setPage] = useState("16");
  return <><div hidden={page !== "16"}><CanonicalExchangeSpace/></div>
    <div hidden={page !== "03"}><CanonicalLibrarySpace purpose="reader" initialDocumentId={selected ? doc.document_id : undefined}/></div>
    <button onClick={() => { stop = beginFirstUseTour(target => { setPage(target); return true; }, mocks.unavailable); }}>开始路径提示</button></>;
}
beforeEach(() => {
  mocks.stages.length = 0; mocks.unavailable.mockReset(); mocks.core.mockReset();
  vi.stubGlobal("crypto", webcrypto);
  vi.spyOn(HTMLElement.prototype, "getClientRects").mockImplementation(() => [{ width: 120, height: 36 }] as unknown as DOMRectList);
});
afterEach(() => { stop?.(); stop = undefined; cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it.each([true, false])("real import and reader components complete presentation stages with selected=%s (SIMULATED Core/Driver, no business actions)", async selected => {
  mocks.core.mockImplementation(async (operation: string) => {
    if (operation === "sources_list") return { sources: [] };
    if (operation === "documents_list") return { documents: selected ? [doc] : [], next_cursor: null, snapshot_count: selected ? 1 : 0 };
    if (operation === "document_get") return doc;
    if (operation === "document_checks") return { document_id: doc.document_id, version: 1, content_sha256: doc.content_sha256, historical: false, default_status: "unverified", checks: [], checks_capped: false, next_offset: null };
    throw new Error("Unexpected operation: " + operation);
  });
  render(<Fixture selected={selected}/>);
  if (selected) await waitFor(() => expect(document.querySelector(".stitch-reader-document .ProseMirror")).not.toBeNull());
  else await waitFor(() => expect(document.querySelector('[data-guide="new-note"]')).not.toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "开始路径提示" }));
  await waitFor(() => expect(mocks.stages).toHaveLength(1));
  expect(mocks.stages[0].element).toBe(screen.getByLabelText("导入原件", { exact: true }));
  mocks.stages[0].popover.onNextClick();
  await waitFor(() => expect(mocks.stages).toHaveLength(2));
  expect(mocks.stages[1].element).toBe(document.querySelector('.stitch-reader-page[data-stitch-library="reader"]'));
  expect(mocks.stages[1].element.querySelector(selected ? ".stitch-reader-document" : ".stitch-reader-empty")).not.toBeNull();
  if (selected) {
    expect(document.querySelector(".stitch-reader-details")).toHaveAttribute("hidden");
    expect(screen.getByRole("button", { name: "属性与引用" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("textbox", { name: "文档草稿" })).toHaveTextContent("保留已选择的正文");
  }
  mocks.stages[1].popover.onNextClick();
  await waitFor(() => expect(mocks.stages).toHaveLength(3));
  expect(mocks.stages[2].element).toBe(screen.getByRole("button", { name: selected ? "保存草稿" : "新建原创笔记" }));
  mocks.stages[2].popover.onNextClick();
  expect(mocks.unavailable).not.toHaveBeenCalled();
  expect(mocks.core.mock.calls.some(([operation]) => ["document_create", "document_draft", "source_import", "job_enqueue"].includes(operation))).toBe(false);
});
