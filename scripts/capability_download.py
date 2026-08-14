#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力资产下载治理 CLI（AXW-ENV-105）。

设计原则（详见 config/environment/download-governance.md）:
  1. 禁止静默首次下载 —— 默认不下载，只 stage（显式 --dest-dir）；
  2. stage -> verify（sha256）-> activate（hash + license 校验后原子激活）；
  3. 可疑/未验证资产 -> quarantine（90-quarantine/）；
  4. 每次操作打印来源/体积/许可证/磁盘位置。

子命令:
  stage      <url> --dest-dir DIR [--name N] [--license LIC] [--license-url U] [--force]
  verify     <manifest>
  quarantine <path> [--quarantine-dir DIR]
  activate   <manifest> <store-root> [--force]

仅用标准库（urllib / hashlib / json / argparse）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

MANIFEST_VERSION = 1
ALLOWED_SCHEMES = ("http", "https", "file")
CHUNK = 1024 * 256


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_to(url: str, dest: str) -> tuple[int, str]:
    """流式下载到 dest，返回 (字节数, sha256)。仅允许 http/https/file。"""
    from urllib.parse import urlsplit
    scheme = urlsplit(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"不允许的 URL scheme: {scheme}（仅 {ALLOWED_SCHEMES}）")
    digest = hashlib.sha256()
    total = 0
    req = urllib.request.Request(url, headers={"User-Agent": "capability_download/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            out.write(chunk)
            digest.update(chunk)
            total += len(chunk)
    return total, digest.hexdigest()


def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise ValueError(f"manifest 版本不兼容: {manifest.get('manifest_version')}")
    return manifest


def manifest_path_for(staging_dir: str, name: str) -> str:
    return os.path.join(staging_dir, f"{name}.download-manifest.json")


def write_manifest(staging_dir: str, name: str, url: str, sha256: str, size: int,
                   license_: str, license_url: str, staged_file: str) -> str:
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "tool": "capability_download",
        "name": name,
        "source_url": url,
        "sha256": sha256,
        "size_bytes": size,
        "license": license_,
        "license_url": license_url or "",
        "downloaded_at": now_iso(),
        "staged_file": os.path.basename(staged_file),
        "staging_dir": os.path.abspath(staging_dir),
    }
    path = manifest_path_for(staging_dir, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------- stage
def cmd_stage(args: argparse.Namespace) -> int:
    dest_dir = os.path.abspath(args.dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    from urllib.parse import urlsplit
    name = args.name or os.path.basename(urlsplit(args.url).path) or "download"
    target = os.path.join(dest_dir, name)
    if os.path.exists(target) and not args.force:
        print(f"[stage] 拒绝覆盖已存在文件（静默覆盖被禁止）: {target}")
        print(f"[stage] 如需强制覆盖请加 --force")
        return 2

    print(f"[stage] 来源: {args.url}")
    print(f"[stage] 许可证: {args.license or 'unknown（activate 将被拒绝，除非 --force）'}")
    tmp = target + ".part"
    try:
        size, digest = download_to(args.url, tmp)
        if os.path.exists(target):
            os.remove(tmp)
            print(f"[stage] 文件在下载期间出现，已放弃本次结果: {target}")
            return 2
        os.replace(tmp, target)  # 原子落盘
    except Exception as exc:
        if os.path.exists(tmp):
            os.remove(tmp)
        print(f"[stage] 下载失败: {exc}")
        return 1

    manifest = write_manifest(dest_dir, name, args.url, digest, size, args.license or "unknown",
                              args.license_url, target)
    print(f"[stage] 已下载: {size:,} 字节  sha256={digest}")
    print(f"[stage] 磁盘位置: {target}")
    print(f"[stage] manifest: {manifest}")
    return 0


# ---------------------------------------------------------------- verify
def cmd_verify(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    staged = os.path.join(manifest["staging_dir"], manifest["staged_file"])
    if not os.path.isfile(staged):
        print(f"[verify] 失败: 暂存文件不存在 {staged}")
        return 1
    actual = sha256_of(staged)
    if actual == manifest["sha256"]:
        print(f"[verify] OK: {staged}")
        print(f"[verify] sha256 一致: {actual}")
        print(f"[verify] 来源: {manifest['source_url']}  许可证: {manifest['license']}")
        return 0
    print(f"[verify] MISMATCH: {staged}")
    print(f"[verify] 期望 {manifest['sha256']}")
    print(f"[verify] 实际 {actual}")
    print(f"[verify] 建议: 立即 quarantine 该文件并重新 stage")
    return 1


# ---------------------------------------------------------------- quarantine
def cmd_quarantine(args: argparse.Namespace) -> int:
    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"[quarantine] 失败: 路径不存在 {path}")
        return 1
    qroot = os.path.abspath(args.quarantine_dir)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    qdir = os.path.join(qroot, stamp)
    os.makedirs(qdir, exist_ok=True)
    name = os.path.basename(path)
    target = os.path.join(qdir, name)
    shutil.move(path, target)
    moved = [target]
    # 相邻 manifest 一并隔离（若存在）
    manifest = manifest_path_for(os.path.dirname(path), name)
    if os.path.isfile(manifest):
        shutil.move(manifest, os.path.join(qdir, os.path.basename(manifest)))
        moved.append(os.path.join(qdir, os.path.basename(manifest)))
    print(f"[quarantine] 已隔离 {len(moved)} 项 -> {qdir}")
    for m in moved:
        print(f"[quarantine]   {m}")
    print(f"[quarantine] 隔离后该资产不再被任何 activate/verify 引用")
    return 0


# ---------------------------------------------------------------- activate
def cmd_activate(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    name = manifest["name"]
    license_ = manifest.get("license") or "unknown"
    if license_ in ("", "unknown") and not args.force:
        print(f"[activate] 拒绝: 许可证未声明（license={license_!r}）。")
        print(f"[activate] 治理规则：许可证未知的资产不得激活。请重新 stage 时传 --license，或 --force 显式放行。")
        return 2

    store_root = os.path.abspath(args.store_root)
    os.makedirs(store_root, exist_ok=True)
    final = os.path.join(store_root, name)
    if os.path.exists(final) and not args.force:
        print(f"[activate] 拒绝覆盖已存在资产（静默覆盖被禁止）: {final}")
        return 2

    staged = os.path.join(manifest["staging_dir"], manifest["staged_file"])
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".activate-", suffix=".part", dir=store_root)
    os.close(tmp_fd)
    try:
        if os.path.isfile(staged) and sha256_of(staged) == manifest["sha256"]:
            shutil.copyfile(staged, tmp_path)
            print(f"[activate] 校验通过（复用暂存文件）: {staged}")
        else:
            print(f"[activate] 暂存文件缺失或哈希不符，重新下载: {manifest['source_url']}")
            size, digest = download_to(manifest["source_url"], tmp_path)
            if digest != manifest["sha256"]:
                print(f"[activate] 拒绝: 重新下载的 sha256 与 manifest 不符")
                print(f"[activate]   期望 {manifest['sha256']}")
                print(f"[activate]   实际 {digest}")
                return 1
        os.replace(tmp_path, final)  # 原子激活（同盘 replace）
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        print(f"[activate] 失败: {exc}")
        return 1

    print(f"[activate] 原子激活完成: {final}")
    print(f"[activate] sha256={manifest['sha256']}  大小={manifest['size_bytes']:,} 字节")
    print(f"[activate] 许可证={license_}  {manifest.get('license_url') or ''}")
    print(f"[activate] 来源={manifest['source_url']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="capability_download.py",
        description="能力资产下载治理 CLI：stage -> verify -> activate 三段式，禁止静默下载",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_stage = sub.add_parser("stage", help="下载到暂存目录并写 manifest（不激活）")
    p_stage.add_argument("url", help="资产 URL（http/https/file）")
    p_stage.add_argument("--dest-dir", required=True, help="暂存目录（60-cache/downloads 语义）")
    p_stage.add_argument("--name", default=None, help="落盘文件名（默认取 URL 末段）")
    p_stage.add_argument("--license", default=None, help="SPDX 许可证标识（activate 需要非 unknown）")
    p_stage.add_argument("--license-url", default=None, help="许可证原文 URL")
    p_stage.add_argument("--force", action="store_true", help="允许覆盖已存在文件")
    p_stage.set_defaults(func=cmd_stage)

    p_verify = sub.add_parser("verify", help="重算 sha256 与 manifest 对比")
    p_verify.add_argument("manifest", help="manifest JSON 路径")
    p_verify.set_defaults(func=cmd_verify)

    p_quar = sub.add_parser("quarantine", help="移动到隔离区（默认 90-quarantine/）")
    p_quar.add_argument("path", help="要隔离的文件（相邻 manifest 一并隔离）")
    p_quar.add_argument("--quarantine-dir", default="90-quarantine", help="隔离区根目录（默认相对当前目录的 90-quarantine）")
    p_quar.set_defaults(func=cmd_quarantine)

    p_act = sub.add_parser("activate", help="hash+license 校验通过后原子激活到 store-root")
    p_act.add_argument("manifest", help="manifest JSON 路径")
    p_act.add_argument("store-root", help="激活目标目录（40-models / 00-registry/licenses 等）")
    p_act.add_argument("--force", action="store_true", help="放行 license=unknown 或覆盖已存在资产")
    p_act.set_defaults(func=cmd_activate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
