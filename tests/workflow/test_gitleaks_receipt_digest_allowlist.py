"""Source-digest false positives must never become a receipt-wide waiver."""
import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def proof_and_rule():
    proof = json.loads((ROOT / "docs/current/receipts/GITLEAKS-SOURCE-DIGEST-AUDIT-20261010.json").read_text(encoding="utf-8"))
    config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
    rule = next(row for row in config["allowlists"]
                if row["description"] == "exact verified receipt source digests")
    return proof, rule


def test_every_receipt_exception_is_an_actual_committed_public_file_digest():
    proof, rule = proof_and_rule()
    assert rule["condition"] == "AND"
    assert rule["targetRules"] == ["generic-api-key"]
    assert rule["regexTarget"] == "secret"
    assert len(proof["findings"]) == 20
    for row in proof["findings"]:
        raw = subprocess.check_output(["git", "show", row["Commit"] + ":" + row["source_path"]], cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest() == row["source_sha256"]
        assert any(re.fullmatch(pattern, row["File"]) for pattern in rule["paths"])
        assert any(re.fullmatch(pattern, row["source_sha256"]) for pattern in rule["regexes"])


def test_a_different_value_in_the_same_receipt_is_not_waived():
    proof, rule = proof_and_rule()
    different_value = hashlib.sha256(b"synthetic scan-boundary mutation").hexdigest()
    assert different_value not in {row["source_sha256"] for row in proof["findings"]}
    assert not any(re.fullmatch(pattern, different_value) for pattern in rule["regexes"])
    assert not any(re.fullmatch(pattern, "app/credential-adapter.py") for pattern in rule["paths"])
