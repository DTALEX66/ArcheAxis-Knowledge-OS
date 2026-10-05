"""Prepare pinned OCR only in a project-local Windows job directory."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import urllib.request

PIN = json.loads(Path(__file__).with_name("windows_ocr.lock.json").read_text(encoding="utf8"))
FIXTURE_SHA = "050538c71fc63ee2d0e8327f2fbdffad6f8cab135d35069aa86dc371300f68c8"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def no_link(path):
    for item in (path, *path.parents):
        if item.exists():
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Linked path rejected")


def download(url, path, expected, maximum):
    request = urllib.request.Request(url, headers={"User-Agent": "ArcheAxis-CI-OCR/1"})
    with urllib.request.urlopen(request, timeout=60) as response, path.open("xb") as output:
        final = response.geturl()
        if not final.startswith(
            (
                "https://github.com/",
                "https://release-assets.githubusercontent.com/",
                "https://raw.githubusercontent.com/",
            )
        ):
            raise ValueError("Unexpected download host")
        total = 0
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > maximum:
                raise ValueError("Download budget exceeded")
            output.write(chunk)
    if not total or sha(path) != expected:
        raise ValueError("Download SHA mismatch")


def run(command, env=None):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=env,
    )
    if result.returncode:
        raise RuntimeError("OCR/tool process failed")
    if len(result.stdout) > 1024 * 1024 or len(result.stderr) > 1024 * 1024:
        raise ValueError("Tool output budget exceeded")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--sevenzip", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    project = args.project_root.absolute()
    root = args.root.absolute()
    tool = args.sevenzip.absolute()
    if not root.is_relative_to(project / ".project-local") or root == project / ".project-local":
        raise ValueError("Root must be a dedicated project-local child")
    for path in (project, root, tool):
        no_link(path)
    if root.exists():
        raise ValueError("Existing root refused; choose a new owned run directory")
    if not tool.is_file():
        raise ValueError("Explicit existing 7zip executable required")
    root.mkdir(parents=True, exist_ok=False)
    receipt = {
        "ok": False,
        "scope": "PROJECT_ONLY_OCR_NO_INSTALLER_EXECUTION_NO_REGISTRY_OR_MACHINE_PATH",
        "pins": PIN,
        "sevenzip_sha256": sha(tool),
        "root": str(root),
    }
    try:
        archive = root / "tesseract-5.5.0.20241111.exe"
        download(PIN["source_url"], archive, PIN["installer_sha256"], 32 * 1024 * 1024)
        expected = {x["name"]: x for x in PIN["local_dlls"]}
        expected["tesseract.exe"] = {"sha256": PIN["binary_sha256"]}
        if len(expected) != 57:
            raise ValueError("Expected exact 57 engine files")
        listing = run([str(tool), "l", "-slt", str(archive)]).stdout
        selected = {}
        for block in re.split(r"\r?\n\r?\n", listing):
            fields = dict(line.split(" = ", 1) for line in block.splitlines() if " = " in line)
            name = fields.get("Path")
            if name not in expected:
                continue
            if name in selected or "/" in name or "\\" in name or ":" in name:
                raise ValueError("Unsafe/duplicate selected member")
            if (
                fields.get("Folder") == "+"
                or fields.get("Symbolic Link")
                or fields.get("Hard Link")
            ):
                raise ValueError("Selected link/directory")
            size = int(fields.get("Size", "0"))
            if size <= 0 or size > 64 * 1024 * 1024:
                raise ValueError("Selected extraction size budget")
            if "bytes" in expected[name] and size != expected[name]["bytes"]:
                raise ValueError("Selected listed bytes mismatch")
            selected[name] = fields
        if set(selected) != set(expected):
            raise ValueError("Installer exact member list mismatch")
        if sum(int(x["Size"]) for x in selected.values()) > 128 * 1024 * 1024:
            raise ValueError("Selected total extraction budget")
        engine = root / "engine"
        engine.mkdir()
        run([str(tool), "e", str(archive), "-o" + str(engine), "-y", *sorted(expected)])
        names = set()
        extracted = {}
        for item in engine.iterdir():
            no_link(item)
            if not item.is_file():
                raise ValueError("Unexpected extracted directory")
            names.add(item.name)
            if item.name not in expected or sha(item) != expected[item.name]["sha256"]:
                raise ValueError("Extracted engine SHA mismatch")
            if item.stat().st_size <= 0:
                raise ValueError("Empty extracted binary")
            extracted[item.name] = {"sha256": sha(item), "bytes": item.stat().st_size}
        if (
            names != set(expected)
            or sum(x["bytes"] for x in extracted.values()) > 128 * 1024 * 1024
        ):
            raise ValueError("Extracted payload budget/members mismatch")
        tessdata = engine / "tessdata"
        tessdata.mkdir()
        eng = tessdata / "eng.traineddata"
        download(PIN["eng_url"], eng, PIN["eng_sha256"], 5 * 1024 * 1024)
        if eng.stat().st_size != PIN["eng_bytes"]:
            raise ValueError("Language data bytes mismatch")
        executable = engine / "tesseract.exe"
        env = dict(os.environ)
        env["TESSDATA_PREFIX"] = str(tessdata)
        version = run([str(executable), "--version"], env).stdout
        if not re.search(r"^tesseract v?5\.5\.0\.20241111\s*$", version, re.MULTILINE):
            raise ValueError("Actual version mismatch")
        langs = run([str(executable), "--list-langs", "--tessdata-dir", str(tessdata)], env).stdout
        if "eng" not in langs.splitlines():
            raise ValueError("English language not available")
        fixture = project / "tests/fixtures/golden/golden-screenshot-ocr.png"
        no_link(fixture)
        if sha(fixture) != FIXTURE_SHA:
            raise ValueError("Known real OCR fixture mismatch")
        actual = run(
            [
                str(executable),
                str(fixture),
                "stdout",
                "--tessdata-dir",
                str(tessdata),
                "-l",
                "eng",
                "--psm",
                "6",
            ],
            env,
        ).stdout
        if "OCR GOLDEN ANCHOR" not in " ".join(actual.split()):
            raise ValueError("Real OCR expected text absent")
        receipt.update(
            ok=True,
            actual_version=version.strip(),
            engine_files=extracted,
            language_sha256=sha(eng),
            fixture_sha256=FIXTURE_SHA,
            ocr_exit_code=0,
            actual_text_sha256=hashlib.sha256(actual.encode()).hexdigest(),
            expected_text_matched=True,
        )
        if github_env := os.environ.get("GITHUB_ENV"):
            no_link(Path(github_env))
            with open(github_env, "a", encoding="utf8") as output:
                output.write(
                    f"TESSERACT_CMD={executable}\nTESSDATA_PREFIX={tessdata}\nARCHEAXIS_OCR_TESSDATA={tessdata}\n"
                )
    except Exception as error:
        receipt["error_type"] = type(error).__name__
        receipt["error"] = str(error)[:200]
    finally:
        (root / "ocr-receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf8")
        print(
            json.dumps(
                {
                    "ok": receipt["ok"],
                    "receipt": str(root / "ocr-receipt.json"),
                    "error": receipt.get("error"),
                }
            )
        )
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
