'''The durable chain receipt must correspond to a commit that really exists in this history.

W32/Q41: a status and its evidence correspond, one to one. A receipt naming a commit that has been
rebased away, or a tree that is not that commit's tree, is a status whose evidence does not reach it
- which is the same failure as citing an old pull request for a regression nobody re-ran.
'''

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs/current/receipts/LIVE-CHAIN-RECEIPTS.json"
EXPECTED_SCOPES = {
    "conversion": "real_conversion_probe",
    "learning": "real_learning_chain_probe",
}


def _receipt() -> dict:
    assert RECEIPT.is_file(), f"the durable receipt is missing: {RECEIPT}"
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True)
    return done.stdout.strip()


def test_the_receipt_declares_its_schema_and_the_commit_it_ran_against() -> None:
    receipt = _receipt()
    assert receipt["schema"] == "archeaxis.live-chain-receipts/v1", receipt["schema"]
    assert len(receipt["commit"]) == 40, receipt["commit"]
    assert len(receipt["tree"]) == 40, receipt["tree"]
    # A receipt that claimed a clean tree while the run that made it had none would be a lie, and
    # the field is here so the claim can be read rather than assumed.
    assert "worktree_state" in receipt, receipt


def test_the_named_commit_exists_and_its_tree_is_the_recorded_tree() -> None:
    receipt = _receipt()
    commit = receipt["commit"]
    assert _git("cat-file", "-e", f"{commit}^{{commit}}") != "" or _git(
        "rev-parse", "--verify", f"{commit}^{{commit}}"
    ), f"the receipt names a commit that is not in this repository: {commit}"
    assert _git("rev-parse", f"{commit}^{{tree}}") == receipt["tree"], (
        "the recorded tree is not the tree of the recorded commit")


def test_the_named_commit_is_in_this_history() -> None:
    '''Evidence from a branch nobody can reach is not evidence for this line of work.'''
    receipt = _receipt()
    done = subprocess.run(
        ["git", "merge-base", "--is-ancestor", receipt["commit"], "HEAD"], cwd=str(ROOT)
    )
    assert done.returncode == 0, (
        f"the receipt names {receipt['commit']}, which is not an ancestor of HEAD")


def test_both_chains_are_ok_and_still_declare_their_scope() -> None:
    receipt = _receipt()
    for name, scope in EXPECTED_SCOPES.items():
        chain = receipt["chains"][name]
        assert chain["ok"] is True, (name, chain)
        assert chain["failed_step"] is None, (name, chain)
        assert chain["scope"] == scope, (name, chain["scope"])
        statuses = [row["status"] for row in chain["steps"]]
        assert statuses, name
        assert all(200 <= status < 300 for status in statuses), (name, statuses)


def test_the_conversion_receipt_still_declines_to_claim_the_loop() -> None:
    chain = _receipt()["chains"]["conversion"]
    assert chain["closed_loop_verified"] is False, (
        "the conversion chain must not be recorded as a verified loop")


def test_the_learning_receipt_still_excludes_human_review() -> None:
    chain = _receipt()["chains"]["learning"]
    assert chain["not_covered"] == ["human knowledge review"], chain["not_covered"]
