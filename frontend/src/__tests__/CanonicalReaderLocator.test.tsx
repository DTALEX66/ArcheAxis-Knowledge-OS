/**
 * Target: frontend/src/__tests__/CanonicalReaderLocator.test.tsx
 * Evidence: SYNTHETIC only. Source bytes, hashes, documents, anchors and Core
 * responses are local fixtures. This is not actual PDF or native qualification.
 * CanonicalLibrarySpace, its handlers and DOM selection remain real. Only the
 * Core boundary and the editor's activation gesture are substituted.
 * Read snapshot (2026-10-22; parent is fixing the source independently):
 * CanonicalLibrarySpace.tsx SHA256 65f63360ea3940e88ccc305b83bf5d05a74048a15bbbf10a8e3dfd0857be4d77
 * DocumentEditor.tsx SHA256 efba5c846300f272dd4bb7404ff3356fe779e64f15f7335832ca025121d50eba
 * SemanticReadingLayout.test.tsx SHA256 757b41bfe8c7b2bdada99bef28db415f8fff8c7a646fe2e34172fb7199ef7fb6
 */
import type { JSONContent } from "@tiptap/core";
import { createHash, webcrypto } from "node:crypto";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  assertCoreDto,
  type AnchorResolutionDto,
  type DocumentDto,
} from "../api/generated/core-contract";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";

const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
vi.mock("../components/DocumentEditor", () => ({
  DocumentEditor: ({ content, onReferenceActivate }: {
    content: JSONContent;
    onReferenceActivate?: (attributes: Record<string, unknown>) => void;
  }) => {
    const findReference = (node: JSONContent): JSONContent | undefined => {
      if (node.type === "evidenceReference") return node;
      for (const child of node.content ?? []) {
        const found = findReference(child);
        if (found) return found;
      }
      return undefined;
    };
    // Read the stored evidenceReference node, then invoke the actual callback
    // received from the real reader. Never replace jump or original rendering.
    const reference = findReference(content);
    return <button type="button" disabled={!reference?.attrs || !onReferenceActivate}
      onClick={() => onReferenceActivate?.(reference!.attrs!)}>
      激活 {String(reference?.attrs?.excerpt ?? "缺少证据引用")}
    </button>;
  },
}));

function fixture(suffix: string, prefix: string, selected: string, ending: string) {
  const text = prefix + selected + ending;
  const bytes = Buffer.from(text, "utf8");
  const digest = createHash("sha256").update(bytes).digest("hex");
  const source = {
    source_id: `src_synthetic_reader_${suffix}`,
    source_revision: digest,
    sha256: digest,
    original_name: `合成阅读原件${suffix}.txt`,
    imported_at: "2026-10-22",
  };
  const position = JSON.stringify({
    type: "text",
    start: Buffer.byteLength(prefix, "utf8"),
    end: Buffer.byteLength(prefix + selected, "utf8"),
    checksum: digest,
  });
  const attributes = {
    source_id: source.source_id,
    source_revision: digest,
    anchor_id: `anchor_synthetic_reader_${suffix}`,
    position,
    excerpt: `证据引用 ${suffix}`,
  };
  const editor: JSONContent = { type: "doc", content: [{
    type: "paragraph", attrs: { block_id: `block_${suffix}` }, content: [
      { type: "text", text: `合成文档 ${suffix} 的来源依据：` },
      { type: "evidenceReference", attrs: attributes },
    ],
  }] };
  const document = assertCoreDto<DocumentDto>("DocumentDto", {
    document_id: `doc_synthetic_reader_${suffix}`,
    title: `合成阅读文档 ${suffix}`,
    version: 2,
    source_id: source.source_id,
    source_revision: digest,
    content_sha256: createHash("sha256").update(JSON.stringify(editor)).digest("hex"),
    text_projection: `合成文档 ${suffix} 的来源依据：`,
    editor_json: editor,
    blocks: [],
    revision_basis: null,
  });
  const summary = {
    document_id: document.document_id, title: document.title,
    version: document.version, source_id: document.source_id,
    source_revision: document.source_revision, content_sha256: document.content_sha256,
  };
  const original = assertCoreDto("OriginalDto", {
    source_id: source.source_id, name: source.original_name,
    media_type: "text/plain", sha256: digest,
    content_base64: bytes.toString("base64"),
  });
  const proof = (status: AnchorResolutionDto["status"] = "CURRENT") =>
    assertCoreDto<AnchorResolutionDto>("AnchorResolutionDto", {
      source_id: source.source_id, anchor_id: attributes.anchor_id, status,
      reason: "synthetic reader locator regression fixture",
      source_revision: digest, current_source_revision: digest,
      position, scope: "locator_provenance_only",
    });
  return { source, document, summary, original, attributes, text, prefix, selected, proof };
}

