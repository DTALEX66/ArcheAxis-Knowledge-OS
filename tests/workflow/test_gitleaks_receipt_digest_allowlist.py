"""Source-digest false positives must never become a receipt-wide waiver."""
import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path

from scripts.maintenance.authority_routes import REGISTRY, public_path, resolve

ROOT = Path(__file__).resolve().parents[2]


def proof_and_rule():
    proof = json.loads((ROOT / "docs/history/repository-consolidation-20261019/current/receipts/GITLEAKS-SOURCE-DIGEST-AUDIT-20261010.json").read_text(encoding="utf-8"))
    config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
    rule = next(row for row in config["allowlists"]
                if row["description"] == "exact verified receipt source digests")
    return proof, rule


def test_every_receipt_exception_is_an_actual_committed_public_file_digest():
    proof, rule = proof_and_rule()
    assert rule["condition"] == "AND"
    assert rule["targetRules"] == ["generic-api-key"]
    assert rule["regexTarget"] == "secret"
    assert len(proof["findings"]) == 22
    for row in proof["findings"]:
        raw = subprocess.check_output(["git", "show", row["Commit"] + ":" + row["source_path"]], cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest() == row["source_sha256"]
        # File is the historical finding locator, while the current scan sees its archive path.
        routes = json.loads(public_path(ROOT, REGISTRY).read_text(encoding="utf-8"))
        identity = resolve(row["File"], routes, ROOT)
        assert identity["role"] == "RETIRED_LOCATOR", identity
        canonical = identity["canonical_path"]
        assert canonical.startswith("docs/history/repository-consolidation-20261019/current/receipts/")
        assert public_path(ROOT, canonical).is_file(), canonical
        assert any(re.fullmatch(pattern, canonical) for pattern in rule["paths"])
        assert any(re.fullmatch(pattern, row["source_sha256"]) for pattern in rule["regexes"])


def test_a_different_value_in_the_same_receipt_is_not_waived():
    proof, rule = proof_and_rule()
    different_value = hashlib.sha256(b"synthetic scan-boundary mutation").hexdigest()
    assert different_value not in {row["source_sha256"] for row in proof["findings"]}
    assert not any(re.fullmatch(pattern, different_value) for pattern in rule["regexes"])
    assert not any(re.fullmatch(pattern, "app/credential-adapter.py") for pattern in rule["paths"])


def test_archive_prefix_is_not_a_receipt_wide_waiver():
    _, rule = proof_and_rule()
    assert not any(re.fullmatch(pattern, "docs/history/repository-consolidation-20261019/current/receipts/UNREVIEWED.json") for pattern in rule["paths"])
    assert not any(re.fullmatch(pattern, "docs/history/unreviewed/AAOS-AI-STAGE-20261010.json") for pattern in rule["paths"])
