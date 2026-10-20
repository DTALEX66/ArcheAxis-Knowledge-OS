"""Source-digest false positives must never become a receipt-wide waiver."""
import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

from scripts.maintenance.authority_routes import REGISTRY, public_path, resolve

ROOT = Path(__file__).resolve().parents[2]


def proof_and_rule():
    proof = json.loads((ROOT / "docs/history/repository-consolidation-20261019/current/receipts/GITLEAKS-SOURCE-DIGEST-AUDIT-20261010.json").read_text(encoding="utf-8"))
    config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
    rule = next(row for row in config["allowlists"]
                if row["description"] == "exact verified receipt source digests")
    return proof, rule


# Finding commits remain immutable evidence locators. These two pre-rebase commits
# have byte-identical trees in current reachable history; CI need not fetch orphans.
REACHABLE_SOURCE_IDENTITIES = {
    "3855f2bb032e69dd10e9ef94d854b0ac8640f137": (
        "88c47a5c32b13351b6642403970b80e53c9954ae",
        "d6a4d027b24f51c0ef0f2a7cd606016e4d722671",
        "crates/archeaxis-api/tests/configuration_plans_api.rs",
        "1faa7429c7b4b7c46ba2888c01ba34bcd9f95f7b50de4e777e2f2aae2edc3ae3",
    ),
    "110fc9d05d4ad46e77c8f339991a31204f79c3b4": (
        "fd32ae1302b0a06193ea5fa9de8d94295f0e7a9f",
        "8b0b2c6027d14dc1893a74741938a39e0868c834",
        "crates/archeaxis-api/tests/character_memory_api.rs",
        "32779d275e481f45155191cd0bb4a3b4fe204927fb69394c6c8b65daa0983a45",
    ),
}


def committed_source(row):
    identity = REACHABLE_SOURCE_IDENTITIES.get(row["Commit"])
    commit = row["Commit"]
    if identity is not None:
        commit, tree, path, digest = identity
        assert row["source_path"] == path
        assert row["source_sha256"] == digest
        actual_tree = subprocess.check_output(
            ["git", "rev-parse", commit + "^{tree}"], cwd=ROOT
        ).decode("ascii").strip()
        assert actual_tree == tree
    # An orphan object retained by this machine cannot qualify the proof.
    subprocess.check_output(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT)
    return subprocess.check_output(["git", "show", commit + ":" + row["source_path"]], cwd=ROOT)


def test_every_receipt_exception_is_an_actual_committed_public_file_digest():
    proof, rule = proof_and_rule()
    assert rule["condition"] == "AND"
    assert rule["targetRules"] == ["generic-api-key"]
    assert rule["regexTarget"] == "secret"
    assert len(proof["findings"]) == 22
    for row in proof["findings"]:
        raw = committed_source(row)
        assert hashlib.sha256(raw).hexdigest() == row["source_sha256"]
        # File is the historical finding locator, while the current scan sees its archive path.
        routes = json.loads(public_path(ROOT, REGISTRY).read_text(encoding="utf-8"))
        identity = resolve(row["File"], routes, ROOT)
        assert identity["role"] == "RETIRED_LOCATOR", identity
        canonical = identity["canonical_path"]
        assert canonical.startswith("docs/history/repository-consolidation-20261019/current/receipts/")
        assert public_path(ROOT, canonical).is_file(), canonical
        assert any(re.fullmatch(pattern, row["File"]) for pattern in rule["paths"])
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


# Each new row is an identified public JSON digest field, not an arbitrary hex waiver.
REVIEWED_EVIDENCE_DIGESTS = [
    ('verified material-question test source digest',
     'f8e69401363eccd634e9b2ce3a669516630d0f5b42dc00a72b207be4a2374d2f', [
         'docs/current/receipts/AAOS-MACHINE-DEADLINE-20261019.json',
         'docs/history/repository-consolidation-20261019/current/receipts/AAOS-MACHINE-DEADLINE-20261019.json',
         'docs/history/oss-absorption-evidence/20261019-machine-deadline/MANIFEST.json',
         'docs/history/oss-absorption-evidence/20261019-machine-deadline/RECEIPT.json',
     ]),
    ('verified conversation test source digest',
     'f4f036ecbe4149aaa31cdcb253fc7f4a4eaf6c8a5a1c63f315140632392f1988', [
         'docs/current/receipts/AAOS-REVIEW-CANCELLATION-20261019.json',
         'docs/history/repository-consolidation-20261019/current/receipts/AAOS-REVIEW-CANCELLATION-20261019.json',
         'docs/history/oss-absorption-evidence/20261019-review-cancellation/MANIFEST.json',
         'docs/history/oss-absorption-evidence/20261019-review-cancellation/RECEIPT.json',
         'docs/history/oss-absorption-evidence/20261019-review-cancellation/source-identities.json',
     ]),
    ('verified learning-state test source digest',
     '0555193f4b9aa3d0c40473029f3c37cc600ee81494f84e95816d5e430ec3143e', [
         'docs/current/receipts/AAOS-REVIEW-TITLE-20261019.json',
         'docs/history/repository-consolidation-20261019/current/receipts/AAOS-REVIEW-TITLE-20261019.json',
         'docs/history/oss-absorption-evidence/20261019-review-title/MANIFEST.json',
         'docs/history/oss-absorption-evidence/20261019-review-title/RECEIPT.json',
     ]),
    ('frozen public OpenAPI candidate digest',
     'a02f211226733e8ead395a080395c9165cddefc051d8bcd6d5d7673e0e905e09', [
         'docs/history/oss-absorption-evidence/20261019-checkout-and-measurement/measurement/CANDIDATE-HASHES.json',
     ]),
    ('verified historical readiness test source digest',
     '7191ad414ea5ba210088f7b3b30d76ceee6247ca34a2c0370a80582aa58b66ee', [
         'docs/history/oss-absorption-evidence/20261019-continuity-native-pdf/pdf/FINAL-VERIFICATION.json',
     ]),
    ('verified public machine-deadline regression log digest',
     '18662aaea3db5e1fcd3fe97c18121db33d27023a4c62e66a9c98e78940091692', [
         'docs/history/oss-absorption-evidence/20261019-machine-deadline/MANIFEST.json',
     ]),
]


