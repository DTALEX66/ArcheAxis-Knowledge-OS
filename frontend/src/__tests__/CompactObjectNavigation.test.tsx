import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../app/App";
import { resetRuntimeClient } from "../api/workspace";

const fixture = vi.hoisted(() => ({ surface: "canonical_library" }));
vi.mock("../spaces/SpaceView", () => ({
  canonicalSurface: () => fixture.surface,
  SpaceView: () => <>{["anchors", "versions", "documents", "sources"].map(region =>
    <section key={region} tabIndex={-1} data-section={region} aria-label={region}>{region}</section>)}</>,
}));

describe("compact object navigation (SIMULATED shell)", () => {
  beforeEach(() => {
    delete window.__TAURI__;
    fixture.surface = "canonical_library";
    window.history.replaceState(null, "", "#space=library");
  });
  afterEach(() => {
    resetRuntimeClient();
    window.history.replaceState(null, "", "#page=01");
  });

  it("opens all four current object controls and closes before focusing each target", async () => {
    const user = userEvent.setup(); render(<App />);
    for (const [label, region] of [["来源锚点", "anchors"], ["文档版本", "versions"], ["已保存文档", "documents"], ["来源原件", "sources"]]) {
      await user.click(screen.getByRole("button", { name: "打开产品导航" }));
      const dialog = screen.getByRole("dialog", { name: "产品导航" });
      const list = within(dialog).getByRole("list", { name: "资料库对象导航" });
      expect(within(list).getAllByRole("button")).toHaveLength(4);
      // Keep one object navigation and one heading ID while the modal is open.
      expect(document.querySelectorAll('ul[aria-label="资料库对象导航"]')).toHaveLength(1);
      expect(document.querySelectorAll("#space-section-heading")).toHaveLength(1);
      await user.click(within(list).getByRole("button", { name: new RegExp(label) }));
      expect(screen.queryByRole("dialog", { name: "产品导航" })).not.toBeInTheDocument();
      expect(screen.getByRole("region", { name: region })).toHaveFocus();
      expect(window.location.hash).toBe("#space=library");
    }
  });

  it("returns focus to the trigger on Escape without choosing an object", async () => {
    const user = userEvent.setup(); render(<App />);
    const trigger = screen.getByRole("button", { name: "打开产品导航" });
    await user.click(trigger); await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(window.location.hash).toBe("#space=library");
  });

  it("keeps unavailable surfaces as explained rows without active object buttons", async () => {
    fixture.surface = "legacy";
    const user = userEvent.setup(); render(<App />);
    await user.click(screen.getByRole("button", { name: "打开产品导航" }));
    const list = within(screen.getByRole("dialog", { name: "产品导航" })).getByRole("list", { name: "资料库对象导航" });
    expect(within(list).queryAllByRole("button")).toHaveLength(0);
    expect(within(list).getAllByText("待开发")).toHaveLength(4);
    await user.click(within(list).getByText("来源锚点"));
    expect(screen.getByRole("dialog", { name: "产品导航" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#space=library");
  });
});
