"""Detect WebView2 runtime mode on this machine (AXW-PKG-604 spike).

Checks:
1. Evergreen: HKLM/HKCU \\Microsoft\\EdgeUpdate\\Clients\\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5} pv
2. Evergreen fallback: WebView2 fixed-version folder under Program Files (x86)\\Microsoft\\EdgeWebView\\Application
3. Bootstrap installer presence (MicrosoftEdgeWebview2Setup.exe)

Output: JSON-ish report for the offline-portable spike decision.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

EVERGREEN_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def reg_query(key: str) -> str | None:
    r = subprocess.run(
        ["reg", "query", key, "/v", "pv"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=15,
    )
    if r.returncode != 0:
        return None
    for line in r.stdout.splitlines():
        if "pv" in line and "REG_SZ" in line:
            return line.split("REG_SZ", 1)[1].strip()
    return None


def main() -> int:
    report: dict = {
        "evergreen": None,
        "fixed_version": None,
        "fixed_version_size_mb": None,
        "offline_installer_present": False,
        "recommendation": "",
    }
    hklm = reg_query(r"HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\\" + EVERGREEN_GUID)
    hkcu = reg_query(r"HKCU\SOFTWARE\Microsoft\EdgeUpdate\Clients\\" + EVERGREEN_GUID)
    report["evergreen"] = hklm or hkcu

    pf_x86 = os.environ.get("PROGRAMFILES(X86)", "")
    pf = os.environ.get("PROGRAMFILES", "")
    fixed_candidates = [
        Path(pf_x86) / "Microsoft" / "EdgeWebView" / "Application" if pf_x86 else None,
        Path(pf) / "Microsoft" / "EdgeWebView" / "Application" if pf else None,
    ]
    for cand in fixed_candidates:
        if cand is None or not cand.is_dir():
            continue
            versions = [p for p in cand.iterdir() if p.is_dir() and p.name[0].isdigit()]
            if versions:
                latest = max(versions)
                size_mb = sum(f.stat().st_size for f in latest.rglob("*") if f.is_file()) // (1024 * 1024)
                report["fixed_version"] = latest.name
                report["fixed_version_size_mb"] = size_mb
                break

    for root in (pf_x86, pf):
        if root and Path(root).joinpath("Microsoft", "EdgeWebView", "Application", "MicrosoftEdgeWebview2Setup.exe").exists():
            report["offline_installer_present"] = True

    if report["evergreen"]:
        report["recommendation"] = "evergreen-ok: default Evergreen mode, no bundled Fixed Version needed"
    elif report["fixed_version"]:
        report["recommendation"] = (
            f"fixed-version-only ({report['fixed_version']}, ~{report['fixed_version_size_mb']} MB): "
            "offline portable must bundle Fixed Version (~250 MB)"
        )
    else:
        report["recommendation"] = (
            "no-webview2: green/portable must ship offline bootstrap installer "
            "(MicrosoftEdgeWebview2Setup.exe) or document explicit fix entry"
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
