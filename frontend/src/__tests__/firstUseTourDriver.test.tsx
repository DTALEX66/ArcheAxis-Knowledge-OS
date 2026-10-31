import { useState } from "react";
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { beginFirstUseTour } from "../presentation/firstUseTour";

// Real installed Driver.js, real reader and asynchronous Core responses. DOM
// geometry is simulated in jsdom; native candidate acceptance stays separate.
const mocks = vi.hoisted(() => ({ core: vi.fn(), unavailable: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: mocks.core }));
const doc = { document_id: "doc_driver_remount", title: "异步读取笔记", version: 1, source_id: null, source_revision: null,
  content_sha256: "a".repeat(64), text_projection: "异步读取后的正文不能让引导退出",
  editor_json: { type: "doc", content: [{ type: "paragraph", attrs: { block_id: "p1" }, content: [{ type: "text", text: "异步读取后的正文不能让引导退出" }] }] }, blocks: [] };
let stop: (() => void) | undefined;
let holdRead = false;
let resolveRead: ((value: typeof doc) => void) | undefined;

function Fixture({ selected }: { selected: boolean }) {
  const [page, setPage] = useState("20");
  const [readerPage, setReaderPage] = useState("20");
  const reader = <CanonicalLibrarySpace purpose={readerPage === "20" ? "history" : "reader"} initialDocumentId={selected ? doc.document_id : undefined}/>;
  return <><div hidden={page !== "16"}><button data-guide="import-originals-tab" aria-pressed="true">原件与转换</button><input aria-label="导入原件" data-guide="first-original" type="file"/></div>
    <div hidden={page !== "03" && page !== "20"}>{/* Actual SpaceView history/read routes have these distinct root shapes. */}
      {readerPage === "20" ? <section className="stitch-history-page">{reader}</section> : reader}
    </div><button onClick={() => { holdRead = selected; stop = beginFirstUseTour(target => { setPage(target); if (target === "03") setReaderPage("03"); return true; }, mocks.unavailable); }}>开始真实提示</button></>;
}

beforeEach(() => {
  mocks.core.mockReset(); mocks.unavailable.mockReset(); holdRead = false; resolveRead = undefined;
  vi.stubGlobal("crypto", webcrypto);
  vi.spyOn(HTMLElement.prototype, "getClientRects").mockImplementation(function (this: HTMLElement) {
    return (this.closest('[hidden],[aria-hidden="true"],[inert]') ? [] : [{ width: 900, height: 600 }]) as unknown as DOMRectList;
  });
  vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
});
afterEach(() => { stop?.(); stop = undefined; cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it.each([true, false])("real Driver survives the history-to-reader remount and async content replacement, selected=%s (simulated Core/geometry)", async selected => {
  mocks.core.mockImplementation(async (operation: string) => {
    if (operation === "sources_list") return { sources: [] };
    if (operation === "documents_list") return { documents: selected ? [doc] : [], next_cursor: null, snapshot_count: selected ? 1 : 0 };
    if (operation === "document_get") return holdRead ? new Promise<typeof doc>(resolve => { resolveRead = resolve; }) : doc;
    if (operation === "document_checks") return { document_id: doc.document_id, version: 1, content_sha256: doc.content_sha256, historical: false, default_status: "unverified", checks: [], checks_capped: false, next_offset: null };
    throw new Error("Unexpected operation: " + operation);
  });
  render(<Fixture selected={selected}/>);
  if (selected) await waitFor(() => expect(document.querySelector(".stitch-history-text")).toHaveTextContent(doc.text_projection));
  else await waitFor(() => expect(document.querySelector('[data-guide="new-note"]')).not.toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "开始真实提示" }));
  await waitFor(() => expect(document.querySelector(".driver-popover-title")).toHaveTextContent("1 / 3"));
  fireEvent.click(screen.getByRole("button", { name: "去阅读页" }));
  await waitFor(() => expect(document.querySelector(".driver-popover-title")).toHaveTextContent("2 / 3"));
  const region = document.querySelector('.stitch-reader-page[data-stitch-library="reader"]');
  expect(region).toHaveClass("driver-active-element");
  if (selected) {
    const temporaryEmpty = region!.querySelector(".stitch-reader-empty");
    expect(temporaryEmpty).not.toBeNull();
    expect(resolveRead).toBeTypeOf("function");
    resolveRead!(doc);
    await waitFor(() => expect(region!.querySelector(".ProseMirror")).toHaveTextContent(doc.text_projection));
    expect(temporaryEmpty!.isConnected).toBe(false);
    expect(document.querySelector('.stitch-reader-page[data-stitch-library="reader"]')).toBe(region);
    expect(document.querySelector(".driver-popover-title")).toHaveTextContent("2 / 3");
    expect(region).toHaveClass("driver-active-element");
  }
  fireEvent.click(screen.getByRole("button", { name: "看保存位置" }));
  await waitFor(() => expect(document.querySelector(".driver-popover-title")).toHaveTextContent("3 / 3"));
  expect(document.querySelector(".driver-active-element")).toBe(screen.getByRole("button", { name: selected ? "保存草稿" : "新建原创笔记" }));
  fireEvent.click(screen.getByRole("button", { name: "结束操作提示" }));
  await waitFor(() => expect(document.querySelector(".driver-popover")).toBeNull());
  expect(mocks.unavailable).not.toHaveBeenCalled();
  expect(mocks.core.mock.calls.some(([operation]) => ["document_create", "document_draft", "source_import", "job_enqueue"].includes(operation))).toBe(false);
});
