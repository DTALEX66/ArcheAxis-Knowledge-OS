import { afterEach, describe, expect, it, vi } from "vitest";
import { createHash, webcrypto } from "node:crypto";
import { readFileSync } from "node:fs";
import { basename, resolve } from "node:path";
import { assertHandoffDto } from "../api/generated/project-handoff";
import { assertPreview, assertSnapshot, parseContextProposal, verifyProposalFingerprint } from "../api/projectHandoff";
import { coreCommand } from "../api/core";

const contracts = resolve(process.cwd(), basename(process.cwd()) === "frontend" ? "../packages/contracts/v2" : "packages/contracts/v2");
const previews = JSON.parse(readFileSync(resolve(contracts, "project-handoff-preview.cases.json"), "utf8"));
const snapshots: Array<{name:string;value:Record<string,any>;schema_valid:boolean}> = JSON.parse(readFileSync(resolve(contracts, "project-handoff-snapshot.cases.json"), "utf8"));
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); delete window.__TAURI__; });
function setup() {
  vi.useFakeTimers(); vi.setSystemTime(previews[0].now_ms); vi.stubGlobal("crypto", webcrypto);
  const proposal = parseContextProposal(JSON.stringify(previews[0].value.proposal));
  return { proposal, preview: structuredClone(previews[0].value), snapshot: structuredClone(snapshots[0].value) };
}
describe("fixed local handoff consumption", () => {
  it.each(snapshots)("enforces shared snapshot schema: $name", (sample) => {
    const decode = () => assertHandoffDto("Snapshot", sample.value);
    if (sample.schema_valid) expect(decode).not.toThrow(); else expect(decode).toThrow();
  });
  it("rejects ambiguous duplicate keys, escaped duplicates, oversized UTF8 and non-context proposals before sending", () => {
    const { proposal } = setup();
    const text = JSON.stringify(proposal);
    for (const field of ['"schema":"wrong",', '"sch\\u0065ma":"wrong",']) expect(() => parseContextProposal("{" + field + text.slice(1))).toThrow(/重复/);
    expect(() => parseContextProposal("中文".repeat(22_000))).toThrow(/64KiB/);
    expect(() => parseContextProposal(JSON.stringify({...proposal, token:"fixture"}))).toThrow();
    expect(() => parseContextProposal(text.replace('"kind":"context"', '"kind":"receipt"'))).toThrow();
  });
  it("checks semantic ranges and rejects unsafe numeric document identity", () => {
    const { proposal } = setup();
    for (const selection of [{kind:"text_range",block_id:"b",start_utf16:2,end_utf16:1}, {kind:"time_range",start_ms:4,end_ms:4}, {kind:"page_range",first_page:4,last_page:1}]) {
      const invalid=structuredClone(proposal); invalid.payload.source.selection=selection as typeof invalid.payload.source.selection;
      expect(() => parseContextProposal(JSON.stringify(invalid))).toThrow();
    }
    proposal.payload.source.reference.version=Number.MAX_SAFE_INTEGER+1;
    expect(() => parseContextProposal(JSON.stringify(proposal))).toThrow();
  });
  it("binds preview to the original context and checks Core-compatible canonical fingerprint", async () => {
    const { proposal, preview } = setup();
    function sorted(v: unknown): unknown { return Array.isArray(v) ? v.map(sorted) : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>[k,sorted(x)])) : v; }
    preview.proposal_sha256=createHash("sha256").update("archeaxis.project-handoff/v1\0").update(JSON.stringify(sorted(proposal))).digest("hex");
    expect(assertPreview(preview,proposal)).toEqual(preview);
    await expect(verifyProposalFingerprint(proposal,preview.proposal_sha256)).resolves.toBeUndefined();
    await expect(verifyProposalFingerprint(proposal,"f".repeat(64))).rejects.toThrow(/指纹/);
    preview.proposal.consumer.instance_id="f".repeat(32);
    expect(() => assertPreview(preview,proposal)).toThrow(/当前引用/);
  });
  it("requires snapshot identity, epoch, digest and fresh deadline for both current and historical body", () => {
    const { proposal, snapshot } = setup();
    for (const state of ["CURRENT","STALE"]) expect(assertSnapshot({...snapshot,reference_state:state},proposal,snapshot.proposal_sha256).reference_state).toBe(state);
    const wrong=structuredClone(snapshot);wrong.reference.version++;
    expect(() => assertSnapshot(wrong,proposal,snapshot.proposal_sha256)).toThrow();
    wrong.reference=snapshot.reference;wrong.producer.restore_epoch="f".repeat(32);
    expect(() => assertSnapshot(wrong,proposal,snapshot.proposal_sha256)).toThrow();
    expect(() => assertSnapshot(snapshot,proposal,"b".repeat(64))).toThrow();
    vi.setSystemTime(proposal.expires_at_ms);
    expect(() => assertSnapshot(snapshot,proposal,snapshot.proposal_sha256)).toThrow(/过期/);
  });
  it("finite Core client rejects unknown/body privilege fields and never treats HTTP errors as snapshots", async () => {
    const { proposal, snapshot } = setup();
    const invoke=vi.fn().mockResolvedValue({status:200,body:snapshot});window.__TAURI__={core:{invoke}};
    await expect(coreCommand("project_handoff_snapshot",{body:proposal})).resolves.toEqual(snapshot);
    for (const body of [{...snapshot,token:"fixture"},{...snapshot,grants_execution:true},{...snapshot,scope:"OBSERVER_READ"}]) {
      invoke.mockResolvedValue({status:200,body});await expect(coreCommand("project_handoff_snapshot",{body:proposal})).rejects.toThrow(/格式/);
    }
    invoke.mockResolvedValue({status:409,body:{code:"HANDOFF_SNAPSHOT_IDENTITY_MISMATCH"}});
    await expect(coreCommand("project_handoff_snapshot",{body:proposal})).rejects.toThrow(/工作区身份或恢复版本/);
  });
});
