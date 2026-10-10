"""Prepare exact public ASR assets in a fresh project directory; no package installation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import stat
import urllib.parse
import urllib.request

REPO = Path(__file__).absolute().parents[2]
LOCK = Path(__file__).with_name("common_asr.lock.json")


def load_pin():
    return json.loads(LOCK.read_text(encoding="utf-8"))


def lexical_path(value):
    raw = str(value)
    windows = PureWindowsPath(raw)
    if windows.drive.lower() in ("e:", "f:") or raw.startswith(("\\\\", "//")):
        raise ValueError("Protected path refused before filesystem access")
    path = Path(value)
    if ".." in path.parts:
        raise ValueError("Traversal refused")
    return path.absolute()


def no_link(path):
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked path refused")


def owned_path(value, project):
    path = lexical_path(value)
    project = lexical_path(project)
    if not path.is_relative_to(project / ".project-local") or path == project / ".project-local":
        raise ValueError("Dedicated project-local child required")
    no_link(project)
    no_link(path)
    return path


def identity(path):
    no_link(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def check_asset(path, expected):
    actual = identity(path)
    if actual != {key: expected[key] for key in ("bytes", "sha256")}:
        raise ValueError("Asset bytes/SHA mismatch: " + path.name)
    if "git_blob" in expected:
        raw = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob != expected["git_blob"]:
            raise ValueError("Public asset Git blob mismatch")
    return actual


def download(url, path, expected):
    no_link(path)
    request = urllib.request.Request(url, headers={"User-Agent": "ArcheAxis-CI-ASR/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        final = urllib.parse.urlparse(response.geturl())
        host = final.hostname or ""
        if final.scheme != "https" or not (
            host in ("huggingface.co", "raw.githubusercontent.com")
            or host.endswith((".huggingface.co", ".hf.co"))
        ):
            raise ValueError("Unexpected public asset download host")
        total = 0
        with path.open("xb") as output:
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > expected["bytes"]:
                    raise ValueError("Asset download budget exceeded")
                output.write(block)
    return check_asset(path, expected)


def validate_prepared_model(model, project=REPO):
    model = owned_path(model, project)
    if model.name != "model":
        raise ValueError("Prepared ASR model must use the dedicated model directory")
    pin = load_pin()
    receipt_path = model.parent / "receipt.json"
    no_link(receipt_path)
    if not receipt_path.is_file():
        raise ValueError("Successful prepared model receipt required")
    if receipt_path.stat().st_size > 1024 * 1024:
        raise ValueError("Receipt size budget exceeded")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not receipt.get("ok") or receipt.get("model_path") != str(model):
        raise ValueError("Successful prepared model receipt required")
    if receipt.get("pin_sha256") != identity(LOCK)["sha256"]:
        raise ValueError("Prepared model lock identity changed")
    if receipt.get("resource_id") != pin["resource_id"] or receipt.get("revision") != pin["revision"]:
        raise ValueError("Prepared model resource/revision mismatch")
    entries = list(model.iterdir())
    if {item.name for item in entries} != set(pin["components"]):
        raise ValueError("Prepared model exact component set required")
    members = {name: check_asset(model / name, expected) for name, expected in pin["components"].items()}
    if members != receipt.get("members"):
        raise ValueError("Prepared model receipt bytes changed")
    if {item.name for item in model.parent.iterdir()} != {"model", "fixture", "receipt.json"}:
        raise ValueError("Prepared root exact entry set required")
    fixture = model.parent / "fixture"
    no_link(fixture)
    source = pin["fixture"]
    required = {"jfk.flac", "transcript.txt", "provenance.json", *source["evidence_assets"]}
    if {item.name for item in fixture.iterdir()} != required:
        raise ValueError("Prepared fixture exact entry set required")
    check_asset(fixture / "jfk.flac", source)
    for name, expected in source["evidence_assets"].items():
        check_asset(fixture / name, expected)
    for name in ("transcript.txt", "provenance.json"):
        no_link(fixture / name)
    if (fixture / "transcript.txt").read_text(encoding="utf-8") != source["transcript"] + "\n":
        raise ValueError("Pinned transcript changed")
    if json.loads((fixture / "provenance.json").read_text(encoding="utf-8")) != source:
        raise ValueError("Public speech provenance changed")
    return {"resource_id": pin["resource_id"], "local_only": True,
            "prepared_public_assets": True, "revision": pin["revision"], "members": members}


def prepare(root, project=REPO):
    root = owned_path(root, project)
    if root.exists():
        raise ValueError("Existing root refused; no reuse of unknown assets")
    pin = load_pin()
    if sum(item["bytes"] for item in pin["components"].values()) != pin["model_bytes"]:
        raise ValueError("Exact model total budget mismatch")
    root.mkdir(parents=True, exist_ok=False)
    model = root / "model"
    fixture = root / "fixture"
    model.mkdir()
    fixture.mkdir()
    receipt = {"ok": False, "qualification": "NOT_EXECUTED", "resource_id": pin["resource_id"],
               "revision": pin["revision"], "model_path": str(model), "pin_sha256": identity(LOCK)["sha256"]}
    try:
        base = "https://huggingface.co/" + pin["repo_id"] + "/resolve/" + pin["revision"] + "/"
        receipt["members"] = {name: download(base + name, model / name, expected)
                              for name, expected in pin["components"].items()}
        source = pin["fixture"]
        url = "https://raw.githubusercontent.com/" + source["repository"] + "/" + source["revision"] + "/" + source["path"]
        flac = fixture / "jfk.flac"
        receipt["fixture"] = download(url, flac, source)
        raw = flac.read_bytes()
        if not raw.startswith(b"fLaC"):
            raise ValueError("Public speech FLAC header mismatch")
        receipt["fixture_evidence"] = {name: download(expected["url"], fixture / name, expected)
                                       for name, expected in source["evidence_assets"].items()}
        (fixture / "transcript.txt").write_text(source["transcript"] + "\n", encoding="utf-8")
        (fixture / "provenance.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
        receipt.update(ok=True, qualification="PUBLIC_ASSET_IDENTITY_VERIFIED_ASR_CORE_NOT_EXECUTED",
                       offline_environment={"ARCHEAXIS_ASR_MODEL_DIR": str(model), "HF_HUB_OFFLINE": "1",
                                            "TRANSFORMERS_OFFLINE": "1"})
    except Exception as error:
        receipt["error_type"] = type(error).__name__
        # Avoid publishing signed redirect URLs or transport diagnostics.
        receipt["error"] = "Public asset preparation failed; no ASR qualification granted"
    finally:
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    receipt = prepare(args.root)
    print(json.dumps({"ok": receipt["ok"], "receipt": str(args.root / "receipt.json")}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
