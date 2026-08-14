import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// AXW-UI-801: App Shell built with Vite; dev server binds loopback only.
// Tauri integration: build output goes to ../desktop/frontend-dist (later batch).
export default defineConfig({
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
});
