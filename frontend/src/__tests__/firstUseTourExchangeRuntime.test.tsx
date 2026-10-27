import { useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CanonicalExchangeSpace } from "../spaces/CanonicalExchangeSpace";
import { beginFirstUseTour } from "../presentation/firstUseTour";

// Real React commits, actual Exchange and installed Driver.js. Core and jsdom
// geometry are simulated; this does not replace exact-candidate native testing.
const mocks = vi.hoisted(() => ({ core: vi.fn(), unavailable: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: mocks.core }));
vi.mock("../components/FolderIngest", () => ({ FolderIngest: () => <p>批量导入</p> }));
vi.mock("../spaces/CanonicalTeachingSpace", () => ({ CanonicalTeachingSpace: () => <label>保留交换草稿<input aria-label="交换会话草稿"/></label> }));
const documentFor = (id: string) => ({ document_id: id, title: id === "doc-new" ? "新选中的笔记" : "此前选中的笔记", version: 1, source_id: null, source_revision: null,
  content_sha256: "a".repeat(64), text_projection: "导出内容必须保留", editor_json: { type: "doc", content: [] }, blocks: [] });
let stop: (() => void) | undefined;
let root: Root | undefined;
let host: HTMLDivElement;
function Fixture({ previous }: { previous?: string }) {
  const [selected, setSelected] = useState(previous), [visible, setVisible] = useState(false);
  return <><div hidden={!visible}><CanonicalExchangeSpace initialDocumentId={selected}/></div>
    <button onClick={() => { stop = beginFirstUseTour(() => { setSelected("doc-new"); setVisible(true); return true; }, mocks.unavailable); }}>重开并开始提示</button></>;
}
beforeEach(() => {
  mocks.core.mockReset(); mocks.unavailable.mockReset();
  // act() flushes passive effects before MutationObserver, which removes the
  // native race under test. Use real scheduling for this narrow phase test.
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", false);
  vi.spyOn(HTMLElement.prototype, "getClientRects").mockImplementation(function (this: HTMLElement) {
    return (this.closest('[hidden],[aria-hidden="true"],[inert]') ? [] : [{ width: 900, height: 600 }]) as unknown as DOMRectList;
  });
  vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
});
afterEach(() => { stop?.(); stop = undefined; root?.unmount(); root = undefined; host.remove(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it.each([undefined, "doc-old"])("new document %s → doc-new cannot overwrite an explicit import tour selection (real Driver, simulated Core/geometry)", async previous => {
  let resolveRead: ((value: ReturnType<typeof documentFor>) => void) | undefined;
  mocks.core.mockImplementation(async (operation: string, payload?: { document_id?: string }) => {
    if (operation === "sources_list") return { sources: [] };
    if (operation === "documents_list") return { documents: [documentFor("doc-new")], next_cursor: null, snapshot_count: 1 };
    if (operation === "document_get") return payload?.document_id === "doc-new" ? new Promise(resolve => { resolveRead = resolve; }) : documentFor(payload!.document_id!);
    throw new Error("Unexpected operation: " + operation);
  });
  root!.render(<Fixture previous={previous}/>);
  await vi.waitFor(() => expect(host.querySelector(".exchange-tabs")).not.toBeNull());
  host.querySelector<HTMLButtonElement>(":scope > button")!.click();
  await vi.waitFor(() => expect(document.querySelector(".driver-popover-title")).toHaveTextContent("1 / 3"));
  await vi.waitFor(() => expect(resolveRead).toBeTypeOf("function"));
  resolveRead!(documentFor("doc-new"));
  await vi.waitFor(() => expect(host.querySelector('[aria-label="导出范围审阅"] h4')).toHaveTextContent("新选中的笔记"));
  expect(host.querySelector('[data-guide="import-originals-tab"]')).toHaveAttribute("aria-pressed", "true");
  expect(host.querySelector('[data-guide="first-original"]')).toBeVisible();
  expect(document.querySelector(".driver-popover-title")).toHaveTextContent("1 / 3");
  expect(mocks.unavailable).not.toHaveBeenCalled();
  stop!();
  host.querySelector<HTMLButtonElement>('.exchange-tabs button:nth-child(2)')!.click();
  await vi.waitFor(() => expect(host.querySelector('#exchange-export form input')).toHaveValue("doc-new"));
  expect(host.querySelector('[aria-label="导出范围审阅"] h4')).toHaveTextContent("新选中的笔记");
  const operations = mocks.core.mock.calls.map(([operation]) => operation);
  expect(operations.filter(operation => operation === "document_get")).toHaveLength(previous ? 2 : 1);
  expect(operations.every(operation => ["sources_list", "documents_list", "document_get"].includes(operation))).toBe(true);
});
