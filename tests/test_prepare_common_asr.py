"""Asset preparation regressions with synthetic bytes; never ASR/model qualification."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import io

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def module():
    spec = importlib.util.spec_from_file_location("prepare_common_asr", ROOT / "scripts/ci/prepare_common_asr.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_assets(module, monkeypatch, project):
    pin = module.load_pin()
    payloads = {name: ("SYNTHETIC_IDENTITY_ONLY:" + name).encode() for name in pin["components"]}
    payloads.update({"jfk.flac": b"fLaC_SYNTHETIC_NOT_AUDIO", "LICENSE": b"synthetic license identity",
                     "upstream-test_transcribe.py.txt": b"synthetic source identity"})
    def expected(raw, with_blob=False):
        result = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        if with_blob:
            result["git_blob"] = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        return result
    for name in pin["components"]:
        pin["components"][name] = expected(payloads[name])
    pin["model_bytes"] = sum(item["bytes"] for item in pin["components"].values())
    pin["fixture"].update(expected(payloads["jfk.flac"], True))
    for name, asset in pin["fixture"]["evidence_assets"].items():
        asset.update(expected(payloads[name], True))
    lock = project / ".project-local" / "synthetic.lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_text(json.dumps(pin), encoding="utf-8")
    monkeypatch.setattr(module, "LOCK", lock)
    calls = []
    def download(url, path, pin):
        calls.append(url)
        path.write_bytes(payloads[path.name])
        return module.check_asset(path, pin)
    monkeypatch.setattr(module, "download", download)
    return payloads, calls


def test_production_pin_preserves_identical_public_weights_and_speech_identity(module):
    pin = module.load_pin()
    assert pin["revision"] == "0c94664816ec82be77b20e824c8e8675995b0029"
    assert pin["repo_id"] == "dropbox-dash/faster-whisper-large-v3-turbo"
    assert sum(item["bytes"] for item in pin["components"].values()) == 1621665983
    assert set(pin["components"]) == {"model.bin", "config.json", "tokenizer.json", "preprocessor_config.json", "vocabulary.json"}
    assert pin["components"]["model.bin"]["sha256"] == "e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da"
    assert pin["fixture"]["sha256"] == "63a4b1e4c1dc655ac70961ffbf518acd249df237e5a0152faae9a4a836949715"
    assert pin["fixture"]["git_blob"] == "e44b7c13897eae7f78beb220c61fe77429a3961d"
    assert set(pin["fixture"]["evidence_assets"]) == {"LICENSE", "upstream-test_transcribe.py.txt"}


@pytest.mark.parametrize("value", ["E:/blocked/assets", "F:/blocked/assets", "\\\\host/share/assets", "//host/share/assets"])
def test_protected_path_is_refused_before_filesystem_access(module, monkeypatch, value):
    def forbidden(*args, **kwargs):
        raise AssertionError("Filesystem access must not occur")
    monkeypatch.setattr(Path, "lstat", forbidden)
    with pytest.raises(ValueError, match="Protected path"):
        module.lexical_path(value)


def test_existing_unknown_root_is_not_reused(module, tmp_path, monkeypatch):
    root = tmp_path / ".project-local" / "unknown"
    root.mkdir(parents=True)
    original = root / "owner-file"
    original.write_bytes(b"keep")
    monkeypatch.setattr(module, "download", lambda *args: pytest.fail("Download must not start"))
    with pytest.raises(ValueError, match="Existing root refused"):
        module.prepare(root, tmp_path)
    assert original.read_bytes() == b"keep"


def test_model_without_preparation_receipt_is_not_qualified(module, tmp_path):
    model = tmp_path / ".project-local" / "unknown" / "model"
    model.mkdir(parents=True)
    with pytest.raises(ValueError, match="Successful prepared model receipt"):
        module.validate_prepared_model(model, tmp_path)


def test_complete_preparation_is_identity_only_with_explicit_offline_environment(module, tmp_path, monkeypatch):
    _, calls = synthetic_assets(module, monkeypatch, tmp_path)
    root = tmp_path / ".project-local" / "assets"
    receipt = module.prepare(root, tmp_path)
    assert receipt["ok"] and len(calls) == 8
    assert receipt["qualification"] == "PUBLIC_ASSET_IDENTITY_VERIFIED_ASR_CORE_NOT_EXECUTED"
    assert receipt["offline_environment"]["HF_HUB_OFFLINE"] == "1"
    assert receipt["offline_environment"]["TRANSFORMERS_OFFLINE"] == "1"
    verified = module.validate_prepared_model(root / "model", tmp_path)
    assert verified["members"] == receipt["members"] and verified["prepared_public_assets"]
    assert (root / "fixture/LICENSE").is_file() and (root / "fixture/upstream-test_transcribe.py.txt").is_file()


def test_bad_download_fails_without_upgrading_qualification(module, tmp_path, monkeypatch):
    payloads, _ = synthetic_assets(module, monkeypatch, tmp_path)
    payloads["tokenizer.json"] = b"corrupted"
    root = tmp_path / ".project-local" / "failed"
    receipt = module.prepare(root, tmp_path)
    assert not receipt["ok"] and receipt["qualification"] == "NOT_EXECUTED"
    with pytest.raises(ValueError, match="Successful prepared model receipt"):
        module.validate_prepared_model(root / "model", tmp_path)


@pytest.mark.parametrize("damage", ["component", "extra", "receipt", "transcript", "license", "provenance"])
def test_prepared_assets_cannot_be_modified_after_receipt(module, tmp_path, monkeypatch, damage):
    synthetic_assets(module, monkeypatch, tmp_path)
    root = tmp_path / ".project-local" / "assets"
    assert module.prepare(root, tmp_path)["ok"]
    if damage == "component":
        path = root / "model/model.bin"
        path.write_bytes(b"X" * path.stat().st_size)
    elif damage == "extra":
        (root / "model/unknown-file").write_bytes(b"unselected")
    elif damage == "receipt":
        receipt = json.loads((root / "receipt.json").read_text())
        receipt["revision"] = "main"
        (root / "receipt.json").write_text(json.dumps(receipt))
    else:
        name = {"transcript": "transcript.txt", "license": "LICENSE", "provenance": "provenance.json"}[damage]
        (root / "fixture" / name).write_bytes(b"tampered")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        module.validate_prepared_model(root / "model", tmp_path)


def test_link_or_windows_reparse_point_is_rejected_without_following(module, tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "lstat", lambda self: SimpleNamespace(st_mode=0, st_file_attributes=0x400))
    with pytest.raises(ValueError, match="Linked path"):
        module.no_link(tmp_path / "model.bin")


def test_stream_download_refuses_bytes_above_exact_pin(module, tmp_path, monkeypatch):
    class Response(io.BytesIO):
        def geturl(self):
            return "https://huggingface.co/fixed/asset"
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *args, **kwargs: Response(b"oversize"))
    with pytest.raises(ValueError, match="Asset download budget exceeded"):
        module.download("https://huggingface.co/fixed/asset", tmp_path / "download", {"bytes": 2, "sha256": "0" * 64})


def test_prepared_probe_branch_retains_the_original_shared_identity_check(module, tmp_path, monkeypatch):
    synthetic_assets(module, monkeypatch, tmp_path)
    root = tmp_path / ".project-local" / "assets"
    assert module.prepare(root, tmp_path)["ok"]
    source = (ROOT / "scripts/probes/aaos01_common_speech_runtime_loop.py").read_text(encoding="utf-8")
    function = "def declared_model(model):" + source.split("def declared_model(model):", 1)[1].split("\ndef generate_speech", 1)[0]
    addition = ("    prepared=office.load('speech_prepared_assets',REPO/'scripts/ci/prepare_common_asr.py')\n"
                "    selected=prepared.lexical_path(model)\n"
                "    if selected.is_relative_to(REPO/'.project-local'):\n"
                "        return prepared.validate_prepared_model(selected,REPO)\n")
    if addition not in function:
        function = function.replace("def declared_model(model):\n", "def declared_model(model):\n" + addition)
    namespace = {"Path": Path, "REPO": tmp_path, "json": json,
                 "office": SimpleNamespace(load=lambda *args: module)}
    exec(compile(function, "minimal-speech-prepared-model-patch", "exec"), namespace)
    assert namespace["declared_model"](root / "model")["prepared_public_assets"]
    registry = tmp_path / "config/environment/external-resources-index.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"resource_id": "ext.models.faster-whisper-large-v3-turbo",
                                    "resolved_absolute": str(tmp_path / "declared-shared-model")}))
    with pytest.raises(AssertionError, match="exact project-declared local ASR resource"):
        namespace["declared_model"](tmp_path / "unselected-model")
