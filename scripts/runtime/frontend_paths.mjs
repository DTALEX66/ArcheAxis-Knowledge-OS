import { existsSync, lstatSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, isAbsolute, join, resolve } from "node:path";

// Check the raw spelling before resolving or touching an ancestor.
export function safePath(raw) {
  if (/^[EF]:[\\/]/i.test(raw) || /^[/\\]{2}/.test(raw)) throw new Error("protected drive or UNC frontend path");
  if (!isAbsolute(raw)) throw new Error("frontend path must be absolute");
  const path = resolve(raw);
  const parents = [];
  for (let part = path; ; part = dirname(part)) {
    parents.unshift(part);
    if (dirname(part) === part) break;
  }
  for (const part of parents) {
    try {
      if (lstatSync(part).isSymbolicLink()) throw new Error(`linked frontend path rejected: ${part}`);
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
  }
  return path;
}

export function projectPython(root) {
  safePath(root);
  const common = safePath(execFileSync("git", ["-C", root, "rev-parse", "--path-format=absolute", "--git-common-dir"], { encoding: "utf8" }).trim());
  const managed = safePath(join(dirname(common), ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python"));
  return existsSync(managed) ? managed : "python";
}

export function verifyBuildEnvironment(root) {
  const python = projectPython(root);
  execFileSync(python, ["-B", join(root, "scripts/runtime/frontend.py"), "--node", process.execPath, "verify"], { cwd: root, stdio: "pipe" });
  return safePath(process.env.ARCHEAXIS_FRONTEND_DIST);
}
