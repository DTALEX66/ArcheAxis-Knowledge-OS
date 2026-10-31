import { StrictMode, useRef } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  DraftRecoveryRegistry, DraftRecoveryScope, useDraftRecoveryRegistry,
  useDraftRecoverySource, type RecoveryDraft,
} from "../workspace/draftRecovery";
import { updateDraftOwners } from "../workspace/draftProtection";
import { CanonicalRelationSpace } from "../spaces/CanonicalRelationSpace";
import { CanonicalTeachingSpace } from "../spaces/CanonicalTeachingSpace";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

afterEach(() => vi.restoreAllMocks());

function Capture({ receive }: { receive: (registry: DraftRecoveryRegistry) => void }) {
  const registry = useDraftRecoveryRegistry();
  if (!registry) throw Error("Test registry scope missing");
  receive(registry);
  return null;
}
function Source({ owner, read }: { owner: string; read: () => RecoveryDraft[] }) {
  useDraftRecoverySource(owner, owner, read);
  return null;
}

it("reads each explicit owner and removes only the owner whose view unmounts, including StrictMode", () => {
  let registry!: DraftRecoveryRegistry;
  function Views({ showB }: { showB: boolean }) {
    return <StrictMode><DraftRecoveryScope><Capture receive={value => { registry = value; }} />
      <Source key="A" owner="A" read={() => [{ label: "A的未保存内容", text: "UNSAVED A" }]} />
      {showB ? <Source key="B" owner="B" read={() => [{ label: "B的未保存内容", text: "UNSAVED B" }]} /> : null}
    </DraftRecoveryScope></StrictMode>;
  }
  const view = render(<Views showB />);
  expect(registry.read()).toEqual([
    { label: "A的未保存内容", text: "UNSAVED A" }, { label: "B的未保存内容", text: "UNSAVED B" },
  ]);
  view.rerender(<Views showB={false} />);
  expect(registry.read()).toEqual([{ label: "A的未保存内容", text: "UNSAVED A" }]);
  view.unmount();
  expect(registry.read()).toEqual([]);
});

it("an old cleanup cannot erase the replacement source registered under the same owner", () => {
  const registry = new DraftRecoveryRegistry();
  const firstCleanup = registry.register("reader", "阅读稿", () => [{ label: "旧稿", text: "OLD" }]);
  const replacementCleanup = registry.register("reader", "阅读稿", () => [{ label: "新稿", text: "NEW" }]);
  firstCleanup(); firstCleanup();
  expect(registry.read()).toEqual([{ label: "新稿", text: "NEW" }]);
  replacementCleanup();
  expect(registry.read()).toEqual([]);
});

it("reads the latest render closure and live refs, including dirty buffers outside the selected document", () => {
  let registry!: DraftRecoveryRegistry;
  let editBackground!: (text: string) => void;
  function Editor({ current }: { current: string }) {
    const buffers = useRef({ selected: "A", B: "BACKGROUND DRAFT v1" });
    editBackground = text => { buffers.current.B = text; };
    useDraftRecoverySource("editor", "编辑器", () => [
      { label: `${buffers.current.selected} 当前稿`, text: current },
      { label: "B 后台未保存稿", text: buffers.current.B },
    ]);
    return null;
  }
  const view = render(<DraftRecoveryScope><Capture receive={value => { registry = value; }} /><Editor current="CURRENT v1" /></DraftRecoveryScope>);
  expect(registry.read().map(row => row.text)).toEqual(["CURRENT v1", "BACKGROUND DRAFT v1"]);
  // The background draft changes without a render or active-document switch.
  act(() => editBackground("BACKGROUND DRAFT v2"));
  expect(registry.read().map(row => row.text)).toEqual(["CURRENT v1", "BACKGROUND DRAFT v2"]);
  view.rerender(<DraftRecoveryScope><Capture receive={value => { registry = value; }} /><Editor current="CURRENT v2" /></DraftRecoveryScope>);
  expect(registry.read().map(row => row.text)).toEqual(["CURRENT v2", "BACKGROUND DRAFT v2"]);
});

it("isolates a failed source, reports its unavailability, and never releases either dirty guard", () => {
  const registry = new DraftRecoveryRegistry();
  const owners = new Set(["A", "B"]);
  const dirtyEvent = vi.fn((event: Event) => updateDraftOwners(owners, (event as CustomEvent).detail));
  window.addEventListener("archeaxis-draft-dirty", dirtyEvent);
  let fails = true;
  registry.register("A", "研究稿", () => {
    if (fails) throw Error("SYNTHETIC exception detail must not be exported");
    return [{ label: "研究稿", text: "A still retained" }];
  });
  registry.register("B", "表达稿", () => [{ label: "表达稿", text: "B still readable" }]);
  try {
    const unavailable = registry.read();
    expect(unavailable).toHaveLength(2);
    expect(unavailable[0].label).toBe("研究稿");
    expect(unavailable[0].text).toMatch(/读取失败.*原页面仍保留/);
    expect(JSON.stringify(unavailable)).not.toContain("SYNTHETIC exception detail");
    expect(unavailable[1]).toEqual({ label: "表达稿", text: "B still readable" });
    fails = false;
    expect(registry.read()[0]).toEqual({ label: "研究稿", text: "A still retained" });
    expect([...owners]).toEqual(["A", "B"]);
    expect(dirtyEvent).not.toHaveBeenCalled();
  } finally {
    window.removeEventListener("archeaxis-draft-dirty", dirtyEvent);
  }
});

