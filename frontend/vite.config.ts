/// <reference types="vitest" />
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// AXW-UI-801: App Shell built with Vite; dev server binds loopback only.
// Tauri integration: build output goes to ../desktop/frontend-dist (later batch).
// AXW-UI-804: Vitest (jsdom) runs component tests; setup file registers
// @testing-library/jest-dom matchers.
// Resolve this from the configuration module rather than process.cwd(). Tauri
// may invoke the frontend through a Windows Junction to shorten NSIS paths;
// a cwd-derived root would then make index.html appear outside the bundle.
const frontendRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: frontendRoot,
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
