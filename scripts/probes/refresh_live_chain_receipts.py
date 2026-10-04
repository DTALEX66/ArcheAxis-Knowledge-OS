"""Write one durable receipt for both live chains, bound to the commit they ran against.

The probes print their receipts into a per-run directory under .project-local, which is ignored and
is not kept. That makes every citation of them ephemeral: the evidence exists until the run
directory is cleaned and then the receipt cites a path that is gone. This runs both probes and
records what they proved, with the commit and tree state they ran against, in a tracked file that
survives - and with absolute paths stripped, because where a checkout lives decides nothing.

Run: python scripts/probes/refresh_live_chain_receipts.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGET = REPO / "docs" / "current" / "receipts" / "LIVE-CHAIN-RECEIPTS.json"
PROBES = {
    "conversion": REPO / "scripts" / "probes" / "r10_core_journey_smoke.py",
    "learning": REPO / "scripts" / "probes" / "r10_learning_chain_smoke.py",
}


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True)
    return done.stdout.strip()


def _run(probe: Path) -> dict:
    done = subprocess.run(
        [sys.executable, str(probe)], cwd=str(REPO),
        capture_output=True, text=True, encoding="utf-8", timeout=600,
    )
    rows = [row for row in done.stdout.splitlines() if row.startswith("{")]
    if not rows:
        return {"ok": False, "exited": done.returncode, "reason": "no receipt printed"}
    receipt = json.loads(rows[-1])
    receipt.pop("receipt_path", None)  # a per-run path proves nothing once the run is gone
    return receipt


def main() -> int:
    bundle = {
        "schema": "archeaxis.live-chain-receipts/v1",
        "commit": _git("rev-parse", "HEAD"),
        "tree": _git("rev-parse", "HEAD^{tree}"),
        "worktree_state": _git("status", "--porcelain=v1") or "clean",
        "note": (
            "Produced by scripts/probes/refresh_live_chain_receipts.py against the commit named here. "
            "Both probes drive a REAL Core process over HTTP; path fields are removed because the "
            "checkout location is not evidence."
        ),
        "chains": {name: _run(probe) for name, probe in PROBES.items()},
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = all(chain.get("ok") is True for chain in bundle["chains"].values())
    print(json.dumps({"target": str(TARGET.relative_to(REPO)), "all_chains_ok": ok,
                      "commit": bundle["commit"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
