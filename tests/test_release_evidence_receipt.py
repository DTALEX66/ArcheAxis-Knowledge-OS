from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_current_reports import load_release_evidence

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "reports" / "release" / "v0.6.7" / "release-evidence.json"
V0614_RECEIPT = ROOT / "reports" / "release" / "v0.6.14" / "release-evidence.json"

EXPECTED_ASSETS = {
    "ArcheAxis.Knowledge-v0.6.7-Windows-x64-Green.zip",
    "ArcheAxis.Knowledge-v0.6.7-Windows-x64-Portable.zip",
    "ArcheAxis.Knowledge-v0.6.7-Windows-x64-Setup.exe",
    "archeaxis_workspace-0.6.7-py3-none-any.whl",
    "release-identity.json",
    "release-manifest.json",
    "SBOM.cdx.json",
    "SHA256SUMS.txt",
    "THIRD_PARTY_NOTICES.txt",
}


def test_v067_release_receipt_binds_distinct_runs_and_all_public_assets() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema_version"] == "archeaxis.release-evidence.v1"
    assert receipt["release"] == {
        "tag": "v0.6.7",
        "version": "0.6.7",
        "channel": "stable",
        "public": True,
        "draft": False,
        "prerelease": False,
        "published_at": "2026-08-22T21:50:57Z",
        "url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.7",
    }
    assert receipt["source"] == {
        "commit_sha": "347d9f957b0509185df8c64e0578061a1ce2f9e3",
        "tree_sha": "ad150aad19c1ebe2766c3c1954ded8e5edd49b13",
    }
    assert receipt["runs"]["verification_ci"]["id"] == 32599003326
    assert receipt["runs"]["verification_ci"]["conclusion"] == "success"
    assert receipt["runs"]["release"]["id"] == 32599851308
    assert receipt["runs"]["release"]["conclusion"] == "success"
    assert (
        receipt["runs"]["verification_ci"]["id"]
        != receipt["runs"]["release"]["id"]
    )

    assets = receipt["assets"]
    assert {asset["name"] for asset in assets} == EXPECTED_ASSETS
    assert len(assets) == len(EXPECTED_ASSETS)
    assert all(asset["size"] > 0 for asset in assets)
    assert all(
        len(asset["sha256"]) == 64
        and set(asset["sha256"]) <= set("0123456789abcdef")
        for asset in assets
    )
    assert receipt["verification"]["provider_digest_match"] is True
    assert receipt["verification"]["downloaded_sha256_match"] is True
    assert receipt["verification"]["checksum_payload_count"] == 8


def test_v067_release_receipt_records_all_dependency_lock_hashes() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert receipt["dependency_locks"] == {
        "uv.lock": "b4500bd574c22b720d0be74bdb108172d129e9e8ece9c75ac3db52d3af3ba626",
        "frontend/package-lock.json": "977f64eccc7e4d1550d9cbc6b6abf9f88bae6f5b047df90a8eff46f70bf29d41",
        "src-tauri/Cargo.lock": "f4f317f1da8bba0f0a640225c28a9a93f589fecb3ac51c193c6ca9ae0edf2cd2",
    }
    assert receipt["limitations"] == [
        "This receipt proves the v0.6.7 release and named lifecycle/readback gates only.",
        "It does not promote incomplete product capabilities or deferred roadmap items.",
    ]


def test_v0614_release_receipt_binds_readback_to_its_exact_tag_and_runs() -> None:
    receipt = load_release_evidence(V0614_RECEIPT)

    assert receipt["release"]["tag"] == "v0.6.14"
    assert receipt["source"] == {
        "commit_sha": "c202c5b5a4789f0dc21accaa7ccbfed4676f0573",
        "tree_sha": "8150692f81883f647806bdb234cedf7d20b31aa1",
    }
    assert receipt["runs"]["verification_ci"]["id"] == 33261549586
    assert receipt["runs"]["release"]["id"] == 33262172637
    assert receipt["runs"]["verification_ci"]["conclusion"] == "success"
    assert receipt["runs"]["release"]["conclusion"] == "success"
    assert {asset["name"] for asset in receipt["assets"]} == {
        "ArcheAxis.Knowledge-v0.6.14-Windows-x64-Green.zip",
        "ArcheAxis.Knowledge-v0.6.14-Windows-x64-Portable.zip",
        "ArcheAxis.Knowledge-v0.6.14-Windows-x64-Setup.exe",
        "archeaxis_workspace-0.6.14-py3-none-any.whl",
        "release-identity.json",
        "release-manifest.json",
        "SBOM.cdx.json",
        "SHA256SUMS.txt",
        "THIRD_PARTY_NOTICES.txt",
    }


