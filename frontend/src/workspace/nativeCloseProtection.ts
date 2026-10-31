type CloseRequest = { request_id: string };
type CloseDecision = CloseRequest & { outcome: "cancelled" | "failed" };
type Unlisten = () => void;
export type NativeClosePort = {
  listenRequest: (handler: (request: unknown) => void) => Promise<Unlisten>;
  listenDecision: (handler: (decision: unknown) => void) => Promise<Unlisten>;
  pending: () => Promise<unknown>;
  respond: (id: string, dirty: boolean) => Promise<unknown>;
};

function request(value: unknown): value is CloseRequest {
  return !!value && typeof value === "object" && "request_id" in value
    && typeof value.request_id === "string" && /^close-[1-9][0-9]{0,19}$/.test(value.request_id);
}

/** Block editing synchronously before reading draft truth, until cancel/failure.
 * This is a close transaction barrier, not another copy of the dirty state. */
export function blockCloseTransactionInputs(): Unlisten {
  const root = document.getElementById("root") ?? document.body;
  const previous = root.inert;
  root.inert = true;
  const stop = (event: Event) => { event.preventDefault(); event.stopImmediatePropagation(); };
  const types = ["beforeinput", "keydown", "pointerdown", "click"];
  types.forEach(type => window.addEventListener(type, stop, true));
  return () => {
    root.inert = previous;
    types.forEach(type => window.removeEventListener(type, stop, true));
  };
}

export function protectNativeClose(port: NativeClosePort, options: {
  isDirty: () => boolean;
  pending: (value: boolean) => void;
  error: (message: string) => void;
  blockInputs?: () => Unlisten;
}): Unlisten {
  let disposed = false, active: string | null = null, releaseInputs: Unlisten | undefined;
  const listeners: Unlisten[] = [];
  const release = () => {
    active = null;
    releaseInputs?.(); releaseInputs = undefined;
    if (!disposed) options.pending(false);
  };
  const failed = () => {
    release();
    if (!disposed) options.error("退出检查未完成，窗口与草稿仍保留。请重试关闭，并在系统确认中选择是否退出。");
  };
  const handle = async (value: unknown) => {
    if (disposed || active || !request(value)) return;
    const id = value.request_id;
    active = id;
    releaseInputs = (options.blockInputs ?? blockCloseTransactionInputs)();
    options.pending(true);
    try {
      // No await between the input barrier and reading the live owner union.
      const state = await port.respond(id, options.isDirty());
      if (state !== "exiting" && state !== "awaiting_confirmation") throw new Error("Invalid close response");
    } catch {
      if (active === id) failed();
    }
  };
  const decision = (value: unknown) => {
    if (disposed || !request(value) || value.request_id !== active || !("outcome" in value)) return;
    const outcome = (value as CloseDecision).outcome;
    if (outcome === "cancelled") release();
    else if (outcome === "failed") failed();
  };
  void (async () => {
    // Subscribe to decisions first, including a quick native cancellation.
    for (const subscribe of [() => port.listenDecision(decision), () => port.listenRequest(value => void handle(value))]) {
      const unlisten = await subscribe();
      if (disposed) { unlisten(); return; }
      listeners.push(unlisten);
    }
    const pending = await port.pending();
    if (!disposed && pending !== null) await handle(pending);
  })().catch(failed);
  return () => {
    disposed = true;
    listeners.forEach(unlisten => unlisten());
    release();
  };
}

export function installNativeCloseProtection(options: Parameters<typeof protectNativeClose>[1]): Unlisten {
  let disposed = false, cleanup: Unlisten | undefined;
  void import("@tauri-apps/api/window").then(({ getCurrentWindow }) => {
    if (disposed) return;
    const current = getCurrentWindow();
    const invoke = window.__TAURI__?.core?.invoke;
    if (!invoke) throw new Error("Native close IPC unavailable");
    cleanup = protectNativeClose({
      listenRequest: handler => current.listen("archeaxis-close-requested", event => handler(event.payload)),
      listenDecision: handler => current.listen("archeaxis-close-decision", event => handler(event.payload)),
      pending: () => invoke("application_close_request"),
      respond: (requestId, dirty) => invoke("application_close_response", { requestId, dirty }),
    }, options);
  }).catch(() => { if (!disposed) options.error("退出保护尚未接通；关闭时将由系统确认是否放弃未保存文字。"); });
  return () => { disposed = true; cleanup?.(); };
}
