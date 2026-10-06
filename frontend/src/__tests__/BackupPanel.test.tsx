import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BackupPanel } from "../components/BackupPanel";
const bridge=vi.hoisted(()=>({call:vi.fn()}));vi.mock("../api/core",()=>({coreCommand:bridge.call}));
const receipt={backup_id:"a".repeat(32),filename:`${"a".repeat(32)}.sqlite`,sha256:"b".repeat(64),bytes:4096,schema_version:"9",sqlite_version:"3.51.3",source_sha_list:["c".repeat(64)],verified:true};
describe("owned consistent backup",()=>{
 beforeEach(()=>bridge.call.mockReset());
 it("creates without any UI path and displays actual hashes and versions",async()=>{
  bridge.call.mockResolvedValue(receipt);render(<BackupPanel/>);await userEvent.setup().click(screen.getByRole("button",{name:"创建一致备份"}));
  expect(await screen.findByText(receipt.filename)).toBeInTheDocument();expect(screen.getByText(/SHA-256/)).toHaveTextContent(receipt.sha256);expect(screen.getByText(/数据结构版本/)).toHaveTextContent("SQLite 3.51.3");
  expect(bridge.call).toHaveBeenCalledWith("workspace_backup",{body:{}});expect(screen.getByRole("status")).toHaveTextContent("独立恢复尚需单独验证");
 });
 it("refuses empty or invalid artifact proof and preserves an earlier valid receipt",async()=>{
  bridge.call.mockResolvedValueOnce(receipt).mockResolvedValueOnce({backups:[{...receipt,sha256:"",bytes:0}]});
  render(<BackupPanel/>);const user=userEvent.setup();await user.click(screen.getByRole("button",{name:"创建一致备份"}));await screen.findByText(receipt.filename);await user.click(screen.getByRole("button",{name:"刷新备份产物"}));
  expect(await screen.findByText(/列表读取失败/)).toBeInTheDocument();expect(screen.getByText(receipt.filename)).toBeInTheDocument();
 });
});
