import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CanonicalExchangeSpace } from "../spaces/CanonicalExchangeSpace";
import { beginFirstUseTour } from "../presentation/firstUseTour";
import { coreCommand } from "../api/core";

const mocks = vi.hoisted(() => ({ highlights: [] as HTMLElement[] }));
vi.mock("driver.js", () => ({ driver: vi.fn((config: { onDestroyed: () => void }) => ({
  highlight: vi.fn(({ element }: { element: HTMLElement }) => { mocks.highlights.push(element); }),
  destroy: vi.fn(() => config.onDestroyed()),
})) }));
vi.mock("../api/core", () => ({ coreCommand: vi.fn(async (operation: string) => {
  if (operation === "sources_list") return { sources: [] };
  if (operation === "documents_list") return { documents: [], next_cursor: null, snapshot_count: 0 };
  throw new Error("Unexpected business operation: " + operation);
}) }));
vi.mock("../components/FolderIngest", () => ({ FolderIngest: () => <p>批量导入</p> }));
vi.mock("../spaces/CanonicalTeachingSpace", () => ({ CanonicalTeachingSpace: () => <label>交换草稿<input aria-label="交换会话草稿"/></label> }));
let stop: (() => void) | undefined;
beforeEach(() => {
  mocks.highlights.length = 0;
  vi.spyOn(HTMLElement.prototype, "getClientRects").mockImplementation(() => [{ width: 120, height: 36 }] as unknown as DOMRectList);
});
afterEach(() => { stop?.(); stop = undefined; cleanup(); vi.clearAllMocks(); vi.restoreAllMocks(); });

it("actual exchange view reopens originals from a retained export tab without replacing the manual draft (SIMULATED Core/Driver)", async () => {
  render(<CanonicalExchangeSpace/>);
  fireEvent.click(screen.getByRole("button", { name: "人工教学交换" }));
  const draft = screen.getByRole("textbox", { name: "交换会话草稿" });
  fireEvent.change(draft, { target: { value: "未提交材料必须保留" } });
  fireEvent.click(screen.getByRole("button", { name: "文档导出" }));
  const original = screen.getByLabelText("导入原件", { exact: true });
  expect(original).not.toBeVisible();
  const route = vi.fn(() => true), unavailable = vi.fn();
  stop = beginFirstUseTour(route, unavailable);
  await waitFor(() => expect(mocks.highlights).toEqual([original]));
  expect(route.mock.calls).toEqual([["16"]]);
  expect(screen.getByRole("button", { name: "原件与转换" })).toHaveAttribute("aria-pressed", "true");
  expect(original).toBeVisible();
  expect(unavailable).not.toHaveBeenCalled();
  expect(draft.isConnected).toBe(true);
  expect(draft).toHaveValue("未提交材料必须保留");
  expect(vi.mocked(coreCommand).mock.calls.every(([operation]) => ["sources_list", "documents_list"].includes(operation))).toBe(true);
  stop();
  fireEvent.click(screen.getByRole("button", { name: "人工教学交换" }));
  expect(screen.getByRole("textbox", { name: "交换会话草稿" })).toBe(draft);
  expect(draft).toHaveValue("未提交材料必须保留");
});

it("guard refusal keeps the real retained export tab and performs no presentation or business action (SIMULATED Core/Driver)", () => {
  render(<CanonicalExchangeSpace/>);
  fireEvent.click(screen.getByRole("button", { name: "文档导出" }));
  const unavailable = vi.fn();
  stop = beginFirstUseTour(() => false, unavailable);
  expect(mocks.highlights).toEqual([]);
  expect(screen.getByRole("button", { name: "文档导出" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "原件与转换" })).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByLabelText("导入原件", { exact: true })).not.toBeVisible();
  expect(unavailable).toHaveBeenCalledWith(expect.stringContaining("草稿"));
});