def scoped_evidence_rules():
    config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
    return [row for row in config["allowlists"] if row.get("condition") == "AND"]


def scoped_waives(path, value):
    return any(any(re.fullmatch(pattern, path) for pattern in row["paths"])
               and any(re.fullmatch(pattern, value) for pattern in row["regexes"])
               for row in scoped_evidence_rules())


def test_existing_context_uuid_and_model_exceptions_keep_original_and_archive_paths():
    rules = scoped_evidence_rules()
    for row in rules:
        for pattern in row["paths"]:
            if pattern.startswith("^docs/history/repository-consolidation-20261019/current/receipts/"):
                original = pattern.replace("^docs/history/repository-consolidation-20261019/current/receipts/", "^docs/current/receipts/")
                assert original in row["paths"], row["description"]


def test_new_public_digest_exceptions_pair_exact_values_and_exact_paths():
    rules = {row["description"]: row for row in scoped_evidence_rules()}
    for description, digest, paths in REVIEWED_EVIDENCE_DIGESTS:
        row = rules[description]
        assert row["targetRules"] == ["generic-api-key"]
        assert row["regexTarget"] == "secret"
        assert row["regexes"] == ["^" + digest + "$"]
        assert set(row["paths"]) == {"^" + re.escape(path) + "$" for path in paths}
        for path in paths:
            assert scoped_waives(path, digest)
            current = path.replace("docs/current/receipts/", "docs/history/repository-consolidation-20261019/current/receipts/")
            # Read the public JSON evidence only. The fixed exact digest must still be present.
            value = json.loads((ROOT / current).read_text(encoding="utf-8"))
            def contains_digest(candidate):
                if isinstance(candidate, dict):
                    return any(contains_digest(item) for item in candidate.values())
                if isinstance(candidate, list):
                    return any(contains_digest(item) for item in candidate)
                return candidate == digest
            assert contains_digest(value), current


def test_scoped_digest_exceptions_reject_bad_values_and_unreviewed_paths():
    changed = hashlib.sha256(b"synthetic unreviewed credential-shaped digest").hexdigest()
    paths = {path for _, _, names in REVIEWED_EVIDENCE_DIGESTS for path in names}
    for path in paths:
        assert not scoped_waives(path, changed)
        assert not scoped_waives(path, changed + "\n")
    for _, digest, _ in REVIEWED_EVIDENCE_DIGESTS:
        for path in ("docs/current/receipts/UNREVIEWED.json",
                     "docs/history/repository-consolidation-20261019/current/receipts/UNREVIEWED.json",
                     "docs/history/unreviewed/RECEIPT.json", "app/credential-adapter.py"):
            assert not scoped_waives(path, digest)


def test_receipt_digest_proof_does_not_require_unreachable_finding_commits(monkeypatch):
    """A full checkout fetches current history, not abandoned pre-rebase commits."""
    original = subprocess.check_output
    unavailable = {
        "3855f2bb032e69dd10e9ef94d854b0ac8640f137",
        "110fc9d05d4ad46e77c8f339991a31204f79c3b4",
    }

    def current_history_only(command, **kwargs):
        if command[:2] == ["git", "show"] and command[2].split(":", 1)[0] in unavailable:
            raise subprocess.CalledProcessError(128, command)
        return original(command, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", current_history_only)
    test_every_receipt_exception_is_an_actual_committed_public_file_digest()


@pytest.mark.parametrize("field,value", [
    ("source_path", "crates/archeaxis-api/tests/unreviewed.rs"),
    ("source_sha256", "0" * 64),
])
def test_reachable_source_identity_rejects_changed_path_or_digest(field, value):
    proof, _ = proof_and_rule()
    for original in proof["findings"][-2:]:
        row = dict(original, **{field: value})
        with pytest.raises(AssertionError):
            committed_source(row)


def test_reachable_source_identity_rejects_wrong_tree(monkeypatch):
    proof, _ = proof_and_rule()
    original = subprocess.check_output

    def wrong_tree(command, **kwargs):
        if command[:2] == ["git", "rev-parse"]:
            return b"0" * 40 + b"\n"
        return original(command, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", wrong_tree)
    for row in proof["findings"][-2:]:
        with pytest.raises(AssertionError):
            committed_source(row)


def test_reachable_source_identity_rejects_unreachable_commit(monkeypatch):
    proof, _ = proof_and_rule()
    original = subprocess.check_output

    def unreachable(command, **kwargs):
        if command[:3] == ["git", "merge-base", "--is-ancestor"]:
            raise subprocess.CalledProcessError(1, command)
        return original(command, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", unreachable)
    for row in proof["findings"][-2:]:
        with pytest.raises(subprocess.CalledProcessError):
            committed_source(row)
