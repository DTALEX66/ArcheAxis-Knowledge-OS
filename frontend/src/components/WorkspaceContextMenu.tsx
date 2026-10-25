import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Menu, MenuOptions } from "@tauri-apps/api/menu";
import { useConsoleWindow } from "./ConsoleWindow";
import "./WorkspaceContextMenu.css";

type EditCommand = "Copy" | "Cut" | "Paste" | "SelectAll";
type Action = { id: string; label: string; run: () => void | Promise<void>; disabled?: boolean; native?: EditCommand; group: string };
type Context = { x: number; y: number; target: HTMLElement; restore: () => void; actions: Action[] };
type Props = {
  onPage: (page: string) => void;
  onCompanion: () => void;
  onInspector: () => void;
  companionOpen: boolean;
  inspectorOpen: boolean;
  disabled?: boolean;
  workspaceActions?: boolean;
};

/** Reuses the current toolbar's guarded actions; the menu never writes document state itself. */
export function WorkspaceContextMenu(props: Props) {
  const consoleWindow = useConsoleWindow();
  const current = useRef({ props, consoleWindow });
  current.current = { props, consoleWindow };
  const [context, setContext] = useState<Context | null>(null);
  const [feedback, setFeedback] = useState("");
  const menuElement = useRef<HTMLDivElement>(null);
  const nativeMenu = useRef<Menu | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    let mounted = true;
    const closeNative = () => {
      const previous = nativeMenu.current;
      nativeMenu.current = null;
      if (previous) void previous.close().catch(() => {});
    };
    const invoke = (entry: Action, snapshot: Context) => {
      if (entry.disabled || !mounted) return;
      setContext(null);
      snapshot.restore();
      Promise.resolve().then(entry.run).catch(() => {
        if (mounted) setFeedback("此操作未完成。文字编辑可使用 Ctrl+C、Ctrl+X 或 Ctrl+V 重试。");
      });
    };
    const show = async (target: HTMLElement, x: number, y: number) => {
      if (target.closest(".workspace-context-menu")) return;
      const ticket = ++generation.current;
      closeNative();
      setContext(null); setFeedback("");
      const input = target.closest<HTMLInputElement | HTMLTextAreaElement>("textarea,input:not([type]),input[type=text],input[type=search],input[type=url],input[type=tel],input[type=password]");
      const rich = target.closest<HTMLElement>('[contenteditable="true"]');
      const editor = input ?? rich;
      const focusTarget = target.closest<HTMLElement>("button,a[href],input,textarea,select,[tabindex]") ?? (document.activeElement instanceof HTMLElement ? document.activeElement : target);
      const password = input instanceof HTMLInputElement && input.type === "password";
      const range = !input && window.getSelection()?.rangeCount ? window.getSelection()!.getRangeAt(0).cloneRange() : null;
      const start = input?.selectionStart ?? 0, end = input?.selectionEnd ?? 0;
      const selected = password ? "" : input ? input.value.slice(start, end) : range && (target.contains(range.commonAncestorContainer) || target.parentElement?.contains(range.commonAncestorContainer)) ? range.toString() : "";
      const restore = () => {
        if (!target.isConnected) return;
        (editor ?? focusTarget).focus({ preventScroll: true });
        if (input) input.setSelectionRange(start, end);
        else if (range && range.commonAncestorContainer.isConnected) {
          const selection = window.getSelection(); selection?.removeAllRanges(); selection?.addRange(range);
        }
      };
      const actions: Action[] = [];
      // Browser preview uses editing commands so rich-text edits still pass through the editor.
      // The installed host uses OS clipboard commands, with no clipboard permission expansion.
      const edit = (command: EditCommand) => {
        if (command === "SelectAll" && input) { input.select(); return; }
        if (command === "SelectAll" && rich) {
          const selection = window.getSelection(), all = document.createRange();
          all.selectNodeContents(rich); selection?.removeAllRanges(); selection?.addRange(all); return;
        }
        const name = command.toLowerCase();
        if (!document.execCommand?.(name)) throw new Error("Editing command unavailable");
      };
      if (selected) actions.push({ id: "copy", label: "复制", group: "edit", native: editor ? "Copy" : undefined, run: () => edit("Copy") });
      if (editor && !(input?.readOnly || input?.disabled)) {
        if (selected && !password) actions.push({ id: "cut", label: "剪切", group: "edit", native: "Cut", run: () => edit("Cut") });
        actions.push({ id: "paste", label: "粘贴", group: "edit", native: "Paste", run: () => edit("Paste") });
      }
      if (editor) actions.push({ id: "select-all", label: "全选", group: "edit", native: "SelectAll", run: () => edit("SelectAll") });

      const surface = target.closest<HTMLElement>("[data-context-surface]");
      surface?.querySelectorAll<HTMLButtonElement>("button[data-context-command]").forEach((button, index) => {
        if (button.closest("[data-context-surface]") !== surface || button.hidden) return;
        actions.push({ id: `surface-${index}`, label: button.dataset.contextLabel || button.textContent?.trim() || button.getAttribute("aria-label") || "操作", group: "surface", disabled: button.disabled,
          run: () => { if (button.isConnected && !button.disabled) button.click(); } });
      });
      const state = current.current;
      const modalOpen = [...document.querySelectorAll<HTMLElement>('[role="dialog"],[role="alertdialog"],dialog[open]')].some(dialog => !dialog.hidden && getComputedStyle(dialog).display !== "none");
      if (!modalOpen && state.props.workspaceActions !== false) {
        const page = (id: string) => { if (!current.current.props.disabled) current.current.props.onPage(id); };
        actions.push(
          { id: "import", label: "导入资料…", group: "navigate", disabled: state.props.disabled, run: () => page("16") },
          { id: "capabilities", label: "查看全部能力", group: "navigate", disabled: state.props.disabled, run: () => page("17") },
          { id: "settings", label: "设置…", group: "navigate", disabled: state.props.disabled, run: () => page("19") },
        );
        if (state.consoleWindow && state.consoleWindow.mode !== "compact") actions.push(
          { id: "expand", label: state.consoleWindow?.mode === "full" ? "还原主控台" : "铺满主控台", group: "window", run: () => current.current.consoleWindow?.toggle() },
          { id: "reset", label: "复位主控台位置与大小", group: "window", run: () => current.current.consoleWindow?.reset() },
        );
        actions.push(
          { id: "companion", label: state.props.companionOpen ? "收起小栖" : "显示小栖", group: "window", disabled: state.props.disabled, run: () => { if (!current.current.props.disabled) current.current.props.onCompanion(); } },
          { id: "inspector", label: state.props.inspectorOpen ? "收起来源检查器" : "显示来源检查器", group: "window", disabled: state.props.disabled, run: () => { if (!current.current.props.disabled) current.current.props.onInspector(); } },
        );
      }
      if (!actions.length) return;
      const snapshot: Context = { target, x, y, restore, actions };
      if ("__TAURI_INTERNALS__" in window) {
        let created: Menu | null = null;
        try {
          const [{ Menu }, { LogicalPosition }] = await Promise.all([import("@tauri-apps/api/menu"), import("@tauri-apps/api/dpi")]);
          if (!mounted || ticket !== generation.current) return;
          const items: NonNullable<MenuOptions["items"]> = [];
          actions.forEach((action, index) => {
            if (index && actions[index - 1].group !== action.group) items.push({ item: "Separator" });
            items.push(action.native ? { item: action.native, text: action.label } : { id: action.id, text: action.label, enabled: !action.disabled, action: () => invoke(action, snapshot) });
          });
          created = await Menu.new({ items });
          if (!mounted || ticket !== generation.current) { await created.close(); return; }
          nativeMenu.current = created;
          restore();
          await created.popup(new LogicalPosition(x, y));
          // popup resolves when shown. Keep its resources until the next popup or unmount.
          return;
        } catch {
          if (nativeMenu.current === created) closeNative();
          else if (created) void created.close().catch(() => {});
        }
      }
      if (mounted && ticket === generation.current) setContext(snapshot);
    };
    const contextMenu = (event: MouseEvent) => {
      const target = event.target instanceof HTMLElement ? event.target : event.target instanceof Element ? event.target.parentElement : null;
      if (!target) return;
      event.preventDefault();
      void show(target, event.clientX, event.clientY);
    };
    const keyboard = (event: KeyboardEvent) => {
      if (event.key !== "ContextMenu" && !(event.shiftKey && event.key === "F10")) return;
      if (!(event.target instanceof HTMLElement)) return;
      event.preventDefault();
      const rect = event.target.getBoundingClientRect();
      void show(event.target, rect.left + 12, rect.top + Math.min(rect.height, 28));
    };
    document.addEventListener("contextmenu", contextMenu);
    document.addEventListener("keydown", keyboard);
    return () => {
      mounted = false; generation.current++; closeNative();
      document.removeEventListener("contextmenu", contextMenu);
      document.removeEventListener("keydown", keyboard);
    };
  }, []);

  useLayoutEffect(() => {
    const menu = menuElement.current;
    if (!context || !menu) return;
    const rect = menu.getBoundingClientRect();
    menu.style.left = `${Math.max(8, Math.min(context.x, window.innerWidth - rect.width - 8))}px`;
    menu.style.top = `${Math.max(8, Math.min(context.y, window.innerHeight - rect.height - 8))}px`;
    menu.querySelector<HTMLButtonElement>("button:not(:disabled)")?.focus();
  }, [context]);
  useEffect(() => {
    if (!context) return;
    const dismiss = () => setContext(null);
    const outside = (event: PointerEvent) => { if (event.target instanceof Node && !menuElement.current?.contains(event.target)) dismiss(); };
    document.addEventListener("pointerdown", outside);
    window.addEventListener("resize", dismiss); window.addEventListener("blur", dismiss);
    return () => { document.removeEventListener("pointerdown", outside); window.removeEventListener("resize", dismiss); window.removeEventListener("blur", dismiss); };
  }, [context]);

  return createPortal(<>
    {context ? <div ref={menuElement} className="workspace-context-menu" role="menu" aria-label="当前位置操作" style={{ left: context.x, top: context.y }} onContextMenu={event => event.preventDefault()} onKeyDown={event => {
      if (event.key === "Escape" || event.key === "Tab") { event.preventDefault(); event.stopPropagation(); setContext(null); context.restore(); return; }
      const buttons = [...event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")];
      const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
      const next = event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : event.key === "ArrowDown" ? (index + 1) % buttons.length : event.key === "ArrowUp" ? (index - 1 + buttons.length) % buttons.length : -1;
      if (next >= 0) { event.preventDefault(); event.stopPropagation(); buttons[next]?.focus(); }
    }}>{context.actions.map((action, index) => <div key={action.id}>
      {index > 0 && context.actions[index - 1].group !== action.group ? <div role="separator"/> : null}
      <button role="menuitem" type="button" disabled={action.disabled} onClick={() => {
        setContext(null); context.restore();
        Promise.resolve().then(action.run).catch(() => setFeedback("此操作未完成。文字编辑可使用 Ctrl+C、Ctrl+X 或 Ctrl+V 重试。"));
      }}>{action.label}</button>
    </div>)}</div> : null}
    {feedback ? <div className="workspace-context-feedback" role="status">{feedback}<button type="button" aria-label="关闭操作提示" onClick={() => setFeedback("")}>×</button></div> : null}
  </>, document.body);
}
