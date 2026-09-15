"""Assemble a project-local, self-contained Green candidate for review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AssemblyResult:
    root: Path
    zip_path: Path


def _native_path(path: Path) -> str | Path:
    """Use the Windows extended-length prefix for deep managed run paths."""
    if path.drive and path.drive.upper() != "E:" and len(str(path)) >= 240:
        return "\\\\?\\" + str(path)
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(_native_path(path), "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_reparse(path: Path) -> None:
    if path.is_symlink() or bool(getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400):
        raise ValueError(f"reparse point is not allowed in candidate input: {path}")


def _remove_tree(path: Path) -> None:
    """Remove a generated candidate without losing deep Windows paths."""
    native = str(_native_path(path))
    for current, directories, files in os.walk(native, topdown=False):
        for name in files:
            child = Path(current) / name
            os.unlink(_native_path(child))
        for name in directories:
            child = Path(current) / name
            os.rmdir(_native_path(child))
    os.rmdir(native)


def assemble(
    desktop: Path,
    core: Path,
    output: Path,
    version: str,
    *,
    runtime: Path | None = None,
    project_root: Path | None = None,
    source_commit: str | None = None,
    source_tree: str | None = None,
) -> AssemblyResult:
    desktop = desktop.resolve()
    core = core.resolve()
    output = output.resolve()
    project_root = (project_root or Path(__file__).resolve().parents[2]).resolve()
    project_local = (project_root / ".project-local").resolve()
    try:
        output.relative_to(project_local)
    except ValueError as exc:
        raise ValueError("output must stay inside project-local") from exc
    if not desktop.is_dir() or not (desktop / "ArcheAxis.Desktop.exe").is_file():
        raise ValueError("desktop publish directory or executable is missing")
    if not core.is_file():
        raise ValueError("Core executable is missing")
    if runtime is not None and not runtime.is_dir():
        raise ValueError("runtime directory is missing")
    _reject_reparse(desktop)
    _reject_reparse(core)
    if runtime is not None:
        _reject_reparse(runtime)

    output.mkdir(parents=True, exist_ok=True)
    root = output / f"ArcheAxis.Knowledge.Green-v{version}-x64"
    if root.exists():
        _remove_tree(root)
    (root / "desktop").mkdir(parents=True)
    (root / "core").mkdir()
    if runtime is not None:
        (root / "runtime").mkdir()
    copied_files: list[Path] = []
    for source in desktop.rglob("*"):
        _reject_reparse(source)
        if source.is_file():
            target = root / "desktop" / source.relative_to(desktop)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_native_path(source), _native_path(target))
            copied_files.append(target)
    core_target = root / "core" / "archeaxis-api.exe"
    shutil.copy2(_native_path(core), _native_path(core_target))
    copied_files.append(core_target)
    if runtime is not None:
        for source in runtime.rglob("*"):
            _reject_reparse(source)
            if source.is_file():
                target = root / "runtime" / source.relative_to(runtime)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(_native_path(source), _native_path(target))
                copied_files.append(target)

    # Keep the portable candidate launchable without requiring users to know
    # the Core environment variable or accidentally opening a framework-only
    # executable from a build directory.
    launcher = root / "启动绿色候选.vbs"
    launcher_text = '''Option Explicit
Dim shell, files, root, executable, dataRoot
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
executable = root & "\\desktop\\ArcheAxis.Desktop.exe"
dataRoot = root & "\\data"
If Not files.FileExists(executable) Then
  MsgBox "未找到自包含桌面程序。请先运行候选包验证。", vbCritical, "星环知识"
  WScript.Quit 1
End If
If Not files.FolderExists(dataRoot) Then files.CreateFolder dataRoot
shell.Environment("PROCESS")("ARCHAXIS_CORE_BIN") = root & "\\core\\archeaxis-api.exe"
shell.Environment("PROCESS")("ARCHAXIS_DATA_DIR") = dataRoot
shell.Environment("PROCESS")("ARCHAXIS_LAUNCHER_DATA_DIR") = dataRoot
shell.Run Chr(34) & executable & Chr(34), 1, False
'''
    launcher.write_text(launcher_text, encoding="utf-8", newline="\r\n")
    copied_files.append(launcher)

    files: dict[str, dict[str, int | str]] = {}
    for path in sorted(copied_files):
        relative = path.relative_to(root).as_posix()
        files[relative] = {"bytes": os.stat(_native_path(path)).st_size, "sha256": _sha256(path)}
    manifest = {
        "schema": "archeaxis.green-candidate/v1",
        "version": version,
        "provenance": {
            "source_commit": source_commit,
            "source_tree": source_tree,
        },
        "files": files,
    }
    manifest_path = root / "candidate-manifest.json"
    with open(_native_path(manifest_path), "w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    zip_path = output / f"ArcheAxis.Knowledge.Green-v{version}-x64.zip"
    with zipfile.ZipFile(_native_path(zip_path), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            archive.write(path, path.relative_to(output).as_posix())
    return AssemblyResult(root=root, zip_path=zip_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--desktop", required=True, type=Path)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-commit")
    parser.add_argument("--source-tree")
    args = parser.parse_args()
    result = assemble(
        args.desktop,
        args.core,
        args.out,
        args.version,
        runtime=args.runtime,
        source_commit=args.source_commit,
        source_tree=args.source_tree,
    )
    print(json.dumps({"root": str(result.root), "zip": str(result.zip_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
