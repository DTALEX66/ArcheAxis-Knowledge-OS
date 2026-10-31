import { afterEach, expect, it, vi } from "vitest";
import { blockCloseTransactionInputs, protectNativeClose, type NativeClosePort } from "../workspace/nativeCloseProtection";

const flush = async () => { for (let index = 0; index < 8; index++) await Promise.resolve(); };
afterEach(() => { document.body.inert = false; vi.restoreAllMocks(); });

function fixture(pending: unknown = null) {
  let request: (value: unknown) => void = () => {}, decision: (value: unknown) => void = () => {};
  const unlistenRequest = vi.fn(), unlistenDecision = vi.fn(), unlock = vi.fn(), block = vi.fn(() => unlock);
  const port: NativeClosePort = {
    listenRequest: vi.fn(async handler => { request = handler; return unlistenRequest; }),
    listenDecision: vi.fn(async handler => { decision = handler; return unlistenDecision; }),
    pending: vi.fn(async () => pending), respond: vi.fn(async () => "awaiting_confirmation"),
  };
  const options = { isDirty: vi.fn(() => true), pending: vi.fn(), error: vi.fn(), blockInputs: block };
  return { port, options, request: (value: unknown) => request(value), decision: (value: unknown) => decision(value),
    block, unlock, unlistenRequest, unlistenDecision };
}

it("checks live dirty after synchronously blocking inputs; duplicate close has only one response", async () => {
  const f = fixture(); const stop = protectNativeClose(f.port, f.options); await flush();
  f.request({ request_id: "close-1" });
  f.request({ request_id: "close-1" });
  expect(f.block).toHaveBeenCalledTimes(1);
  expect(f.block.mock.invocationCallOrder[0]).toBeLessThan(f.options.isDirty.mock.invocationCallOrder[0]);
  expect(f.port.respond).toHaveBeenCalledTimes(1);
  expect(f.port.respond).toHaveBeenCalledWith("close-1", true);
  await flush();
  expect(f.unlock).not.toHaveBeenCalled();
  f.decision({ request_id: "close-1", outcome: "cancelled" });
  expect(f.unlock).toHaveBeenCalledOnce();
  expect(f.options.pending).toHaveBeenLastCalledWith(false);
  stop();
});

it("cancel then new editing reads fresh truth and ignores a late old decision", async () => {
  const f = fixture(); const stop = protectNativeClose(f.port, f.options); await flush();
  f.options.isDirty.mockReturnValueOnce(false).mockReturnValue(true);
  f.request({ request_id: "close-1" }); await flush();
  expect(f.port.respond).toHaveBeenCalledWith("close-1", false);
  f.decision({ request_id: "close-1", outcome: "cancelled" });
  f.request({ request_id: "close-2" }); await flush();
  expect(f.port.respond).toHaveBeenLastCalledWith("close-2", true);
  f.decision({ request_id: "close-1", outcome: "cancelled" });
  expect(f.unlock).toHaveBeenCalledTimes(1);
  f.decision({ request_id: "close-2", outcome: "failed" });
  expect(f.unlock).toHaveBeenCalledTimes(2);
  expect(f.options.error).toHaveBeenCalledOnce();
  stop();
});

it("late registration checks the native pending request", async () => {
  const f = fixture({ request_id: "close-4" });
  const stop = protectNativeClose(f.port, f.options); await flush();
  expect(f.port.respond).toHaveBeenCalledWith("close-4", true);
  stop(); expect(f.unlock).toHaveBeenCalledOnce();
});

it("IPC failure unlocks editing and reports a retained-window recovery message", async () => {
  const f = fixture(); vi.mocked(f.port.respond).mockRejectedValue(new Error("offline"));
  const stop = protectNativeClose(f.port, f.options); await flush();
  f.request({ request_id: "close-1" }); await flush();
  expect(f.unlock).toHaveBeenCalledOnce();
  expect(f.options.error).toHaveBeenCalledWith(expect.stringContaining("窗口与草稿仍保留"));
  stop();
});

it("lost response still unlocks when native fallback reports cancellation", async () => {
  const f = fixture(); vi.mocked(f.port.respond).mockImplementation(() => new Promise(() => {}));
  const stop = protectNativeClose(f.port, f.options); await flush();
  f.request({ request_id: "close-1" }); await flush();
  expect(f.unlock).not.toHaveBeenCalled();
  f.decision({ request_id: "close-1", outcome: "cancelled" });
  expect(f.unlock).toHaveBeenCalledOnce();
  expect(f.options.pending).toHaveBeenLastCalledWith(false);
  stop();
});

it("an old delayed IPC failure never releases the next close transaction", async () => {
  const f = fixture(); let reject!: (reason: Error) => void;
  vi.mocked(f.port.respond).mockImplementationOnce(() => new Promise((_, fail) => { reject = fail; }));
  const stop = protectNativeClose(f.port, f.options); await flush();
  f.request({ request_id: "close-1" });
  f.decision({ request_id: "close-1", outcome: "cancelled" });
  f.request({ request_id: "close-2" }); await flush();
  reject(new Error("late IPC failure")); await flush();
  expect(f.unlock).toHaveBeenCalledTimes(1);
  expect(f.options.error).not.toHaveBeenCalled();
  expect(f.options.pending).toHaveBeenLastCalledWith(true);
  stop();
});

it.each([null, {}, { request_id: "" }, { request_id: "close-0" }, { request_id: 4 }])(
  "malformed close event %j never starts a close transaction", async value => {
    const f = fixture(); const stop = protectNativeClose(f.port, f.options); await flush();
    f.request(value); await flush(); expect(f.port.respond).not.toHaveBeenCalled(); stop();
  },
);

it("unmount before delayed subscription cleans up without responding or blocking a new App", async () => {
  const f = fixture();
  let finish!: (value: () => void) => void;
  const delayed = vi.fn();
  vi.mocked(f.port.listenDecision).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const stop = protectNativeClose(f.port, f.options); stop();
  finish(delayed); await flush();
  expect(delayed).toHaveBeenCalledOnce();
  expect(f.port.listenRequest).not.toHaveBeenCalled();
  expect(f.port.respond).not.toHaveBeenCalled();
});

it("actual DOM barrier blocks editing/click events and restores previous inert state", () => {
  const click = vi.fn(), input = vi.fn();
  const button = document.createElement("button"); document.body.appendChild(button);
  button.addEventListener("click", click); button.addEventListener("beforeinput", input);
  const release = blockCloseTransactionInputs();
  expect(document.body.inert).toBe(true);
  const blocked = new Event("beforeinput", { bubbles: true, cancelable: true });
  button.dispatchEvent(blocked); button.click();
  expect(blocked.defaultPrevented).toBe(true); expect(click).not.toHaveBeenCalled(); expect(input).not.toHaveBeenCalled();
  release(); button.click(); expect(click).toHaveBeenCalledOnce(); expect(document.body.inert).toBe(false); button.remove();
});
