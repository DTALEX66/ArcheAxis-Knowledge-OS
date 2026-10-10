// Default npm entry point. Python owns the canonical Git worktree/run layout.
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { projectPython } from "./frontend_paths.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
try {
  const python = projectPython(root);
  const result = spawnSync(python, ["-B", join(root, "scripts/runtime/frontend.py"), "--node", process.execPath, ...process.argv.slice(2)], { cwd: root, stdio: "inherit" });
  if (result.error) throw result.error;
  process.exitCode = result.status ?? 1;
} catch (error) {
  console.error(`[frontend] ${error.message}`);
  process.exitCode = 2;
}
