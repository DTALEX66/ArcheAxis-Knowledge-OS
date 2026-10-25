import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConsoleWindow, constrainConsole, defaultConsoleRect, stitchConsoleRect } from "../components/ConsoleWindow";
import { TopNavBar } from "../components/TopNavBar";

const original = { width: window.innerWidth, height: window.innerHeight };
function viewport(width: number, height: number) {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: height });
  fireEvent(window, new Event("resize"));
}
function scene() {
  return render(<ConsoleWindow><div className="app-shell cabin-shell"><TopNavBar breadcrumbs={[{ label: "资料库" }]} /><input aria-label="保留的草稿" defaultValue="未保存文字" /></div></ConsoleWindow>);
}
function geometry() { return (document.querySelector(".console-window") as HTMLElement).style; }
afterEach(() => { viewport(original.width, original.height); vi.restoreAllMocks(); });

describe("single console geometry (SIMULATED, no layout qualification)", () => {
  it("keeps Stitch's main window clear of its auxiliary column and reflows without replacing drafts", async () => {
    for (const [width, height] of [[1280, 700], [1440, 1000], [1600, 1000], [2560, 1440]]) {
      const rect = stitchConsoleRect({ width, height, topInset: 48, bottomInset: 64 });
      const sideLeft = width - rect.x - width * .29;
      expect(sideLeft - (rect.x + rect.width)).toBeCloseTo(20);
      expect(rect.y).toBeGreaterThanOrEqual(48);
      expect(rect.y).toBe(48);
      expect(rect.height).toBe(height - 112);
      expect(rect.y + rect.height).toBeLessThanOrEqual(height - 64);
      expect(rect.width / width).toBeCloseTo(.64);
    }
    viewport(1600, 1000);
    render(<ConsoleWindow presentation="stitch"><div className="app-shell cabin-shell"><TopNavBar breadcrumbs={[]}/><input aria-label="Stitch 草稿" defaultValue="保存原文"/></div></ConsoleWindow>);
    const input = screen.getByLabelText("Stitch 草稿"), user = userEvent.setup();
    expect(geometry().width).toBe("1024px"); expect(parseFloat(geometry().left)).toBeCloseTo(46);
    await user.click(screen.getByRole("button", { name: "铺满主控台" }));
    expect(geometry().width).toBe("1100px");
    await user.click(screen.getByRole("button", { name: "还原主控台" }));
    expect(geometry().width).toBe("1024px");
    viewport(640, 480); expect(geometry().width).toBe("640px");
    viewport(1280, 800); expect(geometry().width).toBe("819.2px");
    expect(screen.getByLabelText("Stitch 草稿")).toBe(input); expect(input).toHaveValue("保存原文");
  });
  it("resizes from each additional edge or corner while preserving the opposite edge and cancelling safely", () => {
    class Pointer extends MouseEvent { pointerId: number; constructor(type: string, init: PointerEventInit) { super(type, init); this.pointerId = init.pointerId ?? 1; } }
    vi.stubGlobal("PointerEvent", Pointer);
    viewport(1600, 1000); scene(); const input = screen.getByLabelText("保留的草稿");
    try {
      const cases = [
        ["w", 100, 0, [180, 72, 1340, 840]], ["n", 0, 100, [80, 172, 1440, 740]],
        ["e", 20, 0, [80, 72, 1460, 840]], ["s", 0, 20, [80, 72, 1440, 860]],
        ["nw", 100, 100, [180, 172, 1340, 740]], ["ne", 20, 100, [80, 172, 1460, 740]],
        ["sw", 100, 20, [180, 72, 1340, 860]],
      ] as const;
      for (const [edge, dx, dy, expected] of cases) {
        const handle = document.querySelector(`[data-console-edge="${edge}"]`)!;
        expect(handle).not.toBeNull();
        fireEvent.pointerDown(handle, { button: 0, pointerId: 8, clientX: 300, clientY: 300 });
        fireEvent.pointerMove(handle, { pointerId: 8, clientX: 300 + dx, clientY: 300 + dy });
        expect([geometry().left, geometry().top, geometry().width, geometry().height]).toEqual(expected.map(value => `${value}px`));
        fireEvent.pointerCancel(handle, { pointerId: 8 });
        expect([geometry().left, geometry().top, geometry().width, geometry().height]).toEqual(["80px", "72px", "1440px", "840px"]);
        expect(screen.getByLabelText("保留的草稿")).toBe(input);
        expect(input).toHaveValue("未保存文字");
      }
      const corner = document.querySelector('[data-console-edge="nw"]')!;
      fireEvent.pointerDown(corner, { button: 0, pointerId: 9, clientX: 300, clientY: 300 });
      fireEvent.pointerMove(corner, { pointerId: 9, clientX: 3000, clientY: 3000 });
      expect([geometry().left, geometry().top, geometry().width, geometry().height]).toEqual(["880px", "432px", "640px", "480px"]);
      fireEvent.keyDown(input, { key: "Escape" });
      expect(geometry().left).toBe("80px");
    } finally { vi.unstubAllGlobals(); }
  });

  it("clamps all edges and size floors, including a viewport below the supported native floor", () => {
    expect(constrainConsole({ x: -50, y: 800, width: 10, height: 900 }, { width: 1000, height: 700 })).toEqual({ x: 0, y: 0, width: 640, height: 700 });
    expect(constrainConsole({ x: 9999, y: -10, width: 9999, height: 1 }, { width: 1000, height: 700 })).toEqual({ x: 0, y: 0, width: 1000, height: 480 });
    expect(defaultConsoleRect({ width: 500, height: 300 })).toEqual({ x: 0, y: 0, width: 500, height: 300 });
    expect(constrainConsole({ x: 0, y: -900, width: 1000, height: 900 }, { width: 1600, height: 1000, topInset: 48, bottomInset: 64 })).toEqual({ x: 0, y: 48, width: 1000, height: 888 });
  });

  it("moves/resizes by keyboard, preserves the mounted draft, and writes no layout storage", async () => {
    viewport(1600, 1000); scene(); const user = userEvent.setup();
    const input = screen.getByLabelText("保留的草稿"), storage = vi.spyOn(Storage.prototype, "setItem");
    const handle = screen.getByRole("button", { name: "移动主控台" }); handle.focus();
    expect(geometry().left).toBe("80px");
    await user.keyboard("{ArrowRight}{ArrowDown}{Shift>}{ArrowLeft}{ArrowUp}{/Shift}");
    expect(geometry().left).toBe("90px"); expect(geometry().top).toBe("82px");
    expect(geometry().width).toBe("1430px"); expect(geometry().height).toBe("830px");
    expect(screen.getByLabelText("保留的草稿")).toBe(input);
    expect(input).toHaveValue("未保存文字"); expect(storage).not.toHaveBeenCalled();
  });

  it("fills/restores/resets without replacing children and leaves narrow mode explicitly disabled", async () => {
    viewport(1600, 1000); scene(); const user = userEvent.setup(), input = screen.getByLabelText("保留的草稿");
    await user.click(screen.getByRole("button", { name: "铺满主控台" }));
    expect(geometry().width).toBe("1600px"); expect(screen.getByRole("button", { name: "移动主控台" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "还原主控台" })); expect(geometry().width).toBe("1440px");
    viewport(760, 700); expect(document.querySelector(".console-window")).toHaveAttribute("data-console-mode", "compact");
    expect(geometry().left).toBe("0px"); expect(geometry().width).toBe("760px");
    expect(screen.getByRole("button", { name: "还原主控台" })).toBeDisabled();
    viewport(1600, 1000); expect(geometry().left).toBe("80px"); expect(geometry().width).toBe("1440px");
    await user.click(screen.getByRole("button", { name: "复位主控台" }));
    expect(screen.getByLabelText("保留的草稿")).toBe(input);
    viewport(640, 480); expect(geometry().width).toBe("640px"); expect(geometry().height).toBe("480px");
  });

  it("uses pointer input with bounded resize and cancels gestures without moving from interactive controls", () => {
    class Pointer extends MouseEvent { pointerId: number; constructor(type: string, init: PointerEventInit) { super(type, init); this.pointerId = init.pointerId ?? 1; } }
    vi.stubGlobal("PointerEvent", Pointer);
    viewport(1600, 1000); scene(); const header = document.querySelector(".stitch-window-title")!;
    try {
      fireEvent.pointerDown(header, { button: 2, pointerId: 1, clientX: 100, clientY: 100 });
      fireEvent.pointerMove(header, { pointerId: 1, clientX: 200, clientY: 200 }); expect(geometry().left).toBe("80px");
      fireEvent.pointerDown(header, { button: 0, pointerId: 1, clientX: 100, clientY: 100 });
      fireEvent.pointerMove(header, { pointerId: 2, clientX: 300, clientY: 300 }); expect(geometry().left).toBe("80px");
      fireEvent.pointerMove(header, { pointerId: 1, clientX: -900, clientY: -900 }); expect(geometry().left).toBe("0px");
      const input = screen.getByLabelText("保留的草稿"); input.focus();
      const ordinary = new KeyboardEvent("keydown", { key: "a", cancelable: true, bubbles: true });
      input.dispatchEvent(ordinary); expect(ordinary.defaultPrevented).toBe(false);
      fireEvent.keyDown(input, { key: "Escape" }); expect(geometry().left).toBe("80px"); expect(input).toHaveFocus();
      const resize = screen.getByRole("button", { name: "调整主控台大小" });
      fireEvent.pointerDown(resize, { button: 0, pointerId: 3, clientX: 1400, clientY: 800 });
      fireEvent.pointerMove(resize, { pointerId: 3, clientX: 0, clientY: 0 });
      expect(geometry().width).toBe("640px"); expect(geometry().height).toBe("480px");
      fireEvent.pointerUp(resize, { pointerId: 3 });
      fireEvent.pointerMove(resize, { pointerId: 3, clientX: 1500, clientY: 900 }); expect(geometry().width).toBe("640px");
    } finally { vi.unstubAllGlobals(); }
  });
});
