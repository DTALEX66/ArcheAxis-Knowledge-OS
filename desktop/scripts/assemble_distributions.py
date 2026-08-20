"""Assemble the Green (no-install) and Portable distributions from the SAME
verified runtime (AXW-PKG-602 / AXW-PKG-603).

Layout follows task pack §6 / §7. Assembly is deterministic and local-only;
the release workflow runs this on the exact tagged SHA.

Usage:
  python desktop/scripts/assemble_distributions.py \
      --exe desktop/src-tauri/target/release/ArcheAxis.exe \
      --runtime .hermes/rt/runtime \
      --frontend desktop/bootstrap \
      --identity .hermes/rt/runtime/release-identity.json \
      --out release-assets \
      --version 0.5.0

Outputs (in --out):
  ArcheAxis.Knowledge-v<ver>-Windows-x64-Green.zip
  ArcheAxis.Knowledge-v<ver>-Windows-x64-Portable.zip
"""
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

GREEN_DIR = "ArcheAxis.Knowledge.Green-x64"
PORTABLE_DIR = "ArcheAxis.Knowledge.Portable-x64"


def _copy_tree(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _write_zip(directory: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # explicit directory entries so empty data/capability zones survive
        # the archive round-trip (task pack §7 layout must be present)
        for dir_path in sorted(d for d in directory.rglob("*") if d.is_dir()):
            zf.writestr(f"{dir_path.relative_to(directory.parent).as_posix()}/", "")
        for file in sorted(directory.rglob("*")):
            if file.is_file():
                zf.write(file, file.relative_to(directory.parent))


def assemble_green(exe: Path, runtime: Path, frontend: Path, identity: Path, version: str) -> Path:
    root = Path(GREEN_DIR)
    if root.exists():
        shutil.rmtree(root)
    # program files (immutable bundle content)
    _copy_tree(frontend, root / "frontend")
    _copy_tree(runtime, root / "runtime")
    shutil.copy2(exe, root / "ArcheAxis.exe")
    _copy_tree(identity, root / "release-identity.json")
    (root / "green-profile.toml").write_text(
        "# ArcheAxis Knowledge — green (no-install) profile (AXW-RUN-202)\n"
        "backend = \"bundled\"\n"
        'data_policy = "selected-user-data"\n'
        "reload = false\n",
        encoding="utf-8",
    )
    (root / "licenses").mkdir(exist_ok=True)
    (root / "README-绿色版.txt").write_text(
        "ArcheAxis Knowledge 绿色免安装版（无需安装，数据默认位于用户数据目录）\n"
        "解压后运行 ArcheAxis.exe 即可。\n",
        encoding="utf-8",
    )
    zip_path = Path(f"ArcheAxis.Knowledge-v{version}-Windows-x64-Green.zip")
    _write_zip(root, zip_path)
    return zip_path


def assemble_portable(exe: Path, runtime: Path, frontend: Path, identity: Path, version: str) -> Path:
    root = Path(PORTABLE_DIR)
    if root.exists():
        shutil.rmtree(root)
    # The Tauri shell resolves its resource root beside ArcheAxis.exe.  Keep
    # portable program files at that same root so it uses the identical
    # bundled runtime contract as Setup and Green (AXW-PKG-603).
    _copy_tree(frontend, root / "frontend")
    _copy_tree(runtime, root / "runtime")
    shutil.copy2(exe, root / "ArcheAxis.exe")
    _copy_tree(identity, root / "release-identity.json")
    # root-only data zones (P0-4): everything user-writable lives under data/
    for sub in ("system", "workspaces", "derived-cache", "logs", "backups", "webview-profile"):
        (root / "data" / sub).mkdir(parents=True, exist_ok=True)
    (root / "capability-store").mkdir(exist_ok=True)
    (root / "licenses").mkdir(exist_ok=True)
    # portable.flag + profile: no PowerShell ExecutionPolicy dependency (task pack §7)
    (root / "portable.flag").write_text("", encoding="utf-8")
    (root / "portable-profile.toml").write_text(
        "# ArcheAxis Knowledge — portable profile (AXW-RUN-202)\n"
        "backend = \"bundled\"\n"
        'data_policy = "portable-root-only"\n'
        "reload = false\n",
        encoding="utf-8",
    )
    (root / "README-便携版.txt").write_text(
        "ArcheAxis Knowledge 随身便携版（程序、数据、能力与配置全部位于本目录）\n"
        "整体复制目录即可迁移；复制/备份前请先完全关闭应用。\n",
        encoding="utf-8",
    )
    zip_path = Path(f"ArcheAxis.Knowledge-v{version}-Windows-x64-Portable.zip")
    _write_zip(root, zip_path)
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble Green and Portable distributions")
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--frontend", required=True, type=Path)
    parser.add_argument("--identity", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    for required in (args.exe, args.runtime, args.frontend, args.identity):
        if not required.exists():
            raise SystemExit(f"missing input: {required}")

    args.out.mkdir(parents=True, exist_ok=True)
    green = assemble_green(args.exe, args.runtime, args.frontend, args.identity, args.version)
    portable = assemble_portable(args.exe, args.runtime, args.frontend, args.identity, args.version)
    for z in (green, portable):
        shutil.move(str(z), args.out / z.name)
    print(json.dumps({
        "green": str(args.out / green.name),
        "portable": str(args.out / portable.name),
    }))


if __name__ == "__main__":
    main()
