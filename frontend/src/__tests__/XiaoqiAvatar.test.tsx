import { expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { XiaoqiAvatar } from "../components/XiaoqiAvatar";

it("keeps the state identity across framing changes and falls back to the preserved original before readable failure", () => {
  const view = render(<XiaoqiAvatar state="thinking" presentation="portrait"/>);
  const image = screen.getByRole("img", { name: "小栖：思考中" });
  const source = image.getAttribute("src");
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

it("retains keyboard-accessible interaction when supplied, without adding a second image label", () => {
  const onInteract = vi.fn(); render(<XiaoqiAvatar size="sm" onInteract={onInteract}/>);
  fireEvent.click(screen.getByRole("button", { name: "与小栖互动：待命" }));
  expect(onInteract).toHaveBeenCalledOnce(); expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
