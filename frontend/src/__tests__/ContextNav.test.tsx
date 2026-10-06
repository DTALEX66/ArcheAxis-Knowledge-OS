import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { ContextNav } from "../components/ContextNav";

describe("ContextNav", () => {
  it("navigates actual library object sections without invoking a space change", () => {
    const onNavigate = vi.fn(); const onLibrarySection = vi.fn();
    render(<ContextNav active="library" onNavigate={onNavigate} librarySection="sources" onLibrarySection={onLibrarySection} />);
    const navigation = screen.getByRole("list", {name:"资料库对象导航"});
    expect(within(navigation).getByRole("button", {name:"来源原件"})).toHaveAttribute("aria-current", "location");
    fireEvent.click(within(navigation).getByRole("button", {name:"文档版本"}));
    expect(onLibrarySection).toHaveBeenCalledWith("versions"); expect(onNavigate).not.toHaveBeenCalled();
  });
  it("shows related work without duplicating the active primary-space entry", () => {
    render(<ContextNav active="workspace" onNavigate={() => {}} />);

    const navigation = screen.getByRole("navigation", { name: "当前空间导航" });
    expect(within(navigation).queryByRole("button", { name: /工作台/ })).not.toBeInTheDocument();
    expect(within(navigation).getByRole("button", { name: /资料库/ })).toBeInTheDocument();
    expect(within(navigation).getByRole("button", { name: /导入/ })).toBeInTheDocument();
  });
});
