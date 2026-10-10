// @vitest-environment node

import { describe, expect, it } from "vitest";
import { resolveConfig } from "vite";
import { fileURLToPath } from "node:url";

describe("Vite development server", () => {
  it("proxies the local product API for browser-based integration checks", async () => {
    const config = await resolveConfig({
      configFile: fileURLToPath(new URL("../../vite.config.ts", import.meta.url)),
    }, "serve");
    expect(config.server?.proxy?.["/api"]).toMatchObject({
      target: "http://127.0.0.1:8000",
      changeOrigin: true,
    });
    expect(config.server?.proxy?.["/workspace/api"]).toMatchObject({
      target: "http://127.0.0.1:8000",
      changeOrigin: true,
    });
    expect(config.server?.proxy?.["/workspace/api"]?.configure).toEqual(expect.any(Function));
  });
});
