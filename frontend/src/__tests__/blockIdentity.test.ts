import { describe, expect, it } from "vitest";
import { preserveBlockIdentities } from "../presentation/blockIdentity";

const para = (text: string, attrs: Record<string, unknown> = {}) => ({ type: "paragraph", attrs, content: [{ type: "text", text }] });
const doc = (content: unknown[]) => ({ type: "doc", content }) as never;
const blockId = (node: { attrs?: unknown }) => (node.attrs as Record<string, unknown> | undefined)?.block_id;

describe("block identity preservation", () => {
  it("carries the previous block and canvas node identity onto a rewritten body", () => {
    const previous = doc([para("原画布中文", { block_id: "b1", canvas_node_id: "n1" })]);
    const next = preserveBlockIdentities(previous, doc([para("修改后画布中文")]));
    expect(blockId(next.content![0])).toBe("b1");
    expect((next.content![0].attrs as Record<string, unknown>).canvas_node_id).toBe("n1");
  });
  it("matches identical text before falling back to position", () => {
    const previous = doc([para("一", { block_id: "b1" }), para("二", { block_id: "b2" })]);
    const next = preserveBlockIdentities(previous, doc([para("二"), para("一")]));
    expect(blockId(next.content![0])).toBe("b2");
    expect(blockId(next.content![1])).toBe("b1");
  });
  it("never reuses one identity twice", () => {
    const previous = doc([para("一", { block_id: "b1" })]);
    const next = preserveBlockIdentities(previous, doc([para("新一"), para("新二")]));
    expect(blockId(next.content![0])).toBe("b1");
    expect(blockId(next.content![1])).toBeUndefined();
  });
  it("replaces a freshly minted identity with the one the rewritten block had", () => {
    const previous = doc([para("原画布中文", { block_id: "b1", canvas_node_id: "n1" })]);
    const next = preserveBlockIdentities(previous, doc([para("修改后画布中文", { block_id: "fresh" })]));
    expect(blockId(next.content![0])).toBe("b1");
    expect((next.content![0].attrs as Record<string, unknown>).canvas_node_id).toBe("n1");
  });
  it("keeps an identity the block still owns and restores its canvas node", () => {
    const previous = doc([para("原画布中文", { block_id: "b1", canvas_node_id: "n1" })]);
    const next = preserveBlockIdentities(previous, doc([para("原画布中文改了", { block_id: "b1" })]));
    expect(blockId(next.content![0])).toBe("b1");
    expect((next.content![0].attrs as Record<string, unknown>).canvas_node_id).toBe("n1");
  });
  it("leaves a body that kept some identities to the editor", () => {
    const previous = doc([para("一", { block_id: "b1" }), para("二", { block_id: "b2" })]);
    const next = preserveBlockIdentities(previous, doc([para("新一"), para("新二", { block_id: "b1" })]));
    expect(blockId(next.content![1])).toBe("b1");
    expect(blockId(next.content![0])).toBeUndefined();
  });
  it("leaves a body without previous blocks untouched", () => {
    const next = preserveBlockIdentities(undefined, doc([para("新")]));
    expect(blockId(next.content![0])).toBeUndefined();
  });
});
