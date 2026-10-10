// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ContextNav } from "../components/ContextNav";
import { NavTrail } from "../components/NavTrail";
import { SPACES } from "../spaces/spaces";
import { canonicalSurface } from "../spaces/SpaceView";
import { CanonicalLearningSpace } from "../spaces/CanonicalLearningSpace";
import { CanonicalKnowledgeSpace } from "../spaces/CanonicalKnowledgeSpace";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { SPACE_SECTIONS, spaceSectionsFor, validateSpaceSections } from "../presentation/spaceSections";
import { resolveLegacySpaceAlias } from "../presentation/navigation";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));

describe("UI-02 secondary level covers every space", () => {
  it("keeps the section registry self-consistent: unique ids, a real target or a named missing contract", () => {
    expect(validateSpaceSections()).toEqual([]);
    for (const space of SPACES) {
      expect(SPACE_SECTIONS[space.id]?.length, `space ${space.id} has no secondary group`).toBeGreaterThan(0);
    }
  });

  it("keeps the library group at the four object lists the installed-candidate probe counts", () => {
    // scripts/probes/aaos01_tauri_webdriver_loop.py waits for exactly four buttons in
    // ul[aria-label='资料库对象导航']; a silent change here breaks that real-host evidence.
    expect(spaceSectionsFor("library", "canonical_library").map((section) => section.id))
      .toEqual(["sources", "documents", "anchors", "versions"]);
  });

  it("gives review its own secondary group instead of hiding it behind the learning space", () => {
    const sections = spaceSectionsFor("learning", "canonical_learning");
    expect(sections.map((section) => section.id)).toContain("review");
    render(<ContextNav active="learning" onNavigate={() => {}} sections={sections} onSection={() => {}} />);
    const group = screen.getByRole("list", { name: "学习对象导航" });
    expect(within(group).getByRole("button", { name: /复习队列/ })).toBeInTheDocument();
    // The same label must not be reachable only through the related-spaces list.
    expect(within(screen.getByRole("list", { name: "相关空间" })).queryByRole("button", { name: /复习/ })).not.toBeInTheDocument();
    expect(resolveLegacySpaceAlias("review")).toBe("learning");
  });

  it("states which contract is missing instead of inventing an entry", () => {
    const sections = spaceSectionsFor("intake", "canonical_library");
    const todo = sections.filter((section) => section.state === "todo");
    expect(todo.map((section) => section.id)).toContain("url");
    expect(todo.every((section) => section.reason && section.reason.length > 8)).toBe(true);
  });

  it("reaches and activates a secondary group by keyboard only", async () => {
    const onSection = vi.fn();
    render(<ContextNav active="library" onNavigate={() => {}} sections={spaceSectionsFor("library", "canonical_library")} activeSection="sources" onSection={onSection} />);
    const user = userEvent.setup();
    const target = screen.getByRole("button", { name: /来源锚点/ });
    let steps = 0;
    while (document.activeElement !== target && steps < 40) {
      await user.tab();
      steps += 1;
    }
    expect(document.activeElement, `tab reachability after ${steps} stops`).toBe(target);
    await user.keyboard("{Enter}");
    expect(onSection).toHaveBeenCalledWith(expect.objectContaining({ id: "anchors" }));
  });

  it("resolves the surface from the same predicate the shell routes on", () => {
    expect(canonicalSurface("vault", true)).toBe("canonical_knowledge");
    expect(canonicalSurface("vault", false)).toBe("canonical_knowledge");
    expect(canonicalSurface("workspace", false)).toBe("canonical_workspace");
    expect(canonicalSurface("workspace", true)).toBe("canonical_workspace");
    expect(canonicalSurface("settings", true)).toBe("canonical_capabilities");
  });
});

