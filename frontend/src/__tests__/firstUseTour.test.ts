import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { waitFor } from "@testing-library/react";
import { beginFirstUseTour } from "../presentation/firstUseTour";

const mocks = vi.hoisted(() => ({ instances: [] as { config: Record<string, unknown>; highlight: ReturnType<typeof vi.fn>; destroy: ReturnType<typeof vi.fn> }[] }));
vi.mock("driver.js", () => ({ driver: vi.fn((config: Record<string, unknown>) => {
  const instance = { config, highlight: vi.fn(), destroy: vi.fn(() => (config.onDestroyed as () => void)?.()) };
  mocks.instances.push(instance); return instance;
}) }));
let stop: (() => void) | undefined;
beforeEach(() => {
  mocks.instances.length = 0;
  vi.spyOn(HTMLElement.prototype, "getClientRects").mockImplementation(function () {
    return [{ width: 120, height: 36 }] as unknown as DOMRectList;
  });
});
afterEach(() => { stop?.(); stop = undefined; document.body.innerHTML = ""; vi.useRealTimers(); vi.restoreAllMocks(); });
function mount(markup: string) { document.body.innerHTML = markup; }
const importControl = '<input data-guide="first-original" type="file">';
const reader = '<section data-stitch-library="reader"><nav data-guide="saved-documents">文档</nav><button data-guide="document-save">保存草稿</button></section>';
function next(index: number) { mocks.instances[index].highlight.mock.calls[0][0].popover.onNextClick(); }

describe("Driver.js presentation adapter (SIMULATED; no import/save or model execution)", () => {
  it("uses guarded real routes and points to import, reading and save without business clicks", async () => {
    mount(importControl); const click = vi.fn(); document.body.addEventListener("click", click, { once: true });
    const onPage = vi.fn((page: string) => { if (page === "03") mount(reader); return true; });
    stop = beginFirstUseTour(onPage, vi.fn());
    await waitFor(() => expect(mocks.instances).toHaveLength(1));
    expect(mocks.instances[0].highlight.mock.calls[0][0].element.dataset.guide).toBe("first-original");
    next(0); await waitFor(() => expect(mocks.instances).toHaveLength(2));
    next(1); await waitFor(() => expect(mocks.instances).toHaveLength(3));
    expect(mocks.instances[2].highlight.mock.calls[0][0].element.dataset.guide).toBe("document-save");
    next(2); expect(onPage.mock.calls).toEqual([["16"], ["03"]]); expect(click).not.toHaveBeenCalled();
    expect(mocks.instances.every(item => item.config.animate === false)).toBe(true);
  });
  it("does not start when the existing draft guard refuses navigation", () => {
    mount(importControl); const report = vi.fn(); stop = beginFirstUseTour(() => false, report);
    expect(mocks.instances).toHaveLength(0); expect(report).toHaveBeenCalledWith(expect.stringContaining("草稿"));
  });
  it("waits for the overview modal to unmount and the Dockview target to appear", async () => {
    mount('<div class="aaos-dialog-content"></div>');
    stop = beginFirstUseTour(() => true, vi.fn()); expect(mocks.instances).toHaveLength(0);
    mount(importControl); await waitFor(() => expect(mocks.instances).toHaveLength(1));
  });
  it("pauses for a recovery dialog and never restarts or advances on its own", async () => {
    mount(importControl); stop = beginFirstUseTour(() => true, vi.fn());
    await waitFor(() => expect(mocks.instances).toHaveLength(1));
    document.body.insertAdjacentHTML("beforeend", '<div role="alertdialog">恢复工作区</div>');
    await waitFor(() => expect(mocks.instances[0].destroy).toHaveBeenCalledOnce());
    document.querySelector('[role="alertdialog"]')?.remove(); await Promise.resolve();
    expect(mocks.instances).toHaveLength(1);
  });
  it("reports a missing or hidden target without manufacturing a completed stage", async () => {
    vi.useFakeTimers(); mount('<div hidden>' + importControl + '</div>'); const report = vi.fn();
    stop = beginFirstUseTour(() => true, report);
    await vi.advanceTimersByTimeAsync(3001);
    expect(mocks.instances).toHaveLength(0); expect(report).toHaveBeenCalledWith(expect.stringContaining("原进度已保留"));
  });
  it("cancels pending target observation when the host disables or unmounts the guide", async () => {
    const report = vi.fn(); stop = beginFirstUseTour(() => true, report); stop();
    mount(importControl); await Promise.resolve(); expect(mocks.instances).toHaveLength(0); expect(report).not.toHaveBeenCalled();
  });
});
