import { expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { XiaoqiAvatar } from "../components/XiaoqiAvatar";
import { xiaoqiStateLabels, type XiaoqiState } from "../companion/xiaoqiAssets";

it("keeps the state identity across framing changes and falls back to the preserved original before readable failure", () => {
  const view = render(<XiaoqiAvatar state="thinking" presentation="portrait"/>);
  const image = screen.getByRole("img", { name: "小栖：思考中" });
  const source = image.getAttribute("src");
  expect(source).toContain("xiaoqi-studio-states-v3.png");
  expect(image.closest(".xiaoqi-avatar")).toHaveAttribute("data-art", "studio-v3");
  view.rerender(<XiaoqiAvatar state="thinking" presentation="figure"/>);
  expect(screen.getByRole("img", { name: "小栖：思考中" })).toHaveAttribute("src", source);
  expect(image.closest(".xiaoqi-avatar")).toHaveAttribute("data-media", "raster-2d-still");
  fireEvent.error(image);
  const original = screen.getByRole("img", { name: "小栖：思考中" });
  expect(original.getAttribute("src")).not.toBe(source);
  expect(original.closest(".xiaoqi-avatar")).toHaveAttribute("data-art", "original");
  fireEvent.error(original); expect(screen.getByRole("img", { name: "小栖：思考中，图像暂不可用" })).toBeVisible();
  view.rerender(<XiaoqiAvatar state="completed" presentation="avatar"/>);
  expect(screen.getByRole("img", { name: "小栖：已完成" })).toHaveAttribute("src");
});

it("maps every existing state to its own grid cell while keeping one consistent character sheet", () => {
  const states = Object.keys(xiaoqiStateLabels) as XiaoqiState[];
  const view = render(<XiaoqiAvatar/>);
  const source = screen.getByRole("img", { name: "小栖：待命" }).getAttribute("src");
  states.forEach((state, index) => {
    view.rerender(<XiaoqiAvatar state={state}/>);
    const image = screen.getByRole("img", { name: `小栖：${xiaoqiStateLabels[state]}` });
    const avatar = image.closest<HTMLElement>(".xiaoqi-avatar")!;
    expect(image).toHaveAttribute("src", source);
    expect(avatar).toHaveAttribute("data-visible-state", state);
    expect(avatar).toHaveAttribute("data-media", "raster-2d-still");
    expect(avatar.style.getPropertyValue("--xiaoqi-sheet-col")).toBe(String(index % 3));
    expect(avatar.style.getPropertyValue("--xiaoqi-sheet-row")).toBe(String(Math.floor(index / 3)));
  });
});

it("retains keyboard-accessible interaction when supplied, without adding a second image label", () => {
  const onInteract = vi.fn(); render(<XiaoqiAvatar size="sm" onInteract={onInteract}/>);
  fireEvent.click(screen.getByRole("button", { name: "与小栖互动：待命" }));
  expect(onInteract).toHaveBeenCalledOnce(); expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
