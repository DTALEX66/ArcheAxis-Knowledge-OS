// Mock original bytes verify React identity; decoding is a separate native test.
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createHash, webcrypto } from "node:crypto";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
const bridge = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("../api/core", () => ({ coreCommand: bridge.call }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
it("keeps one owned media reader when reopening the same source", async () => {
  vi.stubGlobal("crypto", webcrypto);
  vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:owned"), revokeObjectURL: vi.fn() });
  const errors = vi.spyOn(console, "error").mockImplementation(() => {});
  const bytes = Buffer.from("RIFF mock original");
  const sha = createHash("sha256").update(bytes).digest("hex");
  const source = { source_id: "media-source", source_revision: sha, sha256: sha, original_name: "sample.wav", imported_at: "2026-10-06" };
  bridge.call.mockImplementation(async (operation: string) => {
    if (operation === "sources_list") return { sources: [source] };
    if (operation === "documents_list") return { documents: [] };
    if (operation === "anchors_list") return { anchors: [] };
    if (operation === "source_jobs") return { source_id: source.source_id, jobs: [], jobs_capped: false };
    if (operation === "capabilities_list") return {};
    if (operation === "source_original") return { source_id: source.source_id, name: source.original_name, media_type: "audio/wav", sha256: sha, content_base64: bytes.toString("base64") };
    throw new Error(operation);
  });
  const view = render(<CanonicalLibrarySpace />);
  const user = userEvent.setup();
  for (let count = 0; count < 3; count++) {
    await user.click(await screen.findByRole("button", { name: "sample.wav" }));
    await screen.findByLabelText("音频原件");
    expect(view.container.querySelectorAll("audio")).toHaveLength(1);
  }
  expect(errors.mock.calls.some(call => call.join(" ").includes("same key"))).toBe(false);
});
