import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UiHostContractPanel } from "../components/UiHostContractPanel";
const read=vi.hoisted(()=>vi.fn());vi.mock("../api/uiHost",()=>({readHostModelInventory:read}));
describe("model inventory host consumer",()=>{
 it("queries only on explicit action and preserves the inventory evidence boundary",async()=>{
  read.mockResolvedValue({status:"READ_VERIFIED",listed_model_count:2});render(<UiHostContractPanel/>);
  expect(read).not.toHaveBeenCalled();await userEvent.setup().click(screen.getByRole("button",{name:"通过宿主读取模型清单"}));
  await screen.findByText(/2 个模型；加载状态未知，未执行推理/);expect(read).toHaveBeenCalledTimes(1);
 });
});
