import {render,screen,fireEvent} from "@testing-library/react";
import {expect,it,vi} from "vitest";
import {CanonicalControlledAiSpace} from "../spaces/CanonicalControlledAiSpace";
vi.mock("../spaces/CanonicalAiAssetsSpace",()=>({CanonicalAiAssetsSpace:()=> <label>资产保留草稿<input defaultValue=""/></label>}));
vi.mock("../spaces/CanonicalContextSpace",()=>({CanonicalContextSpace:()=> <label>上下文保留草稿<input defaultValue=""/></label>}));
vi.mock("../spaces/CanonicalAiJourneySpace",()=>({CanonicalAiJourneySpace:()=> <p>纠正与复测</p>}));
vi.mock("../spaces/CanonicalMachineReceiptsSpace",()=>({CanonicalMachineReceiptsSpace:()=> <p>任务记录</p>}));
vi.mock("../components/CharacterMemoryPanel",()=>({CharacterMemoryPanel:()=>null}));
it("shows one object editor and retains both mounted drafts while switching workspace modes",()=>{
 render(<CanonicalControlledAiSpace pageId="13" onOpenPage={vi.fn()}/>);
 const context=screen.getByLabelText("上下文保留草稿"),asset=screen.getByLabelText("资产保留草稿");
 expect(context).toBeVisible();expect(asset).not.toBeVisible();
 fireEvent.change(context,{target:{value:"上下文未保存内容"}});
 fireEvent.click(screen.getByRole("button",{name:"AI 资产候选"}));
 expect(context).not.toBeVisible();expect(asset).toBeVisible();
 fireEvent.change(asset,{target:{value:"资产未保存内容"}});
 fireEvent.click(screen.getByRole("button",{name:"授权上下文"}));
 expect(context).toBeVisible();expect(context).toHaveValue("上下文未保存内容");expect(asset).toHaveValue("资产未保存内容");
});
