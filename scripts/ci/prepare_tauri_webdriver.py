"""Prepare exact official Windows WebDriver tools in an isolated project root."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import urllib.request
import zipfile
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_webview(explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.is_absolute():
            raise ValueError("Explicit WebView2 executable must be an absolute path")
        if str(explicit).startswith(("\\\\", "//")):
            raise ValueError("Explicit WebView2 executable must be on a local filesystem")
        runtime = explicit.resolve(strict=True)
    else:
        program_files = os.environ.get("PROGRAMFILES(X86)")
        if not program_files:
            raise RuntimeError("Windows PROGRAMFILES(X86) environment path is missing")
        webview = Path(program_files) / "Microsoft/EdgeWebView/Application"
        versions = [
            item
            for item in webview.iterdir()
            if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", item.name)
            and (item / "msedgewebview2.exe").is_file()
        ]
        if not versions:
            raise RuntimeError("No installed WebView2 executable in declared standard system path")
        runtime = max(versions, key=lambda p: tuple(map(int, p.name.split(".")))) / "msedgewebview2.exe"
        runtime = runtime.resolve(strict=True)
    if not runtime.is_file() or runtime.name.casefold() != "msedgewebview2.exe":
        raise ValueError("WebView2 executable must be a regular msedgewebview2.exe file")
    # Inspect the PE container without executing the caller-selected runtime.
    with runtime.open("rb") as binary:
        header = binary.read(64)
        if len(header) < 64 or header[:2] != b"MZ":
            raise ValueError("WebView2 executable is not a PE file")
        pe_offset = int.from_bytes(header[60:64], "little")
        if pe_offset < 64 or pe_offset > runtime.stat().st_size - 24:
            raise ValueError("WebView2 PE header offset is invalid")
        binary.seek(pe_offset)
        if binary.read(4) != b"PE\x00\x00":
            raise ValueError("WebView2 executable PE signature is invalid")
    return runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cargo", default="cargo")
    parser.add_argument(
        "--webview-executable", type=Path,
        help="Absolute packaged WebView2 executable; default detects the installed system runtime",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipt = {
        "ok": False,
        "scope": "Project local only; no registry or global configuration writes",
        "preparation_script": str(Path(__file__).resolve()),
        "preparation_script_sha256": sha(Path(__file__).resolve()),
    }
    try:
        runtime = select_webview(args.webview_executable)
        runtime_sha256 = sha(runtime)
        powershell = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "(Get-Item -LiteralPath '"
                + str(runtime).replace("'", "''")
                + "').VersionInfo.FileVersion",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        version = powershell.stdout.strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
            raise RuntimeError("WebView2 actual executable version missing")
        if sha(runtime) != runtime_sha256:
            raise RuntimeError("WebView2 executable changed while reading its version")
        env = dict(os.environ)
        env["CARGO_HOME"] = str(root / "official-cargo")
        env["CARGO_TARGET_DIR"] = str(root / "target")
        install = root / "tauri-driver-2.1.0"
        command = [
            args.cargo,
            "install",
            "tauri-driver",
            "--version",
            "2.1.0",
            "--locked",
            "--root",
            str(install),
        ]
        with (root / "cargo-install.log").open("wb") as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        if sha(runtime) != runtime_sha256:
            raise RuntimeError("WebView2 executable changed while preparing tools")
        driver = install / "bin/tauri-driver.exe"
        assert driver.is_file() and driver.stat().st_size
        source = f"https://msedgedriver.microsoft.com/{version}/edgedriver_win64.zip"
        archive = root / f"edgedriver-{version}.zip"
        with urllib.request.urlopen(source, timeout=60) as response, archive.open("wb") as output:
            output.write(response.read(64 * 1024 * 1024 + 1))
        if not 0 < archive.stat().st_size <= 64 * 1024 * 1024:
            raise ValueError("EdgeDriver archive empty or exceeds 64 MiB")
        native = root / f"edge-{version}" / "msedgedriver.exe"
        native.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as zipped:
            members = zipped.infolist()
            if len(members) > 32 or sum(item.file_size for item in members) > 128 * 1024 * 1024:
                raise ValueError("EdgeDriver expanded archive exceeds budget")
            for item in members:
                name = item.filename.replace("\\", "/")
                if (
                    name.startswith("/")
                    or ":" in name
                    or ".." in name.split("/")
                    or item.flag_bits & 1
                    or ((item.external_attr >> 16) & 0o170000) == 0o120000
                ):
                    raise ValueError("Unsafe official EdgeDriver archive member")
            binaries = [item for item in members if item.filename == "msedgedriver.exe"]
            if len(binaries) != 1:
                raise ValueError("EdgeDriver archive binary identity ambiguous")
            native.write_bytes(zipped.read(binaries[0]))
        actual = subprocess.run(
            [str(native), "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
        if f"Microsoft Edge WebDriver {version} " not in actual:
            raise RuntimeError("EdgeDriver executable version differs from runtime")
        if sha(runtime) != runtime_sha256:
            raise RuntimeError("WebView2 executable changed while preparing tools")
        receipt.update(
            ok=True,
            driver=str(driver),
            native_driver=str(native),
            tauri_version="2.1.0",
            tauri_source="https://crates.io/api/v1/crates/tauri-driver/2.1.0/download",
            locked=True,
            driver_sha256=sha(driver),
            edge_source=source,
            edge_zip_sha256=sha(archive),
            edge_sha256=sha(native),
            edge_actual_version=actual,
            webview_version=version,
            webview_path=str(runtime),
            webview_sha256=runtime_sha256,
            webview_selection="explicit" if args.webview_executable is not None else "system",
        )
        locks = list((root / "official-cargo/registry/src").glob("*/tauri-driver-2.1.0/Cargo.lock"))
        if len(locks) != 1:
            raise RuntimeError("Exact official tauri-driver lock receipt missing")
        receipt["tauri_lock_sha256"] = sha(locks[0])
    except BaseException as error:
        receipt["ok"] = False
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        path = root / "receipt.json"
        path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(json.dumps(receipt))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
