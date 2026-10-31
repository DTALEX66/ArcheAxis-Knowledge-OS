import { afterEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "../app/App";
import { CanonicalResearchSpace } from "../spaces/CanonicalResearchSpace";
import { CanonicalExpressionSpace } from "../spaces/CanonicalExpressionSpace";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";

const bridge = vi.hoisted(() => ({ status: vi.fn(), verify: vi.fn(), call: vi.fn(), restore: vi.fn() }));
vi.mock("../api/workspace", async original => ({
  ...await original<object>(), getRecoveryStatus: bridge.status, restoreRecoveryBackup: bridge.restore,
  getRecoveryLogTail: vi.fn(async () => ({ lines: [] })), resetRuntimeClient: vi.fn(),
  retryDesktopBackend: vi.fn(async () => {}), enterRecoverySafeMode: vi.fn(),
}));
vi.mock("../api/core", () => ({ verifyCanonicalCore: bridge.verify, coreCommand: bridge.call }));
// Isolate Dock geometry, not editor lifetime: both production content components
// remain children of the actual App branch that previously unmounted on Core loss.
vi.mock("../workspace/DockWorkspace", () => ({ DockWorkspace: () => <><CanonicalResearchSpace /><CanonicalExpressionSpace /></> }));
vi.mock("../components/FirstUseGuide", async original => ({ ...await original<object>(), FirstUseGuide: () => null, requestFirstUseGuide: vi.fn() }));

const flush = async () => { for (let index = 0; index < 24; index++) await Promise.resolve(); };
function closeBlocked() {
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event); return event.defaultPrevented;
}
afterEach(() => { vi.useRealTimers(); delete window.__TAURI__; vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it.each([false, true])("SIMULATED actual App retains editor originals through permanent Core loss and retry (background buffers: %s)", async (background) => {
  vi.useFakeTimers(); vi.stubGlobal("innerWidth", 1024); vi.stubGlobal("innerHeight", 768);
  window.history.replaceState(null, "", "#page=05"); window.__TAURI__ = { core: { invoke: vi.fn() } };
  const ready = { state: "ready", safe_mode: false, backend_available: true, message: "ready", backups: [], external_dev: false };
  const stopped = { ...ready, state: "stopped", backend_available: false, message: "SIMULATED Core stopped", backups: ["cognitive_os_20260823T010203_000000Z.sqlite"] };
  bridge.status.mockReset().mockResolvedValueOnce(ready).mockResolvedValue(stopped);
  bridge.verify.mockResolvedValue({ status: "available" });
  bridge.restore.mockReset();
  let read: any = { schema: "archeaxis.ui-working-state/v1", workspace_id: "a".repeat(32), restore_epoch: "initial", state_revision: 0,
    state: { drafts: {}, opened_documents: [], active_document: null, page_id: null, pending_original: null },
    draft_digests: {}, pending_document_id: null, recovery_candidates: null, recovery_requires_confirmation: false };
  let readGate: Promise<unknown> | null = null;
  const documents = new Map<string, unknown>();
  bridge.call.mockImplementation(async (operation: string, payload: any = {}) => {
    if (operation === "ui_state_read") return readGate ?? structuredClone(read);
    if (operation === "ui_state_write") {
      read = { ...read, state_revision: read.state_revision + 1, state: structuredClone(payload.body.state) };
      return structuredClone(read);
    }
    if (operation === "sources_list") return { sources: [] };
    if (operation === "learning_items") return { items: [], count: 0 };
    if (operation === "document_get") return structuredClone(documents.get(payload.document_id));
    if (operation === "document_create") {
      const editor = structuredClone(payload.body.editor_json);
      editor.content = editor.content.map((node: any, index: number) => ({ ...node, attrs: { ...node.attrs, block_id: node.attrs?.block_id ?? `assigned_${index}` } }));
      const document = { document_id: await documentRequestIdentity(payload.body.create_request_id), version: 1, title: payload.body.title, source_id: null,
        source_revision: null, content_sha256: "a".repeat(64), text_projection: "", blocks: [], editor_json: editor };
      documents.set(document.document_id, document); return structuredClone(document);
    }
    return { documents: [], next_cursor: null, snapshot_count: 0 };
  });
  const events: { owner: string; dirty: boolean }[] = [];
  const listener = (event: Event) => events.push((event as CustomEvent).detail);
  window.addEventListener("archeaxis-draft-dirty", listener);
  try {
    render(<App />); await act(flush);
    if (background) {
      fireEvent.change(screen.getByRole("textbox", { name: "研究问题" }), { target: { value: "BACKGROUND research original" } });
      fireEvent.click(screen.getByRole("button", { name: "新建研究草稿", hidden: true }));
      fireEvent.click(screen.getByRole("button", { name: "保留草稿并切换" })); await act(flush);
      fireEvent.click(screen.getByRole("button", { name: "添加文本节点" }));
      fireEvent.change(screen.getByRole("textbox", { name: "节点文字 1" }), { target: { value: "BACKGROUND expression original" } });
      fireEvent.click(screen.getByRole("button", { name: "新表达草稿" }));
      fireEvent.click(screen.getByRole("button", { name: "保留草稿并切换" })); await act(flush);
    }
    const research = screen.getByRole("textbox", { name: "研究问题" });
    fireEvent.change(research, { target: { value: "UNSAVED research A survives unavailable Core" } });
    fireEvent.click(screen.getByRole("button", { name: "添加文本节点" }));
    const expression = screen.getByRole("textbox", { name: "节点文字 1" });
    fireEvent.change(expression, { target: { value: "UNSAVED expression B survives unavailable Core" } });
    const connection = screen.getByRole("textbox", { name: "新连线文字" });
    fireEvent.change(connection, { target: { value: "PENDING connection text original" } });
    const owners = [...new Set(events.filter(row => row.dirty).map(row => row.owner))];
    expect(owners).toHaveLength(2); expect(closeBlocked()).toBe(true);

    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); await flush(); });
    const recovery = screen.getByRole("dialog", { name: "本地核心暂不可用" });
    expect(within(recovery).getByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
    const retained = document.querySelector<HTMLElement>("[data-retained-workspace]")!;
    expect(retained.inert).toBe(true); expect(retained).toHaveAttribute("aria-hidden", "true");
    expect(retained.querySelector('[data-state="unavailable"]')).toHaveTextContent("本地连接不可用");
    expect(research.isConnected).toBe(true); expect(expression.isConnected).toBe(true);
    expect(research).toHaveValue("UNSAVED research A survives unavailable Core");
    expect(expression).toHaveValue("UNSAVED expression B survives unavailable Core");
    for (const owner of owners) expect(events.filter(row => row.owner === owner).at(-1)).toEqual({ owner, dirty: true });
    expect(closeBlocked()).toBe(true);
    const restore = within(recovery).getByRole("button", { name: "恢复备份" });
    expect(restore).toBeDisabled(); fireEvent.click(restore); expect(bridge.restore).not.toHaveBeenCalled();
    const unrelated = document.createElement("aside");
    unrelated.innerHTML = '<input type="password" value="SYNTHETIC_SETTINGS_SECRET"><pre>SYNTHETIC_DIAGNOSTIC_OBJECT</pre>';
    document.body.append(unrelated);
    const commandsBeforeRead = bridge.call.mock.calls.length;
    const ownersBeforeRead = events.length;
    try {
      fireEvent.click(within(recovery).getByRole("button", { name: "查看已登记编辑区的未保存原稿" }));
      const originals = within(recovery).getByRole("textbox", { name: "未保存原稿（只读）" }) as HTMLTextAreaElement;
      expect(originals.readOnly).toBe(true);
      for (const text of ["UNSAVED research A survives unavailable Core", "UNSAVED expression B survives unavailable Core", "PENDING connection text original"]) expect(originals.value).toContain(text);
      if (background) for (const text of ["BACKGROUND research original", "BACKGROUND expression original"]) expect(originals.value).toContain(text);
      expect(originals.value).not.toMatch(/SYNTHETIC_SETTINGS_SECRET|SYNTHETIC_DIAGNOSTIC_OBJECT/);
      fireEvent.click(within(recovery).getByRole("button", { name: "全选原稿，按 Ctrl+C 复制" }));
      expect(originals.selectionStart).toBe(0); expect(originals.selectionEnd).toBe(originals.value.length);
      expect(bridge.call.mock.calls).toHaveLength(commandsBeforeRead); expect(events).toHaveLength(ownersBeforeRead);
      expect(restore).toBeDisabled(); expect(closeBlocked()).toBe(true);
      // Remaining unavailable never requires a successful Core command to read.
      await act(async () => { await vi.advanceTimersByTimeAsync(10_000); await flush(); });
      expect(originals).toBeInTheDocument(); expect(originals.value).toContain("PENDING connection text original");
    } finally { unrelated.remove(); }
    const input = new Event("beforeinput", { bubbles: true, cancelable: true }); research.dispatchEvent(input);
    expect(input.defaultPrevented).toBe(true);
    fireEvent.click(within(retained).getByRole("button", { name: "添加文本节点", hidden: true }));
    expect(within(retained).queryByRole("textbox", { name: "节点文字 2", hidden: true })).not.toBeInTheDocument();
    fireEvent.keyDown(recovery, { key: "k", ctrlKey: true }); fireEvent.keyDown(recovery, { key: "i", ctrlKey: true, altKey: true });
    expect(screen.queryByRole("dialog", { name: "全局命令" })).not.toBeInTheDocument();
    act(() => { window.history.replaceState(null, "", "#page=03"); window.dispatchEvent(new HashChangeEvent("hashchange")); });
    expect(window.location.hash).toBe("#page=05");
    fireEvent.keyDown(recovery, { key: "Escape" }); expect(recovery).toBeInTheDocument();

    let finishRead!: (value: unknown) => void;
    readGate = new Promise(resolve => { finishRead = resolve; });
    bridge.status.mockResolvedValue(ready);
    fireEvent.click(within(recovery).getByRole("button", { name: "重试启动" }));
    await act(flush);
    // workingEntered is false while this exact reread is pending; the editors
    // must remain the same instances rather than remount with blank useRefs.
    expect(research.isConnected).toBe(true); expect(expression.isConnected).toBe(true);
    expect(closeBlocked()).toBe(true);
    await act(async () => { finishRead(structuredClone(read)); await flush(); });
    readGate = null;
    expect(screen.getByRole("textbox", { name: "研究问题" })).toBe(research);
    expect(screen.getByRole("textbox", { name: "节点文字 1" })).toBe(expression);
    expect(retained.inert).toBe(false); expect(retained).not.toHaveAttribute("aria-hidden");
    expect(screen.queryByRole("dialog", { name: "本地核心暂不可用" })).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "新连线文字" })).toBe(connection);
    expect(connection).toHaveValue("PENDING connection text original");
    fireEvent.click(screen.getByRole("button", { name: "取消未提交连线" }));
    vi.useRealTimers();
    fireEvent.click(screen.getByRole("button", { name: "保存表达草稿" }));
    await screen.findByText("表达草稿已保存并读回核对。"); expect(closeBlocked()).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "保存研究草稿" }));
    await screen.findByText("研究草稿已保存并读回；未变为核验或采用状态。"); expect(closeBlocked()).toBe(background);
    expect(documents.size).toBe(2);
  } finally { window.removeEventListener("archeaxis-draft-dirty", listener); }
});