def test_v068_release_receipt_binds_exact_main_ci_release_and_assets() -> None:
    receipt_path = (
        ROOT / "reports" / "release" / "v0.6.8" / "release-evidence.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_assets = {
        "ArcheAxis.Knowledge-v0.6.8-Windows-x64-Green.zip": (
            223972334,
            "9a7b6c70fce906203a7474f56794784e8dc8b6a6a2ff1d8541f4469e89c1411b",
        ),
        "ArcheAxis.Knowledge-v0.6.8-Windows-x64-Portable.zip": (
            224115986,
            "173c0b7a5e5bc8062faabb760fe686909eb9a2b029c21cbfb8e08e6b17ace019",
        ),
        "ArcheAxis.Knowledge-v0.6.8-Windows-x64-Setup.exe": (
            154349543,
            "132d40a70f2ee1c82a1e57285aa7de57d987a3427d9d0c81952d76e4bc6fa3fc",
        ),
        "archeaxis_workspace-0.6.8-py3-none-any.whl": (
            1068019,
            "0cd48e51340882543b1c4259ec28a18c99d913195aceccaea6aea058e4724667",
        ),
        "release-identity.json": (
            1811,
            "e721f4ec63e03497c4f7ad412ea41b35992becaf49c0f40303f80d7a1785e28d",
        ),
        "release-manifest.json": (
            1694,
            "2fa2df150cbab003f2a270d8e0570e4ab152693bd3529c20f69dc315ee717644",
        ),
        "SBOM.cdx.json": (
            90760,
            "a774cb6ef31f2b9ddc61aefe0e450310e3345880ca093bbb3063b346c7b88296",
        ),
        "SHA256SUMS.txt": (
            811,
            "7fe4e0694720d2edf9a0cae602a25a67c4d08f759c74a9263a5ac86a74cf3ee7",
        ),
        "THIRD_PARTY_NOTICES.txt": (
            26764,
            "4ed609a56d846bda3f2bd55948cd6b7096319ea68a41b8845317bc8e4141fb47",
        ),
    }

    assert receipt["release"] == {
        "tag": "v0.6.8",
        "version": "0.6.8",
        "channel": "stable",
        "public": True,
        "draft": False,
        "prerelease": False,
        "published_at": "2026-08-23T00:45:26Z",
        "url": "https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/releases/tag/v0.6.8",
    }
    assert receipt["source"] == {
        "commit_sha": "93e58a3b2c537dd348903dd2296933e0cfb5a503",
        "tree_sha": "545eaa7ef62bab9e92e55a9ef598012bb368680a",
    }
    assert receipt["runs"]["verification_ci"]["id"] == 32607097436
    assert receipt["runs"]["release"]["id"] == 32607789507
    assert receipt["runs"]["verification_ci"]["id"] != receipt["runs"]["release"]["id"]
    assert {
        asset["name"]: (asset["size"], asset["sha256"])
        for asset in receipt["assets"]
    } == expected_assets
    assert receipt["verification"] == {
        "provider_digest_match": True,
        "downloaded_sha256_match": True,
        "public_asset_count": 9,
        "checksum_payload_count": 8,
        "identity_schema_version": "3.0.0",
        "three_distribution_lifecycle": "PASS",
    }
    assert receipt["dependency_locks"] == {
        "uv.lock": "726b49e66de4f52b48beb9a15bd5dc088183118dbbc455029ee55ee3e1b87ff4",
        "frontend/package-lock.json": "19acd38d57620ab1ded9b02aeb4245eea1d6742e91d9d1eaba47e31a9a44e2f2",
        "src-tauri/Cargo.lock": "2568f8eb0c2949f28591089f6e89c9aae958c699c64c63a89ba1c8f8cb226cd4",
    }
