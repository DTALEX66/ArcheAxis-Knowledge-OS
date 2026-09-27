"""Refuse an installed-runtime qualification that a source checkout can shadow.

A Python environment can look installed and still resolve `app`/`shared`/`config`
from a checkout: an editable install writes a `__editable__*.pth` plus a finder
module into site-packages, and those win over the installed distribution. On this
host the project `.venv` carries exactly that, pointing at the root checkout.

This check is run *before* an installed qualification. It does not modify the
environment it inspects; it only refuses to treat a shadowed run as installed
evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PACKAGES = ("app", "shared", "config", "knowledge_base", "inspiration_research")
EDITABLE_MARKERS = ("__editable__", ".egg-link", ".pth")


def probe_environment(interpreter: Path) -> dict:
    """A neutral environment: no inherited PYTHONPATH, and never the caller's cwd.

    Python puts the current directory on `sys.path` for `-c`, so running this check
    from inside a checkout made every package resolve from that checkout and reported
    a correctly isolated environment as shadowed. The qualification runs *from* the
    runtime, so the probe does too.
    """
    environment = dict(os.environ)
    environment["PYTHONPATH"] = ""
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def run_probe(interpreter: Path, arguments: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(interpreter), *arguments],
        capture_output=True, text=True, encoding="utf-8", check=True,
        cwd=str(interpreter.parent), env=probe_environment(interpreter))


def site_packages(interpreter: Path) -> Path:
    result = run_probe(interpreter, ["-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"])
    return Path(result.stdout.strip())


def editable_entries(site: Path) -> list[str]:
    """Entry files that can register a checkout as an import source."""
    found = []
    if not site.is_dir():
        return found
    for entry in sorted(site.iterdir()):
        if any(marker in entry.name for marker in EDITABLE_MARKERS):
            found.append(entry.name)
    return found


def resolved_origins(interpreter: Path) -> dict:
    script = (
        "import importlib.util, json, sys\n"
        f"names = {list(PACKAGES)!r}\n"
        "out = {}\n"
        "for name in names:\n"
        "    spec = importlib.util.find_spec(name)\n"
        "    out[name] = spec.origin if spec else None\n"
        "print(json.dumps(out))\n"
    )
    result = run_probe(interpreter, ["-c", script])
    return json.loads(result.stdout.strip().splitlines()[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--checkout", action="append", default=[], type=Path,
                        help="checkout root that must not appear in any resolution")
    args = parser.parse_args()

    interpreter = args.python.resolve()
    checkouts = [path.resolve() for path in args.checkout]
    report: dict = {"interpreter": str(interpreter), "checkouts": [str(p) for p in checkouts]}
    site = site_packages(interpreter)
    report["site_packages"] = str(site)
    report["editable_entries"] = editable_entries(site)
    report["origins"] = resolved_origins(interpreter)

    shadowed = []
    for name, origin in report["origins"].items():
        if origin is None:
            continue
        resolved = Path(origin).resolve()
        for checkout in checkouts:
            if resolved.is_relative_to(checkout):
                shadowed.append(f"{name} -> {resolved}")
    report["shadowed"] = shadowed

    # An editable marker is only fatal when a package actually resolves through it;
    # an unrelated `.pth` (coloredlogs, pywin32, distutils-precedence) is not.
    report["verdict"] = "REFUSED" if shadowed else "ISOLATED"
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if shadowed:
        print("installed qualification refused: the environment resolves packages "
              "from a checkout", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
