"""Cache only public Cargo dependencies and build outputs at their effective roots."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from scripts.runtime import dev


def cache_identity(root: Path, *, compiler: str, profile: str, env: dict[str, str]) -> dict:
    if profile not in {"fast", "build"}:
        raise ValueError("unknown Cargo cache profile")
    names = dev.git(root, "ls-files").splitlines()
    inputs = sorted(name for name in names if name.endswith(("Cargo.toml", "Cargo.lock"))
                    or name in {".cargo/config", ".cargo/config.toml", "src-tauri/.cargo/config.toml",
                                ".github/workflows/ci.yml"})
    if not {"Cargo.lock", "src-tauri/Cargo.lock"}.issubset(inputs):
        raise ValueError("both canonical Cargo lockfiles are required")
    hashes = {name: hashlib.sha256(dev.safe_path(root / name).read_bytes()).hexdigest()
              for name in inputs}
    flags = {name: env.get(name, "") for name in ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_BUILD_TARGET")}
    host = re.search(r"^host: (.+)$", compiler, re.M)
    if host is None:
        raise ValueError("rustc identity has no host target")
    identity = {"compiler": compiler, "target": host.group(1), "profile": profile, "audit_version": "0.22.2",
                "inputs": hashes, "flags": flags}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
    platform = re.sub(r"[^A-Za-z0-9_-]", "_", host.group(1))
    prefix = f"aaos-cargo-v7-{platform}-{profile}-{digest}"
    commit = dev.git(root, "rev-parse", "HEAD")
    dirty, patch = dev.worktree_identity(root)
    source = commit + ("-" + patch[:16] if dirty else "")
    return {"schema": "archeaxis.cargo-cache/v1", "profile": profile,
            "target": host.group(1), "input_sha256": hashes,
            "compiler_sha256": hashlib.sha256(compiler.encode()).hexdigest(),
            "flags_sha256": hashlib.sha256(json.dumps(flags, sort_keys=True).encode()).hexdigest(),
            "source_commit": commit, "source_dirty": dirty, "source_patch_sha256": patch,
            "dependency_key": prefix + "-dependencies",
            "build_prefix": prefix + "-outputs-", "build_key": prefix + "-outputs-" + source}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("fast", "build"), required=True)
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument("--record-restore", action="store_true")
    args = parser.parse_args()
    root = dev.safe_path(Path(__file__).resolve().parents[2])
    run = dev.safe_path(Path(os.environ["ARCHEAXIS_RUN_ROOT"]))
    paths = dev.layout(root, run.name)
    if run != paths["run"] or not run.is_dir():
        raise ValueError("Cargo cache needs this checkout's allocated run")
    report_path = run / "artifacts" / "cargo-cache.json"
    if args.record_restore:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["restore_seconds"] = time.time() - report["restore_started_at"]
        report["dependency_hit"] = os.environ.get("CARGO_DEPENDENCY_CACHE_HIT", "") or "MISS"
        report["build_hit"] = os.environ.get("CARGO_BUILD_CACHE_HIT", "") or "MISS_OR_PREFIX_RESTORE"
    else:
        compiler = subprocess.check_output(["rustc", "-vV"], text=True)
        report = cache_identity(root, compiler=compiler, profile=args.profile, env=os.environ)
        cargo_home = dev.safe_path(Path(os.environ["CARGO_HOME"]))
        if cargo_home != paths["cache"] / "cargo":
            raise ValueError("Cargo dependency cache outside effective project root")
        report["paths"] = {"cargo_home": str(cargo_home), "core_target": str(paths["cargo_build"]),
                           "tauri_target": str(paths["tauri_build"]),
                           "uv_cache": str(paths["cache"] / "uv")}
        report["restore_started_at"] = time.time()
        if args.github_output:
            if os.environ.get("GITHUB_ACTIONS") != "true":
                raise ValueError("GitHub output requires an Actions runner")
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                for name in ("dependency_key", "build_key", "build_prefix"):
                    output.write(f"{name}={report[name]}\n")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
