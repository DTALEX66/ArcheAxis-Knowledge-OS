import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../app/App";
vi.mock("../spaces/SpaceView", async importOriginal => {
  const actual=await importOriginal<typeof import("../spaces/SpaceView")>();
  return {...actual,SpaceView:(props:{uiPageId?:string;initialDocumentId?:string;initialLearningItemKey?:string;onOpenDocument?:(id:string)=>void;onReviewItem?:(id:string)=>void})=><section aria-label="SIMULATED navigation port"><output data-testid="page">{props.uiPageId}</output><output data-testid="document">{props.initialDocumentId}</output><output data-testid="item">{props.initialLearningItemKey}</output><button onClick={()=>props.onOpenDocument?.("doc_actual_selection")}>选择真实ID</button><button onClick={()=>props.onReviewItem?.("review_actual_key")}>复习真实key</button></section>};
});
describe("actual App navigation guard with SIMULATED child ports",()=>{
  afterEach(()=>{vi.restoreAllMocks();window.history.replaceState(null,"","#page=01");});
  it("opens shell tools without remounting the active surface, while the global menu still guards dirty navigation",async()=>{
    window.history.replaceState(null,"","#page=01");render(<App/>);
    const surface = screen.getByTestId("page");
    const confirm = vi.spyOn(window,"confirm").mockReturnValue(false);
    act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"shell-tools-test",dirty:true}})));
    fireEvent.click(screen.getByRole("button",{name:"界面与工具设置"}));
    const tools=screen.getByRole("dialog",{name:"界面与工具"});
    expect(within(tools).getByRole("combobox",{name:"界面主题"})).toBeInTheDocument();
    expect(screen.queryByLabelText("导航呈现")).not.toBeInTheDocument();
    expect(screen.getByTestId("page")).toBe(surface);
    expect(confirm).not.toHaveBeenCalled();
    await userEvent.setup().keyboard("{Escape}");
    openReader();
    expect(confirm).toHaveBeenCalled();expect(surface).toHaveTextContent("01");
    expect(window.location.hash).toBe("#page=01");
  });
  it("retains a selected Document and same-page draft without resetting it through navigate",()=>{
    window.history.replaceState(null,"","#page=01");render(<App/>);
    fireEvent.click(screen.getByRole("button",{name:"选择真实ID"}));expect(screen.getByTestId("document")).toHaveTextContent("doc_actual_selection");
    const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
    act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"selection",dirty:true}})));
    openReader();expect(confirm).not.toHaveBeenCalled();expect(screen.getByTestId("page")).toHaveTextContent("03");
    act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"selection",dirty:false}})));
    fireEvent.click(within(screen.getByRole("navigation",{name:"工作空间快捷导航"})).getByRole("button",{name:"工作台"}));fireEvent.click(within(screen.getByRole("navigation",{name:"工作空间快捷导航"})).getByRole("button",{name:"知识"}));openReader();
    expect(screen.getByTestId("document")).toHaveTextContent("doc_actual_selection");expect(window.location.hash).toBe("#page=03");
  });
  it("does not set a review target on refused, composing or restoring navigation",()=>{
    window.history.replaceState(null,"","#page=01");render(<App/>);const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
    act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"draft",dirty:true}})));
    fireEvent.click(screen.getByRole("button",{name:"复习真实key"}));expect(screen.getByTestId("item")).toBeEmptyDOMElement();expect(window.location.hash).toBe("#page=01");expect(confirm).toHaveBeenCalled();
    act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"draft",dirty:false}})));
    fireEvent.compositionStart(window);fireEvent.click(screen.getByRole("button",{name:"复习真实key"}));expect(screen.getByTestId("item")).toBeEmptyDOMElement();fireEvent.compositionEnd(window);
    act(()=>window.dispatchEvent(new Event("workspace-restore-start")));fireEvent.click(screen.getByRole("button",{name:"复习真实key"}));expect(screen.getByTestId("item")).toBeEmptyDOMElement();act(()=>window.dispatchEvent(new Event("workspace-restore-finish")));
    fireEvent.click(screen.getByRole("button",{name:"复习真实key"}));expect(screen.getByTestId("item")).toHaveTextContent("review_actual_key");expect(window.location.hash).toBe("#page=06");
    act(()=>window.dispatchEvent(new CustomEvent("workspace-invalidated",{detail:{confirmed:true}})));expect(screen.getByTestId("item")).toBeEmptyDOMElement();expect(screen.getByTestId("document")).toBeEmptyDOMElement();
  });
});

function openReader() {
 const menu=screen.getByRole("navigation",{name:"应用菜单"});
 const summary=within(menu).getByText("知识",{selector:"summary"});
 fireEvent.click(summary); fireEvent.click(within(summary.parentElement!).getByRole("button",{name:"阅读与编辑"}));
}

// These shell/guard tests isolate onboarding; FirstUseGuideApp and FirstUseGuide test it directly.
vi.mock("../components/FirstUseGuide", async importOriginal => ({ ...await importOriginal<object>(), FirstUseGuide: () => null, requestFirstUseGuide: vi.fn() }));
