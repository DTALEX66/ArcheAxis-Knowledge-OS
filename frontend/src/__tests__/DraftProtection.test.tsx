import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "../app/App";
import { CanonicalExpressionSpace } from "../spaces/CanonicalExpressionSpace";
import { updateDraftOwners } from "../workspace/draftProtection";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call, verifyCanonicalCore: vi.fn() }));
vi.mock("../spaces/SpaceView", async original => ({ ...await original<object>(), SpaceView: () => null }));
vi.mock("../components/FirstUseGuide", async original => ({ ...await original<object>(), FirstUseGuide: () => null, requestFirstUseGuide: vi.fn() }));

beforeEach(() => {
  window.location.hash = "#page=01";
  bridge.call.mockReset();
  const documents = new Map<string, unknown>();
  bridge.call.mockImplementation(async (operation: string, payload: any = {}) => {
    if (operation === "documents_list") return { documents: [], snapshot_count: 0, next_cursor: null };
    if (operation === "document_get") return structuredClone(documents.get(payload.document_id));
    if (operation === "document_create") {
      const editor = structuredClone(payload.body.editor_json);
      editor.content = editor.content.map((node: any, index: number) => ({ ...node, attrs: { ...node.attrs, block_id: node.attrs?.block_id ?? `assigned_${index}` } }));
      const document = { document_id: payload.body.create_request_id, version: 1, title: payload.body.title,
        source_id: null, source_revision: null, content_sha256: "a".repeat(64), text_projection: "", blocks: [], editor_json: editor };
      documents.set(document.document_id, document);
      return structuredClone(document);
    }
    throw new Error(`Unexpected SIMULATED operation: ${operation}`);
  });
});
afterEach(() => vi.restoreAllMocks());

function closeBlocked() {
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}

it("SIMULATED real expression views: B save and close never release A's App close/navigation guard", async () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<App />);
  const a = render(<CanonicalExpressionSpace />);
  const b = render(<CanonicalExpressionSpace />);
  const details: { owner: string; dirty: boolean }[] = [];
  const listener = (event: Event) => details.push((event as CustomEvent).detail);
  window.addEventListener("archeaxis-draft-dirty", listener);
  try {
    for (const [view, text] of [[a, "UNSAVED A"], [b, "SAVED B"]] as const) {
      fireEvent.click(within(view.container).getByRole("button", { name: "添加文本节点" }));
      fireEvent.change(within(view.container).getByLabelText("节点文字 1"), { target: { value: text } });
    }
    const dirtyOwners = new Set(details.filter(detail => detail.dirty).map(detail => detail.owner));
    expect(dirtyOwners.size).toBe(2);
    expect([...dirtyOwners].every(owner => owner.startsWith("expression:"))).toBe(true);
    expect(closeBlocked()).toBe(true);
    fireEvent.click(within(b.container).getByRole("button", { name: "保存表达草稿" }));
    await within(b.container).findByText("表达草稿已保存并读回核对。");
    expect(closeBlocked()).toBe(true);
    b.unmount();
    expect(closeBlocked()).toBe(true);
    const aOwner = details.find(detail => detail.dirty)!.owner;
    expect(details.at(-1)).toEqual({ owner: [...dirtyOwners].find(owner => owner !== aOwner), dirty: false });
    expect(within(a.container).getByLabelText("节点文字 1")).toHaveValue("UNSAVED A");
    confirm.mockClear();
    fireEvent.click(within(screen.getByRole("navigation", { name: "工作空间快捷导航" })).getByRole("button", { name: "知识" }));
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(window.location.hash).toBe("#page=01");
    a.unmount();
    await waitFor(() => expect(closeBlocked()).toBe(false));
  } finally {
    window.removeEventListener("archeaxis-draft-dirty", listener);
  }
});

it.each([null, undefined, {}, { dirty: false }, { owner: "A" }, { owner: "A", dirty: "false" }, { owner: "", dirty: false }])(
  "malformed event %j cannot release an existing owner", detail => {
    const owners = new Set(["A"]);
    expect(updateDraftOwners(owners, detail)).toBe(true);
    expect([...owners]).toEqual(["A"]);
  });

it("unrelated saved/legacy cleanup preserves all named owners until each releases itself", () => {
  const owners = new Set<string>();
  updateDraftOwners(owners, { owner: "A", dirty: true });
  updateDraftOwners(owners, { owner: "B", dirty: true });
  expect(updateDraftOwners(owners, { owner: "B", dirty: false })).toBe(true);
  expect(updateDraftOwners(owners, false)).toBe(true);
  expect([...owners]).toEqual(["A"]);
  expect(updateDraftOwners(owners, { owner: "A", dirty: false })).toBe(false);
});
