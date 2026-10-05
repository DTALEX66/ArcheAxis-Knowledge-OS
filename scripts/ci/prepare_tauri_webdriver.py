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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cargo", default="cargo")
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipt = {
        "ok": False,
        "scope": "Project local only; no registry or global configuration writes",
    }
    try:
        webview = (
            Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
            / "Microsoft/EdgeWebView/Application"
        )
        versions = []
        for item in webview.iterdir():
            if (
                re.fullmatch(r"\d+\.\d+\.\d+\.\d+", item.name)
                and (item / "msedgewebview2.exe").is_file()
            ):
                versions.append(item)
        if not versions:
            raise RuntimeError("No installed WebView2 executable in declared standard system path")
        selected = max(versions, key=lambda p: tuple(map(int, p.name.split("."))))
        runtime = selected / "msedgewebview2.exe"
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
