"""Import the R5 HL01 registry into an explicitly selected Core database."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.evidence.hl01_import import import_registry_candidates, verify_registry_receipt
from app.evidence.source_store_v2 import SourceStoreV2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="explicit SQLite database path")
    parser.add_argument("--registry", type=Path, required=True, help="HL01 registry JSON path")
    parser.add_argument("--command-id", required=True, help="stable idempotency key")
    parser.add_argument(
        "--rights-status",
        choices=("owned", "licensed", "public-domain", "permission-recorded"),
        required=True,
        help="explicit rights status for the imported source records",
    )
    parser.add_argument(
        "--created-at",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error(f"database does not exist: {args.db}")
    if not args.registry.is_file():
        parser.error(f"registry does not exist: {args.registry}")
    receipt = import_registry_candidates(
        SourceStoreV2(args.db),
        args.registry,
        created_at=args.created_at,
        rights_status=args.rights_status,
        command_id=args.command_id,
        repository_root=Path(__file__).parents[1],
    )
    output = dict(receipt.__dict__)
    if receipt.command_id is not None:
        output["readback"] = verify_registry_receipt(args.db, receipt.command_id)
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, default=list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
