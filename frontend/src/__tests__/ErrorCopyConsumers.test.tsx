import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { AiAssetPacketPanel } from "../components/AiAssetPacketPanel";
import { FolderIngest } from "../components/FolderIngest";
import { ImportedCoursePanel } from "../components/ImportedCoursePanel";
import { JobContent } from "../components/JobContent";
import { ModelConfigurationPanel } from "../components/ModelConfigurationPanel";
import { PortableDocumentExchange } from "../components/PortableDocumentExchange";
import { DiagnosticCenter } from "../components/DiagnosticConsole";
import { resetDiagnostics } from "../presentation/diagnostics";
import type { AiAsset, AssetContextGrant } from "../api/generated/ai-asset-contract";
import type { DocumentDto } from "../api/generated/core-contract";

const mocks = vi.hoisted(() => ({ call: vi.fn(), prepare: vi.fn(), save: vi.fn(), reopen: vi.fn(), inventory: vi.fn(), diagnose: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: mocks.call }));
vi.mock("../runtime/modelConnection", () => ({ readModelInventory: mocks.inventory, diagnoseModelConnection: mocks.diagnose }));
vi.mock("../presentation/importedCourseStorage", () => ({ prepareCourseImport: mocks.prepare, saveCourseImport: mocks.save, reopenCourseImport: mocks.reopen }));

// Real React consumer/diagnostic components; Core, import storage and model I/O
// are injected finite failures. This is not a native, network or model test.
const raw = "FAULT_ONLY_HTTP_500\n    at Worker.decode (fixture.ts:10:5)";
const problem = () => new Error(raw);
beforeEach(() => {
  resetDiagnostics();
  vi.stubGlobal("crypto", webcrypto);
  vi.stubGlobal("__TAURI__", undefined);
  Object.values(mocks).forEach(mock => mock.mockReset());
  mocks.call.mockImplementation(async (operation: string) => {
    if (operation === "source_jobs") return { source_id: "source", jobs: [], jobs_capped: false };
    if (operation === "documents_list") return { documents: [], next_cursor: null };
    if (operation === "capabilities_list") return {};
    throw problem();
  });
  mocks.prepare.mockRejectedValue(problem());
  mocks.inventory.mockRejectedValue(problem());
});
afterEach(() => { cleanup(); resetDiagnostics(); vi.unstubAllGlobals(); });

function containsOriginal(value: unknown): boolean {
  if (value === raw) return true;
  return !!value && typeof value === "object" && Object.values(value).some(containsOriginal);
}
async function diagnosticOnly(label: string) {
  const selector = `button[data-diagnostic-label="${label}"]`;
  await waitFor(() => expect(document.querySelector(selector)).not.toBeNull());
  expect(document.body.textContent).not.toContain("FAULT_ONLY_HTTP_500");
  expect(screen.queryByRole("dialog", { name: "运行诊断" })).toBeNull();
  const callsBefore = mocks.call.mock.calls.length;
  fireEvent.click(document.querySelector(selector)!);
  const dialog = await screen.findByRole("dialog", { name: "运行诊断" });
  const payloads = Array.from(within(dialog).getByRole("region", { name: "诊断控制台" }).querySelectorAll("pre"))
    .map(element => JSON.parse(element.textContent!));
  expect(payloads.some(containsOriginal)).toBe(true);
  expect(mocks.call).toHaveBeenCalledTimes(callsBefore);
}

it("SIMULATED_IO keeps an asset save failure readable while retaining its original message and frozen request", async () => {
  const asset = { schema: "archeaxis.ai-asset/v1", kind: "rule", content: "参考规则", purpose: "工作参考", scope: [], provenance: [], expires_at: null, state: "adopted", members: [], conflicts: [], revises: null, review: null, source_payload: null } as AiAsset;
  const document = { document_id: "asset", version: 2, title: "资产", source_id: null, source_revision: null, content_sha256: "a".repeat(64), blocks: [], text_projection: "", editor_json: { type: "doc", attrs: { archeaxis_ai_asset: asset }, content: [] } } as DocumentDto;
  render(<><AiAssetPacketPanel asset={document} parseAsset={value => value as AiAsset} parseGrant={value => value as AssetContextGrant} packetCommand={vi.fn()}/><DiagnosticCenter/></>);
  fireEvent.click(screen.getByRole("button", { name: "为当前已采用资产新建授权" }));
  fireEvent.click(screen.getByRole("button", { name: "保存授权候选" }));
  await screen.findByRole("alert");
  expect(screen.getByRole("alert").textContent).toMatch(/[\u3400-\u9fff]/);
  await diagnosticOnly("资产授权错误详细信息");
  expect(mocks.call.mock.calls.filter(([operation]) => operation === "document_create")).toHaveLength(1);
});

it("SIMULATED_IO keeps a course parsing error out of the alert and preserves it only in the explicit diagnostic", async () => {
  render(<><ImportedCoursePanel/><DiagnosticCenter/></>);
  const file = new File(["{}"], "manifest.json", { type: "application/json" });
  Object.defineProperty(file, "arrayBuffer", { value: async () => new TextEncoder().encode("{}").buffer });
  fireEvent.change(screen.getByLabelText("选择课程 manifest.json"), { target: { files: [file] } });
  await screen.findByRole("alert");
  expect(screen.getByRole("alert").textContent).toMatch(/[\u3400-\u9fff]/);
  await diagnosticOnly("课程导入错误详细信息");
  expect(mocks.save).not.toHaveBeenCalled();
});

it("SIMULATED_IO preserves a portable package read error without performing an import", async () => {
  render(<><PortableDocumentExchange saved={null}/><DiagnosticCenter/></>);
  const file = new File([], "package.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => { throw problem(); } });
  fireEvent.change(screen.getByLabelText("选择本地文档包"), { target: { files: [file] } });
  await diagnosticOnly("文档便携包错误详细信息");
  expect(mocks.call).not.toHaveBeenCalled();
});

it("SIMULATED_IO preserves a model connection error without filtering normal LM Studio instructions", async () => {
  render(<><ModelConfigurationPanel/><DiagnosticCenter/></>);
  fireEvent.click(screen.getByRole("button", { name: "一键连接本机 LM Studio" }));
  await diagnosticOnly("最近模型连接错误详细信息");
  expect(mocks.inventory).toHaveBeenCalledTimes(1);
  expect(mocks.call).not.toHaveBeenCalled();
});

it("SIMULATED_IO keeps a folder history failure readable without importing or running anything", async () => {
  render(<><FolderIngest/><DiagnosticCenter/></>);
  fireEvent.click(screen.getByRole("button", { name: "读取历史批次" }));
  await diagnosticOnly("最近文件夹处理错误详细信息");
  expect(mocks.call.mock.calls.map(([operation]) => operation)).toEqual(["ingest_batches_list"]);
});

it("SIMULATED_IO keeps raw conversion details in diagnostics even after opening the failure disclosure", async () => {
  render(<><JobContent sourceId="source" sourceRevision={"a".repeat(64)} name="sample.xlsx"/><DiagnosticCenter/></>);
  fireEvent.click(screen.getByRole("button", { name: "执行真实内容转换" }));
  await screen.findByText(/转换未完成或产物读取失败/);
  fireEvent.click(screen.getByText("上次处理错误详情"));
  await diagnosticOnly("上次处理错误详细信息");
  expect(mocks.call.mock.calls.filter(([operation]) => operation === "job_enqueue")).toHaveLength(1);
  expect(mocks.call.mock.calls.some(([operation]) => operation === "job_execute")).toBe(false);
});
