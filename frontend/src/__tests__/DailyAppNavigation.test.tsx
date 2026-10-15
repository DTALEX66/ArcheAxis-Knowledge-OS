import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { App } from "../app/App";
vi.mock("../spaces/SpaceView", async importOriginal => {
  const actual=await importOriginal<typeof import("../spaces/SpaceView")>();
  return {...actual,SpaceView:(props:{uiPageId?:string;initialDocumentId?:string;initialLearningItemKey?:string;onOpenDocument?:(id:string)=>void;onReviewItem?:(id:string)=>void})=><section aria-label="SIMULATED navigation port"><output data-testid="page">{props.uiPageId}</output><output data-testid="document">{props.initialDocumentId}</output><output data-testid="item">{props.initialLearningItemKey}</output><button onClick={()=>props.onOpenDocument?.("doc_actual_selection")}>选择真实ID</button><button onClick={()=>props.onReviewItem?.("review_actual_key")}>复习真实key</button></section>};
});
describe("actual App navigation guard with SIMULATED child ports",()=>{
  afterEach(()=>{vi.restoreAllMocks();localStorage.removeItem("aaos.navigation-appearance.v1");window.history.replaceState(null,"","#page=01");});
  it("changes chrome without remounting the active surface or bypassing dirty navigation guards",()=>{
    window.history.replaceState(null,"","#page=01");render(<App/>);
    const surface = screen.getByTestId("page");
    const confirm = vi.spyOn(window,"confirm").mockReturnValue(false);
    act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"top-nav-test",dirty:true}})));
    fireEvent.click(screen.getByLabelText("界面设置"));
    fireEvent.change(screen.getByLabelText("导航呈现"),{target:{value:"top"}});
    expect(screen.getByTestId("page")).toBe(surface);
    expect(confirm).not.toHaveBeenCalled();
    expect(localStorage.getItem("aaos.navigation-appearance.v1")).toBe("top");
    fireEvent.click(screen.getByRole("navigation",{name:"顶部空间导航"}).querySelector("[data-top-page='02']")!);
    fireEvent.click(screen.getByRole("menuitem",{name:"阅读与编辑"}));
    expect(confirm).toHaveBeenCalled();expect(surface).toHaveTextContent("01");
    expect(window.location.hash).toBe("#page=01");
  });
  it("retains a selected Document and same-page draft without resetting it through navigate",()=>{
    window.history.replaceState(null,"","#page=01");render(<App/>);
    fireEvent.click(screen.getByRole("button",{name:"选择真实ID"}));expect(screen.getByTestId("document")).toHaveTextContent("doc_actual_selection");
    const confirm=vi.spyOn(window,"confirm").mockReturnValue(false);
    act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"selection",dirty:true}})));
    fireEvent.click(screen.getByRole("button",{name:"阅读与编辑"}));expect(confirm).not.toHaveBeenCalled();expect(screen.getByTestId("page")).toHaveTextContent("03");
    act(()=>window.dispatchEvent(new CustomEvent("archeaxis-draft-dirty",{detail:{owner:"selection",dirty:false}})));
    fireEvent.click(screen.getByRole("button",{name:"工作台"}));fireEvent.click(screen.getByRole("button",{name:"知识"}));fireEvent.click(screen.getByRole("button",{name:"阅读与编辑"}));
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
