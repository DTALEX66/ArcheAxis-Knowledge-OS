import { afterEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { App } from "../app/App";
import { FIRST_USE_GUIDE_STORAGE_KEY } from "../components/FirstUseGuide";
import { resetRuntimeClient } from "../api/workspace";

afterEach(() => { resetRuntimeClient(); localStorage.clear(); vi.unstubAllGlobals(); history.replaceState(null, "", "/"); });

it("integrates first-use guidance with guarded application routes and the persistent menu entry", async () => {
  localStorage.clear(); history.replaceState(null, "", "/#page=01");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }));
  render(<App/>);
  expect(await screen.findByRole("dialog", { name: "首次使用引导" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "暂时跳过，暂停并关闭首次使用引导" }));
  expect(screen.queryByRole("dialog", { name: "首次使用引导" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "使用引导" }));
  expect(screen.getByRole("dialog", { name: "首次使用引导" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "打开导入导出" }));
  await waitFor(() => expect(document.querySelector('[data-current-page-id="16"]')).not.toBeNull());
  expect(screen.queryByRole("dialog", { name: "首次使用引导" })).not.toBeInTheDocument();
  expect(JSON.parse(localStorage.getItem(FIRST_USE_GUIDE_STORAGE_KEY)!).completed).toEqual([]);
  for (const [step, route, page] of [
    ["阅读、定位与保存", "打开阅读与编辑", "03"],
    ["搜索并比较证据", "打开研究空间", "05"],
    ["学习、练习与复习", "打开学习路径", "06"],
    ["审查 AI 经验与授权", "打开 AI 资产与上下文", "13"],
    ["纠正回答并复测", "打开纠正与复测", "14"],
  ]) {
    fireEvent.click(screen.getByRole("button", { name: "使用引导" }));
    const guide = screen.getByRole("dialog", { name: "首次使用引导" });
    fireEvent.click(within(guide).getByRole("button", { name: step }));
    fireEvent.click(within(guide).getByRole("button", { name: route }));
    await waitFor(() => expect(document.querySelector(`[data-current-page-id="${page}"]`)).not.toBeNull());
    expect(screen.queryByRole("dialog", { name: "首次使用引导" })).not.toBeInTheDocument();
  }
  expect(JSON.parse(localStorage.getItem(FIRST_USE_GUIDE_STORAGE_KEY)!).completed).toEqual([]);
});

// Actual empty reader -> semantic import page, using only a synthetic Core transport.
vi.mock("../api/core", () => ({ coreCommand: async (operation: string) => {
  if (operation === "sources_list") return { sources: [] };
  if (operation === "documents_list") return { documents: [], snapshot_count: 0 };
  throw new Error("SYNTHETIC unsupported operation: " + operation);
} }));

it("opens the real single-file import page from the actual empty reader", async () => {
  localStorage.clear(); history.replaceState(null, "", "/#page=03");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }));
  render(<App/>);
  fireEvent.click(await screen.findByRole("button", { name: "导入第一份资料" }));
  await waitFor(() => expect(document.querySelector('[data-current-page-id="16"]')).not.toBeNull());
  expect(window.location.hash).toBe("#page=16");
  expect(within(screen.getByRole("region", { name: "导入一份原件" })).getByLabelText("导入原件")).toHaveAttribute("type", "file");
});
