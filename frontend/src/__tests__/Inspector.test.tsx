import { describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Inspector, InspectionTarget } from "../components/Inspector";
import {DiagnosticCenter} from "../components/DiagnosticConsole";
import { StatusBar } from "../components/StatusBar";

const target: InspectionTarget = { title: "样板条目", source: "CAS 原件 / Rust Core", lifecycle: "已保存；核验与依据分析独立记录" };

function Harness() {
  const [open, setOpen] = useState(true);
  return (
    <>
      <StatusBar activeSpace="library" backendState="available" inspectorOpen={open} onToggleInspector={() => setOpen((value) => !value)} />
      {open ? <Inspector target={target} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

// The panel is unmounted on close, so both controls used to leave the keyboard user somewhere else.
describe("Inspector dismissal", () => {
  it("SIMULATED: Escape closes the panel through the owner's handler", () => {
    const onClose = vi.fn();
    render(<Inspector target={target} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("SIMULATED: the in-panel close returns focus to the status bar trigger", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "关闭检查器" }));
    expect(screen.queryByRole("complementary", { name: "检查器" })).not.toBeInTheDocument();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "展开检查器" }));
  });
});

it("keeps object identity out of the business explanation while publishing complete structured source diagnostics",async()=>{
 const identity={document_id:"doc_"+"x".repeat(120),version:7,content_sha256:"a".repeat(64),source_id:"src_exact",source_revision:"revision_exact"};
 const value={...target,title:"中文长标题".repeat(12),detail:"已关联来源原件；保存不表示已证实。",identityDetails:identity};
 render(<><Inspector target={value}/><DiagnosticCenter/></>);
 const inspector=screen.getByRole("complementary",{name:"检查器"});expect(inspector).toHaveTextContent(value.title);expect(inspector).toHaveTextContent(value.detail);expect(inspector).not.toHaveTextContent(identity.document_id);expect(inspector).not.toHaveTextContent(identity.content_sha256);
 await userEvent.setup().click(screen.getByRole("button",{name:"查看来源详情：条目来源详细信息"}));
 expect(screen.getByRole("dialog").querySelector("pre")?.textContent).toBe(JSON.stringify(identity,null,2));expect(value.identityDetails).toBe(identity);
});
