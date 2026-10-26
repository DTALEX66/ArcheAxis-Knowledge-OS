import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FIRST_USE_GUIDE_STORAGE_KEY, FIRST_USE_STEPS, FirstUseGuide, requestFirstUseGuide } from "../components/FirstUseGuide";
import { UsageGuidePanel } from "../components/UsageGuide";
import { UI_PAGES } from "../presentation/uiPages";

beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());
const dialog = () => screen.getByRole("dialog", { name: "首次使用引导" });
function returningUser() { localStorage.setItem(FIRST_USE_GUIDE_STORAGE_KEY, JSON.stringify({ version: 1, shown: true, current: 0, completed: [] })); }

describe("first-use guide UI progress (SIMULATED; no business success qualification)", () => {
  it("waits for readiness/home, opens once, and keeps skip reversible", async () => {
    const onPage = vi.fn(), user = userEvent.setup();
    const view = render(<FirstUseGuide onPage={onPage} enabled={false} autoOpen/>);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    view.rerender(<FirstUseGuide onPage={onPage} enabled autoOpen={false}/>);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    view.rerender(<FirstUseGuide onPage={onPage} enabled autoOpen/>);
    expect(await screen.findByRole("dialog", { name: "首次使用引导" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "暂时跳过，暂停并关闭首次使用引导" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    view.rerender(<FirstUseGuide onPage={onPage} enabled={false}/>); view.rerender(<FirstUseGuide onPage={onPage} enabled/>);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    act(() => requestFirstUseGuide()); expect(dialog()).toBeInTheDocument();
    expect(onPage).not.toHaveBeenCalled(); expect(JSON.parse(localStorage.getItem(FIRST_USE_GUIDE_STORAGE_KEY)!)).toMatchObject({ shown: true, completed: [] });
  });

  it("keeps the guide open when guarded navigation rejects and never infers completion from visiting", async () => {
    const onPage = vi.fn<((page: string) => boolean)>().mockReturnValue(false), user = userEvent.setup();
    render(<FirstUseGuide onPage={onPage}/>);
    await user.click(await screen.findByRole("button", { name: "打开导入导出" }));
    expect(onPage).toHaveBeenCalledWith("16"); expect(dialog()).toBeInTheDocument(); expect(screen.getByRole("status")).toHaveTextContent("当前页面暂未切换");
    onPage.mockReturnValue(true); await user.click(screen.getByRole("button", { name: "打开导入导出" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    act(() => requestFirstUseGuide());
    expect(screen.getByRole("checkbox", { name: "我已核对这一步（手动记录）" })).not.toBeChecked();
    expect(JSON.parse(localStorage.getItem(FIRST_USE_GUIDE_STORAGE_KEY)!)).toMatchObject({ completed: [] });
  });

  it("waits for an existing modal to close before the first automatic prompt", async () => {
    const modal = document.createElement("div"); modal.className = "aaos-dialog-content"; document.body.appendChild(modal);
    render(<FirstUseGuide onPage={vi.fn()}/>); expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    act(() => modal.remove());
    expect(await screen.findByRole("dialog", { name: "首次使用引导" })).toBeInTheDocument();
  });

  it("resumes the selected step and only explicit checks change manual progress", async () => {
    returningUser(); const user = userEvent.setup(), onPage = vi.fn();
    const view = render(<FirstUseGuide onPage={onPage}/>); act(() => requestFirstUseGuide());
    await user.click(within(screen.getByRole("navigation", { name: "引导步骤" })).getByRole("button", { name: "审查 AI 经验与授权" }));
    await user.click(screen.getByRole("checkbox"));
    expect(JSON.parse(localStorage.getItem(FIRST_USE_GUIDE_STORAGE_KEY)!)).toMatchObject({ current: 6, completed: ["ai-assets"] });
    await user.click(screen.getByRole("button", { name: "暂时跳过，暂停并关闭首次使用引导" })); view.unmount();
    render(<FirstUseGuide onPage={onPage}/>); expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); act(() => requestFirstUseGuide());
    expect(screen.getByRole("heading", { name: "审查 AI 经验与授权" })).toBeInTheDocument(); expect(screen.getByRole("checkbox")).toBeChecked();
    await user.click(screen.getByRole("checkbox")); expect(JSON.parse(localStorage.getItem(FIRST_USE_GUIDE_STORAGE_KEY)!)).toMatchObject({ completed: [] });
  });

  it("lets the settings entry reopen the guide without a permanent home banner", async () => {
    returningUser(); const user = userEvent.setup();
    render(<><UsageGuidePanel/><FirstUseGuide onPage={vi.fn()} autoOpen={false}/></>);
    await user.click(screen.getByRole("button", { name: "开始或继续首次使用引导" }));
    expect(dialog()).toBeInTheDocument(); expect(FIRST_USE_STEPS.length).toBe(10);
    const routes = FIRST_USE_STEPS.flatMap(step => step.routes.map(route => route.page));
    expect(routes.every(page => UI_PAGES.some(entry => entry.id === page))).toBe(true);
    expect(routes).toEqual(expect.arrayContaining(["16", "03", "05", "02", "06", "11", "12", "13", "14", "19", "22", "17"]));
  });

  it("retains readable progress when local preference storage is unavailable", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    render(<FirstUseGuide onPage={vi.fn()}/>);
    expect(await screen.findByRole("dialog", { name: "首次使用引导" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox")); expect(screen.getByRole("checkbox")).toBeChecked();
    expect(screen.getByText(/本机暂不能保存引导偏好/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "暂时跳过，暂停并关闭首次使用引导" })); act(() => requestFirstUseGuide()); expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it("sanitizes invalid UI preferences and does not allow a partial checklist to finish", async () => {
    localStorage.setItem(FIRST_USE_GUIDE_STORAGE_KEY, JSON.stringify({ version: 1, shown: true, current: 999, completed: ["import", "invented", "import"] }));
    render(<FirstUseGuide onPage={vi.fn()}/>); act(() => requestFirstUseGuide());
    expect(screen.getByRole("heading", { name: "发现全部能力与蓝图" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "完成引导" })).toBeDisabled();
    expect(screen.getByText("1 / 10 步已手动记录")).toBeInTheDocument();
    fireEvent.keyDown(dialog(), { key: "Escape" }); await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("explains concrete actions, saved locations, failure next steps and terms for every stage", async () => {
    const onPage = vi.fn(); render(<FirstUseGuide onPage={onPage}/>);
    await screen.findByRole("dialog", { name: "首次使用引导" });
    for (const step of FIRST_USE_STEPS) {
      fireEvent.click(within(screen.getByRole("navigation", { name: "引导步骤" })).getByRole("button", { name: step.label }));
      expect(within(screen.getByRole("list", { name: "现在做什么" })).getAllByRole("listitem")).toHaveLength(2);
      expect(screen.getByText("保存后在哪找")).toBeInTheDocument(); expect(screen.getByText("没有成功怎么办")).toBeInTheDocument();
      const summary = screen.getByText("核对结果与名词说明"); expect(summary.parentElement).not.toHaveAttribute("open");
      fireEvent.click(summary); expect(summary.parentElement?.querySelectorAll("dt")).toHaveLength(2);
      if (step.id === "recovery") {
        expect(dialog()).not.toHaveTextContent(/隔离测试|核对产物|回执|Core|CAS/);
        expect(dialog()).toHaveTextContent("确认它已出现在备份列表中");
        expect(dialog()).toHaveTextContent("先保存或复制未保存的文字");
        expect(dialog()).toHaveTextContent("替换范围与授权影响");
      }
    }
    const skip = screen.getByRole("button", { name: "暂时跳过，暂停并关闭首次使用引导" });
    expect(skip.getAttribute("aria-label")).toContain(skip.textContent); expect(onPage).not.toHaveBeenCalled();
  });
});
