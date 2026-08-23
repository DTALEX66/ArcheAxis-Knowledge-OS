import { afterEach, describe, expect, it, vi } from "vitest";
import { learningApiExt } from "../api/learning";
import { resetRuntimeClient } from "../api/workspace";

describe("desktop learning API writes", () => {
  afterEach(() => {
    resetRuntimeClient();
    delete window.__TAURI__;
    vi.unstubAllGlobals();
  });

  it("routes every learning write through the scoped runtime client", async () => {
    window.__TAURI__ = {
      core: { invoke: vi.fn().mockResolvedValue({ port: 4312, token: "memory-only", scopes: ["workspace:write"] }) },
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      void init;
      const url = String(input);
      if (url.endsWith("/api/v1/system/handshake")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x",
            backend_version: "0.6.0", source_commit: "abc1234", schema_version: 15,
            runtime_mode: "desktop", workspace_id: "workspace-001", capabilities: [], migration_state: "ready",
          }),
        } as Response;
      }
      return { ok: true, status: 200, json: async () => ({}) } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);
    const api = learningApiExt();

    await api.teachBack({ record_id: "tb-1", concept: "BKT", restatement: "A", reference: "B", key_terms: [] });
    await api.learningPath({ goal: "BKT", graph: { nodes: ["BKT"], edges: [] } });
    await api.tick({ node_id: "BKT", human: {}, machine: {} });
    await api.reviewOutcome({ card_id: "card-1", command_id: "review-1", quality: 4 });

    const writes = fetchMock.mock.calls.filter(([input]) => String(input).includes("/api/v1/learning/"));
    expect(writes).toHaveLength(4);
    for (const [, init] of writes) {
      expect(init?.method).toBe("POST");
      expect(init?.headers).toMatchObject({
        "X-ArcheAxis-Launch-Token": "memory-only",
        "X-ArcheAxis-Scopes": "workspace:write",
        "Idempotency-Key": expect.any(String),
      });
    }
  });
});
