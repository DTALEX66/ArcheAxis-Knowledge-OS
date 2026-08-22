from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "reports" / "release" / "v0.6.7" / "release-evidence.json"

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
