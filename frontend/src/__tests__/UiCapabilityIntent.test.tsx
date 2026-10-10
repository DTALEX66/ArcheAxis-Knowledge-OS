import { CAPABILITY_NAVIGATION_ENTRIES, navigationEntryMatches } from "../presentation/navigation";
import { CAPABILITY_CATALOG } from "../api/generated/capability-catalog";
import { createHash } from "node:crypto";
import originalText from "./fixtures/ui-capability-details-original.json?raw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { UI_CAPABILITY_INTENT, UI_CAPABILITY_SOURCE } from "../presentation/uiCapabilityIntent";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { UI_DAILY_ENTRY_POINTS, UI_FIXED_ENTRY_POINTS } from "../presentation/uiPages";
import { AAOS_THEMES, applyTheme, readThemePreference } from "../design-system/theme";
import { SpaceRail } from "../components/SpaceRail";
import { SPACES } from "../spaces/spaces";
const bridge=vi.hoisted(()=>({call:vi.fn()}));
vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const originalBytes=originalText;
const original=JSON.parse(originalText) as Record<string,string[]>;
const expected=Object.fromEntries(Object.entries(original).map(([id,items])=>[`CAP-${id}`,items]));
describe("preserved independent design intentions",()=>{
  beforeEach(()=>{bridge.call.mockReset();});
  it.each(["CAP-0090","CAP-0100","CAP-0110"])("shows pending research/collection qualifications for %s without changing authored intent",async(id)=>{
    bridge.call.mockResolvedValue({capabilities:[]});
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId={id}/>);
    const boundary=await screen.findByRole("region",{name:"集合与研究实施边界"});
    expect(boundary).toHaveTextContent("未执行");
    expect(boundary).toHaveTextContent("安装态、真人验收与来源平台语义资格仍分别核验");
    if(id==="CAP-0100")for(const term of ["Rollup","公式方言","单位换算","时区","往返语义"])expect(boundary).toHaveTextContent(term);
    if(id==="CAP-0110")expect(boundary).toHaveTextContent("GraphRAG");
    expect(within(screen.getByRole("region",{name:"设计细项与独立证据"})).getAllByRole("listitem")).toHaveLength(expected[id].length);
  });
  it("retains all 16 parent mappings and all 186 authored child strings in their original order",()=>{
    const hash="fc55ef3c996287f13bf6eb3711159ded1a228e2d27e928eb879d71dd24e4cf4f";
    expect(createHash("sha256").update(originalBytes).digest("hex")).toBe(hash);
    expect(UI_CAPABILITY_SOURCE.sha256).toBe(hash);
    expect(Object.keys(expected)).toHaveLength(16);
    expect(Object.values(expected).flat()).toHaveLength(186);
    expect(UI_CAPABILITY_INTENT).toEqual(expected);
    expect(UI_CAPABILITY_SOURCE.evidence).toContain("independent child evidence UNKNOWN");
  });
  it.each(Object.keys(expected))("SIMULATED: healthy parent %s cannot promote a child to independently verified",async(id)=>{
    const parent=CAPABILITY_CATALOG.entries.find(entry=>entry.atlas.capability_id===id)!;
    bridge.call.mockResolvedValue({capabilities:parent.implementation.runtime_capabilities.map(capability=>({capability,enabled:true,health:"handshake_ready"}))});
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} selectedCapabilityId={id}/>);
    const detail=await screen.findByRole("region",{name:"设计细项与独立证据"});
    expect(detail).toHaveTextContent("父能力声明和运行握手不证明这些细项全部完成");
    const items=within(detail).getAllByRole("listitem");
    expect(items).toHaveLength(expected[id].length);
    expected[id].forEach((intent,index)=>expect(items[index]).toHaveTextContent(`${intent} · 独立证据 UNKNOWN`));
    expect(detail).not.toHaveTextContent(/独立证据 (PASS|REAL|VERIFIED|已实现|已完成)/);
  });
  it("discovers every original child phrase through its stable parent in the shared command and capability search projection",()=>{
    for(const [id,intents] of Object.entries(expected)){
      const parent=CAPABILITY_NAVIGATION_ENTRIES.find(entry=>entry.entry_id===id);
      expect(parent,`missing parent ${id}`).toBeDefined();
      for(const intent of intents)expect(navigationEntryMatches(parent!,intent),`${id}: ${intent}`).toBe(true);
    }
  });  it("keeps the new five-domain navigation while the former palettes change only presentation",()=>{
    expect(AAOS_THEMES.map(theme=>theme.id)).toEqual(["blueprint","blueprint-light","black","white","cosmic"]);
    expect(readThemePreference({getItem:()=>null})).toBe("blueprint");
    render(<SpaceRail active="workspace" spaces={SPACES} onNavigate={vi.fn()} pageId="01" onPage={vi.fn()}/>);
    const rail=screen.getByRole("navigation",{name:"主空间导航"});
    for(const theme of ["black","white","cosmic"] as const){
      applyTheme(theme);
      for(const entry of [...UI_DAILY_ENTRY_POINTS,...UI_FIXED_ENTRY_POINTS])expect(within(rail).getByRole("button",{name:entry.label})).toBeInTheDocument();
      expect(within(rail).queryByRole("button",{name:"研究空间"})).toBeNull();
      expect(rail.querySelectorAll("[data-space-id]")).toHaveLength(0);
      expect(rail.querySelectorAll("[data-page-id]")).toHaveLength(7);
    }
    applyTheme("blueprint");
  });
});
