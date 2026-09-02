import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { ContextNav } from "../components/ContextNav";

describe("ContextNav", () => {
  it("shows related work without duplicating the active primary-space entry", () => {
    render(<ContextNav active="workspace" onNavigate={() => {}} />);

    const navigation = screen.getByRole("navigation", { name: "当前空间导航" });
    expect(within(navigation).queryByRole("button", { name: /工作台/ })).not.toBeInTheDocument();
    expect(within(navigation).getByRole("button", { name: /资料库/ })).toBeInTheDocument();
    expect(within(navigation).getByRole("button", { name: /导入/ })).toBeInTheDocument();
  });
});