it("does not share sources between separate scopes and treats an outside-scope source as a no-op", () => {
  let first!: DraftRecoveryRegistry, second!: DraftRecoveryRegistry;
  render(<>
    <DraftRecoveryScope><Capture receive={value => { first = value; }} /><Source owner="same-owner" read={() => [{ label: "一", text: "FIRST" }]} /></DraftRecoveryScope>
    <DraftRecoveryScope><Capture receive={value => { second = value; }} /><Source owner="same-owner" read={() => [{ label: "二", text: "SECOND" }]} /></DraftRecoveryScope>
    <Source owner="outside" read={() => { throw Error("Outside source must never be read"); }} />
  </>);
  expect(first).not.toBe(second);
  expect(first.read()).toEqual([{ label: "一", text: "FIRST" }]);
  expect(second.read()).toEqual([{ label: "二", text: "SECOND" }]);
});

it("has no implicit DOM, settings, authentication or network source", () => {
  render(<><textarea aria-label="未注册的编辑器" defaultValue="SYNTHETIC unrelated draft" /><input aria-label="设置里的鉴权项" type="password" defaultValue="SYNTHETIC credential" /></>);
  const registry = new DraftRecoveryRegistry();
  const query = vi.spyOn(document, "querySelectorAll");
  const single = vi.spyOn(document, "querySelector");
  const storageRead = vi.spyOn(Storage.prototype, "getItem");
  const storageWrite = vi.spyOn(Storage.prototype, "setItem");
  const transport = vi.spyOn(window, "fetch");
  expect(registry.read()).toEqual([]);
  registry.register("explicit", "手动登记内容", () => [{ label: "研究稿", text: "EXPLICIT DRAFT" }]);
  expect(registry.read()).toEqual([{ label: "研究稿", text: "EXPLICIT DRAFT" }]);
  expect(query).not.toHaveBeenCalled(); expect(single).not.toHaveBeenCalled();
  expect(storageRead).not.toHaveBeenCalled(); expect(storageWrite).not.toHaveBeenCalled();
  expect(transport).not.toHaveBeenCalled();
});

it("SIMULATED real relation and teaching editors expose unsaved input without saving or clearing guards", async () => {
  bridge.call.mockReset();
  bridge.call.mockImplementation(async (operation: string) => {
    if (operation === "documents_list") return { documents: [], next_cursor: null, snapshot_count: 0 };
    if (operation === "teaching_list") return { items: [], next_cursor: null };
    throw Error(`Unexpected operation while reading original input: ${operation}`);
  });
  const owners = new Set<string>();
  const dirtyEvent = vi.fn((event: Event) => updateDraftOwners(owners, (event as CustomEvent).detail));
  let registry!: DraftRecoveryRegistry;
  window.addEventListener("archeaxis-draft-dirty", dirtyEvent);
  try {
    render(<DraftRecoveryScope><Capture receive={value => { registry = value; }} /><CanonicalRelationSpace /><CanonicalTeachingSpace /></DraftRecoveryScope>);
    await waitFor(() => expect(bridge.call).toHaveBeenCalledTimes(2));
    fireEvent.change(screen.getByRole("textbox", { name: "关系说明" }), { target: { value: "UNSAVED RELATION INPUT" } });
    fireEvent.change(screen.getByRole("textbox", { name: "内容" }), { target: { value: "UNSAVED TEACHING BODY" } });
    expect(owners.size).toBe(2);
    const dirtyBefore = [...owners], eventsBefore = dirtyEvent.mock.calls.length;
    const drafts = registry.read();
    expect(drafts.some(row => row.label === "未提交关系输入" && JSON.parse(row.text).relationLabel === "UNSAVED RELATION INPUT")).toBe(true);
    expect(drafts.some(row => row.label === "教学当前输入 · 08" && JSON.parse(row.text).draft.form.content === "UNSAVED TEACHING BODY")).toBe(true);
    expect([...owners]).toEqual(dirtyBefore);
    expect(dirtyEvent).toHaveBeenCalledTimes(eventsBefore);
    expect(bridge.call.mock.calls.map(call => call[0])).toEqual(["documents_list", "teaching_list"]);
    expect(screen.getByRole("textbox", { name: "关系说明" })).toHaveValue("UNSAVED RELATION INPUT");
    expect(screen.getByRole("textbox", { name: "内容" })).toHaveValue("UNSAVED TEACHING BODY");
  } finally {
    window.removeEventListener("archeaxis-draft-dirty", dirtyEvent);
  }
});
