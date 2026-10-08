import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { ContextNav } from "../components/ContextNav";
import { spaceSectionsFor } from "../presentation/spaceSections";

describe("ContextNav", () => {
  it("navigates actual library object sections without invoking a space change", () => {
    const onNavigate = vi.fn(); const onSection = vi.fn();
    const sections = spaceSectionsFor("library", "canonical_library");
    render(<ContextNav active="library" onNavigate={onNavigate} sections={sections} activeSection="sources" onSection={onSection} />);
    const navigation = screen.getByRole("list", { name: "资料库对象导航" });
    expect(within(navigation).getByRole("button", { name: /来源原件/ })).toHaveAttribute("aria-current", "location");
    fireEvent.click(within(navigation).getByRole("button", { name: /文档版本/ }));
    expect(onSection).toHaveBeenCalledWith(expect.objectContaining({ id: "versions" }));
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("shows related work without duplicating the active primary-space entry", () => {
    render(<ContextNav active="workspace" onNavigate={() => {}} sections={spaceSectionsFor("workspace", "canonical_capabilities")} />);

    const related = screen.getByRole("list", { name: "相关空间" });
    expect(within(related).queryByRole("button", { name: /工作台/ })).not.toBeInTheDocument();
    expect(within(related).getByRole("button", { name: /资料库/ })).toBeInTheDocument();
    expect(within(related).getByRole("button", { name: /导入/ })).toBeInTheDocument();
  });

  it("turns a section whose surface is not mounted into a labelled 待开发 row instead of a dead button", () => {
    const onSection = vi.fn();
    render(<ContextNav active="library" onNavigate={() => {}} sections={spaceSectionsFor("library", "legacy")} onSection={onSection} />);

    const navigation = screen.getByRole("list", { name: "资料库对象导航" });
    expect(within(navigation).queryAllByRole("button")).toHaveLength(0);
    expect(within(navigation).getAllByText("待开发")).toHaveLength(4);
    fireEvent.click(within(navigation).getByText("来源原件"));
    expect(onSection).not.toHaveBeenCalled();
  });
});