describe("UI-02 tertiary object path", () => {
  it("shows the real object identity and keeps every earlier level navigable", () => {
    const onJump = vi.fn();
    render(<NavTrail onJump={onJump} levels={[
      { id: "space:library", label: "资料库", region: "sources" },
      { id: "section:sources", label: "来源原件", region: "sources" },
      { id: "source:src-1", label: "golden-note.md", detail: "src-1@sha256:abc", region: "sources" },
    ]} />);

    const trail = screen.getByRole("navigation", { name: "对象导航路径" });
    expect(within(trail).getByText("golden-note.md")).toHaveAttribute("aria-current", "location");
    expect(within(trail).getByText("src-1@sha256:abc")).toBeInTheDocument();
    fireEvent.click(within(trail).getByRole("button", { name: /来源原件/ }));
    expect(onJump).toHaveBeenCalledWith("sources");
  });

  it("renders nothing when no object is open, so the shell cannot imply a path", () => {
    const { container } = render(<NavTrail onJump={() => {}} levels={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("UI-02 primary level stays labelled when the window narrows", () => {
  const src = join(dirname(fileURLToPath(import.meta.url)), "..");
  const sheet = ["design-system/tokens.css", "design-system/themes.css", "components/content.css"]
    .map((file) => readFileSync(join(src, file), "utf8"))
    .join("\n");

  it("has no rule that hides a primary rail label at any width", () => {
    expect(sheet).not.toMatch(/\.space-rail-item[^{]*span[^{]*\{[^}]*display:\s*none/);
  });

  it("narrows the shell instead of dropping the section switcher", () => {
    expect(sheet).toMatch(/\.context-subnav\s*\{[^}]*width:\s*168px/);
  });
});

describe("UI-02 levels reach the objects Core actually returns", () => {
  beforeEach(() => {
    bridge.call.mockReset();
  });

  it("labels the library section regions the secondary group points at", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "sources_list") return { sources: [] };
      if (operation === "documents_list") return { documents: [] };
      throw new Error(operation);
    });
    const { rerender } = render(<CanonicalLibrarySpace navigation={{ section: "sources", sequence: 0 }} />);
    await screen.findByRole("heading", { name: "资料库" });
    rerender(<CanonicalLibrarySpace navigation={{ section: "anchors", sequence: 1 }} />);
    const region = document.querySelector('[data-section="anchors"]');
    expect(region).not.toBeNull();
    expect(document.activeElement).toBe(region);
  });

  it("publishes the real learning item key as the tertiary level of the review group", async () => {
    bridge.call.mockImplementation(async (operation: string) => {
      if (operation === "learning_items") return { items: [{ item_key: "item_ui02", next_review: "2026-10-09T00:00:00Z" }] };
      if (operation === "learning_state") return { item_key: "item_ui02", learner: {}, machine: { status: "not_recorded" } };
      if (operation === "learning_history") return { events: [] };
      throw new Error(operation);
    });
    const onTrail = vi.fn();
    render(<CanonicalLearningSpace onTrail={onTrail} />);
    const queue = await screen.findByLabelText("复习队列");
    expect(queue).toHaveAttribute("data-section", "review");
    await userEvent.setup().click(screen.getByRole("button", { name: "item_ui02" }));
    await waitFor(() => expect(onTrail).toHaveBeenCalledWith([
      expect.objectContaining({ id: "section:review", region: "review" }),
      expect.objectContaining({ id: "item:item_ui02", label: "item_ui02", detail: "下次复习 2026-10-09T00:00:00Z", region: "review" }),
    ]));
  });

  it("publishes the knowledge identity and version returned by Core, not a placeholder", async () => {
    bridge.call.mockImplementation(async (operation: string, payload?: Record<string, unknown>) => {
      if (operation === "search") return { items: [{ knowledge_id: "knd_ui02", head: "样板候选", status: "candidate", active: true }], transforms: [], documents: [], count: 1, transform_count: 0 };
      if (operation === "knowledge_get") return { knowledge_id: String((payload as Record<string, unknown>).id), title: "样板候选", body: "正文", version: "3", status: "candidate" };
      if (operation === "knowledge_qualification") return { knowledge_id: "knd_ui02", qualification: "not_provided" };
      throw new Error(operation);
    });
    const onTrail = vi.fn();
    render(<CanonicalKnowledgeSpace onTrail={onTrail} />);
    expect(screen.getByLabelText("知识候选列表")).toHaveAttribute("data-section", "candidates");
    expect(screen.getByLabelText("来源提取文本列表")).toHaveAttribute("data-section", "transforms");
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("搜索内容"), "样板");
    await user.click(screen.getByRole("button", { name: "搜索" }));
    await user.click(await screen.findByRole("button", { name: "样板候选" }));
    await waitFor(() => expect(onTrail).toHaveBeenCalledWith([
      expect.objectContaining({ id: "section:candidates", region: "candidates" }),
      expect.objectContaining({ id: "knowledge:knd_ui02", detail: "knd_ui02 · 版本 3 · candidate", region: "candidates" }),
    ]));
  });
});
