"""Fetch the pinned transcript model for packaging only; installed products never download.

The build machine may not have a shared model library, but an installed product must still be
able to answer a media job offline. This script is the one explicit, reproducible donor step:
it downloads the exact `faster-whisper-base` files from one pinned Hugging Face revision,
verifies every byte against a recorded SHA-256 and size, and never overwrites an existing
directory. The runtime staging step copies the verified donor into `runtime/models/asr`,
where the transcribe worker discovers it; no runtime code calls this script or the network.

A failed or absent download fails the build by name. It is not converted into a candidate
that silently ships no model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO_ID = "Systran/faster-whisper-base"
REVISION = "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"
BASE_URL = "https://huggingface.co/{repo}/resolve/{revision}/{name}"
SCHEMA = "archeaxis.asr-model-fetch/v1"
MAX_FILE_BYTES = 256 * 1024 * 1024
FILES = {
    "model.bin": {
        "bytes": 145217532,
        "sha256": "d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9",
    },
    "config.json": {
        "bytes": 2309,
        "sha256": "56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a",
    },
    "tokenizer.json": {
        "bytes": 2203239,
        "sha256": "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
    },
    "vocabulary.txt": {
        "bytes": 459861,
        "sha256": "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
    },
}
LICENSE = {
    "code_license": "MIT",
    "asset_license": "MIT per the Systran/faster-whisper-base model card; the weights are not relicensed by this repository",
    "source_url": "https://huggingface.co/Systran/faster-whisper-base",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, name: str) -> None:
    expected = FILES[name]
    if not path.is_file():
        raise ValueError(f"missing model file: {name}")
    actual_size = path.stat().st_size
    if actual_size != expected["bytes"]:
        raise ValueError(f"model file size mismatch for {name}: {actual_size} != {expected['bytes']}")
    actual_hash = sha256(path)
    if actual_hash != expected["sha256"]:
        raise ValueError(f"model file SHA-256 mismatch for {name}: {actual_hash}")


def fetch_file(url: str, destination: Path, name: str) -> None:
    """Download one file to a temporary sibling, then verify and atomically place it."""
    temporary = destination.with_name(destination.name + ".part")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "archeaxis-build/1"})
        with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as output:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    raise ValueError(f"model file exceeds the download budget: {name}")
                output.write(chunk)
        verify_file(temporary, name)
        if destination.exists():
            raise ValueError(f"refusing to overwrite an existing model file: {destination}")
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def fetch_model(out: Path, receipt: Path | None = None) -> dict:
    out = Path(os.path.abspath(out))
    if out.exists() and not out.is_dir():
        raise ValueError(f"model output is not a directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict[str, object]] = {}
    reused = downloaded = 0
    for name, expected in FILES.items():
        destination = out / name
        if destination.exists():
            verify_file(destination, name)
            files[name] = {"bytes": expected["bytes"], "sha256": expected["sha256"], "state": "PRESENT_VERIFIED"}
            reused += 1
            continue
        url = BASE_URL.format(repo=REPO_ID, revision=REVISION, name=name)
        fetch_file(url, destination, name)
        files[name] = {"bytes": expected["bytes"], "sha256": expected["sha256"], "state": "DOWNLOADED_VERIFIED"}
        downloaded += 1
    result = {
        "schema": SCHEMA,
        "repo": REPO_ID,
        "revision": REVISION,
        "source": f"https://huggingface.co/{REPO_ID}/tree/{REVISION}",
        "directory": str(out),
        "files": files,
        "license": LICENSE,
        "reused": reused,
        "downloaded": downloaded,
        "network_performed": downloaded > 0,
        "runtime_download": False,
        "note": "build-time donor only; the installed product reads the copied runtime model",
    }
    if receipt is not None:
        receipt = Path(os.path.abspath(receipt))
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True,
                        help="directory named exactly as the bundled model, e.g. .../faster-whisper-base")
    parser.add_argument("--receipt", type=Path, help="write the fetch receipt to this path")
    args = parser.parse_args(argv)
    print(json.dumps(fetch_model(args.out, args.receipt), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
