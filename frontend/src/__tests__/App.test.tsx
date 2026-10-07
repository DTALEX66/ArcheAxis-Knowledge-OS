import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../app/App";
import { resetRuntimeClient } from "../api/workspace";
import { SpaceView } from "../spaces/SpaceView";
import { canNavigateToCapability, EFFECTIVE_NAVIGATION_ENTRIES } from "../presentation/navigation";
import type { SpaceId } from "../spaces/spaces";

// AXW-UI-804: App shell — product routes, default space, landmarks.
// Rail buttons use the English product labels; space headings are Chinese.
describe("App shell", () => {
  afterEach(() => {
    vi.useRealTimers();
    resetRuntimeClient();
    delete window.__TAURI__;
    vi.unstubAllGlobals();
  });
  it.each([
    ["workspace","全能力目录"], ["library","资料库"], ["intake","资料库"],
    ["vault","知识库"], ["evidence","知识库"], ["ai-assets","知识库"],
    ["learning","学习"], ["exchange","资料库"], ["settings","全能力目录"],
  ] as [SpaceId,string][])("routes native %s to the existing canonical view",async(spaceId,heading)=>{
    const invoke=vi.fn(async(command:string,args?:Record<string,unknown>)=>{
      if(command!=="core_command")throw new Error("legacy native command forbidden");
      const operation=(args?.request as Record<string,unknown>).operation;
      const body=operation==="sources_list"?{sources:[]}:operation==="documents_list"?{documents:[]}:operation==="learning_items"?{items:[],count:0}:operation==="search"?{items:[],transforms:[],count:0,transform_count:0}:{capabilities:[]};
      return {status:200,body};
    });
    const fetch=vi.fn();vi.stubGlobal("fetch",fetch);window.__TAURI__={core:{invoke}};
    await act(async()=>{render(<SpaceView spaceId={spaceId} onInspect={vi.fn()} onNavigate={vi.fn()}/>);});
    expect(screen.getByRole("heading",{name:heading})).toBeInTheDocument();
    if(heading==="知识库"){const user=userEvent.setup();await user.type(screen.getByLabelText("搜索内容"),"样板");await user.click(screen.getByRole("button",{name:"搜索"}));}
    expect(invoke).toHaveBeenCalled();expect(invoke.mock.calls.every(([command])=>command==="core_command")).toBe(true);expect(fetch).not.toHaveBeenCalled();
  });

  it("SIMULATED Inspector shortcut shares mouse toggle without navigation, focus loss or draft writes", async () => {
    const user = userEvent.setup();
    render(<App />);
    const main = screen.getByRole("main");
    const before = main.innerHTML;
    const draft = document.createElement("textarea"); draft.value = "未保存草稿"; document.body.append(draft); draft.focus();
    try {
      act(() => window.dispatchEvent(new KeyboardEvent("keydown", {key:"i",ctrlKey:true,altKey:true,bubbles:true})));
      expect(screen.getByRole("complementary", {name:"检查器"})).toBeInTheDocument();
      expect(document.activeElement).toBe(draft); expect(draft.value).toBe("未保存草稿");
      expect(main.innerHTML).toBe(before);
      expect(screen.getByRole("button", {name:"折叠检查器"})).toHaveAttribute("aria-keyshortcuts", "Control+Alt+I");
      await user.click(screen.getByRole("button", {name:"折叠检查器"}));
      expect(screen.queryByRole("complementary", {name:"检查器"})).not.toBeInTheDocument();
    } finally {draft.remove();}
  });
  it("SIMULATED Inspector shortcut ignores composition, repeat, AltGraph and extra modifiers", () => {
    render(<App />);
    const events = [
      new KeyboardEvent("keydown", {key:"i",ctrlKey:true,altKey:true,repeat:true}),
      new KeyboardEvent("keydown", {key:"i",ctrlKey:true,altKey:true,isComposing:true}),
      new KeyboardEvent("keydown", {key:"i",ctrlKey:true,altKey:true,shiftKey:true}),
      new KeyboardEvent("keydown", {key:"i",ctrlKey:true,altKey:true,metaKey:true}),
      new KeyboardEvent("keydown", {key:"i",ctrlKey:true,altKey:true}),
    ];
    Object.defineProperty(events[4], "getModifierState", {value:(key:string)=>key==="AltGraph"});
    for(const event of events) act(() => window.dispatchEvent(event));
    expect(screen.queryByRole("complementary", {name:"检查器"})).not.toBeInTheDocument();
  });
  it("SIMULATED Inspector shortcut is blocked by the actual open command palette", async () => {
    const user=userEvent.setup(); render(<App />);
    await user.click(screen.getByRole("button", {name:"打开全局命令"}));
    expect(screen.getByRole("dialog", {name:"全局命令"})).toBeInTheDocument();
    act(() => window.dispatchEvent(new KeyboardEvent("keydown", {key:"i",ctrlKey:true,altKey:true})));
    expect(document.querySelector('[aria-label="检查器"]')).toBeNull();
    await user.keyboard("{Escape}");
    act(() => window.dispatchEvent(new KeyboardEvent("keydown", {key:"i",ctrlKey:true,altKey:true})));
    expect(screen.getByRole("complementary", {name:"检查器"})).toBeInTheDocument();
  });
  it("SIMULATED Inspector shortcut removes its exact listener on unmount", () => {
    const add=vi.spyOn(window,"addEventListener"); const remove=vi.spyOn(window,"removeEventListener");
    const view=render(<App />);
    const listener=add.mock.calls.find(([type,handler])=>type==="keydown"&&typeof handler==="function"&&handler.name==="shortcut")?.[1];
    expect(listener).toBeDefined();view.unmount();expect(remove).toHaveBeenCalledWith("keydown",listener);
    add.mockRestore();remove.mockRestore();
  });

  it("renders the shell landmarks (banner, navigation, main)", () => {
    render(<App />);
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "主空间导航" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("main", { name: "当前空间内容" }),
    ).toBeInTheDocument();
    const webMode = screen.getByText(/浏览器开发模式/);
    expect(webMode).toHaveAttribute("data-status", "development");
  });

  it("starts on the workspace space with aria-current on its rail button", () => {
    render(<App />);
    const main = screen.getByRole("main");
    const rail = screen.getByRole("navigation", { name: "主空间导航" });
    expect(
      within(main).getByRole("heading", { name: /工作台/ }),
    ).toBeInTheDocument();
    expect(within(rail).getByRole("button", { name: /工作台/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("keeps future capabilities selectable in command search and opens their full details", async () => {
    const initialHash = window.location.hash;
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "打开全局命令" }));
    await user.type(screen.getByRole("searchbox", { name: "搜索空间或命令" }), "CAP-0080");

    const option = document.querySelector<HTMLButtonElement>('[data-entry-id="CAP-0080"]');
    expect(option).not.toBeNull();
    expect(option!.textContent).toContain("空间记忆与沉浸学习");
    const futureEntry = EFFECTIVE_NAVIGATION_ENTRIES.find((entry) => entry.entry_id === "CAP-0080");
    expect(futureEntry?.capability).toBeDefined();
    expect(canNavigateToCapability(futureEntry!.capability!)).toBe(false);
    expect(option!).not.toHaveAttribute("aria-disabled");
    await user.keyboard("{ArrowDown}{Enter}");

    const details = await screen.findByRole("article", { name: "能力详情" });
    expect(details).toHaveTextContent("CAP-0080");
    expect(details).toHaveTextContent("下一步：");
    expect(details).toHaveTextContent("执行前提：");
    expect(details).toHaveTextContent("依赖声明：");
    expect(details).toHaveTextContent("降级与回退：");
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${initialHash}`);
  });

  it("protects dirty versioned drafts when the host window closes", () => {
    render(<App />);
    act(() => { window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: true })); });
    const event = new Event("beforeunload", { cancelable: true }) as BeforeUnloadEvent;
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    act(() => { window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty", { detail: false })); });
    const cleanEvent = new Event("beforeunload", { cancelable: true }) as BeforeUnloadEvent;
    window.dispatchEvent(cleanEvent);
    expect(cleanEvent.defaultPrevented).toBe(false);
  });

  it("switches to Library on rail click and moves aria-current", async () => {
    const user = userEvent.setup();
    render(<App />);
    const main = screen.getByRole("main");
    const rail = screen.getByRole("navigation", { name: "主空间导航" });
    expect(
      within(main).getByRole("heading", { name: /工作台/ }),
    ).toBeInTheDocument();

    await user.click(within(rail).getByRole("button", { name: /资料库/ }));

    expect(
      within(main).getByRole("heading", { name: /资料库/ }),
    ).toBeInTheDocument();
    expect(within(rail).getByRole("button", { name: /资料库/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(rail).getByRole("button", { name: /工作台/ })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("moves from the Recovery Shell into the workspace when background startup becomes ready", async () => {
    let recoveryCalls = 0;
    window.__TAURI__ = { core: { invoke: vi.fn(async (command: string) => {
      if (command === "recovery_status") {
        recoveryCalls += 1;
        return recoveryCalls === 1
          ? { state: "booting", safe_mode: false, backend_available: false, message: "正在启动", backups: [], external_dev: false }
          : { state: "ready", safe_mode: false, backend_available: true, message: "已就绪", backups: [], external_dev: false };
      }
      if (command === "core_command") return { status: 200, body: { runtime: "archeaxis-api", contract: "0.1.0-outline", schema_version: 7, sqlite_version: "3.51.3" } };
      throw new Error(`unexpected command ${command}`);
    }) } };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/system/handshake")) return { ok: true, status: 200, json: async () => ({ product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.11", source_commit: "abc1234", schema_version: 15, runtime_mode: "desktop", workspace_id: "workspace-1", capabilities: [], migration_state: "ready" }) } as Response;
      if (url.endsWith("/workspace/api/status")) return { ok: true, status: 200, json: async () => ({ schema_version: "v1", observed_at: "2026-08-29T00:00:00Z", release: { version: "0.6.11", status: "candidate", public: false }, components: {}, migrations: {}, counts: {}, capabilities: {} }) } as Response;
      if (url.endsWith("/workspace/api/v1/home")) return { ok: true, status: 200, json: async () => ({ release: { version: "0.6.11", status: "candidate", public: false }, counts: {}, capabilities: {}, components: {}, recent_activity: [] }) } as Response;
      if (url.includes("/workspace/api/v1/activity")) return { ok: true, status: 200, json: async () => ({ items: [], next_cursor: null }) } as Response;
      if (url.endsWith("/workspace/api/delivery")) return { ok: true, status: 200, json: async () => ({ summary: { jobs: 0, outbox: {}, receipts: {} } }) } as Response;
      throw new Error(`unexpected URL ${url}`);
    }));

    render(<App />);
    expect(await screen.findByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
    expect(await screen.findByRole("navigation", { name: "主空间导航" })).toBeInTheDocument();
  });

  it("leaves boot polling after the bounded desktop-core startup deadline", async () => {
    vi.useFakeTimers();
    window.__TAURI__ = { core: { invoke: vi.fn(async (command: string) => {
      if (command === "recovery_status") {
        return {
          state: "booting",
          safe_mode: false,
          backend_available: false,
          message: "正在启动",
          backups: [],
          external_dev: false,
        };
      }
      throw new Error(`unexpected command ${command}`);
    }) } };

    render(<App />);
    await act(async () => Promise.resolve());
    await act(async () => vi.advanceTimersByTimeAsync(30_000));

    expect(screen.getByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
    expect(screen.getByText(/本地核心启动超时；可查看安全诊断或重试/))
      .toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeEnabled();
  });

  it("replaces the six-space workspace with the Recovery Shell after desktop bootstrap fails", async () => {
    window.__TAURI__ = {
      core: {
        invoke: vi.fn(async (command: string) => {
          if (command === "recovery_status") {
            return {
              state: "failed",
              safe_mode: false,
              backend_available: false,
              message: "Core startup is unavailable",
              backups: [],
            };
          }
          return null;
        }),
      },
    };

    render(<App />);

    expect(
      await screen.findByRole("main", { name: "恢复工作台" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "主空间导航" }),
    ).not.toBeInTheDocument();
  });

  it("keeps the Recovery Shell when a ready desktop fails the authenticated handshake", async () => {
    const invoke = vi.fn(async (command: string) => {
      if (command === "recovery_status") {
        return {
          state: "ready",
          safe_mode: false,
          backend_available: true,
          message: "Core is ready",
          backups: [],
          external_dev: false,
        };
      }
      if (command === "backend_info") return { port: 4312, token: "memory-only" };
      return null;
    });
    window.__TAURI__ = { core: { invoke } };
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("handshake unavailable")));

    render(<App />);

    expect(await screen.findByRole("main", { name: "恢复工作台" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
    expect(invoke).toHaveBeenNthCalledWith(1, "recovery_status");
    expect(invoke).toHaveBeenNthCalledWith(2, "core_command", { request: { operation: "system_version", payload: {} } });
    expect(invoke).toHaveBeenNthCalledWith(3, "recovery_status");
  });

  it("projects a migrating workspace as a recoverable startup state", async () => {
    window.__TAURI__ = {
      core: {
        invoke: vi.fn(async (command: string) => {
          if (command === "recovery_status") {
            return {
              state: "ready", safe_mode: false, backend_available: true,
              message: "Core is ready", backups: [], external_dev: false,
            };
          }
          if (command === "backend_info") {
            return { port: 4312, token: "memory-only", scopes: ["workspace:write"] };
          }
          return null;
        }),
      },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.0",
        source_commit: "abc1234", schema_version: 15, runtime_mode: "desktop",
        workspace_id: "workspace-001", capabilities: [], migration_state: "migrating",
      }),
    } as Response));

    render(<App />);

    expect(await screen.findByText("本地核心与当前桌面版本不兼容。")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "主空间导航" })).not.toBeInTheDocument();
  });

  it("never renders a control-split raw credential from desktop recovery status", async () => {
    const rawDiagnostic = "to\nken = raw-secret-value";
    window.__TAURI__ = {
      core: {
        invoke: vi.fn(async (command: string) => command === "recovery_status" ? {
          state: "failed",
          safe_mode: false,
          backend_available: false,
          message: rawDiagnostic,
          backups: [],
          external_dev: false,
        } : null),
      },
    };

    render(<App />);

    expect(await screen.findByText(/恢复诊断已隐藏/)).toBeInTheDocument();
    expect(screen.queryByText(rawDiagnostic)).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("raw-secret-value");
  });

  it("withholds a long token that begins after the visible display boundary", async () => {
    const safePrefix = "safe ".repeat(46);
    const rawDiagnostic = `${safePrefix}${"A".repeat(40)}==`;
    window.__TAURI__ = {
      core: {
        invoke: vi.fn(async (command: string) => command === "recovery_status" ? {
          state: "failed",
          safe_mode: false,
          backend_available: false,
          message: rawDiagnostic,
          backups: [],
          external_dev: false,
        } : null),
      },
    };

    render(<App />);

    expect(await screen.findByText(/恢复诊断已隐藏/)).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(safePrefix.slice(0, 50));
    expect(document.body).not.toHaveTextContent("A".repeat(10));
  });
});