const first = fixture("A", "前言🙂：", "证据🧭甲乙", "\n合成尾声 A");
const second = fixture("B", "另一份文档🚀：", "独立证据乙", "\n合成尾声 B");
const samples = [first, second];
type Sample = typeof first;

function installCore(resolve: (sample: Sample) => AnchorResolutionDto | Promise<AnchorResolutionDto> = sample => sample.proof()) {
  bridge.call.mockImplementation(async (operation: string, payload: Record<string, unknown> = {}) => {
    if (operation === "sources_list") return assertCoreDto("SourcesListDto", { sources: samples.map(sample => sample.source) });
    if (operation === "documents_list") return assertCoreDto("DocumentsListDto", {
      documents: samples.map(sample => sample.summary), next_cursor: null, snapshot_count: samples.length,
    });
    if (operation === "document_get" || operation === "document_checks") {
      const sample = samples.find(item => item.document.document_id === payload.document_id);
      if (!sample) throw new Error(`unexpected synthetic document identity: ${String(payload.document_id)}`);
      if (operation === "document_get") return sample.document;
      return assertCoreDto("DocumentChecksDto", {
        document_id: sample.document.document_id, version: sample.document.version,
        content_sha256: sample.document.content_sha256, historical: false,
        default_status: "unverified", checks: [], checks_capped: false, next_offset: null,
      });
    }
    if (["source_original", "anchors_list", "anchor_resolve"].includes(operation)) {
      const sample = samples.find(item => item.source.source_id === payload.source_id);
      if (!sample) throw new Error(`unexpected synthetic source identity: ${String(payload.source_id)}`);
      if (operation === "source_original") return sample.original;
      if (operation === "anchors_list") return { anchors: [{ ...sample.attributes, location_status: "located" }] };
      expect(payload.anchor_id).toBe(sample.attributes.anchor_id);
      return resolve(sample);
    }
    // Import, save, anchor creation and inference are not silently accepted.
    throw new Error(`unconfigured synthetic Core operation: ${operation}`);
  });
}

async function expectReady(sample: Sample) {
  const button = await screen.findByRole("button", { name: `激活 ${sample.attributes.excerpt}` });
  await screen.findByRole("heading", { name: sample.document.title });
  await waitFor(() => expect(screen.getByRole("complementary", { name: "内容详情" }))
    .toHaveTextContent("原件身份、版本与字节已核对"));
  expect(bridge.call).toHaveBeenCalledWith("source_original", { source_id: sample.source.source_id });
  return button;
}

function expectBodyOnly() {
  expect(screen.getByRole("button", { name: "正文" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "原件" })).toHaveAttribute("aria-pressed", "false");
  expect(screen.queryByRole("region", { name: "关联原件阅读" })).toBeNull();
  expect(screen.queryByLabelText("并排原件正文")).toBeNull();
}

function expectNoWrites() {
  expect(bridge.call.mock.calls.filter(([operation]) => [
    "source_import", "document_create", "document_draft", "anchor_create",
    "material_question", "conversation_create", "conversation_request",
  ].includes(operation))).toEqual([]);
}

beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto);
  delete window.__TAURI__;
  window.getSelection()?.removeAllRanges();
  bridge.call.mockReset();
  installCore();
});
afterEach(() => {
  cleanup();
  window.getSelection()?.removeAllRanges();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("SYNTHETIC reader evidence activation with the original initially unmounted", () => {
  it("CURRENT opens the original, then focuses and selects the exact UTF-8-bound text after DOM mount", async () => {
    render(<CanonicalLibrarySpace purpose="reader" initialDocumentId={first.document.document_id} />);
    const activation = await expectReady(first);
    expectBodyOnly();
    // Both the prefix and target contain multibyte characters; emoji also
    // distinguish JS/DOM UTF-16 offsets from Unicode code-point counts.
    expect(Buffer.byteLength(first.prefix, "utf8")).toBeGreaterThan(first.prefix.length);
    await userEvent.setup().click(activation);
    const original = await screen.findByLabelText("并排原件正文");
    await waitFor(() => {
      expect(original).toHaveFocus();
      const selection = window.getSelection();
      expect(selection?.toString()).toBe(first.selected);
      expect(selection?.rangeCount).toBe(1);
      const range = selection!.getRangeAt(0);
      expect(range.startContainer).toBe(original.firstChild);
      expect(range.endContainer).toBe(original.firstChild);
      expect(range.startOffset).toBe(first.prefix.length);
      expect(range.endOffset).toBe((first.prefix + first.selected).length);
    });
    expect(original.textContent).toBe(first.text);
    expect(screen.getByRole("button", { name: "原件" })).toHaveAttribute("aria-pressed", "true");
    expect(bridge.call).toHaveBeenCalledWith("anchor_resolve", {
      source_id: first.source.source_id, anchor_id: first.attributes.anchor_id,
    });
    expectNoWrites();
  });

  it("STALE preserves the body-only view and does not focus or select an unverified original", async () => {
    installCore(sample => sample.proof("STALE"));
    render(<CanonicalLibrarySpace purpose="reader" initialDocumentId={first.document.document_id} />);
    const activation = await expectReady(first);
    expectBodyOnly();
    await userEvent.setup().click(activation);
    await screen.findByText(/引用定位未通过当前核验/);
    expectBodyOnly();
    expect(activation).toHaveFocus();
    expect(window.getSelection()?.toString()).toBe("");
    expect(bridge.call).toHaveBeenCalledWith("anchor_resolve", {
      source_id: first.source.source_id, anchor_id: first.attributes.anchor_id,
    });
    expectNoWrites();
  });

  it("a delayed CURRENT proof for A cannot reopen or locate its source after the reader switches to B", async () => {
    let release!: (value: AnchorResolutionDto) => void;
    const delayed = new Promise<AnchorResolutionDto>(resolve => { release = resolve; });
    installCore(sample => sample === first ? delayed : sample.proof());
    const view = render(<CanonicalLibrarySpace purpose="reader" initialDocumentId={first.document.document_id} />);
    const activationA = await expectReady(first);
    expectBodyOnly();
    await userEvent.setup().click(activationA);
    await waitFor(() => expect(bridge.call).toHaveBeenCalledWith("anchor_resolve", {
      source_id: first.source.source_id, anchor_id: first.attributes.anchor_id,
    }));
    // A real prop-driven object switch invokes the reader's actual openDocument
    // and generation fences while the previous Core request is still pending.
    view.rerender(<CanonicalLibrarySpace purpose="reader" initialDocumentId={second.document.document_id} />);
    const activationB = await expectReady(second);
    expectBodyOnly();
    act(() => { activationB.focus(); });
    expect(activationB).toHaveFocus();
    await act(async () => { release(first.proof()); await delayed; });
    expectBodyOnly();
    expect(activationB).toHaveFocus();
    expect(window.getSelection()?.toString()).toBe("");
    expect(screen.getByRole("heading", { name: second.document.title })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: `激活 ${first.attributes.excerpt}` })).toBeNull();
    expect(bridge.call.mock.calls.filter(([operation]) => operation === "anchor_resolve")).toHaveLength(1);
    expectNoWrites();
  });
});
